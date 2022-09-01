"""
A QWidget designed to highlight SciJava Modules.

Calls to SearchActionDisplay.run() will generate a list of actions that can be performed
using the provided SciJava SearchResult. These actions will appear as QPushButtons.
"""
from typing import Callable, Dict, List, NamedTuple

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
from napari_imagej.widgets.layouts import FlowLayout


class SearchAction(NamedTuple):
    name: str
    action: Callable[[], None]


class SearchActionDisplay(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        self.setLayout(QVBoxLayout())

        self.selected_module_label = QLabel()
        self.layout().addWidget(self.selected_module_label)
        self.button_pane = QWidget()
        self.button_pane.setLayout(FlowLayout())
        self.layout().addWidget(self.button_pane)

        self.selection_action_buttons = []  # type: ignore

    def select(self, result: "jc.SearchResult"):
        """Selects result, displaying its name and its SearchActions as buttons"""
        name = ij().py.from_java(result.name())  # type: ignore
        self._setText(name)

        # Create buttons for each action
        python_actions: List[SearchAction] = self._actions_from_result(result)
        buttons_needed = len(python_actions)
        activated_actions = len(self.selection_action_buttons)
        # Hide buttons if we have more than needed
        while activated_actions > buttons_needed:
            activated_actions = activated_actions - 1
            self.selection_action_buttons[activated_actions].hide()
        # Create buttons if we need more than we have
        while len(self.selection_action_buttons) < buttons_needed:
            button = QPushButton()
            self.selection_action_buttons.append(button)
            self.button_pane.layout().addWidget(button)
        # Rename buttons to reflect selected module's actions
        # TODO: Can we use zip on the buttons and the actions?
        for i, action in enumerate(python_actions):
            # Clean old actions from button
            # HACK: disconnect() throws an exception if there are no connections.
            # Thus we use button name as a proxy for when there is a connected action.
            if self.selection_action_buttons[i].text() != "":
                self.selection_action_buttons[i].disconnect()
                self.selection_action_buttons[i].setText("")
            # Set button name
            self.selection_action_buttons[i].setText(action.name)
            # Set button on-click actions
            self.selection_action_buttons[i].clicked.connect(action.action)
            # Set tooltip
            if name in self._tooltips:
                tooltip = self._tooltips[name]
                self.selection_action_buttons[i].setToolTip(tooltip)
            # Show button
            self.selection_action_buttons[i].show()

    def clear(self):
        """Clears the current selection"""
        self._setText("")
        # Hide buttons
        for button in self.selection_action_buttons:
            button.hide()

    def run(self, result: "jc.SearchResult"):
        """
        Runs a SearchAction of the provided SearchResult.
        The SearchAction chosen depends on keyboard modifiers.
        By default, the highest-priority action is run.
        Using SHIFT, the second-highest action is run.
        :param result: The selected SearchResult
        """
        actions: List[SearchAction] = self._actions_from_result(result)
        # Run the first action UNLESS Shift is also pressed.
        # If so, run the second action
        if len(actions) > 0:
            if len(actions) > 1 and QApplication.keyboardModifiers() & Qt.ShiftModifier:
                actions[1].action()
            else:
                actions[0].action()

    # -- HELPER FUNCTIONALITY -- #

    def _setText(self, text: str):
        """
        Sets the text of this widget's QLabel.
        """
        if text:
            self.selected_module_label.show()
            self.selected_module_label.setText(text)
        else:
            self.selected_module_label.hide()

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

    _tooltips: Dict[str, str] = {
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

    def _execute_module(
        self, name: str, moduleInfo: "jc.ModuleInfo", modal: bool = False
    ) -> None:
        """Helper function to perform module execution."""
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
