"""
A module testing napari_imagej.widgets.results
"""

import pytest
from qtpy.QtCore import QRunnable, Qt, QThreadPool
from qtpy.QtWidgets import QApplication, QMenu

from napari_imagej.java import init_ij
from napari_imagej.widgets.result_tree import (
    SearcherItem,
    SearcherTreeView,
    SearchResultItem,
)
from napari_imagej.widgets.widget_utils import python_actions_for
from tests.utils import DummySearcher, DummySearchEvent, DummySearchResult
from tests.widgets.widget_utils import _populate_tree


@pytest.fixture
def results_tree():
    return SearcherTreeView(None)


@pytest.fixture
def fixed_tree(ij, asserter):
    """Creates a "fake" ResultsTree with deterministic results"""
    # Create a default SearchResultTree
    tree = SearcherTreeView(None)
    _populate_tree(tree, asserter)

    return tree


def test_results_widget_layout(fixed_tree: SearcherTreeView):
    """Tests the number and expected order of results widget children"""
    assert fixed_tree.model().columnCount() == 1
    assert fixed_tree.model().headerData(0, Qt.Horizontal, 0) == "Search"


def test_searchers_persist(fixed_tree: SearcherTreeView, asserter):
    # Find the first searcher, and remove its children
    item = fixed_tree.model().invisibleRootItem().child(0, 0)
    searcher = item.searcher
    asserter(lambda: item.rowCount() > 0)
    fixed_tree.model().process.emit(DummySearchEvent(searcher, []))
    # Ensure that the children disappear, but the searcher remains
    asserter(lambda: item.rowCount() == 0)
    asserter(lambda: fixed_tree.model().invisibleRootItem().rowCount() == 2)


def test_resultTreeItem_regression():
    dummy = DummySearchResult()
    item = SearchResultItem(dummy)
    assert item.result == dummy
    assert item.data(0) == dummy.name()


def test_searcherTreeItem_regression():
    init_ij()
    dummy = DummySearcher("This is not a Searcher")
    item = SearcherItem(dummy)
    assert item.searcher == dummy
    assert (
        item.flags()
        == Qt.ItemIsUserCheckable
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
        | Qt.ItemIsDragEnabled
        | Qt.ItemIsDropEnabled
    )
    assert item.data(0) == dummy.title()


def test_key_return_expansion(fixed_tree: SearcherTreeView, qtbot, asserter):
    idx = fixed_tree.model().index(0, 0)
    fixed_tree.setCurrentIndex(idx)
    expanded = fixed_tree.isExpanded(idx)
    # Toggle with enter
    qtbot.keyPress(fixed_tree, Qt.Key_Return)
    assert fixed_tree.isExpanded(idx) is not expanded
    qtbot.keyPress(fixed_tree, Qt.Key_Return)
    assert fixed_tree.isExpanded(idx) is expanded


def test_search_tree_disable(fixed_tree: SearcherTreeView, asserter):
    # Grab an arbitratry enabled Searcher
    item = fixed_tree.model().invisibleRootItem().child(1, 0)
    # Assert GUI start
    asserter(lambda: item.data(0) == "Test2 (3)")
    asserter(lambda: item.checkState() == Qt.Checked)

    # Disable the searcher, assert the proper GUI response
    item.setCheckState(Qt.Unchecked)
    asserter(lambda: item.data(0) == "Test2")
    asserter(lambda: item.rowCount() == 0)

    # Enable the searcher, assert the proper GUI response
    item.setCheckState(Qt.Checked)
    asserter(lambda: item.data(0) == "Test2")
    asserter(lambda: item.rowCount() == 0)


def test_right_click(fixed_tree: SearcherTreeView, asserter):
    """
    Ensures that SearcherTreeView has a CustomContextMenuPolicy,
    creating a menu that has the SciJava Search Actions relevant for
    an arbitrary SearchResult
    """
    # First, assert the policy
    assert fixed_tree.contextMenuPolicy() == Qt.CustomContextMenu
    # Then, grab an arbitratry Search Result
    idx = fixed_tree.model().index(0, 0).child(0, 0)
    rect = fixed_tree.visualRect(idx)
    item = fixed_tree.model().itemFromIndex(idx)
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
