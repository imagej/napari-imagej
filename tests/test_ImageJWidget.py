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
    py_actions = imagej_widget.highlighter._actions_from_result(results[0])
    assert py_actions[0].name == "Run"
    assert (
        imagej_widget.highlighter.tooltips[py_actions[0][0]]
        == "Runs functionality from a modal widget. Best for single executions"
    )
    assert py_actions[1].name == "Widget"
    assert (
        imagej_widget.highlighter.tooltips[py_actions[1][0]]
        == "Runs functionality from a napari widget. Useful for parameter sweeping"
    )
    assert py_actions[2].name == "Help"
    assert (
        imagej_widget.highlighter.tooltips[py_actions[2][0]]
        == "Opens the functionality's ImageJ.net wiki page"
    )
    assert py_actions[3].name == "Source"
    assert (
        imagej_widget.highlighter.tooltips[py_actions[3][0]]
        == "Opens the source code on GitHub"
    )
    assert py_actions[4].name == "Batch"
    assert py_actions[4].name not in imagej_widget.highlighter.tooltips


def test_keymaps(make_napari_viewer, qtbot):
    """Tests that 'Ctrl+L' is added to the keymap by ImageJWidget"""
    viewer: Viewer = make_napari_viewer()
    assert "Control-L" not in viewer.keymap
    ImageJWidget(viewer)
    assert "Control-L" in viewer.keymap
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


def selected_row_index(table: QTableWidget):
    rows = table.selectionModel().selectedRows()
    if len(rows) == 0:
        return -1
    if len(rows) == 1:
        return rows[0].row()
    raise ValueError()


def test_arrow_keys(imagej_widget: ImageJWidget, qtbot):
    # Search something
    imagej_widget.results._search("Fi")
    # Assert that there is a result in each
    for result in imagej_widget.results.results:
        assert not result.isEmpty()
    # Ensure no row is selected
    for table in imagej_widget.results._tables:
        assert selected_row_index(table) == -1
    # Go down, ensure that the first row gets highlighted
    qtbot.keyPress(imagej_widget, Qt.Key_Down)
    assert selected_row_index(imagej_widget.results._tables[0]) == 0
    # Go up, ensure that the first row is still selected
    qtbot.keyPress(imagej_widget, Qt.Key_Up)
    assert selected_row_index(imagej_widget.results._tables[0]) == 0
    # Iterate through the tables, ensure arrow keys change selection
    imagej_widget._focus_row = -1
    for i, result_arr in enumerate(imagej_widget.results.results):
        if len(result_arr) > 12:
            result_arr = result_arr[:12]
        for j, result in enumerate(result_arr):
            qtbot.keyPress(imagej_widget, Qt.Key_Down)
            assert selected_row_index(imagej_widget.results._tables[i]) == j
            assert (
                imagej_widget.highlighter.focused_module
                == imagej_widget.results.results[i][j]
            )
        for j, table in enumerate(imagej_widget.results._tables):
            if i == j:
                continue
            assert selected_row_index(table) == -1
    # Try going down past the last result, ensure that we can't go further
    qtbot.keyPress(imagej_widget, Qt.Key_Down)
    for i, table in enumerate(imagej_widget.results._tables):
        if i == len(imagej_widget.results._tables) - 1:
            assert (
                selected_row_index(table)
                == imagej_widget.results._tables[i].rowCount() - 1
            )
        else:
            assert selected_row_index(table) == -1
