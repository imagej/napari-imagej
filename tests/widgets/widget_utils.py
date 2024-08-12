"""
A module containing functionality useful for widget testing
"""

from typing import Optional

from scyjava import Priority

from napari_imagej.widgets.result_tree import SearcherTreeItem, SearchResultTree
from tests.utils import DummySearcher, DummySearchEvent, jc


def _searcher_tree_named(
    tree: SearchResultTree, name: str
) -> Optional[SearcherTreeItem]:
    for i in range(tree.topLevelItemCount()):
        if tree.topLevelItem(i).title.startswith(name):
            return tree.topLevelItem(i)
    return None


def _populate_tree(tree: SearchResultTree, asserter):
    asserter(lambda: tree.topLevelItemCount() == 0)
    # Add two searchers
    searcher1 = DummySearcher("Test1")
    item1 = SearcherTreeItem(searcher1, priority=Priority.LOW)
    tree.insert.emit(item1)
    searcher2 = DummySearcher("Test2")
    item2 = SearcherTreeItem(searcher2, priority=Priority.HIGH)
    tree.insert.emit(item2)
    asserter(lambda: tree.topLevelItemCount() == 2)

    # Update each searcher with data
    tree.process.emit(
        DummySearchEvent(
            searcher1, [jc.ClassSearchResult(c, "") for c in (jc.Float, jc.Double)]
        )
    )
    tree.process.emit(
        DummySearchEvent(
            searcher2,
            [jc.ClassSearchResult(c, "") for c in (jc.Short, jc.Integer, jc.Long)],
        )
    )

    # Wait for the tree to populate
    asserter(lambda: tree.topLevelItem(0).childCount() == 3)
    asserter(lambda: tree.topLevelItem(1).childCount() == 2)
