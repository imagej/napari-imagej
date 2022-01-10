"""
This module is an example of a barebones function plugin for napari

It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    import napari

import os, re
import imagej
from scyjava import config, jimport
from collections.abc import Mapping
from qtpy.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QScrollArea, QLineEdit, QTableWidget, QAbstractItemView, QHeaderView, QTableWidgetItem, QLabel
from jpype import JObject, JClass, JProxy
import magicgui
from napari import Viewer

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) #TEMP

# TEMP: Avoid the issues caused by https://github.com/imagej/pyimagej/issues/160
config.add_repositories({'scijava.public': 'https://maven.scijava.org/content/groups/public'})
config.endpoints.append('io.scif:scifio:0.43.1')

logger.debug('Initializing ImageJ2')
config.add_option(f'-Dimagej.dir={os.getcwd()}') #TEMP
ij = imagej.init(headless=False)
ij.log().setLevel(4)
logger.debug(f'Initialized at version {ij.getVersion()}')

Object = jimport('java.lang.Object')
getClass = Object.class_.getMethod('getClass')

def which_class(o):
    return getClass.invoke(o)

PreprocessorPlugin = jimport('org.scijava.module.process.PreprocessorPlugin')
PostprocessorPlugin = jimport('org.scijava.module.process.PostprocessorPlugin')
InputHarvester = jimport('org.scijava.widget.InputHarvester')
LoadInputsPreprocessor = jimport('org.scijava.module.process.LoadInputsPreprocessor')

Initializable = jimport('net.imagej.ops.Initializable')

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
    # ImageJ2 types.
    jimport('net.imagej.mesh.Mesh'):                          'napari.types.SurfaceData'
}

# TODO: Move this function to scyjava.convert and/or ij.py.
def _ptype(java_type):
    for jtype, ptype in _ptypes.items():
        if jtype.class_.isAssignableFrom(java_type): return ptype
    for jtype, ptype in _ptypes.items():
        if ij.convert().supports(java_type, jtype): return ptype
    raise ValueError(f'Unsupported Java type: {java_type}')


def _return_type(info):
    out_types = [o.getType() for o in info.outputs()]
    if len(out_types) == 0: return None
    if len(out_types) == 1: return _ptype(out_types[0])
    return dict


# Credit: https://gist.github.com/xhlulu/95117e225b7a1aa806e696180a72bdd0

def _resolve_remaining_inputs(module, info, postprocessors) -> Callable:
    unresolved_inputs = list(filter(lambda i: not module.isResolved(i.getName()), info.inputs()))
    # HACK: Specifically w.r.t. Ops, the Module can create optional, mutated inputs.
    unresolved_inputs = list(filter(lambda i: not (i.isOutput() and not i.isRequired()), unresolved_inputs))
    print("Unresolved: ", [(i.getName(), i.getType()) for i in unresolved_inputs])
    print("All: ", [(i.getName(), i.getType()) for i in info.inputs()])
    def run_module(*kwargs):
        args = ij.py.jargs(*kwargs)
        print(args)
        # resolve remaining inputs
        for i in range(len(args)):
            name = unresolved_inputs[i].getName()
            obj = args[i]
            print('Resolving ', name, ' with ', obj)
            module.setInput(name, obj)
            module.resolveInput(name)
        
        # sanity check: ensure all inputs resolved
        for input in info.inputs():
            if not module.isInputResolved(input.getName()):
                print("Input ", input.getName(), ' is not resolved!')

        # run module
        logger.debug(f'run_module: {run_module.__qualname__}({args}) -- {info.getIdentifier()}')
        try:
            module.initialize()
            # HACK: module.initialize() does not seem to call Initializable.initialize()
            if isinstance(module.getDelegateObject(), Initializable):
                module.getDelegateObject().initialize()
        except Exception as e:
            print("Initialization Error")
            print(e.stacktrace())

        try:
            module.run()
        except Exception as e:
            print("Run Error")
            print(e.stacktrace())
        # postprocess
        for postprocessor in postprocessors:
            postprocessor.process(module)

        global fun
        fun = module

        # get output
        logger.debug(f'run_module: execution complete')
        outputs = ij.py.from_java(module.getOutputs())
        result = outputs.popitem()[1] if len(outputs) == 1 else outputs
        logger.debug(f'run_module: result = {result}')
        return result

    menu_string = " > ".join(str(p) for p in info.getMenuPath())
    run_module.__doc__ = f"Invoke ImageJ2's {menu_string} command"
    run_module.__name__ = re.sub('[^a-zA-Z0-9_]', '_', menu_string)
    run_module.__qualname__ = menu_string

    # Rewrite the function signature to match the module inputs.
    from inspect import signature, Parameter, Signature
    try:
        sig = signature(run_module)
        run_module.__signature__ = sig.replace(parameters=[
            Parameter(
                str(i.getName()),
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=_ptype(i.getType())
            )
            for i in unresolved_inputs
        ], return_annotation=_return_type(info))
    except Exception as e:
        print(e)

    # Add the type hints as annotations metadata as well.
    # Without this, magicgui doesn't pick up on the types.
    type_hints = {str(i.getName()): _ptype(i.getType()) for i in unresolved_inputs}
    out_types = [o.getType() for o in info.outputs()]
    type_hints['return'] = _ptype(out_types[0]) if len(out_types) == 1 else dict
    run_module.__annotation__ = type_hints

    run_module._info = info
    return run_module


class ExampleQWidget(QWidget):

    def __init__(self, napari_viewer: Viewer):
        super().__init__()
        self.viewer = napari_viewer

        self.setLayout(QVBoxLayout())

        ## Search Bar
        searchWidget = QWidget()
        searchWidget.setLayout(QHBoxLayout())
        searchWidget.layout().addWidget(self._generate_searchbar())
        
        self.layout().addWidget(searchWidget)

        self.searcher = self._generate_searcher()
        self.searchService = self._generate_search_service()

        ## Results box
        labels = ['Module: ']
        self.results = []
        self.maxResults = 12
        self.tableWidget = QTableWidget(self.maxResults, len(labels))
        self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableWidget.setHorizontalHeaderLabels(labels)
        self.tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tableWidget.verticalHeader().hide()
        self.tableWidget.setShowGrid(False)
        self.tableWidget.cellClicked.connect(self._highlight_module)
        self.layout().addWidget(self.tableWidget)

        ## Module highlighter
        self.focus_widget = QWidget()
        self.focus_widget.setLayout(QVBoxLayout())
        self.focused_module = QLabel()
        self.focus_widget.layout().addWidget(self.focused_module)
        self.focused_module.setText("Display Module Here")
        self.layout().addWidget(self.focus_widget)
        self.focused_action_buttons = []

    def _generate_searchbar(self):
        searchbar = QLineEdit()
        searchbar.textChanged.connect(self._search)
        searchbar.returnPressed.connect(lambda :self._highlight_module(0, 0))
        return searchbar

    def _generate_searcher(self):
        pluginService = ij.get('org.scijava.plugin.PluginService')
        moduleServiceCls = jimport('org.scijava.search.module.ModuleSearcher')
        searcherCls = jimport('org.scijava.search.Searcher')
        info = pluginService.getPlugin(moduleServiceCls, searcherCls)
        searcher = info.createInstance()
        ij.context().inject(searcher)
        return searcher

    def _generate_search_service(self):
        return ij.get('org.scijava.search.SearchService')

    def _on_click(self):
        print("napari has", len(self.viewer.layers), "layers")

    def _search(self, text):
        # TODO: Consider adding a button to toggle fuzziness
        breakpoint()
        self.results = self.searcher.search(text, True)
        for i in range(len(self.results)):
            name = ij.py.from_java(self.results[i].name())
            self.tableWidget.setItem(i, 0, QTableWidgetItem(name))
        for i in range(len(self.results), self.maxResults):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(""))

    def _highlight_module(self, row: int, col: int):
        # Print highlighted module
        name = ij.py.from_java(self.results[row].name())
        self.focused_module.setText(name)

        # Create buttons for each action
        self.focused_actions = self.searchService.actions(self.results[row])
        activated_actions = len(self.focused_action_buttons)
        # Hide buttons if we have more than needed
        while activated_actions > len(self.focused_actions):
            activated_actions = activated_actions - 1
            self.focused_action_buttons[activated_actions].hide()
        # Create buttons if we need more than we have
        while len(self.focused_action_buttons) < len(self.focused_actions):
            button = QPushButton()
            self.focused_action_buttons.append(button)
            self.focus_widget.layout().addWidget(button)
        # Rename buttons to reflect focused module's actions
        for i in range(len(self.focused_actions)):
            action_name = ij.py.from_java(self.focused_actions[i].toString())
            self.focused_action_buttons[i].show()
            self.focused_action_buttons[i].setText(action_name)
            self.focused_action_buttons[i].disconnect()
            if action_name == "Run":
                self.focused_action_buttons[i].clicked.connect(lambda : self._run_module(self.results[row].info()))
            else: 
                preprocessors = ij.plugin().getPluginsOfClass('org.scijava.module.process.PreprocessorPlugin')
                postprocessors = ij.plugin().getPluginsOfClass('org.scijava.module.process.PostprocessorPlugin')
                self.focused_action_buttons[i].clicked.connect(lambda : ij.module().run(self.results[row].info(), preprocessors, postprocessors, JObject({}, JClass('java.util.Map'))))
            self.focused_action_buttons[i].show()
    
    def _run_module(self, moduleInfo):
        logging.debug('Creating module...')
        module = ij.module().createModule(moduleInfo)

        self._preprocess_module(module)

        # preprocess using napari GUI
        print('Processing...')
        postprocessors = ij.plugin().createInstancesOfType(PostprocessorPlugin)
        func = _resolve_remaining_inputs(module, moduleInfo, postprocessors)
        self.viewer.window.add_function_widget(func)
    
    def _preprocess_module(self, module):
        # preprocess using plugin preprocessors
        logging.debug('Preprocessing...')
        preprocessors = ij.plugin().createInstancesOfType(PreprocessorPlugin)
        # for i in preprocessors:
        #     print(i)
        for preprocessor in preprocessors:
            if isinstance(preprocessor, InputHarvester) or isinstance(preprocessor, LoadInputsPreprocessor):
                # STOP AT INPUT HARVESTING
                print('Found an Input Harvester; delegating input fulfillment to user')
                break
            else:
                print(preprocessor)
                preprocessor.process(module)
        








