"""
A module testing napari_imagej.types.widget_mappings
"""
from typing import Optional

import magicgui
import napari
import pytest
from magicgui.widgets import (
    FloatSlider,
    FloatSpinBox,
    RadioButtons,
    Select,
    Slider,
    SpinBox,
)
from napari.layers import Image

from napari_imagej.types.widget_mappings import (
    _supported_scijava_styles,
    preferred_widget_for,
)
from napari_imagej.utilities._module_utils import type_hint_for
from napari_imagej.widgets.parameter_widgets import (
    DirectoryWidget,
    MutableOutputWidget,
    OpenFileWidget,
    SaveFileWidget,
    ShapeWidget,
)
from tests.utils import DummyModuleItem, jc


def _assert_widget_matches_item(item, type_hint, widget_type, widget_class):
    # We only need item for the getWidgetStyle() function
    actual = preferred_widget_for(item, type_hint)
    assert widget_type == actual

    def func(foo):
        print(foo, "bar")

    func.__annotation__ = {"foo": type_hint}

    widget = magicgui.magicgui(
        function=func, call_button=False, foo={"widget_type": actual}
    )
    assert len(widget._list) == 1
    assert isinstance(widget._list[0], widget_class)


parameterizations = [
    ("listBox", str, "Select", Select),
    ("radioButtonHorizontal", str, "RadioButtons", RadioButtons),
    ("radioButtonVertical", str, "RadioButtons", RadioButtons),
    ("slider", int, "Slider", Slider),
    ("slider", float, "FloatSlider", FloatSlider),
    ("spinner", int, "SpinBox", SpinBox),
    ("spinner", float, "FloatSpinBox", FloatSpinBox),
]


@pytest.mark.parametrize(
    argnames=["style", "type_hint", "widget_type", "widget_class"],
    argvalues=parameterizations,
)
def test_preferred_widget_for(style, type_hint, widget_type, widget_class):
    """
    Tests that a style and type are mapped to the corresponding widget_class
    :param style: the SciJava style
    :param type_hint: the PYTHON type of a parameter
    :param widget_type: the name of a magicgui widget
    :param widget_class: the class corresponding to name
    """
    item: DummyModuleItem = DummyModuleItem()
    item.setWidgetStyle(style)
    _assert_widget_matches_item(item, type_hint, widget_type, widget_class)
    # let's also check optional parameter
    item: DummyModuleItem = DummyModuleItem(isRequired=False)
    item.setWidgetStyle(style)
    _assert_widget_matches_item(item, Optional[type_hint], widget_type, widget_class)


@pytest.mark.parametrize(
    "type_hint",
    ["napari.layers.Image", Image, Optional["napari.layers.Image"], Optional[Image]],
)
def test_preferred_widget_for_parameter_widgets(type_hint):
    # MutableOutputWidget
    item: DummyModuleItem = DummyModuleItem(
        jtype=jc.ArrayImg, isInput=True, isOutput=True
    )
    widget_type = "napari_imagej.widgets.parameter_widgets.MutableOutputWidget"
    _assert_widget_matches_item(item, type_hint, widget_type, MutableOutputWidget)


def test_all_styles_in_parameterizations():
    """
    Tests that all style mappings declared in supported_styles
    are tested in test_widget_for_style_and_type
    """
    _parameterizations = [p[:-1] for p in parameterizations]
    all_styles = []
    for style in _supported_scijava_styles:
        for type_hint, widget_type in _supported_scijava_styles[style].items():
            all_styles.append((style, type_hint, widget_type))
    assert all_styles == _parameterizations


@pytest.mark.parametrize(
    ["style_str", "widget_type"],
    [
        ("OPEN_STYLE", OpenFileWidget),
        ("SAVE_STYLE", SaveFileWidget),
        ("DIRECTORY_STYLE", DirectoryWidget),
    ],
)
def test_file_widget(style_str, widget_type):
    item = DummyModuleItem(jtype=jc.File)
    # Get the SciJava style from the string
    style = getattr(jc.FileWidget, style_str)
    item.setWidgetStyle(style)

    type_hint = type_hint_for(item)
    _assert_widget_matches_item(item, type_hint, widget_type, widget_type)


def test_shape_widget():
    item = DummyModuleItem(jtype=jc.Shape)
    type_hint = type_hint_for(item)
    _assert_widget_matches_item(item, type_hint, ShapeWidget, ShapeWidget)
