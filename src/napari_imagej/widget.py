"""
This module contains ImageJWidget, a QWidget enabling
graphical access to ImageJ functionality.

This Widget is made accessible to napari through napari.yml
"""
import atexit
from threading import Thread
from typing import Callable, Dict, List, NamedTuple, Optional

from jpype import JArray, JImplements, JOverride
from magicgui import magicgui
from napari import Viewer
from qtpy.QtCore import Qt, Signal, Slot
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
from napari_imagej._helper_widgets import (
    JLineEdit,
    ResultTreeItem,
    SearcherTreeItem,
    SearchEventWrapper,
)
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

        # When the text bar changes, update the search results.
        self.search.bar.textEdited.connect(self.results.search)

        # When clicking a result, focus it in the focus widget
        def click(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.focuser.focus(treeItem.result)
            else:
                self.focuser.clear_focus()

        # self.results.onClick = clickFunc
        self.results.itemClicked.connect(click)

        # When double clicking a result,
        # focus it in the focus widget and run the first action
        def double_click(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, ResultTreeItem):
                self.focuser.run(treeItem.result)

        self.results.itemDoubleClicked.connect(double_click)

        # When pressing the up arrow on the topmost row in the results list,
        # go back up to the search bar
        self.results.floatAbove.connect(self.search.bar.setFocus)

        # When pressing the down arrow on the search bar,
        # go to the first result item
        def key_down_from_search_bar():
            self.search.bar.clearFocus()
            self.results.setFocus()
            self.results.setCurrentItem(self.results.topLevelItem(0))

        self.search.bar.floatBelow.connect(key_down_from_search_bar)

        # When pressing return on the search bar, focus the first result
        # in the results list and run it
        def return_search_bar():
            """Define the return behavior for this widget"""
            result = self.results._first_result()
            if result is not None:
                self.focuser.run(result)

        self.search.bar.returnPressed.connect(return_search_bar)

        # -- Final setup -- #

        # Bind L key to search bar.
        # Note the requirement for an input parameter
        napari_viewer.bind_key(
            "Control-L", lambda _: self.search.bar.setFocus(), overwrite=True
        )

        # Put the focus on the search bar
        self.search.bar.setFocus()


class SearchbarWidget(QWidget):
    """
    A QWidget for streamlining ImageJ functionality searching
    """

    def __init__(
        self,
    ):
        super().__init__()

        # The main functionality is a search bar
        self.bar: JLineEdit = JLineEdit()
        Thread(target=self.bar.enable).start()

        # Set GUI options
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.bar)


class SearchTree(QTreeWidget):

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

        self.focused_action_buttons = []  # type: ignore

    def setText(self, text: str):
        if text:
            self.focused_module_label.show()
            self.focused_module_label.setText(text)
        else:
            self.focused_module_label.hide()

    def run(self, result: "jc.SearchResult"):
        actions: List[SearchAction] = self._actions_from_result(result)
        # Run the first action UNLESS Shift is also pressed.
        # If so, run the second action
        if len(actions) > 0:
            if len(actions) > 1 and QApplication.keyboardModifiers() & Qt.ShiftModifier:
                actions[1].action()
            else:
                actions[0].action()

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

    def clear_focus(self):
        self.setText("")
        # Hide buttons
        for button in self.focused_action_buttons:
            button.hide()

    def focus(self, result: "jc.SearchResult"):
        name = ij().py.from_java(result.name())  # type: ignore
        self.setText(name)

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
