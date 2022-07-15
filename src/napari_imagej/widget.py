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
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from napari_imagej._flow_layout import FlowLayout
from napari_imagej._helper_widgets import ResultTreeItem, SearchBar, SearcherTreeItem
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

        # We actually create the widgets in the opposite order,
        # as the top widgets will want to control the ones below.
        self.setLayout(QVBoxLayout())

        # Module highlighter
        self.focuser: FocusWidget = FocusWidget(napari_viewer)
        # Results List
        self.results: SearchTree = SearchTree()
        # Search Bar
        self.search: SearchbarWidget = SearchbarWidget()

        # Add each in the preferred order
        self.layout().addWidget(self.search)
        self.layout().addWidget(self.results)
        self.layout().addWidget(self.focuser)

        # -- Interwidget connections -- #

        # When clicking a result, focus it in the focus widget
        def clickFunc(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.focuser.focus(treeItem.result)

        self.results.onClick = clickFunc

        # When double clicking a result,
        # focus it in the focus widget and run the first action
        def doubleClickFunc(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.focuser.run(treeItem.result)

        self.results.onDoubleClick = doubleClickFunc

        # When pressing the up arrow on the topmost row in the results list,
        # go back up to the search bar
        def keyUpFromResults():
            self.search.bar.setFocus()

        self.results.keyAboveResults = keyUpFromResults

        # When pressing the down arrow on the search bar,
        # go to the first result item
        def keyDownFromSearchBar():
            self.search.bar.clearFocus()
            self.results.setFocus()
            self.results.setCurrentItem(self.results.topLevelItem(0))

        self.search.on_key_down = keyDownFromSearchBar

        # When pressing return on the search bar, focus the first result
        # in the results list and run it
        def searchBarReturnFunc():
            """Define the return behavior for this widget"""
            result = self.results.first_result()
            if result is not None:
                self.focuser.run(result)

        self.search.bar.returnPressed.connect(searchBarReturnFunc)

        # When changing the text in the search bar, update the search results
        self.search.bar.textChanged.connect(self.results._search)

        # -- Final setup -- #

        # Bind L key to search bar.
        # Note the requirement for an input parameter
        napari_viewer.bind_key(
            "Control-L", lambda _: self.search.bar.setFocus(), overwrite=True
        )

        # Put the focus on the search bar
        self.search.bar.setFocus()


class SearchbarWidget(QWidget):
    def __init__(
        self,
    ):
        super().__init__()
        # self._results = results
        # self._focuser = focuser
        self.on_key_down = property()
        self.bar: SearchBar = SearchBar(on_key_down=lambda: self.on_key_down())

        # Set GUI options
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.bar)

        # Initialize the searchers, which will spin up an ImageJ gateway.
        # By running this in a new thread,
        # the GUI can be shown before the searchers are ready.
        def enable_searchbar():
            ensure_jvm_started()
            # Enable the searchbar now that the searchers are ready
            self.bar.setText("")
            self.bar.setEnabled(True)

        self._searchbar_generator = Thread(target=enable_searchbar)
        self._searchbar_generator.start()


class SearchTree(QTreeWidget):
    def __init__(
        self,
    ):
        super().__init__()

        # Configure GUI Options
        self.setColumnCount(1)
        self.setHeaderLabels(["Search"])
        self.setIndentation(self.indentation() // 2)
        self.onClick = property()
        self.itemClicked.connect(lambda item: self.onClick(item))
        self.onDoubleClick = property()
        self.itemDoubleClicked.connect(lambda item: self.onDoubleClick(item))
        self.keyAboveResults = property()

        def init_searchers():
            for searcher in self.searchers:
                self.addTopLevelItem(SearcherTreeItem(searcher))

        self._searcher_setup = Thread(target=init_searchers)
        self._searcher_setup.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            # Use the enter key to toggle non-leaves
            if self.currentItem().childCount() > 0:
                self.currentItem().setExpanded(not self.currentItem().isExpanded())
            # Use the enter key to run leaves (Plugins)
            else:
                self.onDoubleClick(self.currentItem())
        elif event.key() == Qt.Key_Up and self.currentItem() is self.topLevelItem(0):
            self.clearSelection()
            self.keyAboveResults()
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

    def _wait_for_setup(self):
        self._searcher_setup.join()

    def _search(self, text):
        # TODO: Consider adding a button to toggle fuzziness
        for i in range(self.topLevelItemCount()):
            self.topLevelItem(i).search(text)

    def first_result(self) -> "jc.SearchResult":
        for i in range(self.topLevelItemCount()):
            searcher = self.topLevelItem(i)
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

    def run(self, result: "jc.SearchResult"):
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
