from functools import lru_cache
from inspect import Parameter, Signature, signature
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from magicgui.widgets import Container, Label, LineEdit, Widget
from napari import Viewer
from napari.layers import Layer
from napari.types import LayerDataTuple
from scyjava import JavaIterable, JavaMap, JavaSet, Priority

from napari_imagej._ptypes import TypeMappings, _supported_styles
from napari_imagej.setup_imagej import ij, jc, log_debug


@lru_cache(maxsize=None)
def type_mappings():
    """
    Lazily creates a TypeMappings object.
    This object is then cached upon function return,
    effectively making this function a lazily initialized field.

    This object should be lazily initialized as it will import java classes.
    Those Java classes should not be imported until ImageJ has been able to set
    up the JVM, adding its required JARs to the classpath. For that reason,
    java class importing is done with java_import, which blocks UNTIL the imagej
    gateway has been created (in a separate thread). Thus, prematurely calling this
    function would block the calling thread.

    By lazily initializing this function, we minimize the time this thread is blocked.
    """
    return TypeMappings()


# List of Module Item Converters, along with their priority
_MODULE_ITEM_CONVERTERS: List[Tuple[Callable, int]] = []


def module_item_converter(
    priority: int = Priority.NORMAL,
) -> Callable[["jc.ModuleInfo"], Callable]:
    """
    A decorator used to register the annotated function among the
    available module item converters
    :param priority: How much this converter should be prioritized
    :return: The annotated function
    """

    def converter(func: Callable):
        """Registers the annotated function with its priority"""
        _MODULE_ITEM_CONVERTERS.append((func, priority))
        return func

    return converter


# TODO: Move this function to scyjava.convert and/or ij.py.
def python_type_of(module_item: "jc.ModuleItem"):
    """Returns the Python type associated with the passed ModuleItem."""
    for converter, _ in sorted(
        _MODULE_ITEM_CONVERTERS, reverse=True, key=lambda x: x[1]
    ):
        converted = converter(module_item)
        if converted is not None:
            return converted
    raise ValueError(
        (
            f"Unsupported Java Type: {module_item.getType()}. "
            "Let us know about the failure at https://forum.image.sc, "
            "or file an issue at https://github.com/imagej/napari-imagej!"
        )
    )


def _checkerUsingFunc(
    item: "jc.ModuleItem", func: Callable[[Type, Type], bool]
) -> Optional[Type]:
    """
    The logic of this checker is as follows:

    type_mappings().ptypes.items() contains (java_type, python_type) pairs.
    These pairs are considered to be equivalent types; i.e. we can freely
    convert between these types.

    There are 3 cases:
    1) The ModuleItem is a PURE INPUT:
        We can satisfy item with an object of ptype IF its corresponding
        jtype can be converted to item's type. The conversion then goes
        ptype -> jtype -> java_type
    2) The ModuleItem is a PURE OUTPUT:
        We can satisfy item with ptype IF java_type can be converted to jtype.
        Then jtype can be converted to ptype. The conversion then goes
        java_type -> jtype -> ptype
    3) The ModuleItem is BOTH:
        We can satisfy item with ptype IF we satisfy both 1 and 2.
        ptype -> jtype -> java_type -> jtype -> ptype

    :param item: the ModuleItem we'd like to convert
    :return: the python equivalent of ModuleItem's type, or None if that type
    cannot be converted.
    """
    # Get the type of the Module item
    java_type = item.getType()
    type_pairs = type_mappings().ptypes.items()
    # Case 1
    if item.isInput() and not item.isOutput():
        for jtype, ptype in type_pairs:
            # can we go from jtype to java_type?
            if func(jtype, java_type):
                return ptype
    # Case 2
    elif item.isOutput() and not item.isInput():
        # NB type_pairs is ordered from least to most specific.
        for jtype, ptype in reversed(type_pairs):
            # can we go from java_type to jtype?
            if func(java_type, jtype):
                return ptype
    # Case 3
    elif item.isInput() and item.isOutput():
        for jtype, ptype in type_pairs:
            # can we go both ways?
            if func(java_type, jtype) and func(jtype, java_type):
                return ptype
    # Didn't satisfy any cases!
    return None


@module_item_converter()
def isAssignableChecker(item: "jc.ModuleItem") -> Optional[Type]:
    """
    Determines whether we can simply cast from ptype to item's type java_type
    """

    def isAssignable(from_type, to_type) -> bool:
        # Use Types to get the raw type of each
        from_raw = jc.Types.raw(from_type)
        to_raw = jc.Types.raw(to_type)
        return from_raw.isAssignableFrom(to_raw)

    return _checkerUsingFunc(item, isAssignable)


@module_item_converter(priority=Priority.LOW)
def canConvertChecker(item: "jc.ModuleItem") -> Optional[Type]:
    """
    Determines whether imagej can do a conversion from ptype to item's type java_type.
    """

    def isAssignable(from_type, to_type) -> bool:
        return ij().convert().supports(from_type, to_type)

    return _checkerUsingFunc(item, isAssignable)


def _widget_return_type(module_info: "jc.Module") -> type:
    """
    Determines the return type of execute_module within functionify_module_execution.
    If there are ANY "layer" outputs described in module_info, the output will be
    a List of LayerDataTuple. If there are no "layer" outputs, the return will be
    None.
    """
    for output_item in module_info.outputs():
        # We only return PURE outputs (i.e. not mutable outputs)
        if output_item.isInput():
            continue
        if type_mappings().type_displayable_in_napari(output_item.getType()):
            return List[LayerDataTuple]
    return None


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
        # We don't care about input unless it is a layer
        if not isinstance(input, Layer):
            continue
        # We don't care about input unless it is an output
        if not item.isOutput():
            continue

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
    # Delegate optional output construction to the module
    # We will leave those unresolved
    unresolved = list(
        filter(lambda i: not (i.isOutput() and not i.isRequired()), unresolved)
    )
    # Only leave in the optional parameters that we know how to resolve
    unresolved = list(filter(_resolvable_or_required, unresolved))

    return unresolved


def _initialize_module(module: "jc.Module"):
    """Initializes the passed module."""
    try:
        module.initialize()
        # HACK: module.initialize() does not seem to call
        # Initializable.initialize()
        if isinstance(module.getDelegateObject(), jc.Initializable):
            module.getDelegateObject().initialize()
    except Exception as e:
        print("Initialization Error")
        print(e.stacktrace())


def _run_module(module: "jc.Module"):
    """Runs the passed module."""
    try:
        module.run()
    except Exception as e:
        print("Run Error")
        print(e.stacktrace())


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
        if not type_mappings().type_displayable_in_napari(output_item.getType()):
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
    if default is not None:
        try:
            default = ij().py.from_java(default)
        except Exception:
            pass
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

    # We have to be careful here about passing a default
    # Parameter uses an internal type to denote a required parameter.
    # Passing anything EXCEPT that internal type will make that arugment default.
    # Thus we need to only specify default if we have one.
    if default is not None:
        return Parameter(name=name, kind=kind, default=default, annotation=type_hint)
    else:
        return Parameter(name=name, kind=kind, annotation=type_hint)


def _modify_function_signature(
    function: Callable,
    inputs: List["jc.ModuleItem"],
    module_info: "jc.ModuleInfo",
) -> None:
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
                default=i[1][1],
            )
            for i in _napari_module_param_additions(module_info).items()
        ]
        all_params = module_params + other_params
        return_type = _widget_return_type(module_info)
        function.__signature__ = sig.replace(
            parameters=all_params, return_annotation=return_type
        )
    except Exception as e:
        print(e)


def _layerDataTuple_from_layer(layer: Layer):
    data = layer.data
    metadata: Dict[str, Any] = {}
    layer_type = type(layer).__name__
    metadata["name"] = layer.name
    metadata["metadata"] = layer.metadata
    if hasattr(layer, "shape_type"):
        metadata["shape_type"] = getattr(layer, "shape_type")

    return (data, metadata, layer_type)


def _pure_module_outputs(
    module: "jc.Module",
) -> Tuple[Optional[List[LayerDataTuple]], List[Tuple[str, Any]]]:
    """Gets the pure outputs of the module, or None if the module has no pure output."""
    # Outputs delivered to users through the return of the magicgui widget.
    # Elements are napari.types.LayerDataTuple
    layer_outputs = []
    # Outputs delivered to users through a widget generated by napari-imagej.
    # Elements could be anything, but should not be "layer" types.
    widget_outputs = []

    outputs = module.getOutputs()
    for output_entry in outputs.entrySet():
        # Ignore outputs that are also inputs
        output_name = ij().py.from_java(output_entry.getKey())
        if output_name in module.getInputs():
            continue
        output = ij().py.from_java(output_entry.getValue())
        # Add LayerDataTuples directly
        if isinstance(output, tuple) and len(output) <= 3:
            layer_outputs.append(output)
        # Add arraylike outputs as images
        elif ij().py._is_arraylike(output):
            layerDataTuple = (output, {"name": output_name}, "image")
            layer_outputs.append(layerDataTuple)
        elif isinstance(output, Layer):
            layer_outputs.append(_layerDataTuple_from_layer(output))
        # Ignore None outputs
        elif output is None:
            continue

        # Otherwise, it can't be displayed in napari.
        else:
            widget_outputs.append((output_name, output))

    # napari cannot handle empty List[LayerDataTuple], so we return None if empty
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

    type_hints["return"] = _widget_return_type(info)

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


def _widget_for_style_and_type(
    style: str, type_hint: Union[type, str]
) -> Optional[str]:
    """
    Convenience function for interacting with _supported_styles
    :param style: The SciJava style
    :param type_hint: The PYTHON type for the parameter
    :return: The best widget type, if it is known
    """
    if style not in _supported_styles:
        return None
    style_options = _supported_styles[style]
    for k, v in style_options.items():
        if issubclass(type_hint, k):
            return v
    return None


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
        widget_type = _widget_for_style_and_type(
            input.getWidgetStyle(), type_hints[input.getName()]
        )
        if widget_type is not None:
            _add_param_metadata(param_map, "widget_type", widget_type)

        if len(param_map) > 0:
            metadata[key] = param_map

    return metadata


def functionify_module_execution(
    viewer: Viewer, module: "jc.Module", info: "jc.ModuleInfo"
) -> Tuple[Callable, dict]:
    """Converts a module into a Widget that can be added to napari."""
    # Run preprocessors until we hit input harvesting
    input_harvesters: List["jc.PreprocessorPlugin"]
    input_harvesters = _preprocess_to_harvester(module)

    # Determine which inputs must be resolved by the user
    unresolved_inputs = _filter_unresolved_inputs(module, info.inputs())
    unresolved_inputs = _sink_optional_inputs(unresolved_inputs)

    # Package the rest of the execution into a widget
    # TODO: Ideally, we'd have a return type hint List[LayerDataTuple] here,
    # and we wouldn't need _widget_return_type. This won't work when we return
    # no layers, however: see https://github.com/napari/napari/issues/4571.
    def module_execute(
        *user_resolved_inputs,
    ):
        """
        A function designed to execute module.
        :param user_resolved_inputs: Inputs passed from magicgui
        :return: A List[LayerDataTuple] of the layer data outputs of the module,
            or None if this module does not return any layer data.
        """

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
        layer_outputs: List[LayerDataTuple]
        widget_outputs: List[Any]
        layer_outputs, widget_outputs = _pure_module_outputs(module)
        # log outputs
        if layer_outputs is not None:
            for output in layer_outputs:
                log_debug(f"Result: ({output[2]}) {output[1]['name']}")
        for output in widget_outputs:
            log_debug(f"Result: ({type(output[1])}) {output[0]}")

        # display non-layer outputs in a widget
        display_externally = _napari_specific_parameter(
            module_execute, user_resolved_inputs, "display_results_in_new_window"
        )
        if display_externally is not None and len(widget_outputs) > 0:
            _display_result(widget_outputs, info, viewer, display_externally)

        # Refresh the modified layers
        for layer in mutated_layers:
            layer.refresh()

        # Hand off layer outputs to napari via return
        return layer_outputs

    # Add metadata for widget creation
    _add_napari_metadata(module_execute, info, unresolved_inputs)
    magic_kwargs = _add_scijava_metadata(
        unresolved_inputs, module_execute.__annotation__
    )

    return (module_execute, magic_kwargs)
