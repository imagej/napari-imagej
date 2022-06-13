"""
This module is an example of a barebones function plugin for napari

It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from functools import lru_cache
from threading import Thread
from typing import List

from napari import Viewer
from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from napari_imagej._module_utils import functionify_module_execution
from napari_imagej.setup_imagej import ensure_jvm_started, ij, jc, log_debug


class ImageJWidget(QWidget):
    """The top-level ImageJ widget for napari."""

    def __init__(self, napari_viewer: Viewer):
        super().__init__()

        self.setLayout(QVBoxLayout())

        # Search Bar
        self.search: SearchbarWidget = SearchbarWidget()
        self.layout().addWidget(self.search)

        self.results: ResultsWidget = ResultsWidget()
        self.layout().addWidget(self.results)

        # Module highlighter
        self.highlighter: FocusWidget = FocusWidget(napari_viewer)
        self.layout().addWidget(self.highlighter)

        # -- Interwidget connections -- #

        # When the text bar changes, update the search results.
        self.search.bar.textChanged.connect(self.results._search)

        # If the user presses enter in the search bar,
        # highlight the first module in the results
        self.search.bar.returnPressed.connect(
            lambda: self.highlighter._highlight_module(self.results.results, 0, 0)
        )
        # If the user clicks in any table, highlight
        # the clicked cell
        for i, tableWidget in enumerate(self.results.widgets):
            tableWidget.cellClicked.connect(
                self.highlighter._highlight_from_results_table(self.results.results, i)
            )


class SearchbarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())
        self._searchbar: QLineEdit = self._generate_searchbar()
        self.layout().addWidget(self._searchbar)

        # Initialize the searchers, which will spin up an ImageJ gateway.
        # By running this in a new thread,
        # the GUI can be shown before the searchers are ready.
        def enable_searchbar():
            ensure_jvm_started()
            # Enable the searchbar now that the searchers are ready
            self._searchbar.setText("")
            self._searchbar.setEnabled(True)

        Thread(target=enable_searchbar).start()

    @property
    def bar(self) -> QLineEdit:
        return self._searchbar

    def _generate_searchbar(self) -> QLineEdit:
        searchbar = QLineEdit()
        # Disable the searchbar until the searchers are ready
        searchbar.setText("Initializing ImageJ...Please Wait")
        searchbar.setEnabled(False)
        return searchbar


class ResultsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        # Results box
        self.resultTableNames = ["Modules:", "Ops:"]
        self._results: List[List["jc.SearchResult"]] = [
            [] for _ in self.resultTableNames
        ]
        self._tables: List[QTableWidget] = self._generate_results_tables(
            self.resultTableNames
        )
        for table in self._tables:
            self.layout().addWidget(table)

    @property
    def results(self) -> List[List["jc.SearchResult"]]:
        return self._results

    @property
    def widgets(self) -> List[QTableWidget]:
        return self._tables

    @property
    @lru_cache(maxsize=None)
    def searchers(self) -> List["jc.Searcher"]:
        searcherClasses = [
            jc.ModuleSearcher,
            jc.OpSearcher,
        ]
        pluginService = ij().get("org.scijava.plugin.PluginService")
        searchers = [
            pluginService.getPlugin(cls, jc.Searcher).createInstance()
            for cls in searcherClasses
        ]
        for searcher in searchers:
            ij().context().inject(searcher)
        return searchers

    def _table_from_name(self, name: str) -> QTableWidget:
        # GUI properties
        labels = [name]
        max_results = 12
        tableWidget = QTableWidget(max_results, len(labels))
        # Modules take up a row, so highlight the entire thing
        tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Label the columns with labels
        tableWidget.setHorizontalHeaderLabels(labels)
        tableWidget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tableWidget.verticalHeader().hide()
        tableWidget.setShowGrid(False)
        tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)

        return tableWidget

    def _generate_results_tables(
        self, result_table_names: List[str]
    ) -> List[QTableWidget]:
        return [self._table_from_name(name) for name in result_table_names]

    def _search(self, text):
        # TODO: Consider adding a button to toggle fuzziness
        for i in range(len(self.searchers)):
            self.results[i] = self.searchers[i].search(text, True)
            for j in range(len(self.results[i])):
                name = ij().py.from_java(self.results[i][j].name())
                self.widgets[i].setItem(j, 0, QTableWidgetItem(name))
                self.widgets[i].showRow(j)
            for j in range(len(self.results[i]), self.widgets[i].rowCount()):
                self.widgets[i].setItem(j, 0, QTableWidgetItem(""))
                self.widgets[i].hideRow(j)


class FocusWidget(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        self.setLayout(QVBoxLayout())

        self.focused_module = None
        self.focused_module_label = QLabel()
        self.layout().addWidget(self.focused_module_label)
        self.focused_module_label.setText("Display Module Here")

        self.focused_action_buttons = []  # type: ignore

    def _highlight_from_results_table(
        self, tables: List[List["jc.ModuleInfo"]], index: int
    ):
        # NB: col is needed for tableWidget.cellClicked.
        # We don't use it in _highlight_module, though.
        return lambda row, col: self._highlight_module_from_tables(tables, index, row)

    def _highlight_module_from_tables(
        self, tables: List[List["jc.ModuleInfo"]], index: int, row: int
    ):
        # Ensure the clicked module is an actual selection
        if row >= len(tables[index]):
            return
        # Print highlighted module
        self.focused_module = tables[index][row]
        name = ij().py.from_java(self.focused_module.name())  # type: ignore
        self.focused_module_label.setText(name)

        # Create buttons for each action
        searchService = ij().get("org.scijava.search.SearchService")
        self.focused_actions = searchService.actions(self.focused_module)
        activated_actions = len(self.focused_action_buttons)
        # Hide buttons if we have more than needed
        while activated_actions > len(self.focused_actions):
            activated_actions = activated_actions - 1
            self.focused_action_buttons[activated_actions].hide()
        # Create buttons if we need more than we have
        while len(self.focused_action_buttons) < len(self.focused_actions):
            button = QPushButton()
            self.focused_action_buttons.append(button)
            self.layout().addWidget(button)
        # Rename buttons to reflect focused module's actions
        for i in range(len(self.focused_actions)):
            action_name = ij().py.from_java(self.focused_actions[i].toString())
            self.focused_action_buttons[i].show()
            self.focused_action_buttons[i].disconnect()
            if action_name == "Run":
                # "Run" is a little confusing, we won't be running the module
                # when we click run but will instead pop up an input harvester.
                # Let's be more clear about what we are doing.
                action_name = "Initialize"
                self.focused_action_buttons[i].clicked.connect(
                    lambda: self._execute_module(
                        self._convert_searchResult_to_info(self.focused_module)
                    )
                )
            else:
                self.focused_action_buttons[i].clicked.connect(
                    self.focused_actions[i].run
                )
            self.focused_action_buttons[i].setText(action_name)
            self.focused_action_buttons[i].show()

    def _execute_module(self, moduleInfo):
        log_debug("Creating module...")
        module = ij().module().createModule(moduleInfo)

        # preprocess using napari GUI
        func, param_options = functionify_module_execution(
            self.viewer, module, moduleInfo
        )
        self.viewer.window.add_function_widget(func, magic_kwargs=param_options)

    def _convert_searchResult_to_info(self, search_result):
        info = search_result.info()
        # There is an extra step for Ops - we actually need the CommandInfo
        if isinstance(info, jc.OpInfo):
            info = info.cInfo()
        return info
