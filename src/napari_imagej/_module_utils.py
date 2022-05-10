from functools import lru_cache
from typing import Any, Callable, Collection, Dict, List, Optional, Tuple, Type
from scyjava import Priority
from inspect import Parameter, Signature, signature
from magicgui import magicgui
from napari import Viewer
from napari_imagej._ptypes import PTypes
from napari_imagej.setup_imagej import ij, java_import

# Create Java -> Python type mapper
@lru_cache(maxsize=None)
def type_mappings():
    return PTypes()

# List of Module Item Converters, along with their priority
_MODULE_ITEM_CONVERTERS: List[Tuple[Callable, int]] = []

def module_item_converter(
    priority: int = Priority.NORMAL
    ) -> Callable:
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
def python_type_of(module_item):
    """Returns the Python type associated with the passed ModuleItem."""
    for converter, _ in sorted(_MODULE_ITEM_CONVERTERS, reverse=True, key=lambda x: x[1]):
        converted = converter(module_item)
        if converted is not None:
            return converted
    raise ValueError(f"Unsupported Java Type: {module_item.getType()}. Let us know about the failure at https://forum.image.sc, or file an issue at https://github.com/imagej/napari-imagej!")


def _checkerUsingFunc(
    item,
    func: Callable[[Type, Type], bool]
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
    # Case 1
    if item.isInput() and not item.isOutput():
        for jtype, ptype in type_mappings().ptypes.items():
            # can we go from jtype to java_type?
            if func(jtype, java_type):
                return ptype
    # Case 2
    elif item.isOutput() and not item.isInput():
        for jtype, ptype in type_mappings().ptypes.items():
            # can we go from java_type to jtype?
            if func(java_type, jtype):
                return ptype
    # Case 3
    elif item.isInput() and item.isOutput():
        for jtype, ptype in type_mappings().ptypes.items():
            # can we go both ways?
            if func(java_type, jtype) and func(jtype, java_type):
                return ptype
    # Didn't satisfy any cases!
    return None


@module_item_converter()
def isAssignableChecker(item) -> Optional[Type]:
    """
    Determines whether we can simply cast from ptype to item's type java_type
    """
    def isAssignable(from_type, to_type) -> bool:
        # Use Types to get the raw type of each
        Types = java_import("org.scijava.util.Types")
        from_raw = Types.raw(from_type)
        to_raw = Types.raw(to_type)
        return from_raw.isAssignableFrom(to_raw)
    return _checkerUsingFunc(item, isAssignable)


@module_item_converter(priority = Priority.LOW)
def canConvertChecker(item) -> Optional[Type]:
    """
    Determines whether imagej can do a conversion from ptype to item's type java_type.
    """
    def isAssignable(from_type, to_type) -> bool:
        return ij().convert().supports(from_type, to_type)
    return _checkerUsingFunc(item, isAssignable)

def _return_type(info):
    """Returns the output type of info."""
    outs = info.outputs()
    if len(outs) == 0:
        return None
    if len(outs) == 1:
        return python_type_of(outs[0])
    return dict


def _preprocess_non_inputs(module):
    """Uses all preprocessors up to the InputHarvesters."""
    # preprocess using plugin preprocessors
    PreprocessorPlugin = java_import("org.scijava.module.process.PreprocessorPlugin")
    preprocessors = ij().plugin() \
        .createInstancesOfType(PreprocessorPlugin)
    # we want to avoid these processors
    problematic_processors = (
        java_import("org.scijava.widget.InputHarvester"),
        java_import("org.scijava.module.process.LoadInputsPreprocessor")
    )
    for preprocessor in preprocessors:
        if isinstance(preprocessor, problematic_processors):
            # STOP AT INPUT HARVESTING
            break
        else:
            preprocessor.process(module)


def _resolve_user_input(
    module, # an org.scijava.module.Module
    module_item, # an org.scijava.module.ModuleItem
    input: Any
):
    """Resolves module_item, a ModuleItem in module, with input"""
    name = module_item.getName()
    if module_item.isRequired() and input is None:
        raise ValueError(
            "No selection was made for input {}!".format(name)
        )
    # TODO: Can we just something like:
    # if isinstance(input, python_type_of(module_item)):
    item_class = module_item.getType()
    if not item_class.isInstance(input):
        if ij().convert().supports(input, item_class):
            input = ij().convert().convert(input, item_class)
        else:
            raise ValueError(
                f"{input} is not a {module_item.getType()}!"
            )
    module.setInput(name, input)
    module.resolveInput(name)


def _preprocess_remaining_inputs(
    module, inputs, unresolved_inputs, user_resolved_inputs
):
    """Resolves each input in unresolved_inputs"""
    resolved_java_args = ij().py.jargs(*user_resolved_inputs)
    # resolve remaining inputs
    for module_item, input in zip(unresolved_inputs, resolved_java_args):
        _resolve_user_input(module, module_item, input)

    # sanity check: ensure all inputs resolved
    for input in inputs:
        if input.isRequired() and not module.isInputResolved(input.getName()):
            raise ValueError(
                f"input {input.getName()} of type {input.getType()} was not resolved! If it is impossible to resolve, let us know at forum.image.sc or by filing an issue at https://github.com/imagej/napari-imagej!".format(input.getName())
            )

    return resolved_java_args

def _resolvable_or_required(input):
    """Determines whether input should be resolved in napari"""
    if input.isRequired(): return True
    try:
        type = python_type_of(input)
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
        Initializable = java_import("net.imagej.ops.Initializable")
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
    PostprocessorPlugin = java_import("org.scijava.module.process.PostprocessorPlugin")
    postprocessors = ij().plugin().createInstancesOfType(PostprocessorPlugin)

    problematic_postprocessors = (
        java_import("org.scijava.display.DisplayPostprocessor")
    )
    # Run all discovered postprocessors
    for postprocessor in postprocessors:
        if isinstance(postprocessor, problematic_postprocessors):
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
    if not type_mappings().type_displayable_in_napari(output_item.getType()):
        additional_params["display_results_in_new_window"] = (bool, False)
    return additional_params

def _is_non_default(input):
    """
    Determines whether the ModuleInfo input is optional,
    as far as a python arg would be concerned.
    For the python argument to be optional, we would need
    EITHER a declaration of optionality by input.isRequired() == False,
    OR a default value.
    """
    # TODO: I think this could be
    # return input.isRequired() and input.getDefaultValue() is None
    if not input.isRequired(): return False
    if input.getDefaultValue() is not None: return False
    return True


def _sink_default_inputs(inputs):
    """
    Python functions cannot have required args after an optional arg.
    We need to move all default inputs after the required ones.
    """
    sort_key = lambda x: -1 if _is_non_default(x) else 1
    return sorted(inputs, key=sort_key)


def _param_default_or_none(input):
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


def _param_annotation(input):
    """
    Gets the (Python) type hint for a (Java) input
    """
    type = python_type_of(input)
    if not input.isRequired():
        type = Optional[type]
    return type


def _module_param(input):
    """Converts a java ModuleItem into a python Parameter"""
    name = ij().py.from_java(input.getName())
    kind = Parameter.POSITIONAL_OR_KEYWORD
    default = _param_default_or_none(input)
    annotation = _param_annotation(input)

    # We have to be careful here about passing a default
    # Parameter uses an internal type to denote a required parameter.
    # Passing anything EXCEPT that internal type will make that arugment default.
    # Thus we need to only specify default if we have one.
    if default is not None:
        return Parameter(name=name, kind=kind, default=default, annotation=annotation)
    else:
        return Parameter(name=name, kind=kind, annotation=annotation)


def _modify_function_signature(function, inputs, module_info):
    """Rewrites function with type annotations for all module I/O items."""

    try:
        sig: Signature = signature(function)
        # Grab all options after the module inputs
        inputs = _sink_default_inputs(inputs)
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
        return ij().py.from_java(result)

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
        name = "Result: " + ij().py.from_java(info.getTitle())
        viewer.window.add_dock_widget(result_widget, name=name)
    result_widget.update()


def _add_napari_metadata(execute_module: Callable, info, unresolved_inputs):
    module_name = ij().py.from_java(info.getTitle())
    execute_module.__doc__ = f"Invoke ImageJ2's {module_name}"
    execute_module.__name__ = module_name
    execute_module.__qualname__ = module_name

    # Rewrite the function signature to match the module inputs.
    _modify_function_signature(execute_module, unresolved_inputs, info)

    # Add the type hints as annotations metadata as well.
    # Without this, magicgui doesn't pick up on the types.
    type_hints = {
        str(i.getName()): python_type_of(i) for i in unresolved_inputs
    }
    return_annotation = python_type_of(info.outputs()[0]) if len(info.outputs()) == 1 else dict
    type_hints["return"] = return_annotation
    execute_module.__annotation__ = type_hints  # type: ignore

    execute_module._info = info  # type: ignore


def _add_param_metadata(metadata: dict, key: str, value: Any, add_empty_list = True):
    """
    Adds a particular aspect of ModuleItem metadata to map

    e.g. a numerical input "foo" might want to require a minimum value of 0.
    Then map would be the dict of "foo", key would be "min", and value would be 0.
    :param metadata: The dict of metadata for some parameter
    :param key: The name of a metadata type on that parameter
    :param value: The value of that metadata type
    :param add_empty_list: An option for denoting whether empty collections should be added.
        We usually don't want it if it is e.g. the choices, but we usually want it otherwise.
    """
    if value is None: return
    try:
        py_value = ij.py.from_java(value)
        if isinstance(py_value, Collection):
            if (len(value) == 0 and not add_empty_list): return
            value = [ij.py.from_java(v) for v in value]
        metadata[key] = value
    except Exception:
        pass


def _add_scijava_metadata(unresolved_inputs) -> Dict[str, Dict[str, Any]]:
    metadata = {}
    for input in unresolved_inputs:
        key = ij().py.from_java(input.getName())
        param_map = {}
        _add_param_metadata(param_map, "max", input.getMaximumValue())
        _add_param_metadata(param_map, "min", input.getMinimumValue())
        _add_param_metadata(param_map, "step", input.getStepSize())
        _add_param_metadata(param_map, "label", input.getLabel())
        _add_param_metadata(param_map, "tooltip", input.getDescription())
        _add_param_metadata(param_map, "choices", input.getChoices(), add_empty_list=False)

        if len(param_map) > 0:
            metadata[key] = param_map

    return metadata



def functionify_module_execution(viewer: Viewer, logger, module, info) -> Tuple[Callable, dict]:
    """Converts a module into a Widget that can be added to napari."""
    # Run preprocessors until we hit input harvesting
    _preprocess_non_inputs(module)

    # Determine which inputs must be resolved by the user
    unresolved_inputs = _filter_unresolved_inputs(module, info.inputs())
    unresolved_inputs = _sink_default_inputs(unresolved_inputs)

    # Package the rest of the execution into a widget
    def module_execute(
        *user_resolved_inputs,
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
        result = ij().py.from_java(j_result) 
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
    magic_kwargs = _add_scijava_metadata(unresolved_inputs)

    return (module_execute, magic_kwargs)
