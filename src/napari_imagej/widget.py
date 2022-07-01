"""
This module contains ImageJWidget, a QWidget enabling
graphical access to ImageJ functionality.

This Widget is made accessible to napari through napari.yml
"""
from functools import lru_cache
from threading import Thread
from typing import Callable, Dict, List, NamedTuple, Tuple

from magicgui import magicgui
from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QAbstractItemView,
    QApplication,
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

from napari_imagej._flow_layout import FlowLayout
from napari_imagej._module_utils import (
    convert_searchResult_to_info,
    execute_function_modally,
    functionify_module_execution,
)
from napari_imagej.setup_imagej import ensure_jvm_started, ij, jc, log_debug


class SearchAction(NamedTuple):
    name: str
    action: Callable[[], None]


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
        self._focus_table = 0
        self._focus_row = -1
        self.highlighter: FocusWidget = FocusWidget(napari_viewer)
        self.layout().addWidget(self.highlighter)

        # -- Interwidget connections -- #

        # When the text bar changes, update the search results.
        self.search.bar.textChanged.connect(self.results._search)

        for i, tableWidget in enumerate(self.results.widgets):
            # If the user clicks in any table, highlight
            # the clicked cell
            clickFunc = self.highlighter._table_onClick_generator(
                self.results.results, i
            )
            tableWidget.cellClicked.connect(clickFunc)
            # If the user double clicks in any table, run the clicked cell
            doubleClickFunc = self.highlighter._table_onDoubleClick_generator(
                self.results.results, i
            )
            tableWidget.cellDoubleClicked.connect(doubleClickFunc)

        # -- Final setup -- #

        # Bind L key to search bar.
        # Note the requirement for an input parameter
        napari_viewer.bind_key(
            "Control-L", lambda _: self.search.bar.setFocus(), overwrite=True
        )

    def _change_focused_table_entry(self, down: bool = True) -> Tuple[int, int]:
        if down:
            if (
                self._focus_row < len(self.results.results[self._focus_table]) - 1
                and self._focus_row
                < self.results._tables[self._focus_table].rowCount() - 1
            ):
                self._focus_row = self._focus_row + 1
            else:
                if self._focus_table < len(self.results.results) - 1:
                    self.results._tables[self._focus_table].clearSelection()
                    self._focus_table = self._focus_table + 1
                    self._focus_row = 0
        else:
            if self._focus_row > 0:
                self._focus_row = self._focus_row - 1
            else:
                if self._focus_table > 0:
                    self.results._tables[self._focus_table].clearSelection()
                    self._focus_table = self._focus_table - 1
                    self._focus_row = len(self.results.results[self._focus_table]) - 1

        self.search.bar.clearFocus()
        self.setFocus()
        self.results._tables[self._focus_table].selectRow(self._focus_row)
        self.highlighter._highlight_module_from_tables(
            self.results.results, self._focus_table, self._focus_row
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self._change_focused_table_entry(down=True)
        elif event.key() == Qt.Key_Up:
            self._change_focused_table_entry(down=False)
        elif event.key() == Qt.Key_Return:
            if self._focus_row < 0:
                self._focus_row = 0
            self.highlighter._table_onDoubleClick_generator(
                self.results.results, self._focus_table
            )(self._focus_row, 0)


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

        self.focused_module_label = QLabel()
        self.layout().addWidget(self.focused_module_label)
        self.button_pane = QWidget()
        self.button_pane.setLayout(FlowLayout())
        self.layout().addWidget(self.button_pane)
        self.focused_module_label.setText("Display Module Here")

        self.focused_action_buttons = []  # type: ignore

    def _table_onClick_generator(self, tables: List[List["jc.ModuleInfo"]], index: int):
        # NB: col is needed for tableWidget.cellClicked.
        # We don't use it in _highlight_module, though.
        def func(row: int, col: int):
            self._highlight_module_from_tables(tables, index, row)

        return func

    def _table_onDoubleClick_generator(
        self, tables: List[List["jc.SearchResult"]], index: int
    ):
        # NB: col is needed for tableWidget.cellClicked.
        # We don't use it in _highlight_module, though.
        def func(row: int, col: int):
            if QApplication.keyboardModifiers() & Qt.ShiftModifier:
                selection = "Widget"
            else:
                selection = "Run"

            result = tables[index][row]
            actions: List[SearchAction] = self._actions_from_result(result)
            # Find the widget button
            for action in actions:
                if action.name == selection:
                    action.action()
                    return

        return func

    def _highlight_from_tables_and_run_first(
        self, tables: List[List["jc.ModuleInfo"]], index: int, row: int
    ):
        self._highlight_module_from_tables(tables, index, row)
        if len(self.focused_action_buttons) > 0:
            self.focused_action_buttons[0].click()

    def _python_actions_for(
        self, result: "jc.SearchResult"
    ) -> Dict[str, List[SearchAction]]:
        """
        Gets the list of predefined button parameters that should appear
        for a given action name.
        :return: A dict of button parameter, keyed by the run actions they wrap.
            Button parameters are defined in tuples, where the first element is
            the name, and the section element is the on-click action.
        """
        return {
            "Run": [
                SearchAction(
                    name="Run",
                    action=lambda: self._execute_module(
                        ij().py.from_java(result.name()),
                        convert_searchResult_to_info(result),
                        modal=True,
                    ),
                ),
                SearchAction(
                    name="Widget",
                    action=lambda: self._execute_module(
                        ij().py.from_java(result.name()),
                        convert_searchResult_to_info(result),
                        modal=False,
                    ),
                ),
            ],
        }

    tooltips: Dict[str, str] = {
        "Widget": "Runs functionality from a napari widget. "
        "Useful for parameter sweeping",
        "Run": "Runs functionality from a modal widget. Best for single executions",
        "Source": "Opens the source code on GitHub",
        "Help": "Opens the functionality's ImageJ.net wiki page",
    }

    def _actions_from_result(self, result: "jc.SearchResult") -> List[SearchAction]:
        button_params: List[SearchAction] = []
        # Get all additional python actions for result
        python_action_replacements: Dict[str, SearchAction] = self._python_actions_for(
            result
        )
        # Iterate over all available python actions
        searchService = ij().get("org.scijava.search.SearchService")
        for java_action in searchService.actions(result):
            action_name = ij().py.from_java(java_action.toString())
            # If we have python replacements for this action, use them
            if action_name in python_action_replacements:
                button_params.extend(python_action_replacements[action_name])
            # Otherwise, wrap the java action into a python action
            else:
                params = SearchAction(name=action_name, action=java_action.run)
                button_params.append(params)
        return button_params

    def _highlight_module_from_tables(
        self, tables: List[List["jc.ModuleInfo"]], index: int, row: int
    ):
        # Ensure the clicked module is an actual selection
        if row >= len(tables[index]):
            return
        # Print highlighted module
        self.focused_module = tables[index][row]
        self._highlight_module(tables[index][row])

    def _highlight_module(self, module: "jc.SearchResult"):
        name = ij().py.from_java(module.name())  # type: ignore
        self.focused_module_label.setText(name)

        # Create buttons for each action
        # searchService = ij().get("org.scijava.search.SearchService")
        # self.focused_actions = searchService.actions(module)
        python_actions: List[SearchAction] = self._actions_from_result(module)
        buttons_needed = len(python_actions)
        activated_actions = len(self.focused_action_buttons)
        # Hide buttons if we have more than needed
        while activated_actions > buttons_needed:
            activated_actions = activated_actions - 1
            self.focused_action_buttons[activated_actions].hide()
        # Create buttons if we need more than we have
        while len(self.focused_action_buttons) < buttons_needed:
            button = QPushButton()
            self.focused_action_buttons.append(button)
            self.button_pane.layout().addWidget(button)
        # Rename buttons to reflect focused module's actions
        # TODO: Can we use zip on the buttons and the actions?
        for i, action in enumerate(python_actions):
            # Clean old actions from button
            # HACK: disconnect() throws an exception if there are no connections.
            # Thus we use button name as a proxy for when there is a connected action.
            if self.focused_action_buttons[i].text() != "":
                self.focused_action_buttons[i].disconnect()
                self.focused_action_buttons[i].setText("")
            # Set button name
            self.focused_action_buttons[i].setText(action.name)
            # Set button on-click actions
            self.focused_action_buttons[i].clicked.connect(action.action)
            # Set tooltip
            if name in self.tooltips:
                tooltip = self.tooltips[name]
                self.focused_action_buttons[i].setToolTip(tooltip)
            # Show button
            self.focused_action_buttons[i].show()

    def _execute_module(
        self, name: str, moduleInfo: "jc.ModuleInfo", modal: bool = False
    ) -> None:
        log_debug("Creating module...")
        module = ij().module().createModule(moduleInfo)

        # preprocess using napari GUI
        func, param_options = functionify_module_execution(
            self.viewer, module, moduleInfo
        )
        if modal:
            execute_function_modally(
                viewer=self.viewer, name=name, func=func, param_options=param_options
            )
        else:
            widget = magicgui(function=func, **param_options)
            self.viewer.window.add_dock_widget(widget)
            widget[0].native.setFocus()
