"""
A module used to identify widget preferences for given Java parameters.

Notable functions included in the module:
    * preferred_widget_for()
        - finds the best widget (as a str) for a ModuleItem
        and corresponding python type
"""
from typing import Dict, Optional, Union

from napari_imagej.java import jc

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


def preferred_widget_for(
    item: "jc.ModuleItem",
    type_hint: Union[type, str],
) -> Optional[str]:
    """
    Finds the best MAGICGUI widget for a given SciJava ModuleItem,
    and its corresponding Python type

    For ModuleItems with unknown preferences, None is returned.

    :param item: The ModuleItem with a style
    :param type_hint: The PYTHON type for the parameter
    :return: The best magicgui widget type, if it is known
    """
    if type_hint == "napari.layers.Image" and item.isInput() and item.isOutput():
        return "napari_imagej.widgets.parameter_widgets.MutableOutputWidget"

    style: str = item.getWidgetStyle()
    if style not in _supported_scijava_styles:
        return None
    style_options = _supported_scijava_styles[style]
    for k, v in style_options.items():
        if issubclass(type_hint, k):
            return v
    return None
