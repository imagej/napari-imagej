"""
This module is an example of a barebones function plugin for napari

It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from atexit import unregister
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
from napari_imagej._ptypes import generate_ptypes

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
preprocessors = ij.plugin().createInstancesOfType(PreprocessorPlugin)
PostprocessorPlugin = jimport('org.scijava.module.process.PostprocessorPlugin')
postprocessors = ij.plugin().createInstancesOfType(PostprocessorPlugin)
InputHarvester = jimport('org.scijava.widget.InputHarvester')
LoadInputsPreprocessor = jimport('org.scijava.module.process.LoadInputsPreprocessor')
Initializable = jimport('net.imagej.ops.Initializable')

_ptypes = generate_ptypes()

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

def _preprocess_non_inputs(module):
    # preprocess using plugin preprocessors
    logging.debug('Preprocessing...')
    # for i in preprocessors:
    for preprocessor in preprocessors:
        if isinstance(preprocessor, InputHarvester) or isinstance(preprocessor, LoadInputsPreprocessor):
            # STOP AT INPUT HARVESTING
            break
        else:
            print(preprocessor)
            preprocessor.process(module)

def _preprocess_remaining_inputs(module, inputs, unresolved_inputs, user_resolved_inputs):
    resolved_java_args = ij.py.jargs(*user_resolved_inputs)
    # resolve remaining inputs
    for i in range(len(resolved_java_args)):
        name = unresolved_inputs[i].getName()
        obj = resolved_java_args[i]
        print('Resolving ', name, ' with ', obj)
        module.setInput(name, obj)
        module.resolveInput(name)

    # sanity check: ensure all inputs resolved
    for input in inputs:
        if not module.isInputResolved(input.getName()):
            print("Input ", input.getName(), ' is not resolved!')
    
    return resolved_java_args


def _filter_unresolved_inputs(module, inputs):
    unresolved_inputs = list(filter(lambda i: not module.isResolved(i.getName()), inputs))
    # HACK: Specifically w.r.t. Ops, the Module can create optional, mutated inputs.
    unresolved_inputs = list(filter(lambda i: not (i.isOutput() and not i.isRequired()), unresolved_inputs))
    return unresolved_inputs

def _initialize_module(module):
    try:
        module.initialize()
        # HACK: module.initialize() does not seem to call Initializable.initialize()
        if isinstance(module.getDelegateObject(), Initializable):
            module.getDelegateObject().initialize()
    except Exception as e:
        print("Initialization Error")
        print(e.stacktrace())

def _run_module(module):
        try:
            module.run()
        except Exception as e:
            print("Run Error")
            print(e.stacktrace())

def _postprocess_module(module):
    for postprocessor in postprocessors:
        postprocessor.process(module)

def _modify_function_signature(function, inputs, module_info):
    from inspect import signature, Parameter, Signature
    try:
        sig = signature(function)
        function.__signature__ = sig.replace(parameters=[
            Parameter(
                str(i.getName()),
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=_ptype(i.getType())
            )
            for i in inputs
        ], return_annotation=_return_type(module_info))
    except Exception as e:
        print(e)

def _module_output(module):
    outputs = ij.py.from_java(module.getOutputs())
    return outputs.popitem()[1] if len(outputs) == 1 else outputs

def _functionify_module_execution(module, info) -> Callable:
    # Run preprocessors until we hit input harvesting
    _preprocess_non_inputs(module)

    # Determine which inputs must be resolved by the user
    unresolved_inputs = _filter_unresolved_inputs(module, info.inputs())

    # Package the rest of the execution into a widget
    def execute_module(*user_resolved_inputs):

        # Resolve remaining inputs
        resolved_java_args = _preprocess_remaining_inputs(module, info.inputs(), unresolved_inputs, user_resolved_inputs)
        
        # run module
        logger.debug(f'run_module: {execute_module.__qualname__}({resolved_java_args}) -- {info.getIdentifier()}')
        _initialize_module(module)
        _run_module(module)

        # postprocess
        _postprocess_module(module)

        # get output
        logger.debug(f'run_module: execution complete')
        result = _module_output(module)
        logger.debug(f'run_module: result = {result}')
        return result

    # Format napari metadata
    menu_string = " > ".join(str(p) for p in info.getMenuPath())
    execute_module.__doc__ = f"Invoke ImageJ2's {menu_string} command"
    execute_module.__name__ = re.sub('[^a-zA-Z0-9_]', '_', menu_string)
    execute_module.__qualname__ = menu_string

    # Rewrite the function signature to match the module inputs.
    _modify_function_signature(execute_module, unresolved_inputs, info)

    # Add the type hints as annotations metadata as well.
    # Without this, magicgui doesn't pick up on the types.
    type_hints = {str(i.getName()): _ptype(i.getType()) for i in unresolved_inputs}
    out_types = [o.getType() for o in info.outputs()]
    type_hints['return'] = _ptype(out_types[0]) if len(out_types) == 1 else dict
    execute_module.__annotation__ = type_hints

    execute_module._info = info
    return execute_module


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
                self.focused_action_buttons[i].clicked.connect(lambda : self._execute_module(self.results[row].info()))
            else: 
                preprocessors = ij.plugin().getPluginsOfClass('org.scijava.module.process.PreprocessorPlugin')
                postprocessors = ij.plugin().getPluginsOfClass('org.scijava.module.process.PostprocessorPlugin')
                self.focused_action_buttons[i].clicked.connect(lambda : ij.module().run(self.results[row].info(), preprocessors, postprocessors, JObject({}, JClass('java.util.Map'))))
            self.focused_action_buttons[i].show()
    
    def _execute_module(self, moduleInfo):
        logging.debug('Creating module...')
        module = ij.module().createModule(moduleInfo)

        # preprocess using napari GUI
        logging.debug('Processing...')
        func = _functionify_module_execution(module, moduleInfo)
        self.viewer.window.add_function_widget(func, name=ij.py.from_java(moduleInfo.getTitle()))
    
        








