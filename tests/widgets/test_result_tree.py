"""
A module testing napari_imagej.widgets.results
"""

import pytest
from qtpy.QtCore import QRunnable, Qt, QThreadPool
from qtpy.QtWidgets import QApplication, QMenu

from napari_imagej.widgets.result_tree import (
    SearcherTreeItem,
    SearchResultTree,
    SearchResultTreeItem,
)
from napari_imagej.widgets.widget_utils import python_actions_for
from tests.utils import DummySearcher, DummySearchEvent, DummySearchResult
from tests.widgets.widget_utils import _populate_tree


@pytest.fixture
def results_tree():
    return SearchResultTree(None)


@pytest.fixture
def fixed_tree(ij, asserter):
    """Creates a "fake" ResultsTree with deterministic results"""
    # Create a default SearchResultTree
    tree = SearchResultTree(None)
    _populate_tree(tree, asserter)

    return tree


def test_results_widget_layout(fixed_tree: SearchResultTree):
    """Tests the number and expected order of results widget children"""
    assert fixed_tree.columnCount() == 1
    assert fixed_tree.headerItem().text(0) == "Search"


def test_arrow_key_selection(fixed_tree: SearchResultTree, qtbot, asserter):
    # Start by selecting the first item in the tree
    fixed_tree.setCurrentItem(fixed_tree.topLevelItem(0))
    asserter(lambda: fixed_tree.currentItem() is fixed_tree.topLevelItem(0))
    # HACK: For some reason, they are not expanded in the tests!
    fixed_tree.topLevelItem(0).setExpanded(True)
    for i in range(3):
        qtbot.keyPress(fixed_tree, Qt.Key_Down)
        asserter(
            lambda: fixed_tree.currentItem() is fixed_tree.topLevelItem(0).child(i)
        )
    qtbot.keyPress(fixed_tree, Qt.Key_Down)
    asserter(lambda: fixed_tree.currentItem() is fixed_tree.topLevelItem(1))
    # HACK: For some reason, they are not expanded in the tests!
    fixed_tree.topLevelItem(1).setExpanded(True)
    for i in range(2):
        qtbot.keyPress(fixed_tree, Qt.Key_Down)
        asserter(
            lambda: fixed_tree.currentItem() is fixed_tree.topLevelItem(1).child(i)
        )
    qtbot.keyPress(fixed_tree, Qt.Key_Down)
    asserter(lambda: fixed_tree.currentItem() is fixed_tree.topLevelItem(1).child(1))


def test_searchers_persist(fixed_tree: SearchResultTree, asserter):
    # Find the first searcher, and remove its children
    searcher = fixed_tree.topLevelItem(0)._searcher
    asserter(lambda: fixed_tree.topLevelItem(0).childCount() > 0)
    fixed_tree.process.emit(DummySearchEvent(searcher, []))
    # Ensure that the children disappear, but the searcher remains
    asserter(lambda: fixed_tree.topLevelItem(0).childCount() == 0)
    asserter(lambda: fixed_tree.topLevelItemCount() == 2)
    asserter(lambda: not fixed_tree.topLevelItem(0).isExpanded())


def test_resultTreeItem_regression():
    dummy = DummySearchResult()
    item = SearchResultTreeItem(dummy)
    assert item.result == dummy
    assert item.text(0) == dummy.name()


def test_searcherTreeItem_regression():
    dummy = DummySearcher("This is not a Searcher")
    item = SearcherTreeItem(dummy)
    assert item._searcher == dummy
    assert (
        item.flags()
        == Qt.ItemIsUserCheckable
        | Qt.ItemIsEnabled
        | Qt.ItemIsDragEnabled
        | Qt.ItemIsDropEnabled
    )
    assert item.text(0) == dummy.title()


def test_arrow_key_expansion(fixed_tree: SearchResultTree, qtbot, asserter):
    fixed_tree.setCurrentItem(fixed_tree.topLevelItem(0))
    expanded = fixed_tree.currentItem().isExpanded()
    # Part 1: toggle with Enter
    qtbot.keyPress(fixed_tree, Qt.Key_Return)
    assert fixed_tree.currentItem().isExpanded() is not expanded
    qtbot.keyPress(fixed_tree, Qt.Key_Return)
    assert fixed_tree.currentItem().isExpanded() is expanded
    # Part 2: test arrow keys
    fixed_tree.currentItem().setExpanded(True)
    # Part 2.1: Expanded + Left hides children
    qtbot.keyPress(fixed_tree, Qt.Key_Left)
    assert fixed_tree.currentItem().isExpanded() is False
    # Part 2.2: Hidden + Right shows children
    qtbot.keyPress(fixed_tree, Qt.Key_Right)
    assert fixed_tree.currentItem().isExpanded() is True
    # Part 2.3: Expanded + Right selects first child
    parent = fixed_tree.currentItem()
    qtbot.keyPress(fixed_tree, Qt.Key_Right)
    asserter(lambda: fixed_tree.currentItem() is parent.child(0))
    # Part 2.4: Child + Left returns to parent
    qtbot.keyPress(fixed_tree, Qt.Key_Left)
    asserter(lambda: fixed_tree.currentItem() is parent)


def test_search_tree_disable(fixed_tree: SearchResultTree, asserter):
    # Grab an arbitratry enabled Searcher
    searcher_item = fixed_tree.topLevelItem(0)
    # Assert GUI start
    asserter(lambda: searcher_item.text(0) == searcher_item._searcher.title() + " (3)")
    asserter(lambda: searcher_item.checkState(0) == Qt.Checked)
    asserter(lambda: searcher_item.isExpanded())

    # Disable the searcher, assert the proper GUI response
    searcher_item.setCheckState(0, Qt.Unchecked)
    asserter(lambda: searcher_item.text(0) == searcher_item._searcher.title())
    asserter(lambda: not searcher_item.isExpanded())
    asserter(lambda: searcher_item.childCount() == 0)

    # Enable the searcher, assert the proper GUI response
    searcher_item.setCheckState(0, Qt.Checked)
    asserter(lambda: searcher_item.text(0) == searcher_item._searcher.title())
    asserter(lambda: not searcher_item.isExpanded())
    asserter(lambda: searcher_item.childCount() == 0)


def test_right_click(fixed_tree: SearchResultTree, asserter):
    """
    Ensures that SearchResultTree has a CustomContextMenuPolicy,
    creating a menu that has the SciJava Search Actions relevant for
    an arbitrary SearchResult
    """
    # First, assert the policy
    assert fixed_tree.contextMenuPolicy() == Qt.CustomContextMenu
    # Then, grab an arbitratry Search Result
    item = fixed_tree.topLevelItem(0).child(0)
    rect = fixed_tree.visualItemRect(item)
    # Find its SearchActions
    expected_action_names = [pair[0] for pair in python_actions_for(item.result, None)]

    # NB when the menu pops, this thread will freeze until the menu is resolved
    # To inspect (and close) the menu, we must do so on another thread.
    class Handler(QRunnable):
        def run(self) -> None:
            # Wait for the menu to arise
            asserter(lambda: isinstance(QApplication.activePopupWidget(), QMenu))
            menu = QApplication.activePopupWidget()
            # Assert equality of actions (by name)
            for expected, actual in zip(expected_action_names, menu.actions()):
                assert expected == actual.text()
            # Close the menu (later, on the GUI thread)
            menu.deleteLater()
            self._passed = True

        def passed(self) -> bool:
            return self._passed

    # Start the Runner, so we can evaluate the Menu
    runnable = Handler()
    QThreadPool.globalInstance().start(runnable)
    # Launch the menu
    fixed_tree.customContextMenuRequested.emit(rect.center())
    # Wait for the the runner to finish evaluating, and ensure assertions passed.
    asserter(QThreadPool.globalInstance().waitForDone)
    assert runnable.passed()
