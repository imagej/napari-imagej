"""
A module used to identify Python widget mappings for given Java parameters.

Notable functions included in the module:
    * preferred_widget_for()
        - finds the best widget (as a str) for a ModuleItem
        and corresponding python type
"""

from typing import Callable, Dict, Optional, Union, get_args, get_origin

from napari.layers import Image

from napari_imagej.java import jc
from napari_imagej.widgets.parameter_widgets import (
    ShapeWidget,
    file_widget_for,
    number_widget_for,
    numeric_type_widget_for,
)

PREFERENCE_FUNCTIONS = []


def _widget_preference(
    func: Callable[["jc.ModuleItem", Union[type, str]], Optional[str]],
) -> Callable[["jc.ModuleItem", Union[type, str]], Optional[str]]:
    PREFERENCE_FUNCTIONS.append(func)
    return func


def _unwrap_optional(type_hint: Union[type, str]) -> Union[type, str]:
    origin = get_origin(type_hint)
    args = get_args(type_hint)
    # If it is an optional - unwrap it
    if origin is Union and type(None) in args:
        # Find the (first) argument that is not None
        for arg in args:
            if arg is not None:
                return arg
    # Otherwise - do nothing
    return type_hint


def preferred_widget_for(
    item: "jc.ModuleItem",
    type_hint: Union[type, str],
) -> Optional[Union[type, str]]:
    """
    Finds the best MAGICGUI widget for a given SciJava ModuleItem,
    and its corresponding Python type

    For ModuleItems with unknown preferences, None is returned.

    :param item: The ModuleItem with a style
    :param type_hint: The PYTHON type for the parameter
    :return: The best magicgui widget type, if it is known
    """
    for pref_func in PREFERENCE_FUNCTIONS:
        pref = pref_func(item, type_hint)
        if pref:
            return pref

    return None


@_widget_preference
def _numeric_type_preference(
    item: "jc.ModuleItem", type_hint: Union[type, str]
) -> Optional[Union[type, str]]:
    if issubclass(item.getType(), jc.NumericType):
        return numeric_type_widget_for(item.getType())


@_widget_preference
def _number_preference(
    item: "jc.ModuleItem", type_hint: Union[type, str]
) -> Optional[Union[type, str]]:
    if issubclass(item.getType(), jc.Number):
        return number_widget_for(item.getType())


@_widget_preference
def _mutable_output_preference(
    item: "jc.ModuleItem", type_hint: Union[type, str]
) -> Optional[Union[type, str]]:
    # We only care about mutable outputs
    if item.isInput() and item.isOutput():
        # If the type hint is an (optional) Image, use MutableOutputWidget
        if (
            type_hint == "napari.layers.Image"
            or type_hint == Image
            or type_hint == Optional[Image]
        ):
            return "napari_imagej.widgets.parameter_widgets.MutableOutputWidget"
        # Optional['napari.layers.Image'] is hard to resolve,
        # so we use special case logic for it.
        # HACK: In Python 3.7 (and maybe 3.8), Optional['napari.layers.Image'] does
        # not have the same stringification as it does in Python 3.9+. Thus we have
        # to check two strings.
        if (
            str(type_hint)
            == "typing.Union[ForwardRef('napari.layers.Image'), NoneType]"
            or str(type_hint) == "typing.Optional[ForwardRef('napari.layers.Image')]"
        ):
            return "napari_imagej.widgets.parameter_widgets.MutableOutputWidget"


@_widget_preference
def _shape_preference(
    item: "jc.ModuleItem", type_hint: Union[type, str]
) -> Optional[Union[type, str]]:
    if item.isInput() and not item.isOutput():
        if item.getType() == jc.Shape:
            return ShapeWidget


# The definitive mapping of scijava widget styles to magicgui widget types
_supported_scijava_styles: Dict[str, Dict[type, str]] = {
    # ChoiceWidget styles
    "listBox": {str: "Select"},
    "radioButtonHorizontal": {str: "RadioButtons"},
    "radioButtonVertical": {str: "RadioButtons"},
    # NumberWidget styles
    "slider": {int: "Slider", float: "FloatSlider"},
    "spinner": {int: "SpinBox", float: "FloatSpinBox"},
}


@_widget_preference
def _scijava_style_preference(
    item: "jc.ModuleItem", type_hint: Union[type, str]
) -> Optional[str]:
    style: str = item.getWidgetStyle()
    if style not in _supported_scijava_styles:
        return None
    style_options = _supported_scijava_styles[style]
    type_hint = _unwrap_optional(type_hint)
    for k, v in style_options.items():
        if issubclass(type_hint, k):
            return v


@_widget_preference
def _scijava_path_preference(
    item: "jc.ModuleItem", type_hint: Union[type, str]
) -> Optional[str]:
    if "pathlib.PosixPath" == str(type_hint):
        return file_widget_for(item)
