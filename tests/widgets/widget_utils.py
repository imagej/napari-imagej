"""
A module containing functionality useful for widget testing
"""

from typing import Optional

from qtpy.QtCore import Qt

from napari_imagej.widgets.result_tree import SearcherItem, SearcherTreeView
from tests.utils import DummySearcher, DummySearchEvent, jc


def _searcher_tree_named(tree: SearcherTreeView, name: str) -> Optional[SearcherItem]:
    root = tree.model().invisibleRootItem()
    for i in range(root.rowCount()):
        if str(root.child(i, 0).searcher.title()).startswith(name):
            return root.child(i, 0)
    return None


def _populate_tree(tree: SearcherTreeView, asserter):
    root = tree.model().invisibleRootItem()
    asserter(lambda: root.rowCount() == 0)
    # Add two searchers
    searcher1 = DummySearcher("Test1")
    tree.model().insert_searcher.emit(searcher1)
    searcher2 = DummySearcher("Test2")
    tree.model().insert_searcher.emit(searcher2)
    asserter(lambda: root.rowCount() == 2)
    tree.model().item(0).setCheckState(Qt.Checked)
    tree.model().item(1).setCheckState(Qt.Checked)

    # Update each searcher with data
    tree.model().process.emit(
        DummySearchEvent(
            searcher1, [jc.ClassSearchResult(c, "") for c in (jc.Float, jc.Double)]
        )
    )
    tree.model().process.emit(
        DummySearchEvent(
            searcher2,
            [jc.ClassSearchResult(c, "") for c in (jc.Short, jc.Integer, jc.Long)],
        )
    )

    # Wait for the tree to populate
    count = 2
    asserter(lambda: root.child(0, 0).rowCount() == count)
    data = f'Test1 <span style="color:#8C745E;">({count})</span>'
    asserter(lambda: root.child(0, 0).data(0) == data)

    count = 3
    asserter(lambda: root.child(1, 0).rowCount() == count)
    data = f'Test2 <span style="color:#8C745E;">({count})</span>'
    asserter(lambda: root.child(1, 0).data(0) == data)
