from scyjava import jimport

def generate_ptypes():
    """
    """
    # Primitives.
    _primitives = {
        jimport('[B'):                                            int,
        jimport('[S'):                                            int,
        jimport('[I'):                                            int,
        jimport('[J'):                                            int,
        jimport('[F'):                                            float,
        jimport('[D'):                                            float,
        jimport('[Z'):                                            bool,
        jimport('[C'):                                            str,
    }

    # Primitive wrappers.
    _primitive_wrappers = {
        jimport('java.lang.Boolean'):                             bool,
        jimport('java.lang.Character'):                           str,
        jimport('java.lang.Byte'):                                int,
        jimport('java.lang.Short'):                               int,
        jimport('java.lang.Integer'):                             int,
        jimport('java.lang.Long'):                                int,
        jimport('java.lang.Float'):                               float,
        jimport('java.lang.Double'):                              float,
    }

    # Core library types.
    _core_library_types = {
        jimport('java.math.BigInteger'):                          int,
        jimport('java.lang.String'):                              str,
        jimport('java.lang.Enum'):                                'enum.Enum',
        jimport('java.io.File'):                                  'pathlib.PosixPath',
        jimport('java.nio.file.Path'):                            'pathlib.PosixPath',
        jimport('java.util.Date'):                                'datetime.datetime',
    }

    # SciJava types.
    _scijava_types = {
        jimport('org.scijava.table.Table'):                       'pandas.DataFrame',
    }

    # ImgLib2 types.
    _imglib2_types = {
        jimport('net.imglib2.type.BooleanType'):                  bool,
        jimport('net.imglib2.type.numeric.IntegerType'):          int,
        jimport('net.imglib2.type.numeric.RealType'):             float,
        jimport('net.imglib2.type.numeric.ComplexType'):          complex,
        jimport('net.imglib2.RandomAccessibleInterval'):          'napari.types.ImageData',
        jimport('net.imglib2.IterableInterval'):                  'napari.types.ImageData',
        jimport('net.imglib2.roi.geom.real.PointMask'):           'napari.types.PointsData',
        jimport('net.imglib2.roi.geom.real.RealPointCollection'): 'napari.types.PointsData',
        jimport('net.imglib2.roi.labeling.ImgLabeling'):          'napari.types.LabelsData',
        jimport('net.imglib2.roi.geom.real.Line'):                'napari.types.ShapesData',
        jimport('net.imglib2.roi.geom.real.Box'):                 'napari.types.ShapesData',
        jimport('net.imglib2.roi.geom.real.SuperEllipsoid'):      'napari.types.ShapesData',
        jimport('net.imglib2.roi.geom.real.Polygon2D'):           'napari.types.ShapesData',
        jimport('net.imglib2.roi.geom.real.Polyline'):            'napari.types.ShapesData',
        jimport('net.imglib2.display.ColorTable'):                'vispy.color.Colormap',
    }

    # ImageJ1 types.
    _imagej1_types = {
        jimport('ij.ImagePlus'):                                  'napari.types.ImageData'
    }

    # ImageJ2 types.
    _imagej2_types = {
        jimport('net.imagej.mesh.Mesh'):                          'napari.types.SurfaceData'
    }

    return {**_primitives, **_primitive_wrappers, **_core_library_types, **_scijava_types, **_imglib2_types, **_imagej1_types, **_imagej2_types}