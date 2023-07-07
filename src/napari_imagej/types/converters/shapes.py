"""
scyjava Converters for converting between ImgLib2 RealMasks
and napari Shapes
"""
import numpy as np
from jpype import JArray, JDouble
from napari.layers import Shapes
from scyjava import Priority

from napari_imagej.java import jc
from napari_imagej.types.converters import java_to_py_converter, py_to_java_converter

# -- Shapes Utils -- #


def arr(coords):
    arr = JArray(JDouble)(len(coords))
    arr[:] = coords
    return arr


def realPoint_from(coords: np.ndarray):
    """
    Creates a RealPoint from a numpy [1, D] array of coordinates.
    :param coords: The [1, D] numpy array of coordinates
    :return: a RealPoint
    """
    # JPype doesn't know whether to call the float or double.
    # We make the choice for them using the function arr
    return jc.RealPoint(arr(coords[::-1]))


def _polyshape_to_layer_data(mask):
    vertices = mask.vertices()
    num_dims = mask.numDimensions()
    arr = JArray(JDouble)(int(num_dims))
    data = np.zeros((vertices.size(), num_dims))
    for i in range(len(vertices)):
        vertices.get(i).localize(arr)
        data[i, :] = arr
    return np.flip(data, axis=1)


# -- Ellipses -- #


def _ellipse_data_to_mask(pts):
    center = np.mean(pts, axis=0)
    radii = np.abs(pts[0, :] - center)
    return jc.ClosedWritableEllipsoid(center[::-1], radii[::-1])


def _ellipse_mask_to_data(mask):
    # Make data array
    data = np.zeros((2, mask.numDimensions()))
    # Write center into the first column
    data[0, :] = mask.center().positionAsDoubleArray()
    # Write radii into the second column
    for i in range(data.shape[1]):
        data[1, i] = mask.semiAxisLength(i)
    return np.flip(data, axis=1)


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.SuperEllipsoid),
    priority=Priority.VERY_HIGH,
)
def _ellipse_mask_to_layer(mask: "jc.SuperEllipsoid") -> Shapes:
    layer = Shapes()
    layer.add_ellipses(_ellipse_mask_to_data(mask))
    return layer


# -- Boxes -- #


def _is_axis_aligned(points: np.ndarray) -> bool:
    """
    Given a (2, 4) numpy ndarray of the four corner points of a rectangle,
    this function determines whether the rectangle is axis-aligned.

    :param points: The four corners of the rectangle
    :return: true iff the rectangle defined by points is axis-aligned.
    """
    y_values = points[:, 0]
    x_values = points[:, 1]
    return len(set(x_values)) == 2 and len(set(y_values)) == 2


def _rectangle_data_to_mask(points: np.ndarray):
    # non-aligned rectangles cannot be represented with a Box
    if not _is_axis_aligned(points):
        return _polygon_data_to_mask(points)

    y_values = points[:, 0]
    x_values = points[:, 1]

    min = arr([np.min(x_values), np.min(y_values)])
    max = arr([np.max(x_values), np.max(y_values)])
    return jc.ClosedWritableBox(arr(min), arr(max))


def _rectangle_mask_to_data(mask):
    data = np.zeros((2, mask.numDimensions()))
    data[0, :] = mask.minAsDoubleArray()
    data[1, :] = mask.maxAsDoubleArray()
    return np.flip(data, axis=1)


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.Box), priority=Priority.VERY_HIGH
)
def _rectangle_mask_to_layer(mask: "jc.Box") -> Shapes:
    layer = Shapes()
    layer.add_rectangles(_rectangle_mask_to_data(mask))
    return layer


# -- Polygons -- ##


def _polygon_data_to_mask(points):
    pts = [realPoint_from(x) for x in points]
    ptList = jc.ArrayList(pts)
    return jc.ClosedWritablePolygon2D(ptList)


def _polygon_mask_to_data(mask):
    """
    Polygons are described in the Shapes layer as a set of points.
    This is all a Polyshape is, so a mask's data is just the Polyshape's data.
    """
    return _polyshape_to_layer_data(mask)


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.Polygon2D), priority=Priority.VERY_HIGH
)
def _polygon_mask_to_layer(mask: "jc.Polygon2D") -> Shapes:
    layer = Shapes()
    layer.add_polygons(_polygon_mask_to_data(mask))
    return layer


# -- Lines -- ##


def _line_data_to_mask(points):
    start = realPoint_from(points[0])
    end = realPoint_from(points[1])
    return jc.DefaultWritableLine(start, end)


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
    return np.flip(data, axis=1)


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.Line), priority=Priority.VERY_HIGH
)
def _line_mask_to_layer(mask: "jc.Line") -> Shapes:
    # Create Shapes layer
    layer = Shapes()
    layer.add_lines(_line_mask_to_data(mask))
    return layer


# -- Paths -- ##


def _path_data_to_mask(points):
    pts = [realPoint_from(x) for x in points]
    ptList = jc.ArrayList(pts)
    return jc.DefaultWritablePolyline(ptList)


def _path_mask_to_data(mask):
    """
    Paths are described in the Shapes layer as a set of points.
    This is all a Polyshape is, so a mask's data is just the Polyshape's data.
    """
    return _polyshape_to_layer_data(mask)


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.Polyline), priority=Priority.VERY_HIGH
)
def _path_mask_to_layer(mask: "jc.Polyline") -> Shapes:
    layer = Shapes()
    layer.add_paths(_path_mask_to_data(mask))
    return layer


# -- Shapes / ROITrees -- #


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.ROITree), priority=Priority.VERY_HIGH
)
def _roitree_to_layer(roitree: "jc.ROITree") -> Shapes:
    layer = Shapes()
    rois = [child.data() for child in roitree.children()]
    for roi in rois:
        if isinstance(roi, jc.SuperEllipsoid):
            layer.add_ellipses(_ellipse_mask_to_data(roi))
        elif isinstance(roi, jc.Box):
            layer.add_rectangles(_rectangle_mask_to_data(roi))
        elif isinstance(roi, jc.Polygon2D):
            layer.add_polygons(_polygon_mask_to_data(roi))
        elif isinstance(roi, jc.Line):
            layer.add_lines(_line_mask_to_data(roi))
        elif isinstance(roi, jc.Polyline):
            layer.add_paths(_path_mask_to_data(roi))
        else:
            raise NotImplementedError(
                f"Cannot convert {roi}: conversion not implemented!"
            )
    return layer


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Shapes), priority=Priority.VERY_HIGH
)
def _layer_to_roitree(layer: Shapes) -> "jc.DefaultROITree":
    """Converts a Shapes layer to a RealMask or a list of them."""
    masks = jc.ArrayList()
    for pts, shape_type in zip(layer.data, layer.shape_type):
        if shape_type == "ellipse":
            shape = _ellipse_data_to_mask(pts)
        elif shape_type == "rectangle":
            shape = _rectangle_data_to_mask(pts)
        elif shape_type == "polygon":
            shape = _polygon_data_to_mask(pts)
        elif shape_type == "line":
            shape = _line_data_to_mask(pts)
        elif shape_type == "path":
            shape = _path_data_to_mask(pts)
        else:
            raise NotImplementedError(
                f"Shape type {shape_type} cannot yet be converted!"
            )
        masks.add(shape)
    rois = jc.DefaultROITree()
    rois.addROIs(masks)
    return rois
