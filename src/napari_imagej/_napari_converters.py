import os
from typing import List
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


def _shapes_to_realmasks(layer: Shapes):
    """Converts a Shapes layer to a RealMask or a list of them."""
    masks = []
    for pts, shape_type in zip(layer.data, layer.shape_type):
        if shape_type == 'ellipse':
            center, radii = _format_ellipse_points(pts)
            masks.append(ClosedWritableEllipsoid(center, radii))
    return masks[0] if len(masks) == 1 else masks


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
    

def _napari_to_java_converters(ij) -> List[Converter]:
    return [
        Converter(
            predicate=lambda obj: isinstance(obj, Labels),
            converter=lambda obj: _layer_to_imglabeling(ij, obj),
            priority=Priority.VERY_HIGH
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Shapes),
            converter=_shapes_to_realmasks,
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
    ]


def init_napari_converters(ij):
    """
    Initializes all classes needed by the converters,
    then adding them to the ScyJava converter framework.
    :param ij: An ImageJ gateway
    """
    # Initialize needed classes
    global LabelingIOService
    global SuperEllipsoid
    global ImgLabeling
    global ClosedWritableEllipsoid

    LabelingIOService = jimport(
        'io.scif.labeling.LabelingIOService'
    )
    SuperEllipsoid = jimport(
        'net.imglib2.roi.geom.real.SuperEllipsoid'
    )
    ClosedWritableEllipsoid = jimport(
        'net.imglib2.roi.geom.real.ClosedWritableEllipsoid'
    )
    ImgLabeling = jimport(
        'net.imglib2.roi.labeling.ImgLabeling'
    )

    # Add napari -> Java converters
    for converter in _napari_to_java_converters(ij):
        add_java_converter(converter)

    # Add Java -> napari converters
    for converter in _java_to_napari_converters(ij):
        add_py_converter(converter)
