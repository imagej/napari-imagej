from enum import Enum
from threading import Thread
from typing import List

from magicgui.widgets import request_values
from napari import Viewer
from napari._qt.qt_resources import QColoredSVGIcon
from napari.layers import Layer
from qtpy.QtCore import Qt
from qtpy.QtGui import QIcon, QPixmap
from qtpy.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QWidget

from napari_imagej._module_utils import _get_layers_hack
from napari_imagej.setup_imagej import ensure_jvm_started, ij, jc, running_headless


class GUIWidget(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.from_ij: FromIJButton = FromIJButton(viewer)
        self.layout().addWidget(self.from_ij)

        self.to_ij: ToIJButton = ToIJButton(viewer)
        self.layout().addWidget(self.to_ij)

        self.gui_button: GUIButton = GUIButton()
        self.layout().addWidget(self.gui_button)

        if running_headless():
            self.gui_button.clicked.connect(self.gui_button.disable_popup)
        else:
            self.gui_button.clicked.connect(self._showUI)
            self.gui_button.clicked.connect(lambda: self.to_ij.setEnabled(True))
            self.gui_button.clicked.connect(lambda: self.from_ij.setEnabled(True))

    def _showUI(self):
        """
        NB: This must be its own function to prevent premature calling of ij()
        """
        ensure_jvm_started()
        ij().ui().showUI()


class ToIJButton(QPushButton):
    def __init__(self, viewer):
        super().__init__()
        self.setEnabled(False)
        icon = QColoredSVGIcon.from_resources("long_right_arrow")
        self.setIcon(icon.colored(theme=viewer.theme))
        self.setToolTip("Send layers to ImageJ2")
        self.clicked.connect(self.send_layers)

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

    def send_layers(self):
        layers: dict = request_values(
            title="Send layers to ImageJ2",
            layers={"annotation": Layer, "options": {"choices": _get_layers_hack}},
        )
        if layers is not None:
            for _, layer in layers.items():
                if isinstance(layer, Layer):
                    name = layer.name
                    data = ij().py.to_java(layer.data)
                    ij().ui().show(name, data)


class FromIJButton(QPushButton):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        self.setEnabled(False)
        icon = QColoredSVGIcon.from_resources("long_left_arrow")
        self.setIcon(icon.colored(theme=viewer.theme))
        self.setToolTip("Get layers from ImageJ2")
        self.clicked.connect(self.get_layers)

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

    def _get_objects(self, t):
        compatibleInputs = ij().convert().getCompatibleInputs(t)
        compatibleInputs.addAll(ij().object().getObjects(t))
        return list(compatibleInputs)

    def get_layers(self) -> List[Layer]:
        images = self._get_objects(jc.RandomAccessibleInterval)
        names = [ij().object().getName(i) for i in images]
        choices: dict = request_values(
            title="Send layers to ImageJ2",
            dataset={"annotation": Enum, "options": {"choices": names}},
        )
        if choices is not None:
            for _, name in choices.items():
                i = names.index(name)
                image = ij().py.from_java(images[i])
                if isinstance(image, Layer):
                    image.name = name
                    self.viewer.add_layer(image)
                elif ij().py._is_arraylike(image):
                    self.viewer.add_image(data=image, name=name)
                else:
                    raise ValueError(f"{image} cannot be displayed in napari!")


class GUIButton(QPushButton):
    def __init__(self):
        super().__init__()
        running_headful = not running_headless()
        self.setEnabled(False)
        if running_headful:
            self._setup_headful()
        else:
            self._setup_headless()

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

    def _setup_headful(self):
        self._set_icon("resources/16x16-flat-disabled.png")
        self.setToolTip("Display ImageJ2 GUI (loading)")
        def post_setup():
            ensure_jvm_started()
            self._set_icon("resources/16x16-flat.png")
            self.setEnabled(True)
            self.setToolTip("Display ImageJ2 GUI")
        Thread(target=post_setup).start()

    def _setup_headless(self):
        self._set_icon("resources/16x16-flat-disabled.png")
        self.setToolTip("ImageJ2 GUI unavailable!")

    def disable_popup(self):
        msg: QMessageBox = QMessageBox()
        msg.setText(
            "The ImageJ2 user interface cannot be opened "
            "when running PyImageJ headlessly. Visit "
            '<a href="https://pyimagej.readthedocs.io/en/latest/'
            'Initialization.html#interactive-mode">this site</a> '
            "for more information."
        )
        msg.setTextFormat(Qt.RichText)
        msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
        msg.exec()
