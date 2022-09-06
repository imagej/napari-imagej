"""
A module containing functionality useful for widget testing
"""
from napari_imagej.widgets.result_tree import (
    SearcherTreeItem,
    SearchResultTree,
    SearchResultTreeItem,
)
from tests.utils import DummySearcher, jc


def _populate_tree(tree: SearchResultTree, asserter):
    tree.wait_for_setup()
    assert tree.topLevelItemCount() == 0
    searcher1 = SearcherTreeItem(DummySearcher("Commands"))
    searcher1.update(
        [
            SearchResultTreeItem(jc.ClassSearchResult(c, ""))
            for c in (jc.Short, jc.Integer, jc.Long)
        ]
    )
    tree.addTopLevelItem(searcher1)
    searcher2 = SearcherTreeItem(DummySearcher("Ops"))
    searcher2.update(
        [
            SearchResultTreeItem(jc.ClassSearchResult(c, ""))
            for c in (jc.Float, jc.Double)
        ]
    )
    tree.addTopLevelItem(searcher2)

    # Wait for the tree to populate
    asserter(lambda: tree.topLevelItemCount() == 2)
    asserter(lambda: tree.topLevelItem(0).childCount() == 3)
    asserter(lambda: tree.topLevelItem(1).childCount() == 2)
