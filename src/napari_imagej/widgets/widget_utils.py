from functools import lru_cache
from logging import getLogger
from typing import List

from jpype import JArray, JByte
from scyjava import jvm_started
from magicgui import magicgui
from napari import Viewer
from napari.layers import Image, Labels, Layer, Points, Shapes
from qtpy.QtCore import QByteArray, Signal
from qtpy.QtGui import QFontMetrics, QIcon, QPixmap
from qtpy.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from napari_imagej import nij
from napari_imagej.java import jc
from napari_imagej.utilities._module_utils import (
    execute_function_modally,
    functionify_module_execution,
    info_for,
)

# Generally, Python libraries treat the dimensions i of an array with n
# dimensions as the CONVENTIONAL_DIMS[n][i] axis
CONVENTIONAL_DIMS = [
    [],
    ["X"],
    ["Y", "X"],
    ["Z", "Y", "X"],
    ["Time", "Y", "X", "Channel"],
    ["Time", "Z", "Y", "X", "Channel"],
]


def python_actions_for(
    result: "jc.SearchResult", output_signal: Signal, parent_widget: QWidget = None
):
    actions = []
    # Iterate over all available python actions
    searchService = nij.ij.get("org.scijava.search.SearchService")
    for action in searchService.actions(result):
        action_name = str(action.toString())
        # Add buttons for the java action
        if action_name == "Run":
            actions.extend(_run_actions_for(result, output_signal, parent_widget))
        else:
            actions.append((action_name, action.run))
    return actions


def _run_actions_for(
    result: "jc.SearchResult", output_signal: Signal, parent_widget: QWidget
):
    def execute_result(modal: bool):
        """Helper function to perform module execution."""
        getLogger("napari-imagej").debug("Creating module...")

        name = str(result.name())
        moduleInfo = info_for(result)
        if not moduleInfo:
            getLogger("napari-imagej").debug(f"Search Result {result} cannot be run!")
            return []

        if (
            nij.ij.legacy
            and nij.ij.legacy.isActive()
            and isinstance(moduleInfo, jc.LegacyCommandInfo)
        ):
            reply = QMessageBox.question(
                parent_widget,
                "Warning: ImageJ PlugIn",
                (
                    f'"{name}" is an original ImageJ PlugIn'
                    " and should be run from the ImageJ UI."
                    " Would you like to launch the ImageJ UI?"
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                nij.ij.thread().queue(lambda: nij.ij.ui().showUI())
            return

        module = nij.ij.module().createModule(moduleInfo)

        # preprocess using napari GUI
        func, param_options = functionify_module_execution(
            lambda o: output_signal.emit(o),
            module,
            moduleInfo,
        )
        if modal:
            execute_function_modally(
                name=name,
                func=func,
                param_options=param_options,
            )
        else:
            widget = magicgui(function=func, **param_options)
            widget.name = name
            output_signal.emit(widget)

    run_actions = [
        ("Run", lambda: execute_result(modal=True)),
        ("Widget", lambda: execute_result(modal=False)),
    ]

    return run_actions


class JavaErrorMessageBox(QDialog):
    """A helper widget for creating (and immediately displaying) popups"""

    def __init__(self, title: str, error_message: str, *args, **kwargs):
        QDialog.__init__(self, *args, **kwargs)
        self.setLayout(QGridLayout())
        # Write the title to a Label
        self.layout().addWidget(
            QLabel(title, self), 0, 0, 1, self.layout().columnCount()
        )

        # Write the error message to a TextEdit
        msg_edit = QTextEdit(self)
        msg_edit.setReadOnly(True)
        msg_edit.setText(error_message)
        self.layout().addWidget(msg_edit, 1, 0, 1, self.layout().columnCount())
        msg_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Default size - size of the error message
        font = msg_edit.document().defaultFont()
        fontMetrics = QFontMetrics(font)
        textSize = fontMetrics.size(0, error_message)
        textWidth = textSize.width() + 100
        textHeight = textSize.height() + 100
        self.resize(textWidth, textHeight)
        # Maximum size - ~80% of the user's screen
        screen_size = QApplication.desktop().screenGeometry()
        self.setMaximumSize(
            int(screen_size.width() * 0.8), int(screen_size.height() * 0.8)
        )

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok)
        btn_box.accepted.connect(self.accept)
        self.layout().addWidget(btn_box, 2, 0, 1, self.layout().columnCount())


_IMAGE_LAYER_TYPES = (Image, Labels)
_ROI_LAYER_TYPES = (Points, Shapes)


class LayerComboBox(QWidget):
    """A QWidget for selecting from a List of Layers, with a title"""

    def __init__(self, title: str, choices: List[Layer], required=True):
        super().__init__()
        # Define layout
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(QLabel(title))
        self.combo = QComboBox()
        self.layout().addWidget(self.combo)
        # Add choices to widget
        self.choices = choices
        if not required:
            self.combo.addItem("--------", None)
        for c in choices:
            self.combo.addItem(c.name, c)


class DimsComboBox(QFrame):
    """A QFrame used to map the axes of a Layer to dimension labels"""

    def __init__(self, combo_box: LayerComboBox):
        super().__init__()
        self.selection_box: LayerComboBox = combo_box
        self.setLayout(QVBoxLayout())
        self.setFrameStyle(QFrame.Box)
        self.layout().addWidget(QLabel("Dimensions:"))

    def update(self, index: int):
        """
        Updates the number of dimension combo boxes based on the selected index.

        Designed to be called by a LayerComboBox
        """

        # remove old widgets
        for child in self.children():
            if isinstance(child, self.DimSelector):
                self.layout().removeWidget(child)
                child.deleteLater()
        # Determine the selected layer
        selected = self.selection_box.combo.itemData(index)
        # Guess dimension labels for the selection
        ndim = len(selected.data.shape)
        if (dims := getattr(selected.data, "dims", None)) is not None:
            guess = dims
        elif isinstance(selected, Image) and selected.rgb:
            guess = list(CONVENTIONAL_DIMS[ndim - 1])
            guess.append("Channel")
        else:
            guess = CONVENTIONAL_DIMS[ndim]
        # Create dimension selectors for each dimension of the selection.
        for i, g in enumerate(guess):
            self.layout().addWidget(
                self.DimSelector(f"dim_{i} ({selected.data.shape[i]} px)", g)
            )

    def provided_labels(self):
        """
        Returns a list, where the ith entry provides the label for the
        ith dimension of the selected image
        """
        selections = []
        for child in self.children():
            if isinstance(child, self.DimSelector):
                selections.append(child.combo.currentText())
        return selections

    class DimSelector(QWidget):
        """A QWidget providing potential labels for each dimension"""

        # NB: Strings correspond to supported net.imagej.axis.Axes types
        choices = ["X", "Y", "Z", "Time", "Channel", "Unspecified"]

        def __init__(self, title: str, guess: str):
            # Define widget layout
            super().__init__()
            self.setLayout(QHBoxLayout())
            self.layout().addWidget(QLabel(title))
            self.combo = QComboBox()
            # Add choices
            for c in self.choices:
                self.combo.addItem(c)
            self.combo.setCurrentText(guess)
            self.layout().addWidget(self.combo)


class DetailExportDialog(QDialog):
    """Qt Dialog launched to provide detailed image transfer"""

    def __init__(self, viewer: Viewer):
        super().__init__()
        self.setLayout(QVBoxLayout())
        # Write the title to a Label
        self.layout().addWidget(QLabel("Export data to ImageJ"))

        # Parse layer options
        self.imgs = []
        self.rois = []
        for layer in viewer.layers:
            if isinstance(layer, _IMAGE_LAYER_TYPES):
                self.imgs.append(layer)
            elif isinstance(layer, _ROI_LAYER_TYPES):
                self.rois.append(layer)

        # Add combo boxes
        self.img_container = LayerComboBox("Image:", self.imgs)
        self.layout().addWidget(self.img_container)
        self.roi_container = LayerComboBox("ROIs:", self.rois, required=False)
        self.layout().addWidget(self.roi_container)
        self.dims_container = DimsComboBox(self.img_container)
        self.layout().addWidget(self.dims_container)

        # Determine default selection
        current_layer: Layer = viewer.layers.selection.active
        if isinstance(current_layer, _IMAGE_LAYER_TYPES):
            # The user likely wants to transfer the active layer, if it is an image
            self.img_container.combo.setCurrentText(current_layer.name)
        else:
            self.img_container.combo.setCurrentText(self.imgs[0].name)
        self.dims_container.update(self.img_container.combo.currentIndex())
        self.img_container.combo.currentIndexChanged.connect(self.dims_container.update)

        # Add dialog buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.layout().addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def accept(self):
        super().accept()

        def pass_to_ij():
            img = self.img_container.combo.currentData()
            roi = self.roi_container.combo.currentData()
            # Convert the selections to Java equivalents
            j_img = nij.ij.py.to_java(
                img, dim_order=self.dims_container.provided_labels()
            )
            if roi:
                if isinstance(roi, Points):
                    j_point = nij.ij.py.to_java(roi)
                    j_roi = jc.DefaultROITree()
                    j_roi.addROIs(jc.ArrayList([j_point]))
                else:
                    j_roi = nij.ij.py.to_java(roi)
                j_img.getProperties().put("rois", j_roi)
            # Show the resulting image
            nij.ij.ui().show(j_img)

        nij.ij.thread().queue(lambda: pass_to_ij())


@lru_cache
def _get_icon(path: str, cls: "jc.Class" = None):
    # Ignore falsy paths
    if not path:
        return
    # Web URLs
    if path.startswith("https"):
        # TODO: Add icons from web
        return
    # Java Resources
    # NB: Use java only if JVM started
    elif jvm_started() and isinstance(cls, jc.Class):
        stream = cls.getResourceAsStream(path)
        # Ignore falsy streams
        if not stream:
            return
        # Create a buffer to create the byte[]
        buffer = jc.ByteArrayOutputStream()
        foo = JArray(JByte)(1024)
        while True:
            length = stream.read(foo, 0, foo.length)
            if length == -1:
                break
            buffer.write(foo, 0, length)
        # Convert the byte[] into a bytearray
        bytes_array = bytearray()
        bytes_array.extend(buffer.toByteArray())
        # Convert thte bytearray into a QIcon
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(bytes_array))
        return QIcon(pixmap)
