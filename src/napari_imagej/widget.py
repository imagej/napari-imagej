"""
This module contains ImageJWidget, a QWidget enabling
graphical access to ImageJ functionality.

This Widget is made accessible to napari through napari.yml
"""
from functools import lru_cache
from threading import Thread
from typing import Callable, Dict, List, NamedTuple

from magicgui import magicgui
from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
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
        self.highlighter: FocusWidget = FocusWidget(napari_viewer)
        self.layout().addWidget(self.highlighter)

        # -- Interwidget connections -- #

        # When the text bar changes, update the search results.
        self.search.bar.textChanged.connect(self.results._search)

        # When the user presses enter on the search, run the first action
        def searchBarReturnAction():
            result = self.results.first_result()
            if result is not None:
                self.highlighter._highlight_and_run(result)

        self.search.bar.returnPressed.connect(searchBarReturnAction)

        def searchBarKeyDown():
            self.search.bar.clearFocus()
            self.results._tree.setFocus()
            self.results._tree.setCurrentItem(self.results._tree.topLevelItem(0))

        self.search.bar.keyDownAction = searchBarKeyDown

        def clickFunc(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.highlighter.focus(treeItem.result)

        self.results._tree.itemClicked.connect(clickFunc)

        def doubleClickFunc(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.highlighter._highlight_and_run(treeItem.result)

        self.results._tree.itemDoubleClicked.connect(doubleClickFunc)
        self.results._tree.returnAction = doubleClickFunc
        self.results._tree.keyUpAction = lambda: self.search.bar.setFocus()

        # -- Final setup -- #

        # Bind L key to search bar.
        # Note the requirement for an input parameter
        napari_viewer.bind_key(
            "Control-L", lambda _: self.search.bar.setFocus(), overwrite=True
        )

        # Put the focus on the search bar
        self.search.bar.setFocus()


class SearchBar(QLineEdit):
    def __init__(self):
        super().__init__()
        # Disable the searchbar until the searchers are ready
        self.setText("Initializing ImageJ...Please Wait")
        self.setEnabled(False)
        self.keyDownAction = property()
        self.returnAction = property()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self.keyDownAction()
        else:
            super().keyPressEvent(event)


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
    def bar(self) -> SearchBar:
        return self._searchbar

    def _generate_searchbar(self) -> SearchBar:
        return SearchBar()


class ResultTreeItem(QTreeWidgetItem):
    def __init__(self, result: "jc.SearchResult"):
        super().__init__()
        self.name = ij().py.from_java(result.name())
        self.setText(0, self.name)
        self._result = result

    @property
    def result(self):
        return self._result


class SearcherTreeItem(QTreeWidgetItem):
    def __init__(self, searcher: "jc.Searcher"):
        super().__init__()
        self.setText(0, ij().py.from_java(searcher.title()))
        self.setFlags(self.flags() & ~Qt.ItemIsSelectable)
        self._searcher = searcher

    def search(self, text: str):
        results = self._searcher.search(text, True)
        while self.childCount() > 0:
            self.removeChild(self.child(0))
        for result in results:
            self.addChild(ResultTreeItem(result))
        if len(results) > 0:
            self.setExpanded(True)


class SearchTree(QTreeWidget):
    def __init__(
        self,
    ):
        super().__init__()
        self.setColumnCount(1)
        self.setHeaderLabels(["Search"])
        self.setIndentation(self.indentation() // 2)
        self.keyUpAction = property()
        self.returnAction = property()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            # Use the enter key to toggle non-leaves
            if self.currentItem().childCount() > 0:
                self.currentItem().setExpanded(not self.currentItem().isExpanded())
            # Use the enter key to run leaves (Plugins)
            else:
                self.returnAction(self.currentItem())
        elif event.key() == Qt.Key_Up and self.currentItem() is self.topLevelItem(0):
            self.clearSelection()
            self.keyUpAction()
        elif event.key() == Qt.Key_Right and self.currentItem().childCount() > 0:
            if self.currentItem().isExpanded():
                self.setCurrentItem(self.currentItem().child(0))
            else:
                self.currentItem().setExpanded(True)
        elif event.key() == Qt.Key_Left:
            if self.currentItem().parent() is None:
                self.currentItem().setExpanded(False)
            else:
                self.setCurrentItem(self.currentItem().parent())
        else:
            super().keyPressEvent(event)


class ResultsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())

        # Results
        self._tree: SearchTree = SearchTree()
        self.layout().addWidget(self._tree)

        def init_searchers():
            for searcher in self.searchers:
                self._tree.addTopLevelItem(SearcherTreeItem(searcher))

        self._searcher_setup = Thread(target=init_searchers)
        self._searcher_setup.start()

    @property
    def results(self) -> List[List["jc.SearchResult"]]:
        return self._results

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

    def _wait_for_tree_setup(self):
        self._searcher_setup.join()

    def _search(self, text):
        # TODO: Consider adding a button to toggle fuzziness
        for i in range(self._tree.topLevelItemCount()):
            self._tree.topLevelItem(i).search(text)

    def first_result(self) -> "jc.SearchResult":
        for i in range(self._tree.topLevelItemCount()):
            searcher = self._tree.topLevelItem(i)
            if searcher.childCount() > 0:
                return searcher.child(0).result
        return None


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

    def _highlight_and_run(self, result: "jc.SearchResult"):
        if QApplication.keyboardModifiers() & Qt.ShiftModifier:
            selection = "Widget"
        else:
            selection = "Run"

        actions: List[SearchAction] = self._actions_from_result(result)
        # Find the widget button
        for action in actions:
            if action.name == selection:
                action.action()

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

    def focus(self, result: "jc.SearchResult"):
        name = ij().py.from_java(result.name())  # type: ignore
        self.focused_module_label.setText(name)

        # Create buttons for each action
        # searchService = ij().get("org.scijava.search.SearchService")
        # self.focused_actions = searchService.actions(module)
        python_actions: List[SearchAction] = self._actions_from_result(result)
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
