import pytest
from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from napari_imagej._flow_layout import FlowLayout
from napari_imagej.setup_imagej import JavaClasses
from napari_imagej.widget import (
    FocusWidget,
    ImageJWidget,
    ResultsWidget,
    SearchbarWidget,
)


def test_widget_layout(imagej_widget: ImageJWidget):
    """Ensures a vertical widget layout."""
    assert isinstance(imagej_widget.layout(), QVBoxLayout)


def test_widget_searchbar_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the searchbar widget."""
    searchbar: QWidget = imagej_widget.search
    assert isinstance(searchbar.layout(), QHBoxLayout)
    search_widget: QLineEdit = searchbar.findChild(QLineEdit)
    assert search_widget is not None


def test_widget_table_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the search results table."""
    table: QTableWidget = imagej_widget.findChild(QTableWidget)
    assert 12 == table.rowCount()
    assert 1 == table.columnCount()
    assert QAbstractItemView.SelectRows == table.selectionBehavior()
    assert table.showGrid() is False


def test_widget_subwidget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of imagej_widget children"""
    subwidgets = imagej_widget.children()
    assert len(subwidgets) == 4
    assert isinstance(subwidgets[0], QVBoxLayout)
    assert isinstance(subwidgets[1], SearchbarWidget)
    assert isinstance(subwidgets[2], ResultsWidget)
    assert isinstance(subwidgets[3], FocusWidget)


def test_searchbar_widget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of search widget children"""
    searchbar: SearchbarWidget = imagej_widget.findChild(SearchbarWidget)
    subwidgets = searchbar.children()
    assert len(subwidgets) == 2
    assert isinstance(subwidgets[0], QHBoxLayout)
    assert isinstance(subwidgets[1], QLineEdit)


def test_results_widget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of results widget children"""
    results: ResultsWidget = imagej_widget.findChild(ResultsWidget)
    subwidgets = results.children()
    assert len(subwidgets) == 3
    assert isinstance(subwidgets[0], QVBoxLayout)
    assert isinstance(subwidgets[1], QTableWidget)
    assert isinstance(subwidgets[2], QTableWidget)


def test_focus_widget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of focus widget children"""
    focuser: FocusWidget = imagej_widget.findChild(FocusWidget)
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


jc = JavaClasses()


def test_button_param_regression(ij, imagej_widget: ImageJWidget):
    plugins = ij.get("org.scijava.plugin.PluginService")
    searcher = plugins.getPlugin(jc.ModuleSearcher, jc.Searcher).createInstance()
    ij.context().inject(searcher)
    results = searcher.search("frangi", False)
    assert len(results) == 1
    searchService = ij.get("org.scijava.search.SearchService")
    imagej_widget.highlighter.focused_actions = searchService.actions(results[0])
    button_params = imagej_widget.highlighter._button_params_from_actions()
    assert button_params[0][0] == "Run"
    assert (
        imagej_widget.highlighter.tooltips[button_params[0][0]]
        == "Runs functionality from a modal widget. Best for single executions"
    )
    assert button_params[1][0] == "Widget"
    assert (
        imagej_widget.highlighter.tooltips[button_params[1][0]]
        == "Runs functionality from a napari widget. Useful for parameter sweeping"
    )
    assert button_params[2][0] == "Help"
    assert (
        imagej_widget.highlighter.tooltips[button_params[2][0]]
        == "Opens the functionality's ImageJ.net wiki page"
    )
    assert button_params[3][0] == "Source"
    assert (
        imagej_widget.highlighter.tooltips[button_params[3][0]]
        == "Opens the source code on GitHub"
    )
    assert button_params[4][0] == "Batch"
    assert button_params[4][0] not in imagej_widget.highlighter.tooltips


def test_keymaps(make_napari_viewer, qtbot):
    """Tests that 'L' is added to the keymap by ImageJWidget"""
    viewer: Viewer = make_napari_viewer()
    assert "L" not in viewer.keymap
    ImageJWidget(viewer)
    assert "L" in viewer.keymap
    # TODO: I can't seem to figure out how to assert that pressing 'L'
    # sets the focus of the search bar.
    # Typing viewer.keymap['L'](viewer) does nothing. :(


def test_result_single_click(make_napari_viewer, qtbot):
    viewer: Viewer = make_napari_viewer()
    imagej_widget: ImageJWidget = ImageJWidget(viewer)
    viewer
    # Test single click spawns buttons
    assert len(imagej_widget.highlighter.focused_action_buttons) == 0
    imagej_widget.results._search("Frangi")
    item = imagej_widget.results._tables[0].item(0, 0)
    assert item is not None
    rect = imagej_widget.results._tables[0].visualItemRect(item)
    qtbot.mouseClick(
        imagej_widget.results._tables[0].viewport(), Qt.LeftButton, pos=rect.center()
    )
    assert len(imagej_widget.highlighter.focused_action_buttons) == 5

    # Test double click spawns the widget


def test_result_double_click(make_napari_viewer, qtbot):
    viewer: Viewer = make_napari_viewer()
    imagej_widget: ImageJWidget = ImageJWidget(viewer)
    viewer
    # Test double click spawns the widget
    assert len(viewer.window._dock_widgets) == 0
    imagej_widget.results._search("Frangi")
    item = imagej_widget.results._tables[0].item(0, 0)
    assert item is not None
    rect = imagej_widget.results._tables[0].visualItemRect(item)
    # HACK: For some reason, we need to click before a double click.
    # This seems to be the issue described in
    # https://stackoverflow.com/questions/46795224/qlistwidget-doesnt-recognize-signals-from-qtestmousedclick
    qtbot.mouseClick(
        imagej_widget.results._tables[0].viewport(), Qt.LeftButton, pos=rect.center()
    )
    qtbot.mouseDClick(
        imagej_widget.results._tables[0].viewport(), Qt.LeftButton, pos=rect.center()
    )
    assert len(viewer.window._dock_widgets) == 1
