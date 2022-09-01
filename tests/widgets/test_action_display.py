"""
A module testing napari_imagej.widgets.focuser
"""
import pytest
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from napari_imagej.java import JavaClasses
from napari_imagej.widgets.action_display import SearchActionDisplay
from napari_imagej.widgets.layouts import FlowLayout


class JavaClassesTest(JavaClasses):
    @JavaClasses.blocking_import
    def ModuleSearchResult(self):
        return "org.scijava.search.module.ModuleSearchResult"


jc = JavaClassesTest()


@pytest.fixture
def focuser(viewer):
    return SearchActionDisplay(viewer)


def test_focus_widget_layout(focuser):
    """Tests the number and expected order of focus widget children"""
    subwidgets = focuser.children()
    # Note: This is BEFORE any module is focused.
    assert len(subwidgets) == 3
    # The layout
    assert isinstance(subwidgets[0], QVBoxLayout)
    # The label describing the focused module
    assert isinstance(subwidgets[1], QLabel)
    # The button Container
    assert isinstance(subwidgets[2], QWidget)
    assert isinstance(subwidgets[2].layout(), FlowLayout)


@pytest.fixture
def example_info(ij):
    return ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )


def test_button_param_regression(
    focuser: SearchActionDisplay, example_info: "jc.ModuleInfo"
):
    """Simple regression test ensuring search action button population"""

    result = jc.ModuleSearchResult(example_info, "")
    py_actions = focuser._actions_from_result(result)
    assert py_actions[0].name == "Run"
    assert (
        focuser.tooltips[py_actions[0][0]]
        == "Runs functionality from a modal widget. Best for single executions"
    )
    assert py_actions[1].name == "Widget"
    assert (
        focuser.tooltips[py_actions[1][0]]
        == "Runs functionality from a napari widget. Useful for parameter sweeping"
    )
    assert py_actions[2].name == "Batch"
    assert py_actions[2].name not in focuser.tooltips
