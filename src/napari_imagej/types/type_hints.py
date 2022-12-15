"""
The definitive set of HARDCODED python type hints for java types.

The type hints may be concrete types OR strings that can be treated
as forward references.

Note that many types don't belong here, as they can be determined
in a programmatic way. Those types should be declared elsewhere.

The hint maps are broken up into sub-maps for convenience and utility.
"""
from collections import OrderedDict
from functools import lru_cache
from typing import Any, Callable, Dict, List

from jpype import JBoolean, JByte, JChar, JDouble, JFloat, JInt, JLong, JShort

from napari_imagej.java import jc

MAP_GENERATORS: List[Callable[[], Dict[Any, Any]]] = []


def map_category(func: Callable[[], Dict[Any, Any]]) -> Callable[[], Dict[Any, Any]]:
    @lru_cache(maxsize=None)
    def inner() -> Dict[Any, Any]:
        # We want the map returned by func...
        original = func()
        # ...but without any None keys.
        # NB the second None avoids the KeyError
        original.pop(None, None)
        return original

    MAP_GENERATORS.append(inner)
    return inner


@lru_cache(maxsize=None)
def hint_map() -> OrderedDict:
    types = OrderedDict()
    for generator in MAP_GENERATORS:
        for k, v in generator().items():
            types[k] = v
    return types


@map_category
def booleans() -> Dict[Any, Any]:
    return {
        JBoolean: bool,
        jc.Boolean_Arr: List[bool],
        jc.Boolean: bool,
        jc.BooleanType: bool,
    }


@map_category
def numbers() -> Dict[Any, Any]:
    return {
        JByte: int,
        jc.Byte: int,
        jc.Byte_Arr: List[int],
        JShort: int,
        jc.Short: int,
        jc.Short_Arr: List[int],
        JInt: int,
        jc.Integer: int,
        jc.Integer_Arr: List[int],
        JLong: int,
        jc.Long: int,
        jc.Long_Arr: List[int],
        JFloat: float,
        jc.Float: float,
        jc.Float_Arr: List[float],
        JDouble: float,
        jc.Double: float,
        jc.Double_Arr: List[float],
        jc.BigInteger: int,
        jc.IntegerType: int,
        jc.RealType: float,
        jc.ComplexType: complex,
        jc.NumericType: float,
    }


@map_category
def strings() -> Dict[Any, Any]:
    return {
        JChar: str,
        jc.Character_Arr: str,
        jc.Character: str,
        jc.String: str,
    }


@map_category
def labels() -> Dict[Any, Any]:
    return {jc.ImgLabeling: "napari.layers.Labels"}


@map_category
def images() -> Dict[Any, Any]:
    return {
        jc.RandomAccessibleInterval: "napari.layers.Image",
        jc.RandomAccessible: "napari.layers.Image",
        jc.IterableInterval: "napari.layers.Image",
        jc.Img: "napari.layers.Image",
        jc.ImageDisplay: "napari.layers.Image",
        jc.Dataset: "napari.layers.Image",
        jc.DatasetView: "napari.layers.Image",
        jc.ImagePlus: "napari.layers.Image",
    }


@map_category
def points() -> Dict[Any, Any]:
    return {
        jc.PointMask: "napari.types.PointsData",
        jc.RealPointCollection: "napari.types.PointsData",
    }


@map_category
def shapes() -> Dict[Any, Any]:
    return {
        jc.Line: "napari.layers.Shapes",
        jc.Box: "napari.layers.Shapes",
        jc.SuperEllipsoid: "napari.layers.Shapes",
        jc.Polygon2D: "napari.layers.Shapes",
        jc.Polyline: "napari.layers.Shapes",
        jc.ROITree: "napari.layers.Shapes",
    }


@map_category
def surfaces() -> Dict[Any, Any]:
    return {jc.Mesh: "napari.types.SurfaceData"}


@map_category
def color_tables() -> Dict[Any, Any]:
    return {
        jc.ColorTable: "vispy.color.Colormap",
    }


@map_category
def pd() -> Dict[Any, Any]:
    return {
        jc.Table: "pandas.DataFrame",
    }


@map_category
def paths() -> Dict[Any, Any]:
    return {
        jc.Character_Arr: str,
        jc.Character: str,
        jc.String: str,
        jc.File: "pathlib.PosixPath",
        jc.Path: "pathlib.PosixPath",
    }


@map_category
def enums() -> Dict[Any, Any]:
    return {
        jc.Enum: "enum.Enum",
    }


@map_category
def dates() -> Dict[Any, Any]:
    return {
        jc.Date: "datetime.datetime",
    }