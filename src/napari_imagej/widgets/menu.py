"""
The top-level menu for the napari-imagej widget.
"""
from pathlib import Path
from typing import Iterable, List, Optional

from magicgui.widgets import request_values
from napari import Viewer
from napari._qt.qt_resources import QColoredSVGIcon
from napari.layers import Image, Labels, Layer, Points, Shapes
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon, QPixmap
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from scyjava import is_arraylike

from napari_imagej import settings
from napari_imagej.java import ij, jc
from napari_imagej.resources import resource_path
from napari_imagej.utilities.event_subscribers import UIShownListener
from napari_imagej.utilities.events import subscribe


class NapariImageJMenu(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.setLayout(QHBoxLayout())
        self.layout().addStretch(0)

        self.from_ij: FromIJButton = FromIJButton(viewer)
        self.layout().addWidget(self.from_ij)

        self.to_ij: ToIJButton = ToIJButton(viewer)
        self.layout().addWidget(self.to_ij)

        self.to_ij_extended: ToIJDetailedButton = ToIJDetailedButton(viewer)
        self.layout().addWidget(self.to_ij_extended)

        self.gui_button: GUIButton = GUIButton(viewer)
        self.layout().addWidget(self.gui_button)

        self.settings_button: SettingsButton = SettingsButton(viewer)
        self.layout().addWidget(self.settings_button)

        if settings.headless():
            self.gui_button.clicked.connect(self.gui_button.disable_popup)
        else:
            # NB We need to call ij().ui().showUI() on the GUI thread.
            # TODO: Use PyImageJ functionality
            # see https://github.com/imagej/pyimagej/pull/260
            def show_ui():
                if ij().ui().isVisible():
                    ij().thread().queue(
                        lambda: ij()
                        .ui()
                        .getDefaultUI()
                        .getApplicationFrame()
                        .setVisible(True)
                    )
                else:
                    ij().thread().queue(lambda: ij().ui().showUI())

            self.gui_button.clicked.connect(show_ui)

    def finalize(self):
        # GUIButton initialization
        if not settings.headless():
            self.gui_button._set_icon(resource_path("imagej2-16x16-flat"))
            self.gui_button.setEnabled(True)
            self.gui_button.setToolTip("Display ImageJ2 UI")
        # Subscribe UIShown subscriber
        subscribe(ij(), UIShownListener())


class IJMenuButton(QPushButton):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer
        viewer.events.theme.connect(self.recolor)
        self.recolor()

    def recolor(self, event=None):
        if hasattr(self, "_icon"):
            if isinstance(self._icon, QColoredSVGIcon):
                self.setIcon(self._icon.colored(theme=self.viewer.theme))


class ToIJDetailedButton(IJMenuButton):
    _icon = QColoredSVGIcon(resource_path("export_detailed"))

    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.setEnabled(False)
        self.viewer = viewer

        self.setToolTip("Export napari Layer (detailed)")

        viewer.layers.selection.events.changed.connect(self.layer_selection_changed)
        self.clicked.connect(lambda: DetailExportDialog(self.viewer).exec())

    def _handle_choices(self, choices):
        # Queue UI call on the EDT
        # TODO: Use EventQueue.invokeLater scyjava wrapper, once it exists
        img = ij().convert().convert(ij().py.to_java(choices["image"]), jc.Dataset)
        if choices["rois"]:
            rois = ij().convert().convert(ij().py.to_java(choices["rois"]), jc.ROITree)
            img.getProperties().put("rois", rois)
        ij().ui().show(img)

    def handle_no_choices(self):
        RichTextPopup(
            rich_message="There is no active window to export to ImageJ!",
            exec=True,
        )

    def layer_selection_changed(self, event):
        for layer in self.viewer.layers:
            if isinstance(layer, _IMAGE_LAYER_TYPES):
                self.setEnabled(True)
                return
        self.setEnabled(False)


_IMAGE_LAYER_TYPES = (Image, Labels)
_ROI_LAYER_TYPES = (Points, Shapes)


class DetailExportDialog(QDialog):
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

        self.img_container = self.RichComboBox("Image:", self.imgs)
        self.layout().addWidget(self.img_container)
        self.roi_container = self.RichComboBox("ROIs:", self.rois, required=False)
        self.layout().addWidget(self.roi_container)
        self.dims_container = self.DimsComboBox(self.img_container)
        self.layout().addWidget(self.dims_container)

        current_layer: Layer = viewer.layers.selection.active
        # The user likely wants to transfer the active layer, if it is an image
        if isinstance(current_layer, _IMAGE_LAYER_TYPES):
            self.img_container.combo.setCurrentText(current_layer.name)
        else:
            self.img_container.combo.setCurrentText(self.imgs[0].name)
        self.dims_container.update(self.img_container.combo.currentIndex())
        self.img_container.combo.currentIndexChanged.connect(self.dims_container.update)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.layout().addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

    def accept(self):
        super().accept()

        def pass_to_ij():
            # Grab the selected data
            img = self.img_container.combo.currentData()
            roi = self.roi_container.combo.currentData()

            j_img = ij().py.to_java(img, dim_order=self.dims_container.selections())
            if roi:
                j_img.getProperties().put("rois", ij().py.to_java(roi))

            ij().ui().show(j_img)

        ij().thread().queue(lambda: pass_to_ij())

    class RichComboBox(QWidget):
        def __init__(self, title: str, choices: List[Layer], required=True):
            super().__init__()
            self.setLayout(QHBoxLayout())
            self.layout().addWidget(QLabel(title))
            self.combo = QComboBox()
            self.choices = choices
            if not required:
                self.combo.addItem("--------", None)
            for c in choices:
                self.combo.addItem(c.name, c)
            self.layout().addWidget(self.combo)

    class DimsComboBox(QFrame):
        def __init__(self, combo_box):
            super().__init__()
            self.selection_box = combo_box
            self.setLayout(QVBoxLayout())
            self.setFrameStyle(QFrame.Box)
            self.layout().addWidget(QLabel("Dimensions:"))

            self.dims = [
                [],
                ["X"],
                ["Y", "X"],
                ["Z", "Y", "X"],
                ["T", "Y", "X", "C"],
                ["T", "Z", "Y", "X", "C"],
            ]

        def update(self, index: int):
            # remove old widgets
            for child in self.children():
                if isinstance(child, self.DimSelector):
                    self.layout().removeWidget(child)
                    child.deleteLater()
            selected = self.selection_box.combo.itemData(index)
            guess = self.dims[len(selected.data.shape)]
            for i, g in enumerate(guess):
                self.layout().addWidget(
                    self.DimSelector(f"dim_{i} ({selected.data.shape[i]} px)", g)
                )

        def selections(self):
            selections = []
            for child in self.children():
                if isinstance(child, self.DimSelector):
                    selections.append(child.combo.currentText())
            return selections

        class DimSelector(QWidget):
            choices = ["X", "Y", "Z", "T", "C", "Unspecified"]

            def __init__(self, title: str, guess: str):
                super().__init__()
                self.setLayout(QHBoxLayout())
                self.layout().addWidget(QLabel(title))
                self.combo = QComboBox()
                for c in self.choices:
                    self.combo.addItem(c)
                self.combo.setCurrentText(guess)
                self.layout().addWidget(self.combo)


class ToIJButton(IJMenuButton):
    _icon = QColoredSVGIcon(resource_path("export"))

    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.setEnabled(False)
        viewer.layers.selection.events.active.connect(self.layer_selection_changed)

        self.setToolTip("Export napari Layer")
        self.clicked.connect(self.send_active_layer)

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

    def send_active_layer(self):
        active_layer: Optional[Layer] = self.viewer.layers.selection.active
        if active_layer:
            self._show(active_layer)
        else:
            self.handle_no_choices()

    def _show(self, layer):
        # Queue UI call on the EDT
        # TODO: Use EventQueue.invokeLater scyjava wrapper, once it exists
        ij().thread().queue(lambda: ij().ui().show(ij().py.to_java(layer)))

    def handle_no_choices(self):
        RichTextPopup(
            rich_message="There is no active window to export to ImageJ!",
            exec=True,
        )

    def layer_selection_changed(self, event):
        if event.type == "active":
            self.setEnabled(isinstance(event.source.active, Image))


class FromIJButton(IJMenuButton):
    _icon = QColoredSVGIcon(resource_path("import"))

    def __init__(self, viewer: Viewer):
        super().__init__(viewer)

        self.setToolTip("Import active ImageJ2 Dataset")
        self.clicked.connect(self.get_active_layer)

    def _get_objects(self, t):
        compatibleInputs = ij().convert().getCompatibleInputs(t)
        compatibleInputs.addAll(ij().object().getObjects(t))
        return list(compatibleInputs)

    def get_active_layer(self) -> None:
        # HACK: Sync ImagePlus before transferring
        # This code can be removed once
        # https://github.com/imagej/imagej-legacy/issues/286 is solved.
        if ij().legacy and ij().legacy.isActive():
            current_image_plus = ij().WindowManager.getCurrentImage()
            if current_image_plus is not None:
                ij().py.sync_image(current_image_plus)
        # Get the active view from the active image display
        ids = ij().get("net.imagej.display.ImageDisplayService")
        # TODO: simplify to no-args once
        # https://github.com/imagej/imagej-legacy/pull/287 is merged.
        view = ids.getActiveDatasetView(ids.getActiveImageDisplay())
        if view is not None:
            self._add_layer(view)
        else:
            self.handle_no_choices()

    def _add_layer(self, view):
        # Convert the object into Python
        py_image = ij().py.from_java(view)
        # Create and add the layer
        if isinstance(py_image, Layer):
            self.viewer.add_layer(py_image)
            # Check the metadata for additonal layers, like
            # Shapes/Tracks/Points
            for _, v in py_image.metadata.items():
                if isinstance(v, Layer):
                    self.viewer.add_layer(v)
                elif isinstance(v, Iterable):
                    for itm in v:
                        if isinstance(itm, Layer):
                            self.viewer.add_layer(itm)
        # Other
        elif is_arraylike(py_image):
            name = ij().object().getName(view)
            self.viewer.add_image(data=py_image, name=name)
        else:
            raise ValueError(f"{view} cannot be displayed in napari!")

    def handle_no_choices(self):
        RichTextPopup(
            rich_message="There is no active window to export to napari!",
            exec=True,
        )


class GUIButton(IJMenuButton):
    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.setEnabled(False)
        self._set_icon(resource_path("imagej2-16x16-flat-disabled"))

        if settings.headless():
            self.setToolTip("ImageJ2 GUI unavailable!")
        else:
            self.setToolTip("Display ImageJ2 UI (loading)")

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

    def disable_popup(self):
        RichTextPopup(
            rich_message="The ImageJ2 user interface cannot be opened "
            "when running PyImageJ headlessly. Visit "
            '<a href="https://pyimagej.readthedocs.io/en/latest/'
            'Initialization.html#interactive-mode">this site</a> '
            "for more information.",
            exec=True,
        )


class SettingsButton(IJMenuButton):
    # Signal used to identify changes to user settings
    setting_change = Signal(bool)

    _icon = QColoredSVGIcon(resource_path("gear"))

    def __init__(self, viewer: Viewer):
        super().__init__(viewer)

        self.clicked.connect(self._update_settings)
        self.setting_change.connect(self._handle_settings_change)

    def _update_settings(self):
        """
        Spawn a popup allowing the user to configure napari-imagej settings.
        """
        # Build arguments list by iterating over all default settings.
        args = {k: dict(value=getattr(settings, k)) for k in settings.defaults}

        # Configure some details to improve graphical presentation and behavior.
        args["imagej_directory_or_endpoint"]["options"] = {
            "label": "ImageJ directory or endpoint",
        }
        args["imagej_base_directory"] = {
            "value": Path(settings.imagej_base_directory),
            "annotation": Path,
            "options": {"label": "ImageJ base directory", "mode": "d"},
        }
        args["include_imagej_legacy"]["options"] = {
            "label": "include original ImageJ features",
        }
        args["enable_imagej_gui"]["options"] = {
            "label": "enable ImageJ GUI if possible",
        }
        args["jvm_command_line_arguments"]["options"] = {
            "label": "JVM command line arguments",
        }

        # Use magicgui.request_values to allow user to configure settings
        choices = request_values(title="napari-imagej settings", values=args)
        if not choices:
            # Canceled
            return

        # Update settings with user selections
        any_changed: bool = settings.update(**choices)
        self.setting_change.emit(any_changed)

    def _handle_settings_change(self, any_changed: bool):
        # Present a warning dialog if any settings have validation issues.
        try:
            settings.validate()
        except ValueError as e:
            RichTextPopup(
                rich_message=(
                    "<b>Warning:</b> your settings have the following issues:<ul>"
                    + "".join(f"<li>{arg}</li>" for arg in e.args)
                    + "</ul>"
                ),
                exec=True,
            )
        if any_changed:
            # Notify (using a popup) that a restart is required for settings changes
            # to take effect.
            RichTextPopup(
                rich_message="Please restart napari for napari-imagej settings "
                "changes to take effect!",
                exec=True,
            )
        # Save the settings specified by the user
        settings.save()


class RichTextPopup(QMessageBox):
    """A helper widget for creating (and immediately displaying) popups"""

    def __init__(self, rich_message: str, exec: bool = False):
        super().__init__()
        self.setText(rich_message)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        if exec:
            self.exec()
