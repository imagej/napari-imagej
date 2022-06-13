from typing import List
from jpype import JArray, JDouble
import numpy as np
from napari_imagej.setup_imagej import ij, jc
from napari.layers import Labels, Shapes, Points, Image
from napari_imagej import _ntypes
from scyjava import (
    Converter,
    Priority,
    add_py_converter,
    add_java_converter,
)
from labeling.Labeling import Labeling

# -- Image / Img -- #


def _image_to_img(image: Image) -> "jc.Img":
    data = image.data
    return ij().py.to_java(data)


# -- Labels / ImgLabelings -- #


def _imglabeling_to_layer(imgLabeling) -> Labels:
    """
    Converts a Java ImgLabeling to a napari Labels layer
    :param imgLabeling: the Java ImgLabeling
    :return: a Labels layer
    """
    labeling: Labeling = ij().py._imglabeling_to_labeling(imgLabeling)
    return _ntypes._labeling_to_layer(labeling)


def _layer_to_imglabeling(layer: Labels):
    """
    Converts a napari Labels layer to a Java ImgLabeling
    :param layer: a Labels layer
    :return: the Java ImgLabeling
    """
    labeling: Labeling = _ntypes._layer_to_labeling(layer)
    return ij().py.to_java(labeling)


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


def _ellipse_mask_to_layer(mask):
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


def _rectangle_mask_to_layer(mask):
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


def _polygon_mask_to_layer(mask):
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


def _line_mask_to_layer(mask):
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


def _path_mask_to_layer(mask):
    layer = Shapes()
    layer.add_paths(_path_mask_to_data(mask))
    return layer


# -- Shapes / ROITrees -- #


def _roitree_to_layer(roitree):
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


def _layer_to_roitree(layer: Shapes):
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


# -- Points / RealPointCollection -- #


def _points_to_realpointcollection(points):
    pts = [realPoint_from(x) for x in points.data]
    ptList = jc.ArrayList(pts)
    return jc.DefaultWritableRealPointCollection(ptList)


def _realpointcollection_to_points(collection):
    # data - collection.size() points, collection.numDimensions() values per point
    data = np.zeros((collection.size(), collection.numDimensions()))
    # Create a temporary array to pass to each point
    # N.B. we cannot just write pt.localize(data[i, :]) as JPype does not know
    # whether to use the localize(double[]) method or the localize(float[]) method.
    # We thus have to make the decision ourselves using tmp_arr, a double[].
    tmp_arr_dims = int(collection.numDimensions())
    tmp_arr = JArray(JDouble)(tmp_arr_dims)
    for i, pt in enumerate(collection.points()):
        pt.localize(tmp_arr)
        data[i, :] = tmp_arr
    return Points(data=data)


# -- Colors -- #


def _color_to_array(color: "jc.ColorRGB") -> np.ndarray:
    """
    Converts a SciJava ColorRGB to an arraylike that napari can understand.

    :param color: The object to be converted
    :return: The converted color
    """
    array = [color.getRed(), color.getGreen(), color.getBlue(), color.getAlpha()]
    return np.array(array)


def _is_python_color(arraylike: Any) -> bool:
    """
    Determines whether arraylike is a color (by napari's definition).
    Colors are array-likes of elemetns in [0, 1] that are of size (1, 4).

    :param arraylike: May or may not be a color.
    :return: True iff arraylike satisfies the definition of a color.
    """
    # The color should be an array-like of elements in [0, 1] of size (1, 4)
    if not hasattr(arraylike, "shape"):
        return False
    if not hasattr(arraylike, "dtype"):
        return False
    if not hasattr(arraylike, "__getitem__"):
        return False

    if not getattr(arraylike, "shape") == (1, 4):
        return False

    for i in range(4):
        value = arraylike[0, i]
        if value < 0 or value > 1:
            return False

    return True


def _array_to_color(arraylike: Any) -> "jc.ColorRGBA":
    """
    Converts a napari color arraylike to a SciJava ColorRGBA.

    :param arraylike: The object to be converted
    :return: The converted color
    """
    if not _is_python_color(arraylike):
        raise TypeError(f"{arraylike} is not a color!")
    r = arraylike[0, 0]
    g = arraylike[0, 1]
    b = arraylike[0, 2]
    a = arraylike[0, 3]
    return jc.ColorRGBA(r, g, b, a)


# -- Converters -- #


def _napari_to_java_converters() -> List[Converter]:
    return [
        Converter(
            predicate=lambda obj: isinstance(obj, Image),
            converter=lambda obj: _image_to_img(obj),
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Labels),
            converter=lambda obj: _layer_to_imglabeling(obj),
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Shapes),
            converter=lambda obj: _layer_to_roitree(obj),
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, Points),
            converter=_points_to_realpointcollection,
            priority=Priority.VERY_HIGH,
        ),
        # This converter should win over other arraylike converters
        Converter(
            predicate=_is_python_color,
            converter=_array_to_color,
            priority=Priority.EXTREMELY_HIGH,
        ),
    ]


def _java_to_napari_converters() -> List[Converter]:
    return [
        Converter(
            predicate=lambda obj: isinstance(obj, jc.ImgLabeling),
            converter=lambda obj: _imglabeling_to_layer(obj),
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.SuperEllipsoid),
            converter=_ellipse_mask_to_layer,
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.Box),
            converter=_rectangle_mask_to_layer,
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.Polygon2D),
            converter=_polygon_mask_to_layer,
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.Line),
            converter=_line_mask_to_layer,
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.Polyline),
            converter=_path_mask_to_layer,
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.ROITree),
            converter=_roitree_to_layer,
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.RealPointCollection),
            converter=_realpointcollection_to_points,
            priority=Priority.VERY_HIGH,
        ),
        Converter(
            predicate=lambda obj: isinstance(obj, jc.ColorRGB),
            converter=_color_to_array,
            priority=Priority.VERY_HIGH,
        ),
    ]


def init_napari_converters():
    """
    Adds all converters to the ScyJava converter framework.
    :param ij: An ImageJ gateway
    """
    # Add napari -> Java converters
    for converter in _napari_to_java_converters():
        add_java_converter(converter)

    # Add Java -> napari converters
    for converter in _java_to_napari_converters():
        add_py_converter(converter)
