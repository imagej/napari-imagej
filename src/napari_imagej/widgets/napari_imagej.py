"""
This module contains ImageJWidget, the top-level QWidget enabling
graphical access to ImageJ functionality.

This Widget is made accessible to napari through napari.yml
"""
from napari import Viewer
from qtpy.QtWidgets import QTreeWidgetItem, QVBoxLayout, QWidget

from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.result_runner import ResultRunner
from napari_imagej.widgets.result_tree import ResultTreeItem, SearchResultTree
from napari_imagej.widgets.searchbar import JVMEnabledSearchbar


class NapariImageJWidget(QWidget):
    """The top-level ImageJ widget for napari."""

    def __init__(self, napari_viewer: Viewer):
        super().__init__()
        self.setLayout(QVBoxLayout())

        # -- NapariImageJWidget construction -- #

        # At the top: the napari-imagej menu
        self.menu: NapariImageJMenu = NapariImageJMenu(napari_viewer)
        self.layout().addWidget(self.menu)
        # Next: the search bar
        self.search: JVMEnabledSearchbar = JVMEnabledSearchbar()
        self.layout().addWidget(self.search)
        # Then: The results tree
        self.result_tree: SearchResultTree = SearchResultTree()
        self.layout().addWidget(self.result_tree)
        # Finally: The SearchResult runner
        self.result_runner: ResultRunner = ResultRunner(napari_viewer)
        self.layout().addWidget(self.result_runner)

        # -- Interwidget connections -- #

        # When the text bar changes, update the search results.
        self.search.bar.textEdited.connect(self.result_tree.search)

        # When clicking a result, select it with the ResultRunner
        def click(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.result_runner.select(treeItem.result)
            else:
                self.result_runner.clear()

        # self.results.onClick = clickFunc
        self.result_tree.itemClicked.connect(click)

        # When double clicking a result,
        # select it with the ResultRunner and run the first action
        def double_click(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.result_runner.run(treeItem.result)

        self.result_tree.itemDoubleClicked.connect(double_click)

        # When pressing the up arrow on the topmost row in the results list,
        # go back up to the search bar
        self.result_tree.floatAbove.connect(self.search.bar.setFocus)

        # When pressing the down arrow on the search bar,
        # go to the first result item
        def key_down_from_search_bar():
            self.search.bar.clearFocus()
            self.result_tree.setFocus()
            self.result_tree.setCurrentItem(self.result_tree.topLevelItem(0))

        self.search.bar.floatBelow.connect(key_down_from_search_bar)

        # When pressing return on the search bar, select the first result
        # in the results list and run it
        def return_search_bar():
            """Define the return behavior for this widget"""
            result = self.result_tree._first_result()
            if result is not None:
                self.result_runner.run(result)

        self.search.bar.returnPressed.connect(return_search_bar)

        # -- Final setup -- #

        # Bind L key to search bar.
        # Note the requirement for an input parameter
        napari_viewer.bind_key(
            "Control-L", lambda _: self.search.bar.setFocus(), overwrite=True
        )

        # Put the focus on the search bar
        self.search.bar.setFocus()
