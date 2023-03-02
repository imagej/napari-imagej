"""
A module testing napari_imagej.widgets.result_runner
"""
import pytest
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget

from napari_imagej import settings
from napari_imagej.java import JavaClasses
from napari_imagej.widgets.layouts import QFlowLayout
from napari_imagej.widgets.result_runner import ResultRunner, _action_tooltips


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


RUNNING_LEGACY = settings["include_imagej_legacy"].get(bool)

# TODO: Uncomment once scijava-search 2.0.2 can be required
# @pytest.mark.skipif(RUNNING_LEGACY, reason="Tests Pure IJ2 behavior!")
# def test_button_param_regression(
#     result_runner: ResultRunner, example_info: "jc.ModuleInfo"
# ):
#     """Simple regression test ensuring search action button population"""

#     result = jc.ModuleSearchResult(example_info, "")
#     buttons = result_runner._buttons_for(result)
#     assert buttons[0].text() == "Run"
#     assert (
#         _action_tooltips[buttons[0].text()]
#         == "Runs the command immediately, asking for inputs in a pop-up dialog box"
#     )
#     assert buttons[1].text() == "Widget"
#     assert (
#         _action_tooltips[buttons[1].text()]
#         == "Creates a napari widget for executing this command with varying inputs"
#     )
#     assert buttons[2].text() == "Batch"
#     assert buttons[2].text() not in _action_tooltips


# TODO: Uncomment once scijava-search 2.0.2 can be required
# @pytest.mark.skipif(not RUNNING_LEGACY, reason="Tests ImageJ Legacy behavior!")
# def test_button_param_regression_legacy(
#     result_runner: ResultRunner, example_info: "jc.ModuleInfo"
# ):
#     """Simple regression test ensuring search action button population"""

#     result = jc.ModuleSearchResult(example_info, "")
#     buttons = result_runner._buttons_for(result)
#     assert buttons[0].text() == "Run"
#     assert (
#         _action_tooltips[buttons[0].text()]
#         == "Runs the command immediately, asking for inputs in a pop-up dialog box"
#     )
#     assert buttons[1].text() == "Widget"
#     assert (
#         _action_tooltips[buttons[1].text()]
#         == "Creates a napari widget for executing this command with varying inputs"
#     )
#     assert buttons[2].text() == "Help"
#     assert (
#         _action_tooltips[buttons[2].text()]
#         == "Opens the functionality's ImageJ.net wiki page"
#     )
#     assert buttons[3].text() == "Source"
#     assert _action_tooltips[buttons[3].text()] == "Opens the source code in browser"
#     assert buttons[4].text() == "Batch"
#     assert buttons[4].text() not in _action_tooltips


def test_widget_button_spawns_widget(
    result_runner: ResultRunner, example_info: "jc.ModuleInfo", asserter
):
    """Simple regression test ensuring the widget button spawns a new napari widget"""

    result = jc.ModuleSearchResult(example_info, "")
    buttons = result_runner._buttons_for(result)
    assert buttons[1].text() == "Widget"
    assert (
        _action_tooltips[buttons[0].text()]
        == "Runs the command immediately, asking for inputs in a pop-up dialog box"
    )
    assert result.name() not in result_runner.viewer.window._dock_widgets.keys()
    buttons[1].action()
    assert result.name() in result_runner.viewer.window._dock_widgets.keys()
