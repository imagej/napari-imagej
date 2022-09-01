"""
A QWidget designed to list SciJava SearchResults.

SearchResults are grouped by the SciJava Searcher that created them.
"""
import atexit
from threading import Thread
from typing import List, Optional

from jpype import JArray, JImplements, JOverride
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem

from napari_imagej.java import ensure_jvm_started, ij, jc


class ResultTreeItem(QTreeWidgetItem):
    """
    A QTreeWidgetItem wrapping a org.scijava.search.SearchResult
    """

    def __init__(self, result: "jc.SearchResult"):
        super().__init__()
        self.name = ij().py.from_java(result.name())
        self.result = result

        # Set QtPy properties
        self.setText(0, self.name)


class SearchEventWrapper:
    """
    Python Class wrapping org.scijava.search.SearchEvent.
    Needed for SearchTree.process, as signal types must be Python types.
    """

    def __init__(self, searcher: "jc.Searcher", results: List["jc.SearchResult"]):
        self.searcher = searcher
        self.results = [ResultTreeItem(r) for r in results]


class SearcherTreeItem(QTreeWidgetItem):
    """
    A QTreeWidgetItem wrapping a org.scijava.search.Searcher
    with a set of org.scijava.search.SearchResults
    """

    def __init__(self, searcher: "jc.Searcher"):
        super().__init__()
        self.title = ij().py.from_java(searcher.title())
        self._searcher = searcher

        # Set QtPy properties
        self.setText(0, self.title)
        self.setFlags(self.flags() & ~Qt.ItemIsSelectable)

    def update(self, results: List[SearchEventWrapper]):
        """
        Update children with the results stored in the SearchEventWrapper
        """
        self.takeChildren()
        if results and len(results):
            self.addChildren(results)
        self.setText(0, f"{self.title} ({len(results)})")
        self.setExpanded(len(results) < 10)


class ResultsTree(QTreeWidget):

    # Signal used to update this widget with org.scijava.search.SearchResults.
    # Given a SearchEventWrapper w, process.emit(w) will update the widget.
    process = Signal(SearchEventWrapper)
    floatAbove = Signal()

    def __init__(
        self,
    ):
        super().__init__()

        # -- Configure GUI Options -- #
        self.setColumnCount(1)
        self.setHeaderLabels(["Search"])
        self.setIndentation(self.indentation() // 2)

        # Start up the SearchResult producer/consumer chain
        self._producer_initializer = Thread(target=self._init_producer)
        self._producer_initializer.start()
        self.process.connect(self.update)

    def wait_for_setup(self):
        """
        This object does some setup asynchronously.
        This function can be used to ensure all that is done
        """
        return self._producer_initializer.join()

    def search(self, text: str):
        self.wait_for_setup()
        self._searchOperation.search(text)

    @Slot(SearchEventWrapper)
    def update(self, event: SearchEventWrapper):
        """
        Update the search results using event

        :param event: The org.scijava.search.SearchResult asynchronously
        returned by the org.scijava.search.SearchService
        """
        header = self._get_matching_item(event.searcher)
        if self._valid_results(event):
            if header is None:
                header = self._add_new_searcher(event.searcher)
                self.sortItems(0, Qt.AscendingOrder)
            header.update(event.results)
        elif header is not None:
            self.invisibleRootItem().removeChild(header)

    # -- QWidget Overrides -- #

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            # Use the enter key to toggle Searchers
            if self.currentItem().childCount() > 0:
                self.currentItem().setExpanded(not self.currentItem().isExpanded())
            # use the enter key like double clicking for Results
            else:
                self.itemDoubleClicked.emit(self.currentItem(), 0)
        # Pressing the up arrow while at the top should go back to the search bar
        elif event.key() == Qt.Key_Up and self.currentItem() is self.topLevelItem(0):
            self.clearSelection()
            self.floatAbove.emit()
        # Pressing right on a searcher should either expand it or go to its first child
        elif event.key() == Qt.Key_Right and self.currentItem().childCount() > 0:
            if self.currentItem().isExpanded():
                self.setCurrentItem(self.currentItem().child(0))
            else:
                self.currentItem().setExpanded(True)
        elif event.key() == Qt.Key_Left:
            # Pressing left on a searcher should close it
            if self.currentItem().parent() is None:
                self.currentItem().setExpanded(False)
            # Pressing left on a result should go to the searcher
            else:
                self.setCurrentItem(self.currentItem().parent())
        else:
            super().keyPressEvent(event)
        self.itemClicked.emit(self.currentItem(), 0)

    # -- Helper Functionality -- #

    def _init_producer(self):
        # First, wait for the JVM to start up
        ensure_jvm_started()

        # Then, define our SearchListener
        @JImplements("org.scijava.search.SearchListener")
        class NapariSearchListener:
            def __init__(self, event_handler: Signal):
                super().__init__()
                self.handler = event_handler

            @JOverride
            def searchCompleted(self, event: "jc.SearchEvent"):
                self.handler.emit(SearchEventWrapper(event.searcher(), event.results()))

        # Start the search!
        # NB: SearchService.search takes varargs, so we need an array
        listener_arr = JArray(jc.SearchListener)([NapariSearchListener(self.process)])
        self._searchOperation = (
            ij().get("org.scijava.search.SearchService").search(listener_arr)
        )
        # Make sure that the search stops when we close napari
        # Otherwise the Java threads like to continue
        atexit.register(self._searchOperation.terminate)

    def _first_result(self) -> "jc.SearchResult":
        for i in range(self.topLevelItemCount()):
            searcher = self.topLevelItem(i)
            if searcher.childCount() > 0:
                return searcher.child(0).result
        return None

    def _add_new_searcher(self, searcher: "jc.Searcher") -> SearcherTreeItem:
        tree_item = SearcherTreeItem(searcher)
        tree_item.setExpanded(True)
        self.addTopLevelItem(tree_item)
        return tree_item

    def _get_matching_item(self, searcher: "jc.Searcher") -> Optional[SearcherTreeItem]:
        name: str = ij().py.from_java(searcher.title())
        matches = self.findItems(name, Qt.MatchStartsWith, 0)
        if len(matches) == 0:
            return None
        elif len(matches) == 1:
            return matches[0]
        else:
            raise ValueError(f"Multiple Search Result Items matching name {name}")

    def _valid_results(self, event: SearchEventWrapper):
        results = event.results
        # Return False for results == null
        if not results:
            return False
        # Return False for empty results
        if not len(results):
            return False
        # Return False for search errors
        if len(results) == 1:
            if str(results[0].name) == "<error>":
                return False
        return True
