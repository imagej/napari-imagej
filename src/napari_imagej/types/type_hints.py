"""
The definitive set of HARDCODED python type hints for java types.

The type hints may be concrete types OR strings that can be treated
as forward references.

Note that many types don't belong here, as they can be determined
in a programmatic way. Those types should be declared elsewhere.

The hint maps are broken up into sub-maps for convenience and utility.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Callable

from jpype import JBoolean, JByte, JChar, JDouble, JFloat, JInt, JLong, JShort
from scyjava import Priority

from napari_imagej.java import jc


@dataclass
class TypeHint:
    type: type
    hint: str | type
    priority: float = Priority.NORMAL


HINT_GENERATORS: list[Callable[[], list[TypeHint]]] = []


def hint_category(func: Callable[[], list[TypeHint]]) -> Callable[[], list[TypeHint]]:
    @cache
    def inner() -> list[TypeHint]:
        # We want the map returned by func...
        original: list[TypeHint] = func()
        # ...but without any None keys.
        # NB the second None avoids the KeyError
        return list(filter(lambda hint: hint.type is not None, original))

    HINT_GENERATORS.append(inner)
    return inner


@cache
def type_hints() -> list[TypeHint]:
    """
    Returns a List of all HARDCODED python type hints for java types,
    sorted by priority.
    """
    types: list[TypeHint] = []
    for generator in HINT_GENERATORS:
        types.extend(generator())
    types.sort(reverse=True, key=lambda hint: hint.priority)
    return types


@hint_category
def booleans() -> list[TypeHint]:
    return [
        TypeHint(JBoolean, bool),
        TypeHint(jc.Boolean_Arr, list[bool]),
        TypeHint(jc.Boolean, bool),
        TypeHint(jc.BooleanType, bool, Priority.LOW),
    ]


@hint_category
def numbers() -> list[TypeHint]:
    return [
        TypeHint(JByte, int),
        TypeHint(jc.Byte, int),
        TypeHint(jc.Byte_Arr, list[int]),
        TypeHint(JShort, int),
        TypeHint(jc.Short, int),
        TypeHint(jc.Short_Arr, list[int]),
        TypeHint(JInt, int),
        TypeHint(jc.Integer, int),
        TypeHint(jc.Integer_Arr, list[int]),
        TypeHint(JLong, int),
        TypeHint(jc.Long, int),
        TypeHint(jc.Long_Arr, list[int]),
        TypeHint(JFloat, float),
        TypeHint(jc.Float, float),
        TypeHint(jc.Float_Arr, list[float]),
        TypeHint(JDouble, float),
        TypeHint(jc.Double, float),
        TypeHint(jc.Double_Arr, list[float]),
        TypeHint(jc.BigInteger, int),
        TypeHint(jc.BigDecimal, float),
        TypeHint(jc.IntegerType, int, Priority.LOW),
        TypeHint(jc.RealType, float, Priority.LOW - 1),
        TypeHint(jc.ComplexType, complex, Priority.LOW - 2),
        TypeHint(jc.NumericType, float, Priority.VERY_LOW),
    ]


@hint_category
def strings() -> list[TypeHint]:
    return [
        TypeHint(JChar, str),
        TypeHint(jc.Character_Arr, str),
        TypeHint(jc.Character, str),
        TypeHint(jc.String, str),
    ]


@hint_category
def labels() -> list[TypeHint]:
    return [TypeHint(jc.ImgLabeling, "napari.layers.Labels", priority=Priority.HIGH)]


@hint_category
def images() -> list[TypeHint]:
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
def points() -> list[TypeHint]:
    return [
        TypeHint(jc.PointMask, "napari.layers.Points"),
        TypeHint(jc.RealPointCollection, "napari.layers.Points"),
    ]


@hint_category
def shapes() -> list[TypeHint]:
    return [
        TypeHint(jc.Line, "napari.layers.Shapes"),
        TypeHint(jc.Box, "napari.layers.Shapes"),
        TypeHint(jc.SuperEllipsoid, "napari.layers.Shapes"),
        TypeHint(jc.Polygon2D, "napari.layers.Shapes"),
        TypeHint(jc.Polyline, "napari.layers.Shapes"),
        TypeHint(jc.ROITree, "napari.layers.Shapes"),
    ]


@hint_category
def surfaces() -> list[TypeHint]:
    return [TypeHint(jc.Mesh, "napari.layers.Surface")]


@hint_category
def color_tables() -> list[TypeHint]:
    return [
        TypeHint(jc.ColorTable, "vispy.color.Colormap"),
    ]


@hint_category
def pd() -> list[TypeHint]:
    return [
        TypeHint(jc.Table, "pandas.DataFrame"),
    ]


@hint_category
def paths() -> list[TypeHint]:
    return [
        TypeHint(jc.Character_Arr, str),
        TypeHint(jc.Character, str),
        TypeHint(jc.String, str),
        TypeHint(jc.File, "pathlib.PosixPath"),
        TypeHint(jc.Path, "pathlib.PosixPath"),
    ]


@hint_category
def enums() -> list[TypeHint]:
    return [
        TypeHint(jc.Enum, "enum.Enum"),
    ]


@hint_category
def dates() -> list[TypeHint]:
    return [
        TypeHint(jc.Date, "datetime.datetime"),
    ]
