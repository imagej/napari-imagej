"""
The top-level menu for the napari-imagej widget.
"""
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from magicgui.widgets import request_values
from napari import Viewer
from napari._qt.qt_resources import QColoredSVGIcon
from napari.layers import Layer
from napari.utils._magicgui import get_layers
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon, QPixmap
from qtpy.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QWidget
from scyjava import is_arraylike

from napari_imagej import settings
from napari_imagej.java import ij, jc, on_ij_init
from napari_imagej.resources import resource_path


class NapariImageJMenu(QWidget):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.setLayout(QHBoxLayout())
        self.layout().addStretch(0)

        self.from_ij: FromIJButton = FromIJButton(viewer)
        self.layout().addWidget(self.from_ij)

        self.to_ij: ToIJButton = ToIJButton(viewer)
        self.layout().addWidget(self.to_ij)

        self.gui_button: GUIButton = GUIButton()
        self.layout().addWidget(self.gui_button)

        self.settings_button: SettingsButton = SettingsButton(viewer)
        self.layout().addWidget(self.settings_button)

        if settings["jvm_mode"].get(str) == "headless":
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


class ToIJButton(QPushButton):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        icon = QColoredSVGIcon.from_resources("long_right_arrow")
        self.setIcon(icon.colored(theme=viewer.theme))
        if settings["use_active_layer"].get():
            self.setToolTip("Export active napari layer to ImageJ2")
            self.clicked.connect(self.send_active_layer)
        else:
            self.setToolTip("Export napari layer to ImageJ2")
            self.clicked.connect(self.send_chosen_layer)

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

    def send_active_layer(self):
        active_layer: Optional[Layer] = self.viewer.layers.selection.active
        if active_layer:
            self._show(active_layer)
        else:
            self.handle_no_choices()

    def send_chosen_layer(self):
        # Get Layer choice
        choices: dict = request_values(
            title="Send layers to ImageJ2",
            layer={"annotation": Layer, "options": {"choices": get_layers}},
        )
        # Parse choices for the layer
        if choices is None:
            self.handle_no_choices()
        else:
            layer = choices["layer"]
            if isinstance(layer, Layer):
                # Pass the relevant data to ImageJ2
                self._show(layer)

    def _show(self, layer):
        # Queue UI call on the EDT
        # TODO: Use EventQueue.invokeLater scyjava wrapper, once it exists
        ij().thread().queue(lambda: ij().ui().show(ij().py.to_java(layer)))

    def handle_no_choices(self):
        RichTextPopup(
            rich_message="There is no active window to export to ImageJ!",
            exec=True,
        )


class FromIJButton(QPushButton):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        icon = QColoredSVGIcon.from_resources("long_left_arrow")
        self.setIcon(icon.colored(theme=viewer.theme))
        if settings["use_active_layer"].get():
            self.setToolTip("Import active ImageJ2 Dataset to napari")
            self.clicked.connect(self.get_active_layer)
        else:
            self.setToolTip("Import ImageJ2 Dataset to napari")
            self.clicked.connect(self.get_chosen_layer)

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

    def _get_objects(self, t):
        compatibleInputs = ij().convert().getCompatibleInputs(t)
        compatibleInputs.addAll(ij().object().getObjects(t))
        return list(compatibleInputs)

    def get_chosen_layer(self) -> None:
        # Find all images convertible to a napari layer
        images = self._get_objects(jc.RandomAccessibleInterval)
        names = [ij().object().getName(i) for i in images]
        # Ask the user to pick one of these images by name
        choices: dict = request_values(
            title="Send layers to napari",
            data={"annotation": Enum, "options": {"choices": names}},
        )
        if choices is None:
            self.handle_no_choices
        else:
            # grab the chosen name
            name = choices["data"]
            display = ij().display().getDisplay(name)
            # if the image is displayed, convert the DatasetView
            if display:
                self._add_layer(display.get(0))
            # Otherwise, just convert the object
            else:
                image = images[names.index(name)]
                self._add_layer(image)

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


class GUIButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.setEnabled(False)

        if settings["jvm_mode"].get(str) == "headless":
            self._setup_headless()
        else:
            self._setup_headful()

    def _set_icon(self, path: str):
        icon: QIcon = QIcon(QPixmap(path))
        self.setIcon(icon)

        def finalize(ij: "jc.ImageJ"):
            self.setEnabled(True)

        on_ij_init(finalize)

    def _setup_headful(self):
        self._set_icon(resource_path("imagej2-16x16-flat-disabled"))
        self.setToolTip("Display ImageJ2 GUI (loading)")

        def finalize(ij: "jc.ImageJ"):
            self._set_icon(resource_path("imagej2-16x16-flat"))
            self.setEnabled(True)
            self.setToolTip("Display ImageJ2 GUI")

        on_ij_init(finalize)

    def _setup_headless(self):
        self._set_icon(resource_path("imagej2-16x16-flat-disabled"))
        self.setToolTip("ImageJ2 GUI unavailable!")

    def disable_popup(self):
        RichTextPopup(
            rich_message="The ImageJ2 user interface cannot be opened "
            "when running PyImageJ headlessly. Visit "
            '<a href="https://pyimagej.readthedocs.io/en/latest/'
            'Initialization.html#interactive-mode">this site</a> '
            "for more information.",
            exec=True,
        )


class SettingsButton(QPushButton):
    # Signal used to identify changes to user settings
    setting_change = Signal()

    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        icon = QColoredSVGIcon(resource_path("gear"))
        self.setIcon(icon.colored(theme=viewer.theme))

        self.clicked.connect(self._update_settings)
        self.setting_change.connect(self._notify_settings_change)
        self.setting_change.connect(self._write_settings)

    def _update_settings(self):
        """
        Spawns a popup allowing the user to configure napari-imagej settings.
        """
        args = {}
        # Build values map by iterating over all default settings.
        # NB grabbing settings and defaults has two benefits. Firstly, it
        # ensures that settings ALWAYS appear in the order described in
        # config-default.yaml. Secondly, it ensures that tampering with any user
        # setting files does not add settings to this popup that don't exist in
        # the default file
        default_source = next((s for s in settings.sources if s.default), None)
        if not default_source:
            raise ValueError(
                "napari-imagej settings does not contain a default source!"
            )
        for setting in default_source:
            self._register_setting_param(args, setting)
        # Use magicgui.request_values to allow user to configure settings
        choices = request_values(title="napari-imagej Settings", values=args)
        if choices is not None:
            # Update settings with user selections
            any_changed = False
            for setting, value in choices.items():
                any_changed |= self._apply_setting_param(setting, value)

            if any_changed:
                self.setting_change.emit()

    def _register_setting_param(self, args: Dict[Any, Any], setting: str):
        # General: Set name, and current value as default
        args[setting] = dict(value=settings[setting].get())

        # Setting specific additions
        if setting == "jvm_mode":
            args[setting]["options"] = dict(choices=["headless", "interactive"])
        if setting == "imagej_base_directory":
            args[setting]["annotation"] = Path
            args[setting]["value"] = settings[setting].as_path()
            args[setting]["options"] = dict(mode="d")

    def _apply_setting_param(self, setting: str, value: Any) -> bool:
        """
        Sets setting to value, and returns true iff value is different from before
        """
        # First, any postprocessing
        if isinstance(value, Path):
            value = str(value)

        # Then, validate the new value
        try:
            settings._validate_setting(setting, value)
        except Exception as exc:
            # New value incompatible; report it to the user
            RichTextPopup(
                rich_message=(
                    "<b>Ignoring selection for setting <font face='courier'>"
                    f"{setting}"
                    f"</font>:</b><p>{exc}"
                ),
                exec=True,
            )
            return False

        # Record the old value
        original = settings[setting].get()
        # Set the new value
        settings[setting] = value

        # Report a change in value
        return original != value

    def _notify_settings_change(self):
        """
        Notifies (using a popup) that a restart is required for settings changes
        to take effect
        """
        RichTextPopup(
            rich_message="Please restart napari for napari-imagej settings "
            "changes to take effect!",
            exec=True,
        )

    def _write_settings(self):
        """
        Writes settings to a local configuration YAML file
        """
        output = settings.dump()
        with open(settings.user_config_path(), "w") as f:
            f.write(output)


class RichTextPopup(QMessageBox):
    """A helper widget for creating (and immediately displaying) popups"""

    def __init__(self, rich_message: str, exec: bool = False):
        super().__init__()
        self.setText(rich_message)
        self.setTextFormat(Qt.RichText)
        self.setTextInteractionFlags(Qt.TextBrowserInteraction)
        if exec:
            self.exec()
