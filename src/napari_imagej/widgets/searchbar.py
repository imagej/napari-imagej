"""
A QWidget used to provide input to SciJava Searchers.

The bar is disabled until ImageJ is ready. This ensures the SciJava Searchers
are ready to accept queries.
"""

from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QHBoxLayout, QLineEdit, QWidget

from napari_imagej.java import ij, init_ij, java_signals


class JVMEnabledSearchbar(QWidget):
    """
    A QWidget for streamlining ImageJ functionality searching
    """

    def __init__(
        self,
    ):
        super().__init__()

        # The main functionality is a search bar
        self.bar: JLineEdit = JLineEdit()

        java_signals.when_ij_ready(self.bar.enable)

        # Set GUI options
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.bar)


class JLineEdit(QLineEdit):
    """
    A QLineEdit that is disabled until the JVM is ready
    """

    # Signal that identifies a down arrow pressed
    floatBelow = Signal()

    def __init__(self):
        super().__init__()

        # Set QtPy properties
        self.setText("Initializing ImageJ...Please Wait")
        self.setEnabled(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self.floatBelow.emit()
        else:
            super().keyPressEvent(event)

    def enable(self):
        # Once the JVM is ready, allow editing
        init_ij()
        self.setText("")
        if ij():
            self.setEnabled(True)
