"""
This module is an example of a barebones function plugin for napari

It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING

from napari_plugin_engine import napari_hook_implementation

if TYPE_CHECKING:
    import napari

import os, re
import imagej
from scyjava import config, jimport

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) #TEMP

logger.debug('Initializing ImageJ2')
config.add_option(f'-Dimagej.dir={os.getcwd()}') #TEMP
ij = imagej.init()
logger.debug(f'Initialized at version {ij.getVersion()}')

# Dispose the SciJava context when Python shuts down.
# TODO: Consider registering atexit hook in imagej.init.
import atexit; atexit.register(lambda: ij.dispose())
logger.debug('SciJava cleanup hook registered')

_ptypes = {
    # Primitives.
    jimport('[B'):                                            int,
    jimport('[S'):                                            int,
    jimport('[I'):                                            int,
    jimport('[J'):                                            int,
    jimport('[F'):                                            float,
    jimport('[D'):                                            float,
    jimport('[Z'):                                            bool,
    jimport('[C'):                                            str,
    # Primitive wrappers.
    jimport('java.lang.Boolean'):                             bool,
    jimport('java.lang.Character'):                           str,
    jimport('java.lang.Byte'):                                int,
    jimport('java.lang.Short'):                               int,
    jimport('java.lang.Integer'):                             int,
    jimport('java.lang.Long'):                                int,
    jimport('java.lang.Float'):                               float,
    jimport('java.lang.Double'):                              float,
    # Core library types.
    jimport('java.math.BigInteger'):                          int,
    jimport('java.lang.String'):                              str,
    jimport('java.lang.Enum'):                                'enum.Enum',
    jimport('java.io.File'):                                  'pathlib.PosixPath',
    jimport('java.nio.file.Path'):                            'pathlib.PosixPath',
    jimport('java.util.Date'):                                'datetime.datetime',
    # SciJava types.
    jimport('org.scijava.table.Table'):                       'pandas.DataFrame',
    # ImgLib2 types.
    jimport('net.imglib2.type.BooleanType'):                  bool,
    jimport('net.imglib2.type.numeric.IntegerType'):          int,
    jimport('net.imglib2.type.numeric.RealType'):             float,
    jimport('net.imglib2.type.numeric.ComplexType'):          complex,
    jimport('net.imglib2.RandomAccessibleInterval'):          'napari.types.ImageData',
    jimport('net.imglib2.roi.geom.real.PointMask'):           'napari.types.PointsData',
    jimport('net.imglib2.roi.geom.real.RealPointCollection'): 'napari.types.PointsData',
    jimport('net.imglib2.roi.labeling.ImgLabeling'):          'napari.types.LabelsData',
    jimport('net.imglib2.roi.geom.real.Line'):                'napari.types.ShapesData',
    jimport('net.imglib2.roi.geom.real.Box'):                 'napari.types.ShapesData',
    jimport('net.imglib2.roi.geom.real.SuperEllipsoid'):      'napari.types.ShapesData',
    jimport('net.imglib2.roi.geom.real.Polygon2D'):           'napari.types.ShapesData',
    jimport('net.imglib2.roi.geom.real.Polyline'):            'napari.types.ShapesData',
    jimport('net.imglib2.display.ColorTable'):                'vispy.color.Colormap',
    # ImageJ2 types.
    jimport('net.imagej.mesh.Mesh'):                          'napari.types.SurfaceData'
}


# TODO: Move this function to scyjava.convert and/or ij.py.
def _ptype(java_type):
    for jtype, ptype in _ptypes.items():
        if isinstance(java_type, jtype): return ptype
    for jtype, ptype in _ptypes.items():
        if ij.convert().supports(java_type, jtype): return ptype
    raise ValueError(f'Unsupported Java type: {java_type}')


def _return_type(info):
    out_types = [o.getType() for o in info.outputs()]
    if len(out_types) == 0: return None
    if len(out_types) == 1: return _ptype(out_types[0])
    return dict


def _usable(info):
    #if not info.canRunHeadless(): return False
    menu_path = info.getMenuPath()
    return menu_path is not None and len(menu_path) > 0


# Credit: https://gist.github.com/xhlulu/95117e225b7a1aa806e696180a72bdd0

def _functionify(info):
    def run_module(**kwargs):
        args = kwargs #locals()
        logger.debug(f'run_module: {run_module.__qualname__}({args}) -- {info.getIdentifier()}')
        m = ij.module().run(info, True, ij.py.jargs(args)).get()
        logger.debug(f'run_module: execution complete')
        outputs = ij.py.from_java(m.getOutputs())
        result = outputs.popitem()[1] if len(outputs) == 1 else outputs
        logger.debug(f'run_module: result = {result}')
        return result

    menu_string = " > ".join(str(p) for p in info.getMenuPath())
    run_module.__doc__ = f"Invoke ImageJ2's {menu_string} command"
    run_module.__name__ = re.sub('[^a-zA-Z0-9_]', '_', menu_string)
    run_module.__qualname__ = menu_string

    # Rewrite the function signature to match the module inputs.
    from inspect import signature, Parameter
    try:
        sig = signature(run_module)
        run_module.__signature__ = sig.replace(parameters=[
            Parameter(
                str(i.getName()),
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=_ptype(i.getType())
            )
            for i in info.inputs()
        ], return_annotation=_return_type(info))
    except Exception as e:
        print(e)

    run_module._info = info
    return run_module


@napari_hook_implementation
def napari_experimental_provide_function():
    logger.debug('Converting SciJava modules to Python functions')
    return [_functionify(info) for info in ij.module().getModules() if _usable(info)]
