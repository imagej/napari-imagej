"""
A display showing information relative to the napari-imagej widget
"""
from qtpy.QtWidgets import QLabel, QVBoxLayout, QWidget


class InfoBox(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        # Label for displaying ImageJ version
        self.version_bar = QLabel()
        self.layout().addWidget(self.version_bar)
