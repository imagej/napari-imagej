"""
A widget that provides access to the SciJava REPL.

This supports all of the languages of SciJava.
"""

from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from napari_imagej.model import NapariImageJ


class REPLWidget(QWidget):
    def __init__(self, nij: NapariImageJ, parent: QWidget = None):
        """
        Initialize the REPLWidget.

        :param nij: The NapariImageJ model object to use when evaluating commands.
        :param parent: The parent widget (optional).
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.output_textedit = QTextEdit(self)
        self.output_textedit.setReadOnly(True)
        layout.addWidget(self.output_textedit)

        nij.add_repl_callback(lambda s: self.process_output(s))

        h_layout = QHBoxLayout()
        layout.addLayout(h_layout)

        self.language_combo = QComboBox(self)
        h_layout.addWidget(self.language_combo)

        self.input_lineedit = QLineEdit(self)
        self.input_lineedit.returnPressed.connect(self.process_input)
        h_layout.addWidget(self.input_lineedit)

        self.script_repl = nij.repl
        self.language_combo.addItems(
            [str(el) for el in list(self.script_repl.getInterpretedLanguages())]
        )
        self.language_combo.setCurrentText(
            str(self.script_repl.getInterpreter().getLanguage())
        )
        self.language_combo.currentTextChanged.connect(self.change_language)

    def change_language(self, language: str):
        """
        Change the active scripting language of the REPL.

        :param language: The new scripting language to use.
        """
        self.script_repl.lang(language)
        self.output_textedit.clear()

    def process_input(self):
        """
        Process the user input and evaluate it using the REPL.
        """
        input_text = self.input_lineedit.text()
        self.input_lineedit.clear()

        # Evaluate the input using REPL's evaluate method.
        self.output_textedit.append(f">>> {input_text}")
        self.script_repl.evaluate(input_text)

    def process_output(self, s):
        """
        Display output given from the REPL in the output text area.
        """
        self.output_textedit.append(s)

        # Scroll to the bottom of the output text area.
        cursor = self.output_textedit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_textedit.setTextCursor(cursor)
        self.output_textedit.ensureCursorVisible()
