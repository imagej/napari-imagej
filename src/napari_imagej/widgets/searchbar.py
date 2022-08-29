from threading import Thread

from qtpy.QtWidgets import QHBoxLayout, QWidget

from napari_imagej._helper_widgets import JLineEdit


class ImageJSearchbar(QWidget):
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
