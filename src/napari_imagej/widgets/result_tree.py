"""
A QWidget designed to list SciJava SearchResults.

SearchResults are grouped by the SciJava Searcher that created them.
"""
from threading import Thread
from typing import List, Optional

from jpype import JArray, JImplements, JOverride
from qtpy.QtCore import Qt, Signal, Slot
from qtpy.QtWidgets import QTreeWidget, QTreeWidgetItem
from scyjava import Priority, when_jvm_stops

from napari_imagej.java import ensure_jvm_started, ij, jc
from napari_imagej.utilities.logging import log_debug


class SearchResultTreeItem(QTreeWidgetItem):
    """
    A QTreeWidgetItem wrapping a org.scijava.search.SearchResult
    Within a QTreeWidget, ResultTreeItem is designed to be a LEAF item.
    """

    def __init__(self, result: "jc.SearchResult"):
        super().__init__()
        self.name = ij().py.from_java(result.name())
        self.result = result

        # Set QtPy properties
        self.setText(0, self.name)


class SearcherTreeItem(QTreeWidgetItem):
    """
    A QTreeWidgetItem wrapping a org.scijava.search.Searcher
    with a set of org.scijava.search.SearchResults

    Within a QTreeWidget, ResultTreeItem is designed to be a NON-LEAF item containing
    ResultTreeItem children.
    """

    def __init__(
        self,
        searcher: "jc.Searcher",
        checked: bool = True,
        priority: float = Priority.LAST,
        expanded: bool = False,
    ):
        """
        Creates a new SearcherTreeItem
        :param searcher: the backing SciJava Searcher
        :param checked: Determines whether this SearcherTreeItem starts out checked.
        :param priority: Determines the position of this Searcher in the tree
        :param expanded: Indicates whether this SearcherTreeItem should start expanded
        """
        super().__init__()
        self.title = ij().py.from_java(searcher.title())
        self._searcher = searcher
        # Finding the priority is tricky - Searchers don't know their priority
        # To find it we have to ask the pluginService.
        plugin_info = ij().plugin().getPlugin(searcher.getClass())
        self.priority = plugin_info.getPriority() if plugin_info else priority

        # Set QtPy properties
        self.setText(0, self.title)
        self.setFlags((self.flags() & ~Qt.ItemIsSelectable) | Qt.ItemIsUserCheckable)
        self.setExpanded(expanded)
        self.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)

    def __lt__(self, other):
        """
        Provides an ordering for SearcherTreeItems.
        """
        return self.priority > other.priority

    def update(self, results: List[SearchResultTreeItem]):
        """
        Set the children of this node to results.
        :param results: the future children of this node
        """
        self.takeChildren()
        self.setExpanded(0 < len(results) < 10)
        if self.checkState(0) == Qt.Checked:
            self.setText(0, self.title + f" ({len(results)})")
            if results and len(results):
                self.addChildren(results)
        else:
            self.setText(0, self.title)


class SearchResultTree(QTreeWidget):

    # Signal used to update the children of this widget.
    # NB the object passed in this signal's emissions will always be a
    # org.scijava.search.SearchEvent in practice. BUT the signal requires
    # a concrete type at instantiation time, and we don't want to delay
    # the instantiation of this signal until we'd have that class. So,
    # without a better option, we declare the type as object.
    process = Signal(object)
    insert = Signal(SearcherTreeItem)
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

        # Ensure that once the JVM starts, Searchers are added
        self._searcher_initializer = Thread(target=self._init_searchers)
        self._searcher_initializer.start()
        self.insert.connect(self._add_searcher_tree_item)
        self.itemChanged.connect(self._register_item_change)

    def wait_for_setup(self):
        """
        This object does some setup asynchronously.
        This function can be used to ensure all that is done
        """
        self._producer_initializer.join()
        self._searcher_initializer.join()

    def search(self, text: str):
        self.wait_for_setup()
        self._searchOperation.search(text)

    @Slot(SearcherTreeItem)
    def _add_searcher_tree_item(self, item: SearcherTreeItem):
        """
        Slot designed for custom insertion of SearcherTreeItems
        """
        self.addTopLevelItem(item)
        self.sortItems(0, Qt.AscendingOrder)

    @Slot(object)
    def update(self, event: "jc.SearchEvent"):
        """
        Update the search results using event

        :param event: The org.scijava.search.SearchResult asynchronously
        returned by the org.scijava.search.SearchService
        """
        header = self._get_matching_item(event.searcher())
        result_items = self._generate_result_items(event)
        if header:
            header.update(result_items)
        else:
            log_debug(f"Searcher {event.searcher()} not found!")

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
        class NapariImageJSearchListener:
            def __init__(self, event_handler: Signal):
                super().__init__()
                self.handler = event_handler

            @JOverride
            def searchCompleted(self, event: "jc.SearchEvent"):
                self.handler.emit(event)

        # Start the search!
        # NB: SearchService.search takes varargs, so we need an array
        listener_arr = JArray(jc.SearchListener)(
            [NapariImageJSearchListener(self.process)]
        )
        self._searchOperation = (
            ij().get("org.scijava.search.SearchService").search(listener_arr)
        )
        # Make sure that the search stops when we close napari
        # Otherwise the Java threads like to continue
        when_jvm_stops(self._searchOperation.terminate)

    def _init_searchers(self):
        # First, wait for the JVM to start up
        ensure_jvm_started()

        # Add SearcherTreeItems for each Searcher
        searchers = ij().plugin().createInstancesOfType(jc.Searcher)
        for searcher in searchers:
            self.insert.emit(
                SearcherTreeItem(
                    searcher,
                    checked=ij()
                    .get("org.scijava.search.SearchService")
                    .enabled(searcher),
                    expanded=False,
                )
            )

    def _first_result(self) -> "jc.SearchResult":
        for i in range(self.topLevelItemCount()):
            searcher = self.topLevelItem(i)
            if searcher.childCount() > 0:
                return searcher.child(0).result
        return None

    def _register_item_change(self, item: QTreeWidgetItem, column: int):
        if column == 0:
            if isinstance(item, SearcherTreeItem):
                checked = item.checkState(0) == Qt.Checked
                ij().get("org.scijava.search.SearchService").setEnabled(
                    item._searcher, checked
                )
                if not checked:
                    item.update([])

    def _get_matching_item(self, searcher: "jc.Searcher") -> Optional[SearcherTreeItem]:
        name: str = ij().py.from_java(searcher.title())
        matches = self.findItems(name, Qt.MatchStartsWith, 0)
        if len(matches) == 0:
            return None
        elif len(matches) == 1:
            return matches[0]
        else:
            raise ValueError(f"Multiple Search Result Items matching name {name}")

    def _generate_result_items(
        self, event: "jc.SearchEvent"
    ) -> List[SearchResultTreeItem]:
        results = event.results()
        # Handle null results
        if not results:
            return []
        # Handle empty searches
        # Return False for search errors
        if len(results) == 1:
            if str(results[0].name()) == "<error>":
                log_debug(f"Failed Search: {str(results[0].properties().get(None))}")
                return []
        return [SearchResultTreeItem(r) for r in event.results()]
