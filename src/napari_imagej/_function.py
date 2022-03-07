"""
This module is an example of a barebones function plugin for napari

It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
import imagej
from scyjava import config, jimport, when_jvm_starts, Priority
from magicgui import magicgui
from napari import Viewer
from qtpy.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
    QLabel,
)
from inspect import signature, Signature, Parameter, _empty
from napari_imagej._ptypes import PTypes
from napari_imagej._napari_converters import init_napari_converters

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # TEMP

# TEMP: Avoid issues caused by https://github.com/imagej/pyimagej/issues/160
config.add_repositories(
    {"scijava.public": "https://maven.scijava.org/content/groups/public"}
)
config.endpoints.append("io.scif:scifio:0.43.1")

# Initialize ImageJ
logger.debug("Initializing ImageJ2")
config.add_option(f"-Dimagej.dir={os.getcwd()}")  # TEMP
# TODO: change 'headless=True' -> 'mode=imagej.Mode.HEADLESS'
# This change is waiting on a new pyimagej release
ij = imagej.init(headless=True)
logger.debug(f"Initialized at version {ij.getVersion()}")
# ij.log().setLevel(4)

# Import useful classes

Collections = jimport(
    "java.util.Collections"
)
ImgLabeling = jimport(
    "net.imglib2.roi.labeling.ImgLabeling"
)
PreprocessorPlugin = jimport(
    "org.scijava.module.process.PreprocessorPlugin"
)
PostprocessorPlugin = jimport(
    "org.scijava.module.process.PostprocessorPlugin"
)
InputHarvester = jimport(
    "org.scijava.widget.InputHarvester"
)
LoadInputsPreprocessor = jimport(
    "org.scijava.module.process.LoadInputsPreprocessor"
)
DisplayPostprocessor = jimport(
    "org.scijava.display.DisplayPostprocessor"
)
Initializable = jimport(
    "net.imagej.ops.Initializable"
)
ModuleSearcher = jimport(
    "org.scijava.search.module.ModuleSearcher"
)
OpSearcher = jimport(
    "net.imagej.ops.search.OpSearcher"
)
Searcher = jimport(
    "org.scijava.search.Searcher"
)
SearchResult = jimport(
    "org.scijava.search.SearchResult"
)

# Create Java -> Python type mapper
_ptypes: PTypes  = PTypes()


# Install napari <-> java converters
when_jvm_starts(lambda: init_napari_converters(ij))

_PTYPE_CONVERTERS = []

def ptype_converter(priority: int) -> Callable[[Type], Optional[Type]]:
    def converter(func: Callable[[Type], Optional[Type]]): 
        _PTYPE_CONVERTERS.append((func, priority))
        return func
    return converter

# @ptype_converter(priority = Priority.HIGH)
# def stringAsEnumChecker(java_type: Type) -> Optional[Type]:
#     String = jimport('java.lang.String')
#     if String.class_.isAssignableFrom(java_type):
#         if jtype.class_.isAssignableFrom(java_type):
#             return ptype
#     return None

@ptype_converter(priority = Priority.NORMAL)
def isAssignableChecker(java_type: Type) -> Optional[Type]:
    for jtype, ptype in _ptypes.ptypes.items():
        if jtype.class_.isAssignableFrom(java_type):
            return ptype
    return None

@ptype_converter(priority = Priority.LOW)
def canConvertChecker(java_type: Type) -> Optional[Type]:
    for jtype, ptype in _ptypes.ptypes.items():
        if ij.convert().supports(jtype, java_type):
            return ptype
    return None


# TODO: Move this function to scyjava.convert and/or ij.py.
def _ptype(java_type):
    """Returns the Python type associated with the passed java type."""
    for converter, _ in sorted(_PTYPE_CONVERTERS, reverse=True, key=lambda x: x[1]):
        converted = converter(java_type)
        if converted is not None:
            return converted
    raise ValueError(f"Unsupported Java type: {java_type}")


def _return_type(info):
    """Returns the output type of info."""
    out_types = [o.getType() for o in info.outputs()]
    if len(out_types) == 0:
        return None
    if len(out_types) == 1:
        return _ptype(out_types[0])
    return dict


def _preprocess_non_inputs(module):
    """Uses all preprocessors up to the InputHarvesters."""
    # preprocess using plugin preprocessors
    logging.debug("Preprocessing...")
    preprocessors = ij.plugin() \
        .createInstancesOfType(PreprocessorPlugin)
    # for i in preprocessors:
    for preprocessor in preprocessors:
        if isinstance(preprocessor, InputHarvester) or isinstance(
            preprocessor, LoadInputsPreprocessor
        ):
            # STOP AT INPUT HARVESTING
            break
        else:
            preprocessor.process(module)


def _convert_inputs(napari_args):
    """Converts napari inputs to java inputs"""
    return ij.py.jargs(*napari_args)


def _convert_output(j_result):
    """Converts a java output to a napari output"""
    # Convert java type to python type
    return ij.py.from_java(j_result)


def _preprocess_remaining_inputs(
    module, inputs, unresolved_inputs, user_resolved_inputs
):
    """Resolves each input in unresolved_inputs"""
    resolved_java_args = _convert_inputs(user_resolved_inputs)
    # resolve remaining inputs
    for i in range(len(unresolved_inputs)):
        name = unresolved_inputs[i].getName()
        obj = resolved_java_args[i]
        if obj is None and unresolved_inputs[i].isRequired():
            raise ValueError(
                "No selection was made for input {}!".format(name)
            )
        module.setInput(name, obj)
        module.resolveInput(name)

    # sanity check: ensure all inputs resolved
    for input in inputs:
        if input.isRequired() and not module.isInputResolved(input.getName()):
            raise ValueError(
                "No selection was made for input {}!".format(input.getName())
            )

    return resolved_java_args

def _resolvable_or_required(input):
    if input.isRequired(): return True
    try:
        type = _ptype(input.getType())
        return True
    except ValueError:
        return False


def _filter_unresolved_inputs(module, inputs):
    """Returns a list of all inputs that can only be resolved by the user."""
    # Grab all unresolved inputs
    unresolved = list(
        filter(lambda i: not module.isResolved(i.getName()), inputs)
    )
    # Delegate optional output construction to the module
    # We will leave those unresolved
    unresolved = list(
        filter(
            lambda i: not (i.isOutput() and not i.isRequired()),
            unresolved
        )
    )
    # Only leave in the optional parameters that we know how to resolve
    unresolved = list(
        filter(
            _resolvable_or_required,
            unresolved
        )
    )

    return unresolved


def _initialize_module(module):
    """Initializes the passed module."""
    try:
        module.initialize()
        # HACK: module.initialize() does not seem to call
        # Initializable.initialize()
        if isinstance(module.getDelegateObject(), Initializable):
            module.getDelegateObject().initialize()
    except Exception as e:
        print("Initialization Error")
        print(e.stacktrace())


def _run_module(module):
    """Runs the passed module."""
    try:
        module.run()
    except Exception as e:
        print("Run Error")
        print(e.stacktrace())


def _postprocess_module(module):
    """Runs all known postprocessors on the passed module."""
    # Discover all postprocessors
    postprocessors = ij.plugin().createInstancesOfType(PostprocessorPlugin)
    # Run all discovered postprocessors
    for postprocessor in postprocessors:
        if isinstance(postprocessor, DisplayPostprocessor):
            # HACK: This particular postprocessor is trying to create a Display for lots of different types. Some of those types (specifically ImgLabelings) make this guy throw Exceptions...
            # We are going to ignore it until it behaves (see https://github.com/imagej/imagej-common/issues/100 )
            continue
        print('Postprocessing with ', postprocessor)
        postprocessor.process(module)


# Credit: https://gist.github.com/xhlulu/95117e225b7a1aa806e696180a72bdd0

def _napari_module_param_additions(module_info) -> Dict[str, Tuple[type, Any]]:
    """Returns a set of parameters useful for napari functionality."""
    # additional parameters are in the form "name": (type, default value)
    additional_params: Dict[str, Tuple[type, Any]] = {}
    output_item = module_info.outputs().iterator().next()
    if not _ptypes.type_displayable_in_napari(output_item.getType()):
        additional_params["display_results_in_new_window"] = (bool, False)
    return additional_params

def _is_non_default(input):
    if not input.isRequired(): return False
    if input.getDefaultValue() is not None: return False
    return True


def _sink_optional_inputs(inputs):
    return sorted(inputs, key=lambda x: -1 if _is_non_default(x) else 1)


def _param_default_or_none(input):
    default = input.getDefaultValue()
    if default is not None:
        try:
            default = ij.py.from_java(default)
        except Exception:
            pass
    return default


def _param_annotation(input):
    type = _ptype(input.getType())
    if not input.isRequired():
        type = Optional[type]
    return type


def _module_param(input):
    name = ij.py.from_java(input.getName())
    kind = Parameter.POSITIONAL_OR_KEYWORD
    default = _param_default_or_none(input)
    annotation = _param_annotation(input)

    if _is_non_default(input):
        return Parameter(name=name, kind=kind, annotation=annotation)
    else:
        return Parameter(name=name, kind=kind, default=default, annotation=annotation)


def _modify_function_signature(function, inputs, module_info):
    """Rewrites function with type annotations for all module I/O items."""

    try:
        sig: Signature = signature(function)
        # Grab all options after the module inputs
        inputs = _sink_optional_inputs(inputs)
        module_params = [_module_param(i) for i in inputs]
        other_params = [
            Parameter(
                i[0],
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                annotation=i[1][0],
                default=i[1][1]
            )
            for i in _napari_module_param_additions(module_info).items()
        ]
        all_params = module_params + other_params
        function.__signature__ = sig.replace(
            parameters=all_params, return_annotation=_return_type(module_info)
        )
    except Exception as e:
        print(e)


def _module_output(module):
    """Gets the output of the module, or None if the module has no output."""
    outputs = module.getOutputs()
    output_entry = outputs.entrySet().stream().findFirst()
    if not output_entry.isPresent():
        return None
    output_value = output_entry.get().getValue()
    return output_value


def _napari_specific_parameter(
    func: Callable,
    args: Tuple[Any],
    param: str
) -> Any:
    try:
        index = list(signature(func).parameters.keys()).index(param)
    except ValueError:
        return None

    return args[index]

def _display_result(result: Any, info, viewer: Viewer, external: bool):
    """Displays result in a new widget"""
    def show_tabular_output():
        return ij.py.from_java(result)

    sig: Signature = signature(show_tabular_output)
    show_tabular_output.__signature__ = sig.replace(
        return_annotation=_return_type(info)
    )
    result_widget = magicgui(
        show_tabular_output, result_widget=True, auto_call=True
    )

    if external:
        result_widget.show(run=True)
    else:
        name = "Result: " + ij.py.from_java(info.getTitle())
        viewer.window.add_dock_widget(result_widget, name=name)
    result_widget.update()


def _add_napari_metadata(execute_module: Callable, info, unresolved_inputs):
    module_name = ij.py.from_java(info.getTitle())
    execute_module.__doc__ = f"Invoke ImageJ2's {module_name}"
    execute_module.__name__ = module_name
    execute_module.__qualname__ = module_name

    # Rewrite the function signature to match the module inputs.
    _modify_function_signature(execute_module, unresolved_inputs, info)

    # Add the type hints as annotations metadata as well.
    # Without this, magicgui doesn't pick up on the types.
    type_hints = {
        str(i.getName()): _ptype(i.getType()) for i in unresolved_inputs
    }
    out_types = [o.getType() for o in info.outputs()]
    return_annotation = _ptype(out_types[0]) if len(out_types) == 1 else dict
    type_hints["return"] = return_annotation
    execute_module.__annotation__ = type_hints  # type: ignore

    execute_module._info = info  # type: ignore


def _add_choice(map: dict, key: str, value: Any):
    if value is None: return
    try:
        map[key] = ij.py.from_java(value)
    except Exception:
        pass


def _add_scijava_metadata(info, unresolved_inputs) -> Dict[str, Dict[str, Any]]:
    metadata = {}
    for input in unresolved_inputs:
        key = ij.py.from_java(input.getName())
        param_map = {}
        _add_choice(param_map, "max", input.getMaximumValue())
        _add_choice(param_map, "min", input.getMinimumValue())
        _add_choice(param_map, "step", input.getStepSize())
        _add_choice(param_map, "label", input.getLabel())
        _add_choice(param_map, "tooltip", input.getDescription())
        _add_choice(param_map, "choices", [ij.py.from_java(c) for c in input.getChoices()])

        if len(param_map) > 0:
            metadata[key] = param_map

    return metadata



def _functionify_module_execution(module, info, viewer: Viewer) -> Tuple[Callable, dict]:
    """Converts a module into a Widget that can be added to napari."""
    # Run preprocessors until we hit input harvesting
    _preprocess_non_inputs(module)

    # Determine which inputs must be resolved by the user
    unresolved_inputs = _filter_unresolved_inputs(module, info.inputs())
    unresolved_inputs = _sink_optional_inputs(unresolved_inputs)

    # Package the rest of the execution into a widget
    def module_execute(
        *user_resolved_inputs,
        # display_results_in_new_window: bool = False
    ):

        # Resolve remaining inputs
        resolved_java_args = _preprocess_remaining_inputs(
            module, info.inputs(), unresolved_inputs, user_resolved_inputs
        )

        # run module
        logger.debug(
            f"run_module: {module_execute.__qualname__} \
                ({resolved_java_args}) -- {info.getIdentifier()}"
        )
        _initialize_module(module)
        _run_module(module)

        # postprocess
        _postprocess_module(module)

        # get output
        logger.debug("run_module: execution complete")
        j_result = _module_output(module)
        result = _convert_output(j_result) 
        logger.debug(f"run_module: result = {result}")

        # display result 
        display_externally = _napari_specific_parameter(
            module_execute,
            user_resolved_inputs,
            'display_results_in_new_window'
        )
        if display_externally is not None:
            _display_result(result, info, viewer, display_externally)

        return result

    # Add metadata for widget creation
    _add_napari_metadata(module_execute, info, unresolved_inputs)
    magic_kwargs = _add_scijava_metadata(info, unresolved_inputs)

    return (module_execute, magic_kwargs)


class ImageJWidget(QWidget):
    """The top-level ImageJ widget for napari."""
    def __init__(self, napari_viewer: Viewer):
        super().__init__()
        self.viewer = napari_viewer
        self._ij = ij

        self.setLayout(QVBoxLayout())

        # Search Bar
        self._search_widget: QWidget = QWidget()
        self._search_widget.setLayout(QHBoxLayout())
        self._search_widget.layout().addWidget(self._generate_searchbar())

        self.layout().addWidget(self._search_widget)

        self.searchers, self.resultConverters = self._generate_searchers()
        self.searchService = self._generate_search_service()

        # Results box
        self.results = [[] for _ in range(len(self.searchers))]
        self.resultTables: QWidget
        self.tableWidgets: List[QTableWidget]
        self.resultTables, self.tableWidgets = self._generate_results_widget()
        self.layout().addWidget(self.resultTables)

        # Module highlighter
        self.focus_widget = QWidget()
        self.focus_widget.setLayout(QVBoxLayout())
        self.focused_module = None
        self.focused_module_label = QLabel()
        self.focus_widget.layout().addWidget(self.focused_module_label)
        self.focused_module_label.setText("Display Module Here")
        self.layout().addWidget(self.focus_widget)
        self.focused_action_buttons = []  # type: ignore


    def _generate_searchbar(self) -> QLineEdit:
        searchbar = QLineEdit()
        searchbar.textChanged.connect(self._search)
        searchbar.returnPressed.connect(lambda: self._highlight_module(0, 0))
        return searchbar

    def _generate_searchers(self) -> List[Any]:
        searcherClasses = [ModuleSearcher, OpSearcher]
        resultToModuleInfoConverters = [
            lambda result: result.info(),
            lambda result: result.info().cInfo(),
        ]
        pluginService = ij.get("org.scijava.plugin.PluginService")
        infos = [pluginService.getPlugin(cls, Searcher) for cls in searcherClasses]
        searchers = [info.createInstance() for info in infos]
        [ij.context().inject(searcher) for searcher in searchers]
        return searchers, resultToModuleInfoConverters

    def _generate_search_service(self):
        return ij.get("org.scijava.search.SearchService")
    
    def _highlight_from_results_table(self, searcher_index):
        index = searcher_index
        return lambda row, col: self._highlight_module(index, row, col)

    def _generate_results_widget(self) -> QTableWidget:
        resultTables = []
        for i in range(len(self.searchers)):
            searcher = self.searchers[i]
            # GUI properties
            labels = [ij.py.from_java(searcher.title())]
            max_results = 12
            tableWidget = QTableWidget(max_results, len(labels))
            # Modules take up a row, so highlight the entire thing
            tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
            # Label the columns with labels
            tableWidget.setHorizontalHeaderLabels(labels)
            tableWidget.horizontalHeader().setSectionResizeMode(
                0,
                QHeaderView.Stretch
            )
            tableWidget.verticalHeader().hide()
            tableWidget.setShowGrid(False)
            tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tableWidget.cellClicked.connect(self._highlight_from_results_table(i))
            resultTables.append(tableWidget)

        container = QWidget()
        container.setLayout(QVBoxLayout())
        [container.layout().addWidget(w) for w in resultTables]
        return (container, resultTables)

    def _search(self, text):
        # TODO: Consider adding a button to toggle fuzziness
        for i in range(len(self.searchers)):
            self.results[i] = self.searchers[i].search(text, True)
            for j in range(len(self.results[i])):
                name = ij.py.from_java(self.results[i][j].name())
                self.tableWidgets[i].setItem(j, 0, QTableWidgetItem(name))
                self.tableWidgets[i].showRow(j)
            for j in range(len(self.results[i]), self.tableWidgets[i].rowCount()):
                self.tableWidgets[i].setItem(j, 0, QTableWidgetItem(""))
                self.tableWidgets[i].hideRow(j)

    def _highlight_module(self, table: int, row: int, col: int):
        # Ensure the clicked module is an actual selection
        if (row >= len(self.results[table])):
            return
        # Print highlighted module
        self.focused_module = self.results[table][row]
        name = ij.py.from_java(self.focused_module.name())  # type: ignore
        self.focused_module_label.setText(name)

        # Create buttons for each action
        self.focused_actions = self.searchService.actions(self.focused_module)
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
                self.focused_action_buttons[i].clicked.connect(
                    lambda: self._execute_module(
                        self.resultConverters[table](self.focused_module)
                    )
                )
            else:
                self.focused_action_buttons[i].clicked.connect(
                    self.focused_actions[i].run
                )
            self.focused_action_buttons[i].show()

    def _execute_module(self, moduleInfo):
        logging.debug("Creating module...")
        module = ij.module().createModule(moduleInfo)

        # preprocess using napari GUI
        logging.debug("Processing...")
        func, param_options = _functionify_module_execution(module, moduleInfo, self.viewer)
        self.viewer.window.add_function_widget(
            func, magic_kwargs=param_options
        )
