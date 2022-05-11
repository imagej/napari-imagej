from typing import List
from napari_imagej.setup_imagej import java_import


class TypeMappings:
    """
    The definitive set of "equal" Java and Python types.
    This map allows us to determine the "best" Python type for the conversion
    of any Java object, or the "best" Java type for the conversion of any
    Python object.
    """
    def __init__(self):
        # Numbers
        self._numbers = {
            java_import('java.lang.Byte'):                                int,
            java_import('[B'):                                            List[int],
            java_import('java.lang.Short'):                               int,
            java_import('[S'):                                            List[int],
            java_import('java.lang.Integer'):                             int,
            java_import('[I'):                                            List[int],
            java_import('java.lang.Long'):                                int,
            java_import('[J'):                                            List[int],
            java_import('java.lang.Float'):                               float,
            java_import('[F'):                                            List[float],
            java_import('java.lang.Double'):                              float,
            java_import('[D'):                                            List[float],
            java_import('java.math.BigInteger'):                          int,
            java_import('net.imglib2.type.numeric.IntegerType'):          int,
            java_import('net.imglib2.type.numeric.RealType'):             float,
            java_import('net.imglib2.type.numeric.ComplexType'):          complex,
        }

        # Booleans
        self._booleans = {
            java_import('[Z'):                                            List[bool],
            java_import('java.lang.Boolean'):                             bool,
            java_import('net.imglib2.type.BooleanType'):                  bool,
        }

        # Strings
        self._strings = {
            java_import('[C'):                                            str,
            java_import('java.lang.Character'):                           str,
            java_import('java.lang.String'):                              str,
        }

        # Images
        self._images = {
            java_import('net.imglib2.RandomAccessible'):                  'napari.types.ImageData',
            java_import('net.imglib2.RandomAccessibleInterval'):          'napari.types.ImageData',
            java_import('net.imglib2.IterableInterval'):                  'napari.types.ImageData',
            # TODO: remove 'add_legacy=False' -> struggles with LegacyService
            # This change is waiting on a new pyimagej release
            # java_import('ij.ImagePlus'):                                  'napari.types.ImageData'
        }

        # Points
        self._points = {
            java_import('net.imglib2.roi.geom.real.PointMask'):           'napari.types.PointsData',
            java_import('net.imglib2.roi.geom.real.RealPointCollection'): 'napari.types.PointsData',
        }

        # Shapes
        self._shapes = {
            java_import('net.imglib2.roi.geom.real.Line'):                'napari.layers.Shapes',
            java_import('net.imglib2.roi.geom.real.Box'):                 'napari.layers.Shapes',
            java_import('net.imglib2.roi.geom.real.SuperEllipsoid'):      'napari.layers.Shapes',
            java_import('net.imglib2.roi.geom.real.Polygon2D'):           'napari.layers.Shapes',
            java_import('net.imglib2.roi.geom.real.Polyline'):            'napari.layers.Shapes',
            java_import('net.imagej.roi.ROITree'):                        'napari.layers.Shapes',
        }

        # Surfaces
        self._surfaces = {
            java_import('net.imagej.mesh.Mesh'):                          'napari.types.SurfaceData'
        }

        # Labels
        self._labels = {
            java_import('net.imglib2.roi.labeling.ImgLabeling'):          'napari.layers.Labels'
        }

        # Color tables
        self._color_tables = {
            java_import('net.imglib2.display.ColorTable'):                'vispy.color.Colormap',
        }

        # Pandas dataframe
        self._pd = {
            java_import('org.scijava.table.Table'):                       'pandas.DataFrame',
        }

        # Paths
        self._paths = {
            java_import('java.io.File'):                                  'pathlib.PosixPath',
            java_import('java.nio.file.Path'):                            'pathlib.PosixPath',
        }

        # Enums
        self._enums = {
            java_import('java.lang.Enum'):                                'enum.Enum',
        }

        # Dates
        self._dates = {
            java_import('java.util.Date'):                                'datetime.datetime',
        }

        # NB we put booleans over numbers because otherwise some of the boolean types will satisfy a numbers type.
        # TODO: Consider adding priorities
        self.ptypes = {
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
            **self._dates}

        self._napari_layer_types = {
            **self._images,
            **self._points,
            **self._shapes,
            **self._surfaces,
            **self._labels
        }.keys()

    def displayable_in_napari(self, data):
        return any(filter(lambda x: isinstance(data, x), self._napari_layer_types))

    def type_displayable_in_napari(self, type):
        return any(filter(lambda x: issubclass(type, x), self._napari_layer_types))
