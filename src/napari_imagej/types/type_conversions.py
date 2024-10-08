"""
A module containing TYPE conversion utilities.

When wrapping Java functionality, we must perform data conversion in two phases.

The first phase of conversion involves noting the required JAVA type of a parameter
and determining the corresponding PYTHON type to use in harvesting input.

The second phase of conversion involves transforming accepted PYTHON inputs into
their "equivalent" JAVA objects.

This module concerns itself with the first phase of conversion, while the second phase
is left to PyImageJ's to_java function.

Notable functions included in the module:
    * python_type_of()
        - determines an "equivalent" python type for a given SciJava ModuleItem
"""

from typing import Callable, List, Optional, Tuple, Type

from jpype import JObject
from scyjava import Priority

from napari_imagej import nij
from napari_imagej.java import jc
from napari_imagej.types.enum_likes import enum_like
from napari_imagej.types.enums import py_enum_for
from napari_imagej.types.type_hints import type_hints
from napari_imagej.widgets.parameter_widgets import widget_supported_java_types

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


def type_hint_for(module_item: "jc.ModuleItem"):
    """Returns a python type hint for the passed Java ModuleItem."""
    for converter, _ in sorted(
        _MODULE_ITEM_CONVERTERS, reverse=True, key=lambda x: x[1]
    ):
        converted = converter(module_item)
        if converted is not None:
            return converted
    raise ValueError(
        (
            f"Cannot determine python type hint of {module_item.getType()}. "
            "Let us know about the failure at https://forum.image.sc, "
            "or file an issue at https://github.com/imagej/napari-imagej!"
        )
    )


def _optional_of(p_type: type, item: "jc.ModuleItem") -> type:
    if not p_type:
        return p_type
    return p_type if item.isRequired() else Optional[p_type]


@module_item_converter(priority=Priority.HIGH)
def enum_like_converter(item: "jc.ModuleItem"):
    """
    Checks to see if this type can be satisfied by a PythonStandin.
    For a PythonStandin to work, it MUST be a pure input.
    This is because the python type has no functionality, as it is just an Enum choice.
    """
    if item.isInput() and not item.isOutput():
        return _optional_of(enum_like(item.getType(), None), item)


@module_item_converter(priority=Priority.HIGH)
def enum_converter(item: "jc.ModuleItem"):
    """
    Checks to see if this type can be satisfied by an autogenerated Enum
    """
    t = item.getType()
    if not isinstance(t, jc.Class):
        t = t.class_
    return _optional_of(py_enum_for(t), item)


@module_item_converter()
def widget_enabled_java_types(item: "jc.ModuleItem"):
    """
    Checks to see if this JAVA type is fully supported through magicgui widgets.
    This is sometimes done to expose object creation/usage when there ISN'T
    a good Python equivalent.
    """
    if item.isInput() and not item.isOutput():
        if item.getType() in widget_supported_java_types():
            # TODO: NB: Ideally, we'd return item.getType() here.
            # Unfortunately, though, that doesn't work, and I can't figure out why
            # due to https://github.com/imagej/napari-imagej/issues/7
            # For that reason, we return the Python type JObject instead.
            # While this return isn't WRONG, it could be MORE correct.
            return JObject


def _checkerUsingFunc(
    item: "jc.ModuleItem", func: Callable[[Type, Type], bool]
) -> Optional[Type]:
    """
    The logic of this checker is as follows:

    type_hints contains a bunch of TypeHints, data classes mapping a Java type
    to a corresponding python hint.

    There are 3 cases:
    1) The ModuleItem is a PURE INPUT:
        We can satisfy item with an object of python type hint.hint IF its
        corresponding java type hint.type can be converted to item's type.
        The conversion then goes:
        hint.hint -> hint.type -> java_type
    2) The ModuleItem is a PURE OUTPUT:
        We can satisfy item with an object of python type hint.hint IF we can convert
        java_type into its corresponding java type hint.type. The conversion then goes
        java_type -> hint.type -> hint.hint
    3) The ModuleItem is BOTH:
        We can satisfy item with ptype IF we satisfy both 1 and 2.
        hint.hint -> hint.type -> java_type -> hint.type -> hint.hint

    :param item: the ModuleItem we'd like to convert
    :return: the python equivalent of ModuleItem's type, or None if that type
    cannot be converted.
    """
    # Get the type of the Module item
    java_type = item.getType()
    # Case 1
    if item.isInput() and not item.isOutput():
        for hint in type_hints():
            # can we go from hint.type to java_type?
            if func(hint.type, java_type):
                return _optional_of(hint.hint, item)
    # Case 2
    elif item.isOutput() and not item.isInput():
        # NB type_pairs is ordered from least to most specific.
        for hint in type_hints():
            # can we go from java_type to hint.type?
            if func(java_type, hint.type):
                return _optional_of(hint.hint, item)
    # Case 3
    elif item.isInput() and item.isOutput():
        for hint in type_hints():
            # can we go both ways?
            if func(hint.type, java_type) and func(java_type, hint.type):
                return _optional_of(hint.hint, item)

    # Didn't satisfy any cases!
    return None


@module_item_converter(priority=Priority.HIGH)
def isEqualChecker(item: "jc.ModuleItem") -> Optional[Type]:
    """
    Determines whether we have a type hint for this SPECIFIC type.
    """

    def isAssignable(from_type, to_type) -> bool:
        # Use Types to get the raw type of each
        from_raw = jc.Types.raw(from_type)
        to_raw = jc.Types.raw(to_type)
        return to_raw.equals(from_raw)

    return _checkerUsingFunc(item, isAssignable)


@module_item_converter()
def isAssignableChecker(item: "jc.ModuleItem") -> Optional[Type]:
    """
    Determines whether we can simply cast from ptype to item's type java_type
    """

    def isAssignable(from_type, to_type) -> bool:
        # Use Types to get the raw type of each
        from_raw = jc.Types.raw(from_type)
        to_raw = jc.Types.raw(to_type)
        return to_raw.isAssignableFrom(from_raw)

    return _checkerUsingFunc(item, isAssignable)


@module_item_converter(priority=Priority.LOW)
def canConvertChecker(item: "jc.ModuleItem") -> Optional[Type]:
    """
    Determines whether imagej can do a conversion from ptype to item's type java_type.
    """

    def isAssignable(from_type, to_type) -> bool:
        return nij.ij.convert().supports(from_type, to_type)

    return _checkerUsingFunc(item, isAssignable)
