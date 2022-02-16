import os
from typing import List
from jpype import JArray, JDouble
import numpy as np
from napari.layers import Labels, Shapes
from napari_imagej import _ntypes
from scyjava import Converter, Priority, jimport, add_py_converter, add_java_converter
from labeling.Labeling import Labeling


def _delete_labeling_files(filepath):
    """
    Removes any Labeling data left over at filepath
    :param filepath: the filepath where Labeling (might have) saved data
    """
    pth_bson = filepath + '.bson'
    pth_tif = filepath + '.tif'
    if os.path.exists(pth_tif):
        os.remove(pth_tif)
    if os.path.exists(pth_bson):
        os.remove(pth_bson)


def _imglabeling_to_layer(ij, labeling):
    """Converts a Labeling to a Labels layer"""
    labels = ij.context().getService(LabelingIOService)
    # Convert the data to an ImgLabeling
    data = ij.convert().convert(labeling, ImgLabeling)

    # Save the image on the java side
    tmp_pth = os.getcwd() + '/tmp'
    tmp_pth_bson = tmp_pth + '.bson'
    tmp_pth_tif = tmp_pth + '.tif'
    try:
        _delete_labeling_files(tmp_pth)
        labels.save(data, tmp_pth_tif) # TODO: improve, likely utilizing the data's name
    except Exception:
        print('Failed to save the data')
    
    # Load the labeling on the python side
    labeling = Labeling.from_file(tmp_pth_bson)
    _delete_labeling_files(tmp_pth)
    return _ntypes._labeling_to_layer(labeling)


def _layer_to_imglabeling(ij, layer: Labels):
    """Converts a Labels layer to a Labeling"""
    labeling = _ntypes._layer_to_labeling(layer)
    
    return ij.py.to_java(labeling)


def _format_ellipse_points(pts):
    if pts.shape[0] == 2:
        return pts[0, :], pts[1, :]
    center = np.mean(pts, axis=0)
    radii = np.abs(pts[0, :] - center)

    return center, radii

def arr(coords):
    arr = JArray(JDouble)(len(coords))
    arr[:] = coords
    return arr

def _polygon_from_points(points):
    # HACK: JPype doesn't know whether to call the float or double
    def point_from_coords(coords):
        arr = JArray(JDouble)(2)
        arr[:] = coords
        return RealPoint(arr)
    pts = [point_from_coords(x) for x in points]
    ptList = ArrayList(pts)
    return ClosedWritablePolygon2D(ptList)


def _rectangle_from_points(points):
    # find rectangle min
    origin = np.array([0, 0])
    dists = [np.linalg.norm(origin - pt) for pt in points]
    min = points[np.argmin(dists)]
    # find rectangle max
    min_dists = [np.linalg.norm(min - pt) for pt in points]
    max = points[np.argmax(min_dists)]
    # determine whether the rectangle is axis aligned
    other = next(filter(lambda p2: not np.array_equal(min, p2) and not np.array_equal(max, p2), points), None)
    min_diff = other - min
    is_box = any(d == 0 for d in min_diff)
    # Return box if axis aligned
    if is_box:
        return ClosedWritableBox(arr(min), arr(max))
    # Return polygon if not
    else:
        return _polygon_from_points(points)


def _shapes_to_realmasks(ij, layer: Shapes):
    """Converts a Shapes layer to a RealMask or a list of them."""
    masks = ArrayList()
    for pts, shape_type in zip(layer.data, layer.shape_type):
        if shape_type == 'ellipse':
            center, radii = _format_ellipse_points(pts)
            shape = ClosedWritableEllipsoid(center, radii)
        if shape_type == 'rectangle':
            shape = _rectangle_from_points(pts)
        masks.add(shape)
    rois = DefaultROITree()
    rois.addROIs(masks)
    return rois


def _ellipsoid_to_shapes(ij, mask):
    center = mask.center().positionAsDoubleArray()
    center = ij.py.from_java(center)
    radii = mask.minAsDoubleArray()
    radii = ij.py.from_java(radii)
    for i in range(len(radii)):
        radii[i] = mask.semiAxisLength(i)
    data = np.zeros((2, len(center)))
    data[0, :] = center
    data[1, :] = radii
    layer = Shapes()
    layer.add_ellipses(data)
    return layer

def _box_to_shapes(ij, mask):
    min = mask.minAsDoubleArray()
    min = ij.py.from_java(min)
    max = mask.maxAsDoubleArray()
    max = ij.py.from_java(max)
    data = np.zeros((2, len(min)))
    data[0, :] = min
    data[1, :] = max
    layer = Shapes()
    layer.add_rectangles(data)
    return layer
    

def _napari_to_java_converters(ij) -> List[Converter]:
    return [
        Converter(
            predicate=lambda obj: isinstance(obj, Labels),
            converter=lambda obj: _layer_to_imglabeling(ij, obj),
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Shapes),
            converter=lambda obj: _shapes_to_realmasks(ij, obj),
            priority=Priority.VERY_HIGH
        ),
    ]


def _java_to_napari_converters(ij) -> List[Converter]:
    return [
        Converter(
            predicate=lambda obj: isinstance(obj, ImgLabeling),
            converter=_imglabeling_to_layer,
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, SuperEllipsoid),
            converter=lambda obj: _ellipsoid_to_shapes(ij, obj),
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Box),
            converter=lambda obj: _box_to_shapes(ij, obj),
            priority=Priority.VERY_HIGH
        ),
    ]


def init_napari_converters(ij):
    """
    Initializes all classes needed by the converters,
    then adding them to the ScyJava converter framework.
    :param ij: An ImageJ gateway
    """
    # Initialize needed classes
    global Double
    global ArrayList
    global LabelingIOService
    global DefaultROITree
    global SuperEllipsoid
    global Box
    global ImgLabeling
    global ClosedWritableEllipsoid
    global ClosedWritablePolygon2D
    global ClosedWritableBox
    global RealPoint
    global Point
    global PointMatch
    global RigidModel2D
    global AffineTransform
    global RealViews

    Double = jimport(
        'java.lang.Double'
    )
    ArrayList = jimport(
        'java.util.ArrayList'
    )
    LabelingIOService = jimport(
        'io.scif.labeling.LabelingIOService'
    )
    DefaultROITree = jimport(
        'net.imagej.roi.DefaultROITree'
    )
    SuperEllipsoid = jimport(
        'net.imglib2.roi.geom.real.SuperEllipsoid'
    )
    Box = jimport(
        'net.imglib2.roi.geom.real.Box'
    )
    ClosedWritableEllipsoid = jimport(
        'net.imglib2.roi.geom.real.ClosedWritableEllipsoid'
    )
    ClosedWritablePolygon2D = jimport(
        'net.imglib2.roi.geom.real.ClosedWritablePolygon2D'
    )
    ClosedWritableBox = jimport(
        'net.imglib2.roi.geom.real.ClosedWritableBox'
    )
    ImgLabeling = jimport(
        'net.imglib2.roi.labeling.ImgLabeling'
    )
    RealPoint = jimport(
        'net.imglib2.RealPoint'
    )
    Point = jimport(
        'mpicbg.models.Point'
    )
    PointMatch = jimport(
        'mpicbg.models.PointMatch'
    )
    RigidModel2D = jimport(
        'mpicbg.models.RigidModel2D'
    )
    AffineTransform = jimport(
        'net.imglib2.realtransform.AffineTransform'
    )
    RealViews = jimport(
        'net.imglib2.realtransform.RealViews'
    )

    # Add napari -> Java converters
    for converter in _napari_to_java_converters(ij):
        add_java_converter(converter)

    # Add Java -> napari converters
    for converter in _java_to_napari_converters(ij):
        add_py_converter(converter)
