"""
A widget that provides access to the SciJava REPL.

This supports all of the languages of SciJava.
"""
from qtpy.QtGui import QTextCursor
from qtpy.QtWidgets import QComboBox, QLineEdit, QTextEdit, QVBoxLayout, QWidget

from napari_imagej.java import jc


class REPLWidget(QWidget):
    def __init__(self, script_repl, parent=None):
        """
        Initialize the REPLWidget.

        Parameters:
        - script_repl (ScriptREPL): The ScriptREPL object for evaluating commands.
        - parent (QWidget): The parent widget (optional).

        Set up the user interface and connect signals for the REPLWidget.
        """
        super().__init__(parent)
        self.script_repl = script_repl

        layout = QVBoxLayout(self)

        self.language_combo = QComboBox(self)
        self.language_combo.addItems(
            [str(el) for el in list(self.script_repl.getInterpretedLanguages())]
        )
        self.language_combo.currentTextChanged.connect(self.change_language)
        layout.addWidget(self.language_combo)

        self.output_textedit = QTextEdit(self)
        self.output_textedit.setReadOnly(True)
        layout.addWidget(self.output_textedit)

        self.input_lineedit = QLineEdit(self)
        self.input_lineedit.returnPressed.connect(self.process_input)
        layout.addWidget(self.input_lineedit)

    def change_language(self, language):
        """
        Change the scripting language of the ScriptREPL object.

        Parameters:
        - language (str): The selected scripting language.

        Update the scripting language setting of the ScriptREPL object based on
        the user's selection.
        """
        self.script_repl.lang(language)
        self.output_textedit.clear()

    def process_input(self):
        """
        Process the user input and evaluate it using the ScriptREPL.

        Display the results in the output text area.
        """
        input_text = self.input_lineedit.text()
        self.input_lineedit.clear()

        # Catch script errors when evaluating
        try:
            # Evaluate the input using interpreter's eval method
            result = self.script_repl.getInterpreter().eval(input_text)

            # Display the result in the output text area
            self.output_textedit.append(f">>> {input_text}")
            self.output_textedit.append(str(result))
        except jc.ScriptException as e:
            # Display the exception message in the output text area
            self.output_textedit.append(f">>> {input_text}")
            self.output_textedit.append(f"Error: {str(e)}")
        finally:
            self.output_textedit.append("")

        # Scroll to the bottom of the output text area
        cursor = self.output_textedit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_textedit.setTextCursor(cursor)
        self.output_textedit.ensureCursorVisible()
