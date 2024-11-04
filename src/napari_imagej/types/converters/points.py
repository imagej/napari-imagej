"""
scyjava Converters for converting between ImageJ2 RealPointCollections
and napari Points
"""

import numpy as np
from jpype import JArray, JDouble
from napari.layers import Points
from scyjava import Priority

from napari_imagej.java import jc
from napari_imagej.types.converters import java_to_py_converter, py_to_java_converter


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


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Points), priority=Priority.VERY_HIGH
)
def _points_to_realpointcollection(points: Points) -> "jc.RealPointCollection":
    """Converts a napari Points into an ImageJ2 RealPointCollection"""
    data = points.data
    n = data.shape[1]
    # Reshape data to align with language conventions
    if n == 2:
        data = data[:, [1, 0]]  # (Y, X) in Python --> (X, Y) in Java
    elif n == 3:
        data = data[:, [2, 1, 0]]  # (Z, Y, X) in Python --> (X, Y, Z) in Java
    else:
        raise ValueError(f"Do not know how to translate point of {n} dimensions")
    pts = [realPoint_from(x) for x in data]
    ptList = jc.ArrayList(pts)
    return jc.DefaultWritableRealPointCollection(ptList)


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.RealPointCollection),
    priority=Priority.VERY_HIGH,
)
def _realpointcollection_to_points(collection: "jc.RealPointCollection") -> Points:
    """Converts an ImageJ2 RealPointsCollection into a napari Points"""
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
    # Reshape data to align with language conventions
    n = data.shape[1]
    if n == 2:
        data = data[:, [1, 0]]  # (X, Y) in Java --> (Y, X) in Python
    elif n == 3:
        data = data[:, [2, 1, 0]]  # (X, Y, Z) in Java --> (Z, Y, X) in Python
    else:
        raise ValueError(f"Do not know how to translate point of {n} dimensions")
    return Points(data=data)
