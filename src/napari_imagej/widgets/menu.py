"""
The top-level menu for the napari-imagej widget.
"""

from pathlib import Path
from typing import Iterable, Optional

from magicgui.widgets import request_values
from napari import Viewer
from napari._qt.qt_resources import QColoredSVGIcon
from napari.layers import Image, Layer
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon, QPixmap
from qtpy.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QWidget
from scyjava import is_arraylike

from napari_imagej import nij, settings
from napari_imagej.resources import resource_path
from napari_imagej.utilities.event_subscribers import UIShownListener
from napari_imagej.utilities.events import subscribe, unsubscribe
from napari_imagej.widgets.repl import REPLWidget
from napari_imagej.widgets.widget_utils import _IMAGE_LAYER_TYPES, DetailExportDialog


class NapariImageJMenu(QWidget):
    """Container widget comprising the napari-imagej menu bar."""

    def __init__(self, viewer: Viewer):
        super().__init__()
        self.setLayout(QHBoxLayout())
        self.layout().addStretch(0)

        self.from_ij: FromIJButton = FromIJButton(viewer)
        self.layout().addWidget(self.from_ij)

        self.to_ij: ToIJButton = ToIJButton(viewer)
        self.layout().addWidget(self.to_ij)

        self.to_ij_detail: ToIJDetailedButton = ToIJDetailedButton(viewer)
        self.layout().addWidget(self.to_ij_detail)

        self.gui_button: GUIButton = GUIButton(viewer)
        self.layout().addWidget(self.gui_button)

        self.repl_button: REPLButton = REPLButton(viewer)
        self.layout().addWidget(self.repl_button)

        self.settings_button: SettingsButton = SettingsButton(viewer)
        self.layout().addWidget(self.settings_button)

        if settings.headless():
            self.gui_button.clicked.connect(self.gui_button.disable_popup)
        else:
            # NB We need to call nij.ij.ui().showUI() on the GUI thread.
            # TODO: Use PyImageJ functionality
            # see https://github.com/imagej/pyimagej/pull/260
            def show_ui():
                if nij.ij.ui().isVisible():
                    nij.ij.thread().queue(
                        lambda: nij.ij.ui()
                        .getDefaultUI()
                        .getApplicationFrame()
                        .setVisible(True)
                    )
                else:
                    nij.ij.thread().queue(lambda: nij.ij.ui().showUI())

            self.gui_button.clicked.connect(show_ui)

    def finalize(self):
        # GUIButton initialization
        if not settings.headless():
            self.gui_button._icon_path = resource_path("imagej2-16x16-flat")
            self.gui_button.setIcon(self.gui_button._icon())
            self.gui_button.setEnabled(True)
            self.gui_button.setToolTip("Display ImageJ2 UI")

        # Now the REPL can be enabled
        self.repl_button.setEnabled(True)

        # Subscribe UIShownListener
        self.subscriber = UIShownListener()
        subscribe(nij.ij, self.subscriber)

    def __del__(self):
        # Unsubscribe UIShownListener
        if self.subscriber:
            unsubscribe(nij.ij, self.subscriber)


class IJMenuButton(QPushButton):
    """Base class defining shared napari-imagej menu button functionality"""

    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer
        viewer.events.theme.connect(self.recolor)
        self.recolor()

    def recolor(self, event=None):
        """Recolors this button's icon, if it can be recolored."""
        if icon := self._icon():
            if isinstance(icon, QColoredSVGIcon):
                self.setIcon(icon.colored(theme=self.viewer.theme))

    def _icon(self):
        """
        Placeholder function returning this button's icon.
        This function should be overwritten by subclasses.
        """
        return None


class ToIJDetailedButton(IJMenuButton):
    """
    Button providing detailed image transfer from napari to ImageJ2.
    Detailed image transfer allows the selection of an "image" layer
    (either Image or Labels), along with the assignment of a "rois" layer
    (either Points or Shapes), and the identification of dimension assignments
    """

    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.setEnabled(False)
        self.viewer = viewer

        self.setToolTip("Export napari Layer (detailed)")

        viewer.layers.selection.events.changed.connect(self.layer_selection_changed)
        self.clicked.connect(lambda: DetailExportDialog(self.viewer).exec())

    def _icon(self):
        return QColoredSVGIcon(resource_path("export_detailed"))

    def layer_selection_changed(self, event):
        """Disables the button if there are no "image" layers"""
        for layer in self.viewer.layers:
            if isinstance(layer, _IMAGE_LAYER_TYPES):
                self.setEnabled(True)
                return
        self.setEnabled(False)


class ToIJButton(IJMenuButton):
    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.setEnabled(False)
        viewer.layers.selection.events.active.connect(self.layer_selection_changed)

        self.setToolTip("Export napari Layer")
        self.clicked.connect(self.send_active_layer)

    def _icon(self):
        return QColoredSVGIcon(resource_path("export"))

    def send_active_layer(self):
        layer: Optional[Layer] = self.viewer.layers.selection.active
        if layer:
            # Queue UI call on the EDT
            # TODO: Use EventQueue.invokeLater scyjava wrapper, once it exists
            nij.ij.thread().queue(lambda: nij.ij.ui().show(nij.ij.py.to_java(layer)))
        else:
            self.handle_no_choices()

    def handle_no_choices(self):
        RichTextPopup(
            rich_message="There is no active window to export to ImageJ!",
            exec=True,
        )

    def layer_selection_changed(self, event):
        if event.type == "active":
            self.setEnabled(isinstance(event.source.active, Image))


class FromIJButton(IJMenuButton):
    def __init__(self, viewer: Viewer):
        super().__init__(viewer)

        self.setToolTip("Import active ImageJ2 Dataset")
        self.clicked.connect(self.get_active_layer)

    def _icon(self):
        return QColoredSVGIcon(resource_path("import"))

    def _get_objects(self, t):
        compatibleInputs = nij.ij.convert().getCompatibleInputs(t)
        compatibleInputs.addAll(nij.ij.object().getObjects(t))
        return list(compatibleInputs)

    def get_active_layer(self) -> None:
        # HACK: Sync ImagePlus before transferring
        # This code can be removed once
        # https://github.com/imagej/imagej-legacy/issues/286 is solved.
        if nij.ij.legacy and nij.ij.legacy.isActive():
            current_image_plus = nij.ij.WindowManager.getCurrentImage()
            if current_image_plus is not None:
                nij.ij.py.sync_image(current_image_plus)
        # Get the active view from the active image display
        ids = nij.ij.get("net.imagej.display.ImageDisplayService")
        # TODO: simplify to no-args once
        # https://github.com/imagej/imagej-legacy/pull/287 is merged.
        view = ids.getActiveDatasetView(ids.getActiveImageDisplay())
        if view is not None:
            self._add_layer(view)
        else:
            self.handle_no_choices()

    def _add_layer(self, view):
        # Convert the object into Python
        py_image = nij.ij.py.from_java(view)
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
            name = nij.ij.object().getName(view)
            self.viewer.add_image(data=py_image, name=name)
        else:
            raise ValueError(f"{view} cannot be displayed in napari!")

    def handle_no_choices(self):
        RichTextPopup(
            rich_message="There is no active window to export to napari!",
            exec=True,
        )


class GUIButton(IJMenuButton):
    _icon_path = resource_path("imagej2-16x16-flat-disabled")

    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.setEnabled(False)
        self.setIcon(self._icon())

        if settings.headless():
            self.setToolTip("ImageJ2 GUI unavailable!")
        else:
            self.setToolTip("Display ImageJ2 UI (loading)")

    def _icon(self):
        return QIcon(QPixmap(self._icon_path))

    def disable_popup(self):
        RichTextPopup(
            rich_message="The ImageJ2 user interface cannot be opened "
            "when running PyImageJ headlessly. Visit "
            '<a href="https://pyimagej.readthedocs.io/en/latest/'
            'Initialization.html#interactive-mode">this site</a> '
            "for more information.",
            exec=True,
        )


class REPLButton(IJMenuButton):
    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.viewer = viewer
        self.setToolTip("Show/hide the SciJava REPL")

        self.setEnabled(False)

        self.clicked.connect(self._toggle_repl)
        self._widget = None

    def _icon(self):
        return QColoredSVGIcon(resource_path("repl"))

    def _add_repl_to_dock(self):
        self._widget = REPLWidget(nij=nij)
        self._widget.visible = False
        self.viewer.window.add_dock_widget(
            self._widget, name="napari-imagej REPL", area="bottom"
        )

    def _toggle_repl(self):
        """
        Toggle visibility the SciJava REPL widget.
        """
        if not self._widget:
            self._add_repl_to_dock()
        else:
            self.viewer.window.remove_dock_widget(self._widget)
            self._widget.close()
            self._widget = None


class SettingsButton(IJMenuButton):
    # Signal used to identify changes to user settings
    setting_change = Signal(bool)

    def __init__(self, viewer: Viewer):
        super().__init__(viewer)
        self.setToolTip("Show napari-imagej settings")

        self.clicked.connect(self._update_settings)
        self.setting_change.connect(self._handle_settings_change)

    def _icon(self):
        return QColoredSVGIcon(resource_path("gear"))

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
