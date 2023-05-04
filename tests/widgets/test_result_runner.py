"""
A module testing napari_imagej.widgets.result_runner
"""
import pytest
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from napari_imagej.java import JavaClasses
from napari_imagej.widgets.layouts import QFlowLayout
from napari_imagej.widgets.result_runner import ResultRunner


class JavaClassesTest(JavaClasses):
    @JavaClasses.blocking_import
    def ModuleSearchResult(self):
        return "org.scijava.search.module.ModuleSearchResult"


jc = JavaClassesTest()


@pytest.fixture
def result_runner(imagej_widget):
    return imagej_widget.result_runner


def test_result_runner(result_runner):
    """Tests the number and expected order of ResultRunner widget children"""
    subwidgets = result_runner.children()
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
    result_runner: ResultRunner, example_info: "jc.ModuleInfo"
):
    """Simple regression test ensuring search action button population"""

    result = jc.ModuleSearchResult(example_info, "")
    buttons = result_runner._buttons_for(result)
    assert len(buttons) == 5
    assert {b.text() for b in buttons} == {"Batch", "Help", "Run", "Source", "Widget"}


def test_widget_button_spawns_widget(
    result_runner: ResultRunner, example_info: "jc.ModuleInfo", asserter
):
    """Simple regression test ensuring the widget button spawns a new napari widget"""

    result = jc.ModuleSearchResult(example_info, "")
    buttons = result_runner._buttons_for(result)
    assert buttons[1].text() == "Widget"
    assert result.name() not in result_runner.viewer.window._dock_widgets.keys()
    buttons[1].action()
    assert result.name() in result_runner.viewer.window._dock_widgets.keys()
