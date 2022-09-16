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
from inspect import Parameter, Signature, _empty, signature
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from jpype import JException
from magicgui.widgets import Container, Label, LineEdit, Widget, request_values
from magicgui.widgets._bases import CategoricalWidget
from napari import Viewer, current_viewer
from napari.layers import Layer
from napari.utils._magicgui import find_viewer_ancestor
from scyjava import JavaIterable, JavaMap, JavaSet, jstacktrace

from napari_imagej.java import ij, jc
from napari_imagej.types.type_conversions import python_type_of
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
    log_debug("Preprocessing...")

    preprocessors = ij().plugin().createInstancesOfType(jc.PreprocessorPlugin)
    for i, preprocessor in enumerate(preprocessors):
        # if preprocessor is an InputHarvester, stop and return the remaining list
        if isinstance(preprocessor, jc.InputHarvester):
            return list(preprocessors)[i:]
        # preprocess
        preprocessor.process(module)


def _resolve_user_input(module: "jc.Module", module_item: "jc.ModuleItem", input: Any):
    """
    Resolves module_item, a ModuleItem in module, with JAVA object input
    :param module: The module to be resolved
    :param module_item: The particular item being resolved
    :param input: The JAVA input that is resolving module_item.
    """
    name = module_item.getName()
    if module_item.isRequired() and input is None:
        raise ValueError("No selection was made for input {}!".format(name))
    item_class = module_item.getType()
    if not item_class.isInstance(input):
        if ij().convert().supports(input, item_class):
            input = ij().convert().convert(input, item_class)
        else:
            raise ValueError(f"{input} is not a {module_item.getType()}!")
    module.setInput(name, input)
    module.resolveInput(name)


def _preprocess_remaining_inputs(
    module: "jc.Module",
    inputs: List["jc.ModuleItem"],
    unresolved_inputs: List["jc.ModuleItem"],
    user_resolved_inputs: List[Any],
    remaining_preprocessors: List["jc.PreprocessorPlugin"],
):
    """Resolves each input in unresolved_inputs"""
    resolved_java_args = ij().py.jargs(*user_resolved_inputs)
    # resolve remaining inputs
    for module_item, input in zip(unresolved_inputs, resolved_java_args):
        _resolve_user_input(module, module_item, input)

    # Deliberately ignore optional inputs
    for input in inputs:
        if not input.isRequired() and not module.isInputResolved(input.getName()):
            module.resolveInput(input.getName())

    for processor in remaining_preprocessors:
        processor.process(module)

    # sanity check: ensure all inputs resolved
    for input in inputs:
        if input.isRequired() and not module.isInputResolved(input.getName()):
            raise ValueError(
                (
                    f"input {input.getName()} of type {input.getType()} "
                    " was not resolved! If it is impossible to resolve, "
                    " let us know at forum.image.sc or by filing an issue "
                    " at https://github.com/imagej/napari-imagej!"
                )
            )

    return resolved_java_args


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
    # The ModuleItem is resolvable iff python_type_of
    # does not throw a ValueError.
    try:
        python_type_of(input)
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


def _initialize_module(module: "jc.Module"):
    """Initializes the passed module."""
    module.initialize()
    # HACK: module.initialize() does not seem to call
    # Initializable.initialize()
    if isinstance(module.getDelegateObject(), jc.Initializable):
        module.getDelegateObject().initialize()


def _run_module(module: "jc.Module"):
    """Runs the passed module."""
    module.run()


def _postprocess_module(module: "jc.Module"):
    """Runs all known postprocessors on the passed module."""
    log_debug("Postprocessing...")
    # Discover all postprocessors
    postprocessors = ij().plugin().createInstancesOfType(jc.PostprocessorPlugin)

    problematic_postprocessors = (
        # HACK: This particular postprocessor is trying to create a Display
        # for lots of different types. Some of those types (specifically
        # ImgLabelings) make this guy throw Exceptions. We are going to ignore
        # it until it behaves.
        # (see https://github.com/imagej/imagej-common/issues/100 )
        jc.DisplayPostprocessor,
    )
    # Run all discovered postprocessors unless we have marked it as problematic
    for postprocessor in postprocessors:
        if not isinstance(postprocessor, problematic_postprocessors):
            postprocessor.process(module)


# Credit: https://gist.github.com/xhlulu/95117e225b7a1aa806e696180a72bdd0


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


def _is_optional_arg(input: "jc.ModuleItem") -> bool:
    """
    Determines whether the ModuleInfo input is optional,
    as far as a python arg would be concerned.
    For the python argument to be optional, we would need
    EITHER a declaration of optionality by input.isRequired() == False,
    OR a default value.
    """
    # TODO: I think this could be
    # return input.isRequired() and input.getDefaultValue() is None
    if not input.isRequired():
        return False
    if input.getDefaultValue() is not None:
        return False
    return True


def _sink_optional_inputs(inputs: List["jc.ModuleItem"]) -> List["jc.ModuleItem"]:
    """
    Python functions cannot have required args after an optional arg.
    We need to move all optional inputs after the required ones.
    """

    def sort_key(x):
        return -1 if _is_optional_arg(x) else 1

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


def _type_hint_for_module_item(input: "jc.ModuleItem") -> type:
    """
    Gets the (Python) type hint for a (Java) input
    """
    type = python_type_of(input)
    if not input.isRequired():
        type = Optional[type]
    return type


def _module_param(input: "jc.ModuleItem") -> Parameter:
    """Converts a java ModuleItem into a python Parameter"""
    name = ij().py.from_java(input.getName())
    kind = Parameter.POSITIONAL_OR_KEYWORD
    default = _param_default_or_none(input)
    type_hint = _type_hint_for_module_item(input)

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

    outputs = module.getOutputs()
    for output_entry in outputs.entrySet():
        # Ignore outputs that were provided by the user
        output_name = ij().py.from_java(output_entry.getKey())
        if module.getInfo().getInput(output_name) in user_inputs:
            if module.getInput(output_name):
                continue
        output = ij().py.from_java(output_entry.getValue())
        # Add arraylike outputs as images
        if ij().py._is_arraylike(output):
            layer = Layer.create(
                data=output, meta={"name": output_name}, layer_type="image"
            )
            layer_outputs.append(layer)
        # Add Layers directly
        elif isinstance(output, Layer):
            layer_outputs.append(output)
        # Ignore None outputs
        elif output is None:
            continue

        # Otherwise, it can't be displayed in napari.
        else:
            widget_outputs.append((output_name, output))

    # napari cannot handle empty List[Layer], so we return None if empty
    if not len(layer_outputs):
        layer_outputs = None
    return (layer_outputs, widget_outputs)


def _napari_specific_parameter(func: Callable, args: Tuple[Any], param: str) -> Any:
    try:
        index = list(signature(func).parameters.keys()).index(param)
    except ValueError:
        return None

    return args[index]


def _non_layer_widget(results: List[Tuple[str, Any]]) -> Widget:

    widgets = []
    for result in results:
        name = result[0]
        value = str(result[1])
        result_name: Label = Label(value=name)

        result_value: LineEdit = LineEdit(value=value)
        result_value.enabled = False

        widget = Container(layout="horizontal", widgets=(result_name, result_value))
        widgets.append(widget)

    return Container(widgets=widgets)


def _display_result(
    results: List[Tuple[str, Any]],
    info: "jc.ModuleInfo",
    viewer: Viewer,
    external: bool,
) -> None:
    """Displays result in a new widget"""

    widget: Widget = _non_layer_widget(results)

    if external:
        widget.show(run=True)
    else:
        name = "Result: " + ij().py.from_java(info.getTitle())
        viewer.window.add_dock_widget(widget, name=name)


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
    type_hints = {str(i.getName()): python_type_of(i) for i in unresolved_inputs}

    type_hints["return"] = List[Layer]

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
        py_value = ij().py.from_java(value)
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


def functionify_module_execution(
    viewer: Viewer, module: "jc.Module", info: "jc.ModuleInfo"
) -> Tuple[Callable, dict]:
    """Converts a module into a Widget that can be added to napari."""
    try:
        # Run preprocessors until we hit input harvesting
        input_harvesters: List["jc.PreprocessorPlugin"]
        input_harvesters = _preprocess_to_harvester(module)

        # Determine which inputs must be resolved by the user
        unresolved_inputs = _filter_unresolved_inputs(module, info.inputs())
        unresolved_inputs = _sink_optional_inputs(unresolved_inputs)

        # Package the rest of the execution into a widget
        def module_execute(
            *user_resolved_inputs,
        ) -> List[Layer]:
            """
            A function designed to execute module.
            :param user_resolved_inputs: Inputs passed from magicgui
            :return: A List[Layer] of the layer data outputs of the module,
                or None if this module does not return any layer data.
            """
            try:
                # Resolve remaining inputs
                resolved_java_args = _preprocess_remaining_inputs(
                    module,
                    info.inputs(),
                    unresolved_inputs,
                    user_resolved_inputs,
                    input_harvesters,
                )

                mutated_layers = _mutable_layers(
                    unresolved_inputs,
                    user_resolved_inputs,
                )

                # run module
                log_debug(
                    f"Running {module_execute.__qualname__} \
                        ({resolved_java_args}) -- {info.getIdentifier()}"
                )
                _initialize_module(module)
                _run_module(module)

                # postprocess
                _postprocess_module(module)
                log_debug("Execution complete")

                # get all outputs
                layer_outputs: List[Layer]
                widget_outputs: List[Any]
                layer_outputs, widget_outputs = _pure_module_outputs(
                    module, unresolved_inputs
                )
                # log outputs
                if layer_outputs is not None:
                    for layer in layer_outputs:
                        log_debug(f"Result: ({type(layer).__name__}) {layer.name}")
                for output in widget_outputs:
                    log_debug(f"Result: ({type(output[1])}) {output[0]}")

                # display non-layer outputs in a widget
                display_externally = _napari_specific_parameter(
                    module_execute,
                    user_resolved_inputs,
                    "display_results_in_new_window",
                )
                if display_externally is not None and len(widget_outputs) > 0:
                    _display_result(widget_outputs, info, viewer, display_externally)

                # Refresh the modified layers
                for layer in mutated_layers:
                    layer.refresh()

                # Hand off layer outputs to napari via return
                return layer_outputs
            except JException as exc:
                # chain exc to a Python exception
                raise Exception(
                    f"Caught Java Exception\n\n {jstacktrace(exc)}"
                ) from None

        # Add metadata for widget creation
        _add_napari_metadata(module_execute, info, unresolved_inputs)
        magic_kwargs = _add_scijava_metadata(
            unresolved_inputs, module_execute.__annotation__
        )

        return (module_execute, magic_kwargs)
    except JException as exc:
        # chain exc to a Python exception
        raise Exception(f"Caught Java Exception\n\n {jstacktrace(exc)}") from None


def _get_layers_hack(gui: CategoricalWidget) -> List[Layer]:
    """Mimics the functional changes of https://github.com/napari/napari/pull/4715"""
    viewer = find_viewer_ancestor(gui.native)
    if viewer is None:
        viewer = current_viewer()
    return [x for x in viewer.layers if isinstance(x, gui.annotation)]


def _request_values_args(
    func: Callable, param_options: Dict[str, Dict]
) -> Dict[str, Dict]:
    """Gets the arguments for request_values from a function"""
    import inspect

    signature = inspect.signature(func)

    # Convert function parameters and param_options to a dictionary
    args = {}
    for param in signature.parameters.values():
        args[param.name] = {}
        # Add type to dict
        args[param.name]["annotation"] = param.annotation
        # Add magicgui preferences, if they exist, to dict
        if param.name in param_options:
            args[param.name]["options"] = param_options[param.name]
        # Add default value, if we have one, to dict
        if param.default is not inspect._empty:
            args[param.name]["value"] = param.default
        # Add layer choices, if relevant
        if (
            inspect.isclass(param.annotation) and issubclass(param.annotation, Layer)
        ) or (
            type(param.annotation) is str
            and param.annotation.startswith("napari.layers")
        ):
            if "options" not in args[param.name]:
                args[param.name]["options"] = {}
            # TODO: Once napari > 0.4.16 is released, replace this with
            # napari.util._magicgui.get_layers
            args[param.name]["options"]["choices"] = _get_layers_hack
    return args


def _execute_function_with_params(viewer: Viewer, params: Dict, func: Callable):
    if params is not None:
        inputs = params.values()
        outputs: Optional[List[Layer]] = func(*inputs)
        if outputs is not None:
            for output in outputs:
                viewer.add_layer(output)


def execute_function_modally(
    viewer: Viewer, name: str, func: Callable, param_options: Dict[str, Dict]
) -> None:
    # Determine which arguments are needed
    args: dict = _request_values_args(func, param_options)
    # Get any needed arguments
    if len(args) > 0:
        params = request_values(title=name, **args)
    else:
        params = dict()
    # Execute the function with the arguments
    _execute_function_with_params(viewer, params, func)


def info_for(search_result: "jc.SearchResult") -> "jc.ModuleInfo":
    info = search_result.info()
    # There is an extra step for Ops - we actually need the CommandInfo
    if isinstance(info, jc.OpInfo):
        info = info.cInfo()
    return info
