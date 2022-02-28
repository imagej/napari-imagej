from typing import Any, Callable, Dict, Tuple, Type
from scyjava import jimport
import numpy as np


class PTypes:
    def __init__(self):
        # Numbers
        self._numbers = {
            jimport('[B'):                                            int,
            jimport('[S'):                                            int,
            jimport('[I'):                                            int,
            jimport('[J'):                                            int,
            jimport('[F'):                                            float,
            jimport('[D'):                                            float,
            jimport('java.lang.Byte'):                                int,
            jimport('java.lang.Short'):                               int,
            jimport('java.lang.Integer'):                             int,
            jimport('java.lang.Long'):                                int,
            jimport('java.lang.Float'):                               float,
            jimport('java.lang.Double'):                              float,
            jimport('java.math.BigInteger'):                          int,
            jimport('net.imglib2.type.numeric.IntegerType'):          int,
            jimport('net.imglib2.type.numeric.RealType'):             float,
            jimport('net.imglib2.type.numeric.ComplexType'):          complex,
        }

        # Booleans
        self._booleans = {
            jimport('[Z'):                                            bool,
            jimport('java.lang.Boolean'):                             bool,
            jimport('net.imglib2.type.BooleanType'):                  bool,
        }

        # Strings
        self._strings = {
            jimport('[C'):                                            str,
            jimport('java.lang.Character'):                           str,
            jimport('java.lang.String'):                              str,
        }

        # Images
        self._images = {
            jimport('net.imglib2.RandomAccessible'):                  'napari.types.ImageData',
            jimport('net.imglib2.RandomAccessibleInterval'):          'napari.types.ImageData',
            jimport('net.imglib2.IterableInterval'):                  'napari.types.ImageData',
            jimport('ij.ImagePlus'):                                  'napari.types.ImageData'
        }

        # Points
        self._points = {
            jimport('net.imglib2.roi.geom.real.PointMask'):           'napari.types.PointsData',
            jimport('net.imglib2.roi.geom.real.RealPointCollection'): 'napari.types.PointsData',
        }

        # Shapes
        self._shapes = {
            jimport('net.imglib2.roi.geom.real.Line'):                'napari.layers.Shapes',
            jimport('net.imglib2.roi.geom.real.Box'):                 'napari.layers.Shapes',
            jimport('net.imglib2.roi.geom.real.SuperEllipsoid'):      'napari.layers.Shapes',
            jimport('net.imglib2.roi.geom.real.Polygon2D'):           'napari.layers.Shapes',
            jimport('net.imglib2.roi.geom.real.Polyline'):            'napari.layers.Shapes',
            jimport('net.imagej.roi.ROITree'):                        'napari.layers.Shapes',
        }

        # Surfaces
        self._surfaces = {
            jimport('net.imagej.mesh.Mesh'):                          'napari.types.SurfaceData'
        }

        # Labels
        self._labels = {
            jimport('net.imglib2.roi.labeling.ImgLabeling'):          'napari.layers.Labels'
        }

        # Color tables
        self._color_tables = {
            jimport('net.imglib2.display.ColorTable'):                'vispy.color.Colormap',
        }

        # Pandas dataframe
        self._pd = {
            jimport('org.scijava.table.Table'):                       'pandas.DataFrame',
        }

        # Paths
        self._paths = {
            jimport('java.io.File'):                                  'pathlib.PosixPath',
            jimport('java.nio.file.Path'):                            'pathlib.PosixPath',
        }

        # Enums
        self._enums = {
            jimport('java.lang.Enum'):                                'enum.Enum',
        }

        # Dates
        self._dates = {
            jimport('java.util.Date'):                                'datetime.datetime',
        }

        self.ptypes = {
            **self._numbers,
            **self._booleans,
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
