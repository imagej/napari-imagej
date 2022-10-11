"""
A QWidget designed to run SciJava SearchResult functionality.

Calls to ResultRunner.select(result) will generate a set of actions that operate
on the provided SciJava SearchResult. These actions will appear as QPushButtons.
"""
from typing import Callable, Dict, List, Union

from magicgui import magicgui
from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from napari_imagej.java import ij, jc
from napari_imagej.utilities._module_utils import (
    execute_function_modally,
    functionify_module_execution,
    info_for,
)
from napari_imagej.utilities.logging import log_debug
from napari_imagej.widgets.layouts import QFlowLayout

_action_tooltips: Dict[str, str] = {
    "Widget": "Creates a napari widget for executing this command with varying inputs",
    "Run": "Runs the command immediately, asking for inputs in a pop-up dialog box",
    "Source": "Opens the source code in browser",
    "Help": "Opens the functionality's ImageJ.net wiki page",
}


class ActionButton(QPushButton):
    """
    A QPushButton that starts with a function, occuring on click
    """

    def __init__(self, name: str, func: Callable[[], None]):
        super().__init__()
        self.setText(name)
        if name in _action_tooltips:
            self.setToolTip(_action_tooltips[name])

        self.action = func
        self.clicked.connect(self.action)


class ResultRunner(QWidget):
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
        """Selects result, displaying its name and its actions as buttons"""
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
        Runs an action of the provided SearchResult.
        The action chosen depends on keyboard modifiers.
        By default, the highest-priority action is run.
        Using SHIFT, the second-highest action is run.
        :param result: The selected SearchResult
        """
        buttons: List[ActionButton] = self._buttons_for(result)
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

    def _buttons_for(self, result: "jc.SearchResult") -> List[ActionButton]:
        buttons: List[ActionButton] = []

        # Iterate over all available python actions
        searchService = ij().get("org.scijava.search.SearchService")
        for action in searchService.actions(result):
            action_name = str(action.toString())
            # Add buttons for the java action
            if action_name == "Run":
                buttons.extend(self._run_actions_for(result))
            else:
                buttons.append(ActionButton(action_name, action.run))

        return buttons

    def _run_actions_for(self, result: "jc.SearchResult") -> List["ActionButton"]:
        def execute_result(modal: bool):
            """Helper function to perform module execution."""
            log_debug("Creating module...")

            name = str(result.name())
            moduleInfo = info_for(result)
            if not moduleInfo:
                log_debug(f"Search Result {result} cannot be run!")
                return []

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
            ActionButton(name="Run", func=lambda: execute_result(modal=True)),
            ActionButton(name="Widget", func=lambda: execute_result(modal=False)),
        ]

        return buttons
