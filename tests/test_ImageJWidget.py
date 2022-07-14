import pytest
from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTreeWidget,
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
    assert len(subwidgets) == 2
    assert isinstance(subwidgets[0], QVBoxLayout)
    assert isinstance(subwidgets[1], QTreeWidget)


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
    imagej_widget.results._wait_for_tree_setup()
    imagej_widget.results._search("Frangi")
    tree = imagej_widget.results._tree
    item = tree.topLevelItem(0).child(0)
    rect = tree.visualItemRect(item)
    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=rect.center())
    assert len(imagej_widget.highlighter.focused_action_buttons) == 5


def test_arrow_key_expansion(imagej_widget: ImageJWidget, qtbot):
    # Wait for the searchers to be ready
    imagej_widget.results._wait_for_tree_setup()
    # Search something
    imagej_widget.results._search("Fi")
    tree = imagej_widget.results._tree
    tree.setCurrentItem(tree.topLevelItem(0))
    expanded = tree.currentItem().isExpanded()
    # Part 1: toggle with Enter
    qtbot.keyPress(tree, Qt.Key_Return)
    assert tree.currentItem().isExpanded() is not expanded
    qtbot.keyPress(tree, Qt.Key_Return)
    assert tree.currentItem().isExpanded() is expanded
    # Part 2: test arrow keys
    tree.currentItem().setExpanded(True)
    # Part 2.1: Expanded + Left hides children
    qtbot.keyPress(tree, Qt.Key_Left)
    assert tree.currentItem().isExpanded() is False
    # Part 2.2: Hidden + Right shows children
    qtbot.keyPress(tree, Qt.Key_Right)
    assert tree.currentItem().isExpanded() is True
    # Part 2.3: Expanded + Right selects first child
    parent = tree.currentItem()
    qtbot.keyPress(tree, Qt.Key_Right)
    qtbot.waitUntil(lambda: tree.currentItem() is parent.child(0))
    # Part 2.4: Child + Left returns to parent
    qtbot.keyPress(tree, Qt.Key_Left)
    qtbot.waitUntil(lambda: tree.currentItem() is parent)


def test_arrow_key_selection(imagej_widget: ImageJWidget, qtbot):
    # Wait for the searchers to be ready
    imagej_widget.results._wait_for_tree_setup()
    # Search something
    imagej_widget.results._search("Fi")
    tree = imagej_widget.results._tree
    # Assert that there is a result in each
    for i in range(tree.topLevelItemCount()):
        assert tree.topLevelItem(i).childCount() > 0
    # Ensure no row is selected
    assert tree.currentItem() is None
    # Go down, ensure that the first row gets highlighted
    qtbot.keyPress(imagej_widget.search.bar, Qt.Key_Down)
    qtbot.waitUntil(lambda: tree.currentItem() is tree.topLevelItem(0))
    # Iterate through the tables, ensure arrow keys change selection
    for i in range(tree.topLevelItemCount()):
        for j in range(tree.topLevelItem(i).childCount()):
            qtbot.keyPress(tree, Qt.Key_Down)
            qtbot.waitUntil(lambda: tree.currentItem() is tree.topLevelItem(i).child(j))
        if i < tree.topLevelItemCount() - 1:
            qtbot.keyPress(tree, Qt.Key_Down)
            qtbot.waitUntil(lambda: tree.currentItem() is tree.topLevelItem(i + 1))
    # The last key press was with the last element selected.
    # ensure that we can't go further
    last_searcher = tree.topLevelItem(tree.topLevelItemCount() - 1)
    qtbot.waitUntil(
        lambda: tree.currentItem()
        is last_searcher.child(last_searcher.childCount() - 1)
    )
