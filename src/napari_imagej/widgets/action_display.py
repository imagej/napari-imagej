"""
A QWidget designed to highlight SciJava Modules.

Calls to SearchActionDisplay.run() will generate a list of actions that can be performed
using the provided SciJava SearchResult. These actions will appear as QPushButtons.
"""
from typing import Callable, Dict, List, Union

from magicgui import magicgui
from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from napari_imagej.java import ij, jc
from napari_imagej.utilities._module_utils import (
    convert_searchResult_to_info,
    execute_function_modally,
    functionify_module_execution,
)
from napari_imagej.utilities.logging import log_debug
from napari_imagej.widgets.layouts import QFlowLayout


class SearchActionDisplay(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        self.setLayout(QVBoxLayout())

        self.selected_module_label = QLabel()
        self.layout().addWidget(self.selected_module_label)
        self.button_pane = QWidget()
        self.button_pane.setLayout(QFlowLayout())
        self.layout().addWidget(self.button_pane)

    def select(self, result: "jc.SearchResult"):
        """Selects result, displaying its name and its SearchActions as buttons"""
        # First, remove the old information
        self.clear()

        # Then, set the label
        self._setText(result.name())

        # Finally, create buttons for each action
        for button in self._buttons_for(result):
            self.button_pane.layout().addWidget(button)

    def clear(self):
        """Clears the current selection"""
        self._setText("")
        # Remove all old buttons
        for child in self.button_pane.children():
            if isinstance(child, QPushButton):
                child.deleteLater()

    def run(self, result: "jc.SearchResult"):
        """
        Runs a SearchAction of the provided SearchResult.
        The SearchAction chosen depends on keyboard modifiers.
        By default, the highest-priority action is run.
        Using SHIFT, the second-highest action is run.
        :param result: The selected SearchResult
        """
        buttons: List[SearchActionButton] = self._buttons_for(result)
        # Run the first action UNLESS Shift is also pressed.
        # If so, run the second action
        if len(buttons) > 0:
            if len(buttons) > 1 and QApplication.keyboardModifiers() & Qt.ShiftModifier:
                buttons[1].action()
            else:
                buttons[0].action()

    # -- HELPER FUNCTIONALITY -- #

    def _setText(self, text: Union[str, "jc.String"]):
        """
        Sets the text of this widget's QLabel.
        """
        if text:
            self.selected_module_label.show()
            # NB Java strings need to be converted explicitly
            self.selected_module_label.setText(str(text))
        else:
            self.selected_module_label.hide()

    def _buttons_for(self, result: "jc.SearchResult") -> List["SearchActionButton"]:
        buttons: List["SearchActionButton"] = []

        # Iterate over all available python actions
        searchService = ij().get("org.scijava.search.SearchService")
        for action in searchService.actions(result):
            action_name = str(action.toString())
            # Add buttons for the java SearchAction
            if action_name == "Run":
                buttons.extend(self._run_actions_for(result))
            else:
                buttons.append(SearchActionButton(action_name, action.run))

        return buttons

    def _run_actions_for(self, result: "jc.SearchResult") -> List["SearchActionButton"]:
        def execute_result(modal: bool):
            """Helper function to perform module execution."""
            log_debug("Creating module...")

            name = str(result.name())
            moduleInfo = convert_searchResult_to_info(result)
            module = ij().module().createModule(moduleInfo)

            # preprocess using napari GUI
            func, param_options = functionify_module_execution(
                self.viewer, module, moduleInfo
            )
            if modal:
                execute_function_modally(
                    viewer=self.viewer,
                    name=name,
                    func=func,
                    param_options=param_options,
                )
            else:
                widget = magicgui(function=func, **param_options)
                self.viewer.window.add_dock_widget(widget)
                widget[0].native.setFocus()

        buttons = [
            SearchActionButton(name="Run", action=lambda: execute_result(modal=True)),
            SearchActionButton(
                name="Widget", action=lambda: execute_result(modal=False)
            ),
        ]

        return buttons


_tooltips: Dict[str, str] = {
    "Widget": "Runs functionality from a napari widget. "
    "Useful for parameter sweeping",
    "Run": "Runs functionality from a modal widget. Best for single executions",
    "Source": "Opens the source code on GitHub",
    "Help": "Opens the functionality's ImageJ.net wiki page",
}


class SearchActionButton(QPushButton):
    def __init__(self, name: str, action: Callable[[], None]):
        super().__init__()
        self.setText(name)
        if name in _tooltips:
            self.setToolTip(_tooltips[name])

        self.action = action
        self.clicked.connect(self.action)
