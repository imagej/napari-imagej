"""
The definitive mapping of scyjava widget styles to magicgui widget types
"""
from typing import Dict, Optional, Union

from napari_imagej.setup_imagej import jc

# The definitive mapping of scyjava widget styles to magicgui widget types
# This map allows us to determine the "best" widget for a given ModuleItem.
# For particular styles, there are sometimes multiple corresponding widgets.
# We then have to differentiate by the PYTHON type of the parameter.
supported_styles: Dict[str, Dict[type, str]] = {
    # ChoiceWidget styles
    "listBox": {str: "Select"},
    "radioButtonHorizontal": {str: "RadioButtons"},
    "radioButtonVertical": {str: "RadioButtons"},
    # NumberWidget styles
    "slider": {int: "Slider", float: "FloatSlider"},
    "spinner": {int: "SpinBox", float: "FloatSpinBox"},
}


def widget_for_item_and_type(
    item: "jc.ModuleItem",
    type_hint: Union[type, str],
) -> Optional[str]:
    """
    Convenience function for interacting with _supported_styles
    :param item: The ModuleItem with a style
    :param type_hint: The PYTHON type for the parameter
    :return: The best widget type, if it is known
    """
    if type_hint == "napari.layers.Image" and item.isInput() and item.isOutput():
        return "napari_imagej.widgets.parameter_widgets.MutableOutputWidget"

    style: str = item.getWidgetStyle()
    if style not in supported_styles:
        return None
    style_options = supported_styles[style]
    for k, v in style_options.items():
        if issubclass(type_hint, k):
            return v
    return None
