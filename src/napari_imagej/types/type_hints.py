"""
The definitive set of HARDCODED python type hints for java types.

The type hints may be concrete types OR strings that can be treated
as forward references.

Note that many types don't belong here, as they can be determined
in a programmatic way. Those types should be declared elsewhere.

The hint maps are broken up into sub-maps for convenience and utility.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Callable, List, Union

from jpype import JBoolean, JByte, JChar, JDouble, JFloat, JInt, JLong, JShort
from scyjava import Priority

from napari_imagej.java import jc


@dataclass
class TypeHint:
    type: type
    hint: Union[str, type]
    priority: float = Priority.NORMAL


HINT_GENERATORS: List[Callable[[], List[TypeHint]]] = []


def hint_category(func: Callable[[], List[TypeHint]]) -> Callable[[], List[TypeHint]]:
    @lru_cache(maxsize=None)
    def inner() -> List[TypeHint]:
        # We want the map returned by func...
        original: List[TypeHint] = func()
        # ...but without any None keys.
        # NB the second None avoids the KeyError
        return list(filter(lambda hint: hint.type is not None, original))

    HINT_GENERATORS.append(inner)
    return inner


@lru_cache(maxsize=None)
def type_hints() -> List[TypeHint]:
    """
    Returns a List of all HARDCODED python type hints for java types,
    sorted by priority.
    """
    types: List[TypeHint] = []
    for generator in HINT_GENERATORS:
        types.extend(generator())
    types.sort(reverse=True, key=lambda hint: hint.priority)
    return types


@hint_category
def booleans() -> List[TypeHint]:
    return [
        TypeHint(JBoolean, bool),
        TypeHint(jc.Boolean_Arr, List[bool]),
        TypeHint(jc.Boolean, bool),
        TypeHint(jc.BooleanType, bool, Priority.LOW),
    ]


@hint_category
def numbers() -> List[TypeHint]:
    return [
        TypeHint(JByte, int),
        TypeHint(jc.Byte, int),
        TypeHint(jc.Byte_Arr, List[int]),
        TypeHint(JShort, int),
        TypeHint(jc.Short, int),
        TypeHint(jc.Short_Arr, List[int]),
        TypeHint(JInt, int),
        TypeHint(jc.Integer, int),
        TypeHint(jc.Integer_Arr, List[int]),
        TypeHint(JLong, int),
        TypeHint(jc.Long, int),
        TypeHint(jc.Long_Arr, List[int]),
        TypeHint(JFloat, float),
        TypeHint(jc.Float, float),
        TypeHint(jc.Float_Arr, List[float]),
        TypeHint(JDouble, float),
        TypeHint(jc.Double, float),
        TypeHint(jc.Double_Arr, List[float]),
        TypeHint(jc.BigInteger, int),
        TypeHint(jc.BigDecimal, float),
        TypeHint(jc.IntegerType, int, Priority.LOW),
        TypeHint(jc.RealType, float, Priority.LOW - 1),
        TypeHint(jc.ComplexType, complex, Priority.LOW - 2),
        TypeHint(jc.NumericType, float, Priority.VERY_LOW),
    ]


@hint_category
def strings() -> List[TypeHint]:
    return [
        TypeHint(JChar, str),
        TypeHint(jc.Character_Arr, str),
        TypeHint(jc.Character, str),
        TypeHint(jc.String, str),
    ]


@hint_category
def labels() -> List[TypeHint]:
    return [TypeHint(jc.ImgLabeling, "napari.layers.Labels", priority=Priority.HIGH)]


@hint_category
def images() -> List[TypeHint]:
    return [
        TypeHint(
            jc.RandomAccessibleInterval, "napari.layers.Image", priority=Priority.LOW
        ),
        TypeHint(
            jc.RandomAccessible, "napari.layers.Image", priority=Priority.VERY_LOW
        ),
        TypeHint(
            jc.IterableInterval, "napari.layers.Image", priority=Priority.VERY_LOW
        ),
        TypeHint(jc.ImageDisplay, "napari.layers.Image"),
        TypeHint(jc.Img, "napari.layers.Image"),
        TypeHint(jc.ImgPlus, "napari.layers.Image"),
        TypeHint(jc.Dataset, "napari.layers.Image"),
        TypeHint(jc.DatasetView, "napari.layers.Image"),
        TypeHint(jc.ImagePlus, "napari.layers.Image"),
    ]


@hint_category
def points() -> List[TypeHint]:
    return [
        TypeHint(jc.PointMask, "napari.types.PointsData"),
        TypeHint(jc.RealPointCollection, "napari.types.PointsData"),
    ]


@hint_category
def shapes() -> List[TypeHint]:
    return [
        TypeHint(jc.Line, "napari.layers.Shapes"),
        TypeHint(jc.Box, "napari.layers.Shapes"),
        TypeHint(jc.SuperEllipsoid, "napari.layers.Shapes"),
        TypeHint(jc.Polygon2D, "napari.layers.Shapes"),
        TypeHint(jc.Polyline, "napari.layers.Shapes"),
        TypeHint(jc.ROITree, "napari.layers.Shapes"),
    ]


@hint_category
def surfaces() -> List[TypeHint]:
    return [TypeHint(jc.Mesh, "napari.types.SurfaceData")]


@hint_category
def color_tables() -> List[TypeHint]:
    return [
        TypeHint(jc.ColorTable, "vispy.color.Colormap"),
    ]


@hint_category
def pd() -> List[TypeHint]:
    return [
        TypeHint(jc.Table, "pandas.DataFrame"),
    ]


@hint_category
def paths() -> List[TypeHint]:
    return [
        TypeHint(jc.Character_Arr, str),
        TypeHint(jc.Character, str),
        TypeHint(jc.String, str),
        TypeHint(jc.File, "pathlib.PosixPath"),
        TypeHint(jc.Path, "pathlib.PosixPath"),
    ]


@hint_category
def enums() -> List[TypeHint]:
    return [
        TypeHint(jc.Enum, "enum.Enum"),
    ]


@hint_category
def dates() -> List[TypeHint]:
    return [
        TypeHint(jc.Date, "datetime.datetime"),
    ]
