from collections import OrderedDict
from typing import List

from jpype import JBoolean, JByte, JChar, JDouble, JFloat, JInt, JLong, JShort

from napari_imagej.setup_imagej import jc


class TypeMappings:
    """
    The definitive set of "equal" Java and Python types.
    This map allows us to determine the "best" Python type for the conversion
    of any Java object, or the "best" Java type for the conversion of any
    Python object.
    """

    def __init__(self):

        # Strings
        self._strings = {
            JChar: str,
            jc.Character_Arr: str,
            jc.Character: str,
            jc.String: str,
        }

        # Booleans
        self._booleans = {
            JBoolean: bool,
            jc.Boolean_Arr: List[bool],
            jc.Boolean: bool,
            jc.BooleanType: bool,
        }

        # Numbers
        self._numbers = {
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
        }

        # Images
        self._images = {
            jc.RandomAccessibleInterval: "napari.layers.Image",
            jc.RandomAccessible: "napari.layers.Image",
            jc.IterableInterval: "napari.layers.Image",
            # TODO: remove 'add_legacy=False' -> struggles with LegacyService
            # This change is waiting on a new pyimagej release
            # java_import('ij.ImagePlus'):
            # 'napari.types.ImageData'
        }

        # Points
        self._points = {
            jc.PointMask: "napari.types.PointsData",
            jc.RealPointCollection: "napari.types.PointsData",
        }

        # Shapes
        self._shapes = {
            jc.Line: "napari.layers.Shapes",
            jc.Box: "napari.layers.Shapes",
            jc.SuperEllipsoid: "napari.layers.Shapes",
            jc.Polygon2D: "napari.layers.Shapes",
            jc.Polyline: "napari.layers.Shapes",
            jc.ROITree: "napari.layers.Shapes",
        }

        # Surfaces
        self._surfaces = {jc.Mesh: "napari.types.SurfaceData"}

        # Labels
        self._labels = {jc.ImgLabeling: "napari.layers.Labels"}

        # Color tables
        self._color_tables = {
            jc.ColorTable: "vispy.color.Colormap",
        }

        # Pandas dataframe
        self._pd = {
            jc.Table: "pandas.DataFrame",
        }

        # Paths
        self._paths = {
            jc.Character_Arr: str,
            jc.Character: str,
            jc.String: str,
            jc.File: "pathlib.PosixPath",
            jc.Path: "pathlib.PosixPath",
        }

        # Enums
        self._enums = {
            jc.Enum: "enum.Enum",
        }

        # Dates
        self._dates = {
            jc.Date: "datetime.datetime",
        }

        # NB we put booleans over numbers because otherwise some of the
        # boolean types will satisfy a numbers type.
        # TODO: Consider adding priorities
        self.ptypes = OrderedDict(
            {
                **self._booleans,
                **self._numbers,
                **self._strings,
                **self._labels,
                **self._images,
                **self._points,
                **self._shapes,
                **self._surfaces,
                **self._color_tables,
                **self._pd,
                **self._paths,
                **self._enums,
                **self._dates,
            }
        )

        self._napari_layer_types = {
            **self._images,
            **self._points,
            **self._shapes,
            **self._surfaces,
            **self._labels,
        }.keys()

    def displayable_in_napari(self, data):
        return any(filter(lambda x: isinstance(data, x), self._napari_layer_types))

    def type_displayable_in_napari(self, type):
        return any(filter(lambda x: issubclass(type, x), self._napari_layer_types))
