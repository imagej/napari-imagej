"""
A module testing napari_imagej.widgets.results
"""
import pytest
from qtpy.QtCore import Qt

from napari_imagej.widgets.results import (
    ResultsTree,
    ResultTreeItem,
    SearcherTreeItem,
    SearchEventWrapper,
)
from tests.utils import DummySearcher, jc
from tests.widgets.widget_utils import _populate_tree


@pytest.fixture
def results_tree():
    return ResultsTree()


def test_results_widget_layout(results_tree: ResultsTree):
    """Tests the number and expected order of results widget children"""
    assert results_tree.columnCount() == 1
    assert results_tree.headerItem().text(0) == "Search"


def test_arrow_key_selection(results_tree: ResultsTree, qtbot, asserter):
    # Set up the tree
    _populate_tree(results_tree, asserter)
    # Start by selecting the first item in the tree
    results_tree.setCurrentItem(results_tree.topLevelItem(0))
    asserter(lambda: results_tree.currentItem() is results_tree.topLevelItem(0))
    # HACK: For some reason, they are not expanded in the tests!
    results_tree.topLevelItem(0).setExpanded(True)
    for i in range(3):
        qtbot.keyPress(results_tree, Qt.Key_Down)
        asserter(
            lambda: results_tree.currentItem() is results_tree.topLevelItem(0).child(i)
        )
    qtbot.keyPress(results_tree, Qt.Key_Down)
    asserter(lambda: results_tree.currentItem() is results_tree.topLevelItem(1))
    # HACK: For some reason, they are not expanded in the tests!
    results_tree.topLevelItem(1).setExpanded(True)
    for i in range(2):
        qtbot.keyPress(results_tree, Qt.Key_Down)
        asserter(
            lambda: results_tree.currentItem() is results_tree.topLevelItem(1).child(i)
        )
    qtbot.keyPress(results_tree, Qt.Key_Down)
    asserter(
        lambda: results_tree.currentItem() is results_tree.topLevelItem(1).child(1)
    )


def test_searchers_disappear(results_tree: ResultsTree, asserter):
    # Wait for the searchers to be ready
    results_tree.wait_for_setup()
    # Update the Tree with some search results
    searcher = DummySearcher("foo")
    results = [jc.ClassSearchResult(c, "") for c in (jc.Float, jc.Double)]
    results_tree.process.emit(SearchEventWrapper(searcher, results))
    asserter(lambda: results_tree.topLevelItemCount() == 1)
    asserter(lambda: results_tree.topLevelItem(0).childCount() == 2)

    # Update the tree with no search results, ensure that the searcher disappears
    results_tree.process.emit(SearchEventWrapper(searcher, []))
    asserter(lambda: results_tree.topLevelItemCount() == 0)


def test_resultTreeItem_regression():
    class DummySearchResult(object):
        def name(self):
            return "This is not a Search Result"

    dummy = DummySearchResult()
    item = ResultTreeItem(dummy)
    assert item.result == dummy
    assert item.text(0) == dummy.name()


def test_searcherTreeItem_regression():
    class DummySearcher(object):
        def title(self):
            return "This is not a Searcher"

    dummy = DummySearcher()
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


def test_arrow_key_expansion(results_tree: ResultsTree, qtbot, asserter):
    # Wait for the searchers to be ready
    results_tree.wait_for_setup()
    _populate_tree(results_tree, asserter)
    results_tree.setCurrentItem(results_tree.topLevelItem(0))
    expanded = results_tree.currentItem().isExpanded()
    # Part 1: toggle with Enter
    qtbot.keyPress(results_tree, Qt.Key_Return)
    assert results_tree.currentItem().isExpanded() is not expanded
    qtbot.keyPress(results_tree, Qt.Key_Return)
    assert results_tree.currentItem().isExpanded() is expanded
    # Part 2: test arrow keys
    results_tree.currentItem().setExpanded(True)
    # Part 2.1: Expanded + Left hides children
    qtbot.keyPress(results_tree, Qt.Key_Left)
    assert results_tree.currentItem().isExpanded() is False
    # Part 2.2: Hidden + Right shows children
    qtbot.keyPress(results_tree, Qt.Key_Right)
    assert results_tree.currentItem().isExpanded() is True
    # Part 2.3: Expanded + Right selects first child
    parent = results_tree.currentItem()
    qtbot.keyPress(results_tree, Qt.Key_Right)
    asserter(lambda: results_tree.currentItem() is parent.child(0))
    # Part 2.4: Child + Left returns to parent
    qtbot.keyPress(results_tree, Qt.Key_Left)
    asserter(lambda: results_tree.currentItem() is parent)
