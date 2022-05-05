import os
from typing import List
from jpype import JArray, JDouble
import numpy as np
from napari.layers import Labels, Shapes
from napari_imagej import _ntypes
from scyjava import Converter, Priority, jimport, add_py_converter, add_java_converter
from labeling.Labeling import Labeling


# -- Labels / ImgLabelings -- #


def _imglabeling_to_layer(ij, imgLabeling) -> Labels:
    """
    Converts a Java ImgLabeling to a napari Labels layer
    :param imgLabeling: the Java ImgLabeling
    :return: a Labels layer
    """
    labeling: Labeling = ij.py._imglabeling_to_labeling(imgLabeling)
    return _ntypes._labeling_to_layer(labeling)


def _layer_to_imglabeling(ij, layer: Labels):
    """
    Converts a napari Labels layer to a Java ImgLabeling
    :param layer: a Labels layer
    :return: the Java ImgLabeling
    """
    labeling: Labeling = _ntypes._layer_to_labeling(layer)
    return ij.py.to_java(labeling)


# -- Shapes Utils -- #


def arr(coords):
    arr = JArray(JDouble)(len(coords))
    arr[:] = coords
    return arr

def _polyshape_to_layer_data(mask):
    vertices = mask.vertices()
    num_dims = mask.numDimensions()
    arr = JArray(JDouble)(int(num_dims))
    data = np.zeros((vertices.size(), num_dims))
    for i in range(len(vertices)):
        vertices.get(i).localize(arr)
        data[i, :] = arr
    return data


# -- Ellipses -- #


def _ellipse_layer_to_mask(pts):
    if pts.shape[0] == 2:
        return pts[0, :], pts[1, :]
    center = np.mean(pts, axis=0)
    radii = np.abs(pts[0, :] - center)
    return ClosedWritableEllipsoid(center, radii)


def _ellipse_mask_to_data(mask):
    # Make data array
    data = np.zeros((2, mask.numDimensions()))
    # Write center into the first column
    center = mask.center().positionAsDoubleArray()
    data[0, :] = center[:] # Slice needed for JArray
    # Write radii into the second column
    for i in range(data.shape[1]):
        data[1, i] = mask.semiAxisLength(i)
    return data


def _ellipse_mask_to_layer(mask):
    layer = Shapes()
    layer.add_ellipses(_ellipse_mask_to_data(mask))
    return layer


# -- Boxes -- #


def _rectangle_layer_to_mask(points):
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
        return _polygon_layer_to_mask(points)


def _rectangle_mask_to_data(mask):
    min = mask.minAsDoubleArray()
    max = mask.maxAsDoubleArray()
    data = np.zeros((2, len(min)))
    data[0, :] = min[:] # Slice needed for JArray
    data[1, :] = max[:] # Slice needed for JArray
    return data


def _rectangle_mask_to_layer(mask):
    layer = Shapes()
    layer.add_rectangles(_rectangle_mask_to_data(mask))
    return layer


# -- Polygons -- ##


def _polygon_layer_to_mask(points):
    # HACK: JPype doesn't know whether to call the float or double
    def point_from_coords(coords):
        arr = JArray(JDouble)(2)
        arr[:] = coords
        return RealPoint(arr)
    pts = [point_from_coords(x) for x in points]
    ptList = ArrayList(pts)
    return ClosedWritablePolygon2D(ptList)


def _polygon_mask_to_data(mask):
    return _polyshape_to_layer_data(mask)


def _polygon_mask_to_layer(mask):
    layer = Shapes()
    layer.add_polygons(_polygon_mask_to_data(mask))
    return layer


# -- Lines -- ##


def _line_layer_to_mask(points):
    # HACK: JPype doesn't know whether to call the float or double
    def point_from_coords(coords):
        arr = JArray(JDouble)(2)
        arr[:] = coords
        return RealPoint(arr)
    pts = [point_from_coords(x) for x in points]
    return DefaultWritableLine(pts[0], pts[1])


def _line_mask_to_data(mask):
    num_dims = mask.numDimensions()
    arr = JArray(JDouble)(int(num_dims))
    data = np.zeros((2, num_dims))
    # First point
    mask.endpointOne().localize(arr)
    data[0, :] = arr
    # Second point
    mask.endpointTwo().localize(arr)
    data[1, :] = arr
    return data


def _line_mask_to_layer(mask):
    # Create Shapes layer
    layer = Shapes()
    layer.add_lines(_line_mask_to_data(mask))
    return layer


# -- Paths -- ##


def _path_layer_to_mask(points):
    def point_from_coords(coords):
        arr = JArray(JDouble)(2)
        arr[:] = coords
        return RealPoint(arr)
    pts = [point_from_coords(x) for x in points]
    ptList = ArrayList(pts)
    return DefaultWritablePolyline(ptList)


def _path_mask_to_data(mask):
    return _polyshape_to_layer_data(mask)


def _path_mask_to_layer(mask):
    layer = Shapes()
    layer.add_paths(_path_mask_to_data(mask))
    return layer


# -- Shapes / ROITrees -- #


def _roitree_to_layer(roitree):
    layer = Shapes()
    rois = [child.data() for child in roitree.children()]
    for roi in rois:
        if isinstance(roi, SuperEllipsoid):
            layer.add_ellipses(_ellipse_mask_to_data(roi))
        elif isinstance(roi, Box):
            layer.add_rectangles(_rectangle_mask_to_data(roi))
        elif isinstance(roi, Polygon2D):
            layer.add_polygons(_polygon_mask_to_data(roi))
        elif isinstance(roi, Line):
            layer.add_lines(_line_mask_to_data(roi))
        elif isinstance(roi, Polyline):
            layer.add_paths(_path_mask_to_data(roi))
        else:
            raise NotImplementedError(f'Cannot convert {roi}: conversion not implemented!')
    return layer


def _layer_to_roitree(layer: Shapes):
    """Converts a Shapes layer to a RealMask or a list of them."""
    masks = ArrayList()
    for pts, shape_type in zip(layer.data, layer.shape_type):
        if shape_type == 'ellipse':
            shape = _ellipse_layer_to_mask(pts)
        elif shape_type == 'rectangle':
            shape = _rectangle_layer_to_mask(pts)
        elif shape_type == 'polygon':
            shape = _polygon_layer_to_mask(pts)
        elif shape_type == 'line':
            shape = _line_layer_to_mask(pts)
        elif shape_type == 'path':
            shape = _path_layer_to_mask(pts)
        else:
            raise NotImplementedError(f"Shape type {shape_type} cannot yet be converted!")
        masks.add(shape)
    rois = DefaultROITree()
    rois.addROIs(masks)
    return rois


# -- Converters -- #


def _napari_to_java_converters(ij) -> List[Converter]:
    return [
        Converter(
            predicate=lambda obj: isinstance(obj, Labels),
            converter=lambda obj: _layer_to_imglabeling(ij, obj),
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Shapes),
            converter=lambda obj: _layer_to_roitree(obj),
            priority=Priority.VERY_HIGH
        ),
    ]


def _java_to_napari_converters(ij) -> List[Converter]:
    return [
        Converter(
            predicate=lambda obj: isinstance(obj, ImgLabeling),
            converter=lambda obj: _imglabeling_to_layer(ij, obj),
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, SuperEllipsoid),
            converter=_ellipse_mask_to_layer,
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Box),
            converter=_rectangle_mask_to_layer,
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Polygon2D),
            converter=_polygon_mask_to_layer,
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Line),
            converter=_line_mask_to_layer,
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Polyline),
            converter=_path_mask_to_layer,
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, ROITree),
            converter=_roitree_to_layer,
            priority=Priority.VERY_HIGH + 1
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
    global Polygon2D
    global Line
    global Polyline
    global ROITree
    global ImgLabeling
    global ClosedWritableEllipsoid
    global ClosedWritablePolygon2D
    global ClosedWritableBox
    global DefaultWritableLine
    global DefaultWritablePolyline
    global RealPoint

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
    Polygon2D = jimport(
        'net.imglib2.roi.geom.real.Polygon2D'
    )
    Line = jimport(
        'net.imglib2.roi.geom.real.Line'
    )
    Polyline = jimport(
        'net.imglib2.roi.geom.real.Polyline'
    )
    ROITree = jimport(
        'net.imagej.roi.DefaultROITree'
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
    DefaultWritableLine = jimport(
        'net.imglib2.roi.geom.real.DefaultWritableLine'
    )
    DefaultWritablePolyline = jimport(
        'net.imglib2.roi.geom.real.DefaultWritablePolyline'
    )
    ImgLabeling = jimport(
        'net.imglib2.roi.labeling.ImgLabeling'
    )
    RealPoint = jimport(
        'net.imglib2.RealPoint'
    )

    # Add napari -> Java converters
    for converter in _napari_to_java_converters(ij):
        add_java_converter(converter)

    # Add Java -> napari converters
    for converter in _java_to_napari_converters(ij):
        add_py_converter(converter)
