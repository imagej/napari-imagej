"""
This module contains various utilities for interacting with SciJava Modules.
Most of these functions are designed for INTERNAL USE ONLY.

There are a few functions that are designed for use by graphical widgets, namely:
    * functionify_module_execution(viewer, module, module_info)
        - converts a SciJava module into a Python function
    * execute_function_modally(viewer, name, function, param_options)
        - executes a Python function, obtaining inputs through a modal dialog
    * info_for(searchResult)
        - converts a SciJava SearchResult to a ModuleInfo
"""
from inspect import Parameter, Signature, _empty, isclass, signature
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from jpype import JException, JImplements, JOverride
from magicgui.widgets import Container, Label, LineEdit, Table, Widget, request_values
from napari.layers import Layer
from napari.utils._magicgui import get_layers
from pandas import DataFrame
from scyjava import JavaIterable, JavaMap, JavaSet, is_arraylike, isjava, jstacktrace

from napari_imagej.java import ij, jc
from napari_imagej.types.type_conversions import type_hint_for
from napari_imagej.types.type_utils import type_displayable_in_napari
from napari_imagej.types.widget_mappings import preferred_widget_for
from napari_imagej.utilities.logging import log_debug


def _preprocess_to_harvester(module) -> List["jc.PreprocessorPlugin"]:
    """
    Uses all preprocessors up to the InputHarvesters.
    We stop at the InputHarvesters as they would attempt to resolve inputs that
    we want to resolve in napari.

    We return the list of preprocessors that HAVE NOT YET RUN, so the calling code
    can run them later.

    :param module: The module to preprocess
    :return: The list of preprocessors that have not yet run.
    """

    preprocessors = ij().plugin().createInstancesOfType(jc.PreprocessorPlugin)
    for i, preprocessor in enumerate(preprocessors):
        # if preprocessor is an InputHarvester, stop and return the remaining list
        if isinstance(preprocessor, jc.InputHarvester):
            return preprocessors.subList(i, preprocessors.size())
        # preprocess
        preprocessor.process(module)


NAPARI_IMAGEJ_PREPROCESSORS: List[Callable[["jc.Module"], None]] = []


def preprocessor(func: Callable[["jc.Module"], None]) -> Callable[["jc.Module"], None]:
    NAPARI_IMAGEJ_PREPROCESSORS.append(func)
    return func


@preprocessor
def optional_preallocated_output_real_type_preprocessor(module: "jc.Module"):
    """
    Optional Preallocated RealType Outputs are annoying, since we can't resolve them
    in napari. So we resolve them here
    """
    for input in module.getInfo().inputs():
        # We don't care about resolved inputs
        if module.isInputResolved(input.getName()):
            continue
        # We don't care about pure inputs
        if not input.isOutput():
            continue
        # We don't care about required inputs
        if input.isRequired():
            continue
        # We only care about RealType/Number inputs
        if issubclass(input.getType(), (jc.RealType, jc.Number)):
            module.resolveInput(input.getName())


def _preprocess_napari_imagej(module: "jc.Module"):
    """
    Runs various PreprocessorPlugin-like functions to resolve Module inputs.
    Ideally, we'd make these functions PreprocessorPlugins, but that turns out
    to be a little tricky.
    :param module: The module to be resolved
    :param info: The ModuleInfo creating the module
    """
    for preprocessor in NAPARI_IMAGEJ_PREPROCESSORS:
        preprocessor(module)


def _mutable_layers(
    unresolved_inputs: List["jc.ModuleItem"], user_resolved_inputs: List[Any]
) -> List[Layer]:
    """
    Finds all layers passed to a module that will be mutated
    :param unresolved_inputs: The ModuleItems declaring I/O intent
    :param user_resolved_inputs: The PYTHON inputs passed by magicgui
    :return: The Layer arguments that will be modified
    """
    mutable_layers: List[Layer] = []
    for item, input in zip(unresolved_inputs, user_resolved_inputs):
        if isinstance(input, Layer) and item.isOutput():
            mutable_layers.append(input)

    return mutable_layers


def _resolvable_or_required(input: "jc.ModuleItem"):
    """Determines whether input should be resolved in napari"""
    # Return true if required
    if input.isRequired():
        return True
    # Return true if resolvable
    # The ModuleItem is resolvable iff type_hint_for
    # does not throw a ValueError.
    try:
        type_hint_for(input)
        return True
    except ValueError:
        return False


def _filter_unresolved_inputs(
    module: "jc.Module", inputs: List["jc.ModuleItem"]
) -> List["jc.ModuleItem"]:
    """Returns a list of all inputs that can only be resolved by the user."""
    # Grab all unresolved inputs
    unresolved = list(filter(lambda i: not module.isResolved(i.getName()), inputs))
    # Only leave in the optional parameters that we know how to resolve
    unresolved = list(filter(_resolvable_or_required, unresolved))

    return unresolved


# Credit: https://gist.github.com/xhlulu/95118e225b7a1aa806e696180a72bdd0


def _napari_module_param_additions(
    module_info: "jc.ModuleInfo",
) -> Dict[str, Tuple[type, Any]]:
    """Returns a set of parameters useful for napari functionality."""
    # additional parameters are in the form "name": (type, default value)
    additional_params: Dict[str, Tuple[type, Any]] = {}
    # If the module outputs cannot be coerced into a layer type, they will have
    # to be displayed in a new widget made by napari-imagej. For convenience, we
    # give users the option to spawn that widget within the main napari window,
    # or in a new window. We thus check for any output types that cannot be
    # coerced into a layer. If there are any, we add the option to the
    # parameter map.
    for output_item in module_info.outputs():
        if not type_displayable_in_napari(output_item.getType()):
            additional_params["display_results_in_new_window"] = (bool, False)
    return additional_params


def _is_required_arg(input: "jc.ModuleItem") -> bool:
    """
    Determines whether the ModuleInfo input is required,
    as far as a python arg would be concerned.
    For the python argument to be required, we would need
    BOTH input.isRequired() == True AND no default value.
    """
    return input.isRequired() and input.getDefaultValue() is None


def _sink_optional_inputs(inputs: List["jc.ModuleItem"]) -> List["jc.ModuleItem"]:
    """
    Python functions cannot have required args after an optional arg.
    We need to move all optional inputs after the required ones.
    """

    def sort_key(x):
        return -1 if _is_required_arg(x) else 1

    return sorted(inputs, key=sort_key)


def _param_default_or_none(input: "jc.ModuleItem") -> Optional[Any]:
    """
    Gets the Python function's default value, if it exists, for input.
    """
    default = input.getDefaultValue()
    if default is None and input.isRequired():
        # We have to be careful here about passing a default of None
        # Parameter uses an internal type to denote a required parameter.
        return _empty
    try:
        return ij().py.from_java(default)
    except Exception:
        return default


def _module_param(input: "jc.ModuleItem") -> Parameter:
    """Converts a java ModuleItem into a python Parameter"""
    # NB ModuleInfo.py_name() defined using JImplementationFor
    name = input.py_name()
    kind = Parameter.POSITIONAL_OR_KEYWORD
    default = _param_default_or_none(input)
    type_hint = type_hint_for(input)

    return Parameter(name=name, kind=kind, default=default, annotation=type_hint)


def _modify_function_signature(
    function: Callable,
    inputs: List["jc.ModuleItem"],
    module_info: "jc.ModuleInfo",
) -> None:
    """Rewrites function with type annotations for all module I/O items."""

    sig: Signature = signature(function)
    # Grab all options after the module inputs
    inputs = _sink_optional_inputs(inputs)
    module_params = [_module_param(i) for i in inputs]
    other_params = [
        Parameter(
            i[0],
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=i[1][0],
            default=i[1][1],
        )
        for i in _napari_module_param_additions(module_info).items()
    ]
    all_params = module_params + other_params
    function.__signature__ = sig.replace(parameters=all_params)


def _pure_module_outputs(
    module: "jc.Module",
    user_inputs: List["jc.ModuleItem"],
) -> Tuple[Optional[List[Layer]], List[Tuple[str, Any]]]:
    """Gets the pure outputs of the module, or None if the module has no pure output."""
    # Outputs delivered to users through the return of the magicgui widget.
    # Elements are napari.layers.Layer
    layer_outputs = []
    # Outputs delivered to users through a widget generated by napari-imagej.
    # Elements could be anything, but should not be "layer" types.
    widget_outputs = []

    # Partition outputs into layer and widget outputs
    outputs = module.getOutputs()
    for output_entry in outputs.entrySet():
        # Ignore None outputs
        if output_entry.getValue() is None:
            continue
        # Get relevant output parameters
        name = str(output_entry.getKey())
        output = ij().py.from_java(output_entry.getValue())
        # If the output is layer data, add it as a layer output
        if is_arraylike(output) or isinstance(output, Layer):
            # If the layer was also an input, it came from a napari layer. We
            # don't want duplicate layers, so skip this one.
            if module.getInfo().getInput(name) in user_inputs and module.getInput(name):
                continue
            # Convert layer data into a layer
            if is_arraylike(output):
                output = Layer.create(
                    data=output, meta={"name": name}, layer_type="image"
                )
            # Add the layer to the layer output list
            layer_outputs.append(output)
        # Otherwise, this output needs to go in a widget
        else:
            widget_outputs.append((name, output))

    # napari cannot handle empty List[Layer], so we return None if empty
    return (layer_outputs, widget_outputs)


def _napari_specific_parameter(func: Callable, args: Tuple[Any], param: str) -> Any:
    try:
        index = list(signature(func).parameters.keys()).index(param)
    except ValueError:
        return None

    return args[index]


def _non_layer_widget(results: List[Tuple[str, Any]], widget_name: str = "") -> Widget:
    widgets = []
    for result in results:
        name = result[0]
        value = result[1]
        result_name: Label = Label(value=name)

        if isinstance(value, DataFrame):
            result_value: Table = Table(value)
        else:
            result_value: LineEdit = LineEdit(value=str(value))
            result_value.enabled = False

        widget = Container(layout="horizontal", widgets=(result_name, result_value))
        widgets.append(widget)

    return Container(widgets=widgets, name=widget_name)


def _add_napari_metadata(
    execute_module: Callable,
    info: "jc.ModuleInfo",
    unresolved_inputs: List["jc.ModuleItem"],
) -> None:
    module_name = ij().py.from_java(info.getTitle())
    execute_module.__doc__ = f"Invoke ImageJ2's {module_name}"
    execute_module.__name__ = module_name
    execute_module.__qualname__ = module_name

    # Rewrite the function signature to match the module inputs.
    _modify_function_signature(execute_module, unresolved_inputs, info)

    # Add the type hints as annotations metadata as well.
    # Without this, magicgui doesn't pick up on the types.
    type_hints = {str(i.getName()): type_hint_for(i) for i in unresolved_inputs}

    type_hints["return"] = signature(execute_module).return_annotation

    execute_module._info = info  # type: ignore
    execute_module.__annotation__ = type_hints  # type: ignore


def _add_param_metadata(metadata: dict, key: str, value: Any) -> None:
    """
    Adds a particular aspect of ModuleItem metadata to map

    e.g. a numerical input "foo" might want to require a minimum value of 0.
    Then map would be the dict of "foo", key would be "min", and value would be 0.
    :param metadata: The dict of metadata for some parameter
    :param key: The name of a metadata type on that parameter
    :param value: The value of that metadata type
    """
    if value is None:
        return
    try:
        py_value = ij().py.from_java(value) if isjava(value) else value
        if isinstance(py_value, JavaMap):
            py_value = dict(py_value)
        elif isinstance(py_value, JavaSet):
            py_value = set(py_value)
        elif isinstance(py_value, JavaIterable):
            py_value = list(py_value)
        metadata[key] = py_value
    except TypeError:
        # If we cannot convert the value, we don't want to add anything to the dict.
        pass


def _add_scijava_metadata(
    unresolved_inputs: List["jc.ModuleItem"],
    type_hints: Dict[str, Union[str, type]],
) -> Dict[str, Dict[str, Any]]:
    metadata = {}
    for input in unresolved_inputs:
        key = ij().py.from_java(input.getName())
        param_map = {}
        _add_param_metadata(param_map, "max", input.getMaximumValue())
        _add_param_metadata(param_map, "min", input.getMinimumValue())
        _add_param_metadata(param_map, "step", input.getStepSize())
        _add_param_metadata(param_map, "label", input.getLabel())
        _add_param_metadata(param_map, "tooltip", input.getDescription())
        # SciJava parameters with no choices should be fully left to the user.
        # With no choices, the returned list will be empty.
        # Unfortunately, magicgui doesn't know how to handle an empty list,
        # so we only add it if it is not empty.
        choices = input.getChoices()
        if choices is not None and len(choices) > 0:
            _add_param_metadata(param_map, "choices", choices)
        # Convert supported SciJava styles to widget types.
        widget_type = preferred_widget_for(input, type_hints[input.getName()])
        if widget_type is not None:
            _add_param_metadata(param_map, "widget_type", widget_type)

        if len(param_map) > 0:
            metadata[key] = param_map

    return metadata


def _get_postprocessors():
    """
    Returns the list of PostprocessorPlugins that should be used
    on SciJava Modules from napari-imagej
    """
    # Discover all postprocessors
    postprocessors = ij().plugin().createInstancesOfType(jc.PostprocessorPlugin)

    problematic_postprocessors = (
        # HACK: This particular postprocessor is trying to create a Display
        # for lots of different types. Some of those types (specifically
        # ImgLabelings) make this guy throw Exceptions. We are going to ignore
        # it until it behaves.
        # (see https://github.com/imagej/imagej-common/issues/100 )
        jc.DisplayPostprocessor,
        # HACK: This postprocessor will display data within a SciJava Table.
        # We want to display the data in napari, so we don't want to run this.
        jc.ResultsPostprocessor,
    )

    itr = postprocessors.iterator()
    while itr.hasNext():
        postprocessor = itr.next()
        if type(postprocessor) in problematic_postprocessors:
            itr.remove()

    # Return non-problematic postprocessors
    return postprocessors


def functionify_module_execution(
    output_handler: Callable[[object], None],
    module: "jc.Module",
    info: "jc.ModuleInfo",
) -> Tuple[Callable, dict]:
    """
    Converts a module into a Widget that can be added to napari.
    :param output_handler: The callback function for Module outputs
    :param module: The SciJava Module to turn into a Python function
    :param info: The ModuleInfo of module.
    """
    try:
        # Run preprocessors until we hit input harvesting
        remaining_preprocessors = _preprocess_to_harvester(module)
        # Then, perform napari-imagej specific preprocessing
        _preprocess_napari_imagej(module)

        # Determine which inputs must be resolved by the user
        unresolved_inputs = _filter_unresolved_inputs(module, info.inputs())
        unresolved_inputs = _sink_optional_inputs(unresolved_inputs)

        # Package the rest of the execution into a widget
        def module_execute(
            *user_resolved_inputs,
        ) -> None:
            """
            A function designed to execute module.
            :param user_resolved_inputs: Inputs passed from magicgui
            :return: A List[Layer] of the layer data outputs of the module,
                or None if this module does not return any layer data.
            """
            # Start timing
            start_time = perf_counter()

            # Create user input map
            resolved_java_args = ij().py.jargs(*user_resolved_inputs)
            input_map = jc.HashMap()
            for module_item, input in zip(unresolved_inputs, resolved_java_args):
                input_map.put(module_item.getName(), input)

            # Create postprocessors
            postprocessors: "jc.ArrayList" = _get_postprocessors()
            postprocessors.add(
                NapariPostProcessor(
                    module_execute,
                    output_handler,
                    user_resolved_inputs,
                    unresolved_inputs,
                    start_time,
                )
            )

            log_debug("Processing...")

            ij().module().run(
                module,
                remaining_preprocessors,
                postprocessors,
                input_map,
            )

        # Add metadata for widget creation
        _add_napari_metadata(module_execute, info, unresolved_inputs)
        magic_kwargs = _add_scijava_metadata(
            unresolved_inputs, module_execute.__annotation__
        )

        return (module_execute, magic_kwargs)
    except JException as exc:
        # chain exc to a Python exception
        raise Exception(f"Caught Java Exception\n\n {jstacktrace(exc)}") from None


def _request_values_args(
    func: Callable, param_options: Dict[str, Dict]
) -> Dict[str, Dict]:
    """Gets the arguments for request_values from a function"""

    # Convert function parameters and param_options to a dictionary
    args = {}
    for param in signature(func).parameters.values():
        args[param.name] = {}
        # Add type to dict
        args[param.name]["annotation"] = param.annotation
        # Add magicgui preferences, if they exist, to dict
        if param.name in param_options:
            args[param.name]["options"] = param_options[param.name]
        # Add default value, if we have one, to dict
        if param.default not in [None, _empty]:
            args[param.name]["value"] = param.default
        # Add layer choices, if relevant
        if (isclass(param.annotation) and issubclass(param.annotation, Layer)) or (
            type(param.annotation) is str
            and param.annotation.startswith("napari.layers")
        ):
            if "options" not in args[param.name]:
                args[param.name]["options"] = {}
            # TODO: Once napari > 0.4.16 is released, replace this with
            args[param.name]["options"]["choices"] = get_layers
    return args


def execute_function_modally(
    name: str, func: Callable, param_options: Dict[str, Dict]
) -> None:
    # Determine which arguments are needed
    args: dict = _request_values_args(func, param_options)
    # Get any needed arguments
    if len(args) > 0:
        params = request_values(title=name, **args)
    else:
        params = dict()
    # Execute the function with the arguments
    if params is not None:
        inputs = params.values()
        func(*inputs)


def info_for(search_result: "jc.SearchResult") -> Optional["jc.ModuleInfo"]:
    if hasattr(search_result, "info"):
        info = search_result.info()
        # There is an extra step for Ops - we actually need the CommandInfo
        if isinstance(info, jc.OpInfo):
            info = info.cInfo()
        return info
    return None


@JImplements("org.scijava.module.process.PostprocessorPlugin", deferred=True)
class NapariPostProcessor(object):
    def __init__(
        self,
        function: Callable,
        output_handler: Callable[[object], None],
        args,
        params: List["jc.ModuleInfo"],
        start_time: float,
    ):
        self.function = function
        self.output_handler = output_handler
        self.params = params
        self.args = args
        self.start_time = start_time

    # -- Contextual methods -- #

    @JOverride
    def context(self):
        return self.ctx

    @JOverride
    def getContext(self):
        return self.ctx

    @JOverride
    def setContext(self, ctx):
        self.ctx = ctx

    # -- ProcessorPlugin methods -- #

    @JOverride
    def process(self, module: "jc.Module"):
        # get all outputs
        layer_outputs: List[Layer]
        widget_outputs: List[Any]
        layer_outputs, widget_outputs = _pure_module_outputs(module, self.params)
        # log outputs
        for layer in layer_outputs:
            log_debug(f"Result: ({type(layer).__name__}) {layer.name}")
        for output in widget_outputs:
            log_debug(f"Result: ({type(output[1])}) {output[0]}")

        mutated_layers = _mutable_layers(
            self.params,
            self.args,
        )

        # display non-layer outputs in a widget
        display_externally = _napari_specific_parameter(
            self.function,
            self.args,
            "display_results_in_new_window",
        )
        if display_externally is not None and len(widget_outputs) > 0:
            name = "Result: " + ij().py.from_java(module.getInfo().getTitle())
            self.output_handler(
                {"data": widget_outputs, "name": name, "external": display_externally}
            )

        # Refresh the modified layers
        for layer in mutated_layers:
            layer.refresh()

        log_debug("Refreshed all layers")

        # Hand off layer outputs to napari via return
        for layer in layer_outputs:
            self.output_handler(layer)

        end_time = perf_counter()
        log_debug(f"Computation completed in {end_time - self.start_time:0.4f} seconds")
