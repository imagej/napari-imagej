"""
scyjava Converters for converting between ImgLib2 RealMasks
and napari Shapes
"""
import numpy as np
from jpype import JArray, JDouble
from napari.layers import Shapes
from scyjava import Priority

from napari_imagej.setup_imagej import jc
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
    return jc.RealPoint(arr(coords))


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


def _ellipse_data_to_mask(pts):
    center = np.mean(pts, axis=0)
    radii = np.abs(pts[0, :] - center)
    return jc.ClosedWritableEllipsoid(center, radii)


def _ellipse_mask_to_data(mask):
    # Make data array
    data = np.zeros((2, mask.numDimensions()))
    # Write center into the first column
    center = mask.center().positionAsDoubleArray()
    data[0, :] = center[:]  # Slice needed for JArray
    # Write radii into the second column
    for i in range(data.shape[1]):
        data[1, i] = mask.semiAxisLength(i)
    return data


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.SuperEllipsoid),
    priority=Priority.VERY_HIGH,
)
def _ellipse_mask_to_layer(mask: "jc.SuperEllipsoid") -> Shapes:
    layer = Shapes()
    layer.add_ellipses(_ellipse_mask_to_data(mask))
    return layer


# -- Boxes -- #


def _is_axis_aligned(min: np.ndarray, max: np.ndarray, points: np.ndarray) -> bool:
    """
    Our rectangle consists of four points. We have:
    * The "minimum" point, the point closest to the origin
    * The "maximum" point, the point farthest from the origin
    * Two other points
    If our rectangle is axis aligned, then the distance vector between
    the minimum and another NON-MAXIMUM point will be zero in at least
    one dimension.

    :param min: The minimum corner of the rectangle
    :param max: The maximum corner of the rectangle
    :param points: The four corners of the rectangle
    :return: true iff the rectangle defined by points is axis-aligned.
    """
    other = next(
        filter(
            lambda p2: not np.array_equal(min, p2) and not np.array_equal(max, p2),
            points,
        ),
        None,
    )
    min_diff = other - min
    return any(d == 0 for d in min_diff)


def _rectangle_data_to_mask(points):
    # find rectangle min - closest point to origin
    origin = np.array([0, 0])
    distances = [np.linalg.norm(origin - pt) for pt in points]
    min = points[np.argmin(distances)]
    # find rectangle max - farthest point from minimum
    min_distances = [np.linalg.norm(min - pt) for pt in points]
    max = points[np.argmax(min_distances)]
    # Return box if axis aligned
    if _is_axis_aligned(min, max, points):
        return jc.ClosedWritableBox(arr(min), arr(max))
    # Return polygon if not
    else:
        return _polygon_data_to_mask(points)


def _rectangle_mask_to_data(mask):
    min = mask.minAsDoubleArray()
    max = mask.maxAsDoubleArray()
    data = np.zeros((2, len(min)))
    data[0, :] = min[:]  # Slice needed for JArray
    data[1, :] = max[:]  # Slice needed for JArray
    return data


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
    return data


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
