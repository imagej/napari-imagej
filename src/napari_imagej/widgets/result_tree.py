"""
A QWidget designed to list SciJava SearchResults.

SearchResults are grouped by the SciJava Searcher that created them.
"""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from qtpy.QtCore import QRectF, Qt, Signal, QSize
from qtpy.QtGui import QStandardItem, QStandardItemModel, QTextDocument
from qtpy.QtWidgets import (
    QAction,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
)
from scyjava import Priority

from napari_imagej import nij
from napari_imagej.java import jc
from napari_imagej.widgets.widget_utils import _get_icon, python_actions_for

if TYPE_CHECKING:
    from qtpy.QtCore import QModelIndex

    from typing import Dict, List


# Color used for additional information in the QTreeView
HIGHLIGHT = "#8C745E"


class SearcherTreeView(QTreeView):
    floatAbove = Signal()

    def __init__(self, output_signal: Signal):
        super().__init__()
        self.output_signal = output_signal

        # Qt properties
        self.setModel(SearchResultModel())
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._create_custom_menu)
        self.model().rowsInserted.connect(self.expand_searchers)
        self.setItemDelegate(HTMLItemDelegate())

    def search(self, text: str):
        """Convenience method for calling self.model().search()"""
        self.model().search(text)

    def expand_searchers(self, parent_idx, first: int, last: int):
        # Searchers will have a null parent index
        if parent_idx.row() != -1 or parent_idx.column() != -1:
            return
        for i in range(first, last + 1):
            self.setExpanded(self.model().index(i, 0, parent_idx), True)

    # -- QWidget Overrides -- #

    def keyPressEvent(self, event):
        # Pressing the up arrow while at the top should go back to the search bar
        if event.key() == Qt.Key_Up:
            idx = self.currentIndex()
            if idx.row() == 0 and not idx.parent().isValid():
                self.selectionModel().clearSelection()
                self.floatAbove.emit()
        elif event.key() == Qt.Key_Return:
            idx = self.currentIndex()
            # Use the enter key to toggle Searchers
            if not idx.parent().isValid():
                self.setExpanded(idx, not self.isExpanded(idx))
            # use the enter key like double clicking for Results
            else:
                self.doubleClicked.emit(idx)
        super().keyPressEvent(event)

    def _create_custom_menu(self, pos):
        item = self.model().itemFromIndex(self.indexAt(pos))
        if not isinstance(item, SearchResultItem):
            return
        menu: QMenu = QMenu(self)

        for name, action in python_actions_for(item.result, self.output_signal, self):
            newAct = QAction(name, self)
            newAct.triggered.connect(action)
            menu.addAction(newAct)

        menu.exec_(self.mapToGlobal(pos))


class SearcherItem(QStandardItem):
    def __init__(
        self,
        searcher: "jc.Searcher",
    ):
        super().__init__(str(searcher.title()))
        self.searcher = searcher

        # Finding the priority is tricky - Searchers don't know their priority
        # To find it we have to ask the pluginService.
        plugin_info = nij.ij.plugin().getPlugin(searcher.getClass())
        self.priority = plugin_info.getPriority() if plugin_info else Priority.NORMAL

        # Set QtPy properties
        self.setEditable(False)
        self.setFlags(self.flags() | Qt.ItemIsUserCheckable)
        checked = nij.ij.get("org.scijava.search.SearchService").enabled(searcher)
        self.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def __lt__(self, other):
        """
        Provides an ordering for SearcherTreeItems.
        """
        return self.priority > other.priority


class SearchResultItem(QStandardItem):
    def __init__(self, result: "jc.SearchResult"):
        props = result.properties()
        text = str(result.name())
        # Wrap up the icon path in "highlight text"
        if "Menu path" in props:
            text += f' <span style="color:{HIGHLIGHT};">{props["Menu path"]}</span>'
        super().__init__(text)
        self.result = result

        # Set QtPy properties
        self.setEditable(False)
        if icon := _get_icon(str(result.iconPath()), result.getClass()):
            self.setIcon(icon)


class HTMLItemDelegate(QStyledItemDelegate):
    """A QStyledItemDelegate that can handle HTML in provided text"""

    def paint(self, painter, option, index: QModelIndex):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        rich_text = options.text

        # "clear" the item using "normal" behavior.
        # mimics qt source code.
        options.text = ""
        style = options.widget.style()
        style.drawControl(QStyle.CE_ItemViewItem, options, painter, options.widget)

        # paint the HTML text
        doc = QTextDocument()
        text_color = options.palette.text().color().name()
        rich_text = f'<span style="color:{text_color};">{rich_text}</span>'
        doc.setHtml(rich_text)

        painter.save()
        # Translate the painter to the correct item
        # NB offset is necessary to account for checkbox, icon
        text_offset = style.subElementRect(
            QStyle.SE_ItemViewItemText, options, options.widget
        ).x()
        painter.translate(text_offset, options.rect.top())
        # Paint the rich text
        rect = QRectF(0, 0, options.rect.width(), options.rect.height())
        doc.drawContents(painter, rect)

        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        # size hint is the size of the rendered HTML
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        size = QSize(int(doc.idealWidth()), int(doc.size().height()))
        return size


class SearchResultModel(QStandardItemModel):
    insert_searcher: Signal = Signal(object)
    process: Signal = Signal(object)

    def __init__(self):
        super().__init__()
        self.searchers: Dict["jc.Searcher", SearcherItem] = {}
        self.insert_searcher.connect(self.register_searcher)
        self.process.connect(self.handle_search_event)

        self.setHorizontalHeaderLabels(["Search"])
        self.itemChanged.connect(self._detect_check_change)
        self.rowsInserted.connect(self._update_searcher_title)
        self.rowsRemoved.connect(self._update_searcher_title)

    def search(self, text: str):
        self._searchOperation.search(text)

    def register_searcher(self, searcher: "jc.Searcher"):
        if searcher not in self.searchers:
            searcher_item: SearcherItem = SearcherItem(searcher)
            self.searchers[str(searcher.title())] = searcher_item
            self.invisibleRootItem().appendRow(searcher_item)

    def handle_search_event(self, event: "jc.SearchEvent"):
        searcher_name = str(event.searcher().title())
        if searcher_name in self.searchers:
            searcher_item = self.searchers[searcher_name]
            # Clear all children
            if searcher_item.hasChildren():
                searcher_item.removeRows(0, searcher_item.rowCount())
            # Add new children
            result_items = self._generate_result_items(event)
            searcher_item.appendRows(result_items)
            # Update title
        else:
            getLogger("napari-imagej").debug(f"Searcher {event.searcher()} not found!")

    def first_search_result(self) -> "jc.SearchResult":
        root = self.invisibleRootItem()
        for i in range(root.rowCount()):
            child = root.child(i, 0)
            if child.hasChildren():
                return child.child(0, 0).result

    def _generate_result_items(self, event: "jc.SearchEvent") -> List[SearchResultItem]:
        results = event.results()
        # Handle null results
        if not results:
            return []
        # Return False for search errors
        if len(results) == 1:
            if str(results[0].name()) == "<error>":
                getLogger("napari-imagej").debug(
                    f"Failed Search: {str(results[0].properties().get(None))}"
                )
                return []
        return [SearchResultItem(r) for r in event.results()]

    def _detect_check_change(self, item):
        if isinstance(item, SearcherItem):
            checked = item.checkState() == Qt.Checked
            nij.ij.get("org.scijava.search.SearchService").setEnabled(
                item.searcher, checked
            )
            if not checked and item.hasChildren():
                item.removeRows(0, item.rowCount())

    def _update_searcher_title(self, parent_idx, first: int, last: int):
        item = self.itemFromIndex(parent_idx)
        if isinstance(item, SearcherItem):
            if item.hasChildren():
                item.setData(
                    # Write the number of results in "highlight text"
                    f'{item.searcher.title()} <span style="color:{HIGHLIGHT};">({item.rowCount()})</span>',
                    Qt.DisplayRole,
                )
            else:
                item.setData(str(item.searcher.title()), Qt.DisplayRole)
