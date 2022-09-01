"""
A module testing napari_imagej.widgets.action_display
"""
import pytest
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from napari_imagej.java import JavaClasses
from napari_imagej.widgets.action_display import SearchActionDisplay, _tooltips
from napari_imagej.widgets.layouts import QFlowLayout


class JavaClassesTest(JavaClasses):
    @JavaClasses.blocking_import
    def ModuleSearchResult(self):
        return "org.scijava.search.module.ModuleSearchResult"


jc = JavaClassesTest()


@pytest.fixture
def action_display(viewer):
    return SearchActionDisplay(viewer)


def test_action_display_widget_layout(action_display):
    """Tests the number and expected order of SearchActionDisplay widget children"""
    subwidgets = action_display.children()
    # Note: This is BEFORE any module is selected.
    assert len(subwidgets) == 3
    # The layout
    assert isinstance(subwidgets[0], QVBoxLayout)
    # The label describing the selected module
    assert isinstance(subwidgets[1], QLabel)
    # The button Container
    assert isinstance(subwidgets[2], QWidget)
    assert isinstance(subwidgets[2].layout(), QFlowLayout)


@pytest.fixture
def example_info(ij):
    return ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )


def test_button_param_regression(
    action_display: SearchActionDisplay, example_info: "jc.ModuleInfo"
):
    """Simple regression test ensuring search action button population"""

    result = jc.ModuleSearchResult(example_info, "")
    buttons = action_display._buttons_for(result)
    assert buttons[0].text() == "Run"
    assert (
        _tooltips[buttons[0].text()]
        == "Runs functionality from a modal widget. Best for single executions"
    )
    assert buttons[1].text() == "Widget"
    assert (
        _tooltips[buttons[1].text()]
        == "Runs functionality from a napari widget. Useful for parameter sweeping"
    )
    assert buttons[2].text() == "Batch"
    assert buttons[2].text() not in _tooltips
