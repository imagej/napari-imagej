"""
A QWidget designed to run SciJava SearchResult functionality.

Calls to ResultRunner.select(result) will generate a set of actions that operate
on the provided SciJava SearchResult. These actions will appear as QPushButtons.
"""

from typing import Callable, Dict, List, Union

from napari import Viewer
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from napari_imagej.java import jc
from napari_imagej.widgets.layouts import QFlowLayout
from napari_imagej.widgets.widget_utils import python_actions_for

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
    def __init__(self, viewer: Viewer, output_signal: Signal):
        super().__init__()
        self.viewer = viewer
        self.output_signal = output_signal

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
        return [
            ActionButton(*a)
            for a in python_actions_for(result, self.output_signal, self)
        ]
