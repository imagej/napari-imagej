"""
A module testing napari_imagej.widgets.result_runner
"""

from __future__ import annotations

import pytest
from qtpy.QtWidgets import QVBoxLayout, QWidget
from scyjava import JavaClasses
from superqt import QElidingLabel

from napari_imagej.widgets.layouts import QFlowLayout
from napari_imagej.widgets.result_runner import ResultRunner


class JavaClassesTest(JavaClasses):
    @JavaClasses.java_import
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
    assert isinstance(subwidgets[1], QElidingLabel)
    # The button Container
    assert isinstance(subwidgets[2], QWidget)
    assert isinstance(subwidgets[2].layout(), QFlowLayout)


def test_result_runner_size_hints(result_runner: ResultRunner):
    """Ensuring the widget doesn't grow when text is set."""
    # The problem we want to safeguard against here is ensuring the minimum
    # size hint doesn't change - this is what causes issues like
    # https://github.com/imagej/napari-imagej/issues/273

    # Capture size hint
    hint = result_runner.minimumSizeHint()
    width_hint, height_hint = hint.width(), hint.height()
    # Resize result_runner
    result_runner._setText("o" * 50)
    # Assert size hint did not change
    hint = result_runner.minimumSizeHint()
    assert width_hint == hint.width()
    assert height_hint == hint.height()


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
