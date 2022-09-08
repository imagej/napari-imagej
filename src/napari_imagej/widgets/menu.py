"""
The top-level menu for the napari-imagej widget.
"""
from enum import Enum
from threading import Thread
from typing import Optional

from jpype import JImplements, JOverride
from magicgui.widgets import request_values
from napari import Viewer
from napari._qt.qt_resources import QColoredSVGIcon
from napari.layers import Layer
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon, QPixmap
from qtpy.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QWidget

from napari_imagej import settings
from napari_imagej.java import ensure_jvm_started, ij, jc, log_debug, running_headless
from napari_imagej.utilities._module_utils import _get_layers_hack
from napari_imagej.widgets.resources import resource_path


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

        if running_headless():
            self.gui_button.clicked.connect(self.gui_button.disable_popup)
        else:
            self.gui_button.clicked.connect(self._showUI)
            self.gui_button.clicked.connect(lambda: self.to_ij.setEnabled(True))
            self.gui_button.clicked.connect(lambda: self.from_ij.setEnabled(True))

    @property
    def gui(self) -> "jc.UserInterface":
        """Convenience function for obtaining the default UserInterface"""
        ensure_jvm_started()
        return ij().ui().getDefaultUI()

    def _showUI(self):
        """
        NB: This must be its own function to prevent premature calling of ij()
        """
        ensure_jvm_started()
        # First time showing
        if not self.gui.isVisible():
            # First things first, show the GUI
            ij().ui().showUI(self.gui)
            # Then, add our custom settings to the User Interface
            if ij().legacy and ij().legacy.isActive():
                self._ij1_UI_setup()
            else:
                self._ij2_UI_setup()
        # Later shows - the GUI is "visible", but the appFrame probably isn't
        else:
            self.gui.getApplicationFrame().setVisible(True)

    def _ij1_UI_setup(self):
        """Configures the ImageJ Legacy GUI"""
        ij().IJ.getInstance().exitWhenQuitting(False)

    def _ij2_UI_setup(self):
        """Configures the ImageJ2 Swing GUI"""
        appFrame = self.gui.getApplicationFrame()
        # Overwrite the WindowListeners so we control closing behavior
        if isinstance(appFrame, jc.Window):
            self._kill_window_listeners(appFrame)
        elif isinstance(appFrame, jc.UIComponent):
            self._kill_window_listeners(appFrame.getComponent())

    def _kill_window_listeners(self, window):
        """Replaces the WindowListeners present on window with our own"""
        # Remove all preset WindowListeners
        for listener in window.getWindowListeners():
            window.removeWindowListener(listener)

        # Add our own behavior for WindowEvents
        @JImplements("java.awt.event.WindowListener")
        class NapariAdapter(object):
            @JOverride
            def windowOpened(self, event):
                pass

            @JOverride
            def windowClosing(self, event):
                # We don't want to shut down anything, we just want to hide the window.
                window.setVisible(False)

            @JOverride
            def windowClosed(self, event):
                pass

            @JOverride
            def windowIconified(self, event):
                pass

            @JOverride
            def windowDeiconified(self, event):
                pass

            @JOverride
            def windowActivated(self, event):
                pass

            @JOverride
            def windowDeactivated(self, event):
                pass

        window.addWindowListener(NapariAdapter())


class ToIJButton(QPushButton):
    def __init__(self, viewer: Viewer):
        super().__init__()
        self.viewer = viewer

        self.setEnabled(False)
        icon = QColoredSVGIcon.from_resources("long_right_arrow")
        self.setIcon(icon.colored(theme=viewer.theme))
        if settings["choose_active_layer"].get():
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
            name = active_layer.name
            data = ij().py.to_java(active_layer.data)
            ij().ui().show(name, data)
        else:
            log_debug("There is no active layer to export to ImageJ2")

    def send_chosen_layer(self):
        # Get Layer choice
        # TODO: Once napari > 0.4.16 is released, replace _get_layers_hack with
        # napari.util._magicgui.get_layers
        choices: dict = request_values(
            title="Send layers to ImageJ2",
            layer={"annotation": Layer, "options": {"choices": _get_layers_hack}},
        )
        # Parse choices for the layer
        if choices is not None:
            layer = choices["layer"]
            if isinstance(layer, Layer):
                # Pass the relevant data to ImageJ2
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
        if settings["choose_active_layer"].get():
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
        if choices is not None:
            # grab the chosen name
            name = choices["data"]
            # grab the chosen image
            i = names.index(name)
            image = ij().py.from_java(images[i])
            # if the conversion is already a layer, add it directly
            if isinstance(image, Layer):
                image.name = name
                self.viewer.add_layer(image)
            # otherwise, try to coerce it into an Image layer
            elif ij().py._is_arraylike(image):
                self.viewer.add_image(data=image, name=name)
            # if we can't coerce it, give up
            else:
                raise ValueError(f"{image} cannot be displayed in napari!")

    def get_active_layer(self) -> None:
        # Choose the active Dataset
        image = ij().get("net.imagej.display.ImageDisplayService").getActiveDataset()
        if image is None:
            log_debug("There is no active window to export to napari")
            return
        # Get the stuff needed for a new layer
        py_image = ij().py.from_java(image)
        name = ij().object().getName(image)
        # Create and add the layer
        if isinstance(py_image, Layer):
            py_image.name = name
            self.viewer.add_layer(py_image)
        elif ij().py._is_arraylike(py_image):
            self.viewer.add_image(data=py_image, name=name)
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

        def post_setup():
            ensure_jvm_started()
            self.setEnabled(True)

        Thread(target=post_setup).start()

    def _setup_headful(self):
        self._set_icon(resource_path("imagej2-16x16-flat-disabled"))
        self.setToolTip("Display ImageJ2 GUI (loading)")

        def post_setup():
            ensure_jvm_started()
            self._set_icon(resource_path("imagej2-16x16-flat"))
            self.setEnabled(True)
            self.setToolTip("Display ImageJ2 GUI")

        Thread(target=post_setup).start()

    def _setup_headless(self):
        self._set_icon(resource_path("imagej2-16x16-flat-disabled"))
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
        args = {}
        default_source = next(s for s in settings.sources if s.default)
        for k, v in default_source.items():
            args[k] = {}
            args[k]["value"] = settings[k].get()
        choices = request_values(title="napari-imagej Settings", values=args)
        if choices is not None:
            any_changed = False
            for k, v in choices.items():
                if v != settings[k].get():
                    any_changed = True
                    settings[k] = v

            if any_changed:
                self.setting_change.emit()

    def _notify_settings_change(self):
        """
        Notifies (using a popup) that a restart is required for settings changes
        to take effect
        """
        msg: QMessageBox = QMessageBox()
        msg.setText(
            "Please restart napari for napari-imagej settings changes to take effect!"
        )
        msg.exec()

    def _write_settings(self):
        """
        Writes settings to a local configuration YAML file
        """
        output = settings.dump()
        with open(settings.user_config_path(), "w") as f:
            f.write(output)
