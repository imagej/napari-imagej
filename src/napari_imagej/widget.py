"""
This module is an example of a barebones function plugin for napari

It implements the ``napari_experimental_provide_function`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
from typing import Any, List
from napari import Viewer
from qtpy.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QAbstractItemView,
    QHeaderView,
    QTableWidgetItem,
    QLabel,
)
from scyjava import when_jvm_starts
from napari_imagej.setup_imagej import ij, logger, java_import
from napari_imagej._module_utils import functionify_module_execution
from napari_imagej._napari_converters import init_napari_converters
from threading import Thread


class ImageJWidget(QWidget):
    """The top-level ImageJ widget for napari."""
    def __init__(self, napari_viewer: Viewer):
        super().__init__()

        # Install napari <-> java converters
        when_jvm_starts(lambda: init_napari_converters())

        self.viewer = napari_viewer
        
        self.setLayout(QVBoxLayout())

        # Search Bar
        self._search_widget: QWidget = QWidget()
        self._search_widget.setLayout(QHBoxLayout())
        self._searchbar: QLineEdit  = self._generate_searchbar()
        self._search_widget.layout().addWidget(self._searchbar)

        self.layout().addWidget(self._search_widget)

        # Searcher plugins
        def init_searchers(): 
            self.searchers, self.resultConverters = self._generate_searchers()
            self.searchService = self._generate_search_service()
            # Enable the searchbar now that the searchers are ready
            self._searchbar.setText("")
            self._searchbar.setEnabled(True)
        # Initialize the searchers, which will spin up an ImageJ gateway.
        # By running this in a new thread,
        # the GUI can be shown before the searchers are ready.
        Thread(target=init_searchers).start()

        # Results box
        self.resultTableNames = [
            "Modules:",
            "Ops:"
        ]
        self.results = [[] for _ in self.resultTableNames]
        self.resultTables, self.tableWidgets = self._generate_results_widget(self.resultTableNames)
        self.layout().addWidget(self.resultTables)

        # Module highlighter
        self.focus_widget = QWidget()
        self.focus_widget.setLayout(QVBoxLayout())
        self.focused_module = None
        self.focused_module_label = QLabel()
        self.focus_widget.layout().addWidget(self.focused_module_label)
        self.focused_module_label.setText("Display Module Here")
        self.layout().addWidget(self.focus_widget)
        self.focused_action_buttons = []  # type: ignore


    def _generate_searchbar(self) -> QLineEdit:
        searchbar = QLineEdit()
        # Disable the searchbar until the searchers are ready
        searchbar.setText('Initializing ImageJ...Please Wait')
        searchbar.setEnabled(False)
        searchbar.textChanged.connect(self._search)
        searchbar.returnPressed.connect(lambda: self._highlight_module(0, 0))
        return searchbar

    def _generate_searchers(self) -> List[Any]:
        searcherClasses = [
            java_import("org.scijava.search.module.ModuleSearcher"),
            java_import("net.imagej.ops.search.OpSearcher"),
        ]
        resultToModuleInfoConverters = [
            lambda result: result.info(),
            lambda result: result.info().cInfo(),
        ]
        pluginService = ij().get("org.scijava.plugin.PluginService")
        Searcher = java_import("org.scijava.search.Searcher")
        infos = [pluginService.getPlugin(cls, Searcher) for cls in searcherClasses]
        searchers = [info.createInstance() for info in infos]
        [ij().context().inject(searcher) for searcher in searchers]
        return searchers, resultToModuleInfoConverters

    def _generate_search_service(self):
        return ij().get("org.scijava.search.SearchService")
    
    def _highlight_from_results_table(self, searcher_index):
        index = searcher_index
        return lambda row, col: self._highlight_module(index, row, col)

    def _generate_results_widget(self, resultTableNames) -> QTableWidget:
        resultTables = []
        for i, name in enumerate(resultTableNames):
            # GUI properties
            labels = [name]
            max_results = 12
            tableWidget = QTableWidget(max_results, len(labels))
            # Modules take up a row, so highlight the entire thing
            tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
            # Label the columns with labels
            tableWidget.setHorizontalHeaderLabels(labels)
            tableWidget.horizontalHeader().setSectionResizeMode(
                0,
                QHeaderView.Stretch
            )
            tableWidget.verticalHeader().hide()
            tableWidget.setShowGrid(False)
            tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tableWidget.cellClicked.connect(self._highlight_from_results_table(i))
            resultTables.append(tableWidget)

        container = QWidget()
        container.setLayout(QVBoxLayout())
        [container.layout().addWidget(w) for w in resultTables]
        return (container, resultTables)

    def _search(self, text):
        # TODO: Consider adding a button to toggle fuzziness
        for i in range(len(self.searchers)):
            self.results[i] = self.searchers[i].search(text, True)
            for j in range(len(self.results[i])):
                name = ij().py.from_java(self.results[i][j].name())
                self.tableWidgets[i].setItem(j, 0, QTableWidgetItem(name))
                self.tableWidgets[i].showRow(j)
            for j in range(len(self.results[i]), self.tableWidgets[i].rowCount()):
                self.tableWidgets[i].setItem(j, 0, QTableWidgetItem(""))
                self.tableWidgets[i].hideRow(j)

    def _highlight_module(self, table: int, row: int, col: int):
        # Ensure the clicked module is an actual selection
        if (row >= len(self.results[table])):
            return
        # Print highlighted module
        self.focused_module = self.results[table][row]
        name = ij().py.from_java(self.focused_module.name())  # type: ignore
        self.focused_module_label.setText(name)

        # Create buttons for each action
        self.focused_actions = self.searchService.actions(self.focused_module)
        activated_actions = len(self.focused_action_buttons)
        # Hide buttons if we have more than needed
        while activated_actions > len(self.focused_actions):
            activated_actions = activated_actions - 1
            self.focused_action_buttons[activated_actions].hide()
        # Create buttons if we need more than we have
        while len(self.focused_action_buttons) < len(self.focused_actions):
            button = QPushButton()
            self.focused_action_buttons.append(button)
            self.focus_widget.layout().addWidget(button)
        # Rename buttons to reflect focused module's actions
        for i in range(len(self.focused_actions)):
            action_name = ij().py.from_java(self.focused_actions[i].toString())
            self.focused_action_buttons[i].show()
            self.focused_action_buttons[i].setText(action_name)
            self.focused_action_buttons[i].disconnect()
            if action_name == "Run":
                self.focused_action_buttons[i].clicked.connect(
                    lambda: self._execute_module(
                        self.resultConverters[table](self.focused_module)
                    )
                )
            else:
                self.focused_action_buttons[i].clicked.connect(
                    self.focused_actions[i].run
                )
            self.focused_action_buttons[i].show()

    def _execute_module(self, moduleInfo):
        logger().debug("Creating module...")
        module = ij().module().createModule(moduleInfo)

        # preprocess using napari GUI
        logger().debug("Processing...")
        func, param_options = functionify_module_execution(self.viewer, logger(), module, moduleInfo)
        self.viewer.window.add_function_widget(
            func, magic_kwargs=param_options
        )
