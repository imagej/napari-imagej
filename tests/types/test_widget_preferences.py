import magicgui
import pytest
from magicgui.widgets import (
    FloatSlider,
    FloatSpinBox,
    RadioButtons,
    Select,
    Slider,
    SpinBox,
)

from napari_imagej.types.widget_preferences import (
    _supported_scijava_styles,
    preferred_widget_for,
)
from napari_imagej.widgets.parameter_widgets import MutableOutputWidget
from tests.utils import DummyModuleItem, jc

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
    # We only need item for the getWidgetStyle() function
    item: DummyModuleItem = DummyModuleItem()
    item.setWidgetStyle(style)
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


def test_preferred_widget_for_parameter_widgets():

    # MutableOutputWidget
    item: DummyModuleItem = DummyModuleItem(
        jtype=jc.ArrayImg, isInput=True, isOutput=True
    )
    type_hint = "napari.layers.Image"
    actual = preferred_widget_for(item, type_hint)
    assert "napari_imagej.widgets.parameter_widgets.MutableOutputWidget" == actual

    def func(foo):
        print(foo, "bar")

    func.__annotation__ = {"foo": type_hint}

    widget = magicgui.magicgui(
        function=func, call_button=False, foo={"widget_type": actual}
    )
    assert len(widget._list) == 1
    assert isinstance(widget._list[0], MutableOutputWidget)


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