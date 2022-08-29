from napari_imagej.widgets.results import ResultsTree, ResultTreeItem, SearcherTreeItem
from tests.utils import DummySearcher, jc


def _populate_tree(tree: ResultsTree, asserter):
    tree.wait_for_setup()
    assert tree.topLevelItemCount() == 0
    searcher1 = SearcherTreeItem(DummySearcher("Commands"))
    searcher1.update(
        [
            ResultTreeItem(jc.ClassSearchResult(c, ""))
            for c in (jc.Short, jc.Integer, jc.Long)
        ]
    )
    tree.addTopLevelItem(searcher1)
    searcher2 = SearcherTreeItem(DummySearcher("Ops"))
    searcher2.update(
        [ResultTreeItem(jc.ClassSearchResult(c, "")) for c in (jc.Float, jc.Double)]
    )
    tree.addTopLevelItem(searcher2)

    # Wait for the tree to populate
    asserter(lambda: tree.topLevelItemCount() == 2)
    asserter(lambda: tree.topLevelItem(0).childCount() == 3)
    asserter(lambda: tree.topLevelItem(1).childCount() == 2)
