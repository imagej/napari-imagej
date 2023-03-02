"""
A module testing napari_imagej.widgets.menu
"""

import sys
from typing import Callable

import numpy
import pytest
import yaml
from napari import Viewer
from napari.layers import Image, Layer
from napari.viewer import current_viewer
from qtpy.QtCore import QRunnable, Qt, QThreadPool
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QApplication, QHBoxLayout, QMessageBox

from napari_imagej import settings
from napari_imagej.resources import resource_path
from napari_imagej.widgets import menu
from napari_imagej.widgets.menu import (
    FromIJButton,
    GUIButton,
    NapariImageJMenu,
    RichTextPopup,
    SettingsButton,
    ToIJButton,
)
from tests.utils import jc

# Determine whether we are testing headlessly
TESTING_HEADLESS: bool = settings["jvm_mode"].get(str) == "headless"


@pytest.fixture(autouse=True)
def napari_mocker(viewer: Viewer):
    """Fixture allowing the mocking of napari utilities"""

    # REQUEST_VALUES MOCK
    oldfunc = menu.request_values

    def newfunc(values={}, title="", **kwargs):
        values.update(kwargs)
        results = {}
        # Solve each parameter
        for name, options in kwargs.items():
            if "value" in options:
                results[name] = options["value"]
                continue
            if "choices" in options["options"]:
                if options["annotation"] == Layer:
                    results[name] = viewer.layers[0]
                else:
                    choices = options["options"]["choices"]
                    results[name] = choices[0]

                continue

            # Otherwise, we don't know how to solve that parameter
            raise NotImplementedError()
        return results

    menu.request_values = newfunc

    yield

    menu.request_values = oldfunc


@pytest.fixture()
def popup_handler(asserter) -> Callable[[str, Callable[[], None]], None]:
    """Fixture used to handle RichTextPopups"""

    def handle_popup(text: str, popup_generator: Callable[[], None]):
        # # Start the handler in a new thread
        class Handler(QRunnable):
            # Test popup when running headlessly
            def run(self) -> None:
                asserter(lambda: isinstance(QApplication.activeWindow(), RichTextPopup))
                msg = QApplication.activeWindow()
                if text != msg.text():
                    self._passed = False
                    return
                if Qt.RichText != msg.textFormat():
                    self._passed = False
                    return
                if Qt.TextBrowserInteraction != msg.textInteractionFlags():
                    self._passed = False
                    return

                ok_button = msg.button(QMessageBox.Ok)
                ok_button.clicked.emit()
                asserter(lambda: QApplication.activeModalWidget() is not msg)
                self._passed = True

            def passed(self) -> bool:
                return self._passed

        runnable = Handler()
        QThreadPool.globalInstance().start(runnable)

        # Click the button
        popup_generator()
        # Wait for the popup to be handled
        asserter(QThreadPool.globalInstance().waitForDone)
        assert runnable.passed()

    return handle_popup


@pytest.fixture(autouse=True)
def clean_layers_and_Displays(asserter, ij, viewer: Viewer):
    """Fixture to remove image data from napari and ImageJ2"""

    # Test pre-processing

    # Test processing
    yield

    # Test post-processing

    # After each test runs, clear all layers from napari
    if viewer is not None:
        viewer.layers.clear()

    # After each test runs, clear all displays from ImageJ2
    while ij.display().getActiveDisplay() is not None:
        current_display = ij.display().getActiveDisplay()
        current_display.close()
        asserter(lambda: ij.display().getActiveDisplay() is not current_display)

    # After each test runs, clear all ImagePlus objects from ImageJ
    if ij.legacy and ij.legacy.isActive():
        while ij.WindowManager.getCurrentImage():
            imp = ij.WindowManager.getCurrentImage()
            imp.changes = False
            imp.close()


def test_widget_layout(gui_widget: NapariImageJMenu):
    """Tests the number and expected order of imagej_widget children"""
    subwidgets = gui_widget.children()
    assert len(subwidgets) == 5
    assert isinstance(subwidgets[0], QHBoxLayout)

    assert isinstance(subwidgets[1], FromIJButton)
    assert not subwidgets[1].isEnabled()

    assert isinstance(subwidgets[2], ToIJButton)
    assert not subwidgets[2].isEnabled()

    assert isinstance(subwidgets[3], GUIButton)

    assert isinstance(subwidgets[4], SettingsButton)


@pytest.mark.skipif(TESTING_HEADLESS, reason="Only applies when not running headlessly")
def test_GUIButton_layout_headful(qtbot, asserter, ij, gui_widget: NapariImageJMenu):
    """Tests headful-specific settings of GUIButton"""
    button: GUIButton = gui_widget.gui_button

    expected: QPixmap = QPixmap(resource_path("imagej2-16x16-flat"))
    actual: QPixmap = button.icon().pixmap(expected.size())
    assert expected.toImage() == actual.toImage()

    assert "" == button.text()

    # Sometimes ImageJ2 can take a little while to be ready
    expected_toolTip = "Display ImageJ2 GUI"
    asserter(lambda: expected_toolTip == button.toolTip())

    # Test showing UI
    assert not ij.ui().isVisible()
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)
    asserter(ij.ui().isVisible)


@pytest.mark.skipif(not TESTING_HEADLESS, reason="Only applies when running headlessly")
def test_GUIButton_layout_headless(popup_handler, gui_widget: NapariImageJMenu):
    """Tests headless-specific settings of GUIButton"""
    # Wait until the JVM starts to test settings
    button: GUIButton = gui_widget.gui_button

    expected: QPixmap = QPixmap(resource_path("imagej2-16x16-flat-disabled"))
    actual: QPixmap = button.icon().pixmap(expected.size())
    assert expected.toImage() == actual.toImage()

    assert "" == button.text()

    expected_text = "ImageJ2 GUI unavailable!"
    assert expected_text == button.toolTip()

    expected_popup_text = (
        "The ImageJ2 user interface cannot be opened "
        "when running PyImageJ headlessly. Visit "
        '<a href="https://pyimagej.readthedocs.io/en/latest/'
        'Initialization.html#interactive-mode">this site</a> '
        "for more information."
    )
    popup_handler(expected_popup_text, button.clicked.emit)


@pytest.mark.skipif(TESTING_HEADLESS, reason="Only applies when not running headlessly")
def test_active_data_send(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    button: ToIJButton = gui_widget.to_ij
    assert not button.isEnabled()

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    asserter(lambda: button.isEnabled())

    # Add some data to the viewer
    sample_data = numpy.ones((100, 100, 3))
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)

    # Press the button, handle the Dialog
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)

    # Assert that the data is now in Fiji
    def check_active_display():
        if not ij.display().getActiveDisplay():
            return False
        return ij.display().getActiveDisplay().getName() == "test_to"

    asserter(check_active_display)


@pytest.mark.skipif(TESTING_HEADLESS, reason="Only applies when not running headlessly")
def test_active_data_receive(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    button: FromIJButton = gui_widget.from_ij
    assert not button.isEnabled()

    # Show the button
    gui_widget.gui_button.clicked.emit()
    asserter(lambda: button.isEnabled())

    # Add some data to ImageJ
    sample_data = jc.ArrayImgs.bytes(10, 10, 10)
    ij.ui().show("test_from", sample_data)
    asserter(lambda: ij.display().getActiveDisplay() is not None)

    # Press the button, handle the Dialog
    assert 0 == len(button.viewer.layers)
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)

    # Assert that the data is now in napari
    asserter(lambda: 1 == len(button.viewer.layers))
    layer = button.viewer.layers[0]
    assert isinstance(layer, Image)
    assert (10, 10, 10) == layer.data.shape


@pytest.mark.skipif(TESTING_HEADLESS, reason="Only applies when not running headlessly")
def test_data_choosers(asserter, qtbot, ij, gui_widget_chooser):
    button_to: ToIJButton = gui_widget_chooser.to_ij
    button_from: FromIJButton = gui_widget_chooser.from_ij
    assert not button_to.isEnabled()
    assert not button_from.isEnabled()

    # Show the button
    qtbot.mouseClick(gui_widget_chooser.gui_button, Qt.LeftButton, delay=1)
    asserter(button_to.isEnabled)
    asserter(button_from.isEnabled)

    # Add a layer
    sample_data = numpy.ones((100, 100, 3))
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)

    # Use the chooser to transfer data to ImageJ2
    button_to.clicked.emit()

    # Assert that the data is now in ImageJ2
    asserter(lambda: isinstance(ij.display().getDisplay("test_to"), jc.ImageDisplay))

    # Use the chooser to transfer that data back
    button_from.clicked.emit()

    # Assert that the data is now in napari
    asserter(lambda: 2 == len(button_to.viewer.layers))


def test_settings_no_change(gui_widget: NapariImageJMenu):
    """Ensure that no changes are made when there is no change from the defaults"""
    button: SettingsButton = gui_widget.settings_button

    # First record the old settings
    old_yaml = [(k, v.get()) for k, v in settings.items()]

    # Then update the settings, but select all defaults
    # NB settings handling is done by napari_mocker above
    button._update_settings()
    # Then record the new settings and compare
    new_yaml = [(k, v.get()) for k, v in settings.items()]
    assert new_yaml == old_yaml


def test_settings_change(popup_handler, gui_widget: NapariImageJMenu):
    """Change imagej_directory_or_endpoint and ensure that the settings change"""
    button: SettingsButton = gui_widget.settings_button

    # REQUEST_VALUES MOCK
    oldfunc = menu.request_values

    key = "imagej_directory_or_endpoint"
    old_value = settings[key]
    new_value = "foo"

    assert old_value != new_value

    def newfunc(values={}, title="", **kwargs):
        results = {}
        # Solve each parameter
        for name, options in values.items():
            if name == "imagej_directory_or_endpoint":
                results[name] = new_value
                continue
            elif "value" in options:
                results[name] = options["value"]
                continue

            # Otherwise, we don't know how to solve that parameter
            raise NotImplementedError()
        return results

    menu.request_values = newfunc

    # Handle the popup from button._update_settings
    expected_text = (
        "Please restart napari for napari-imagej settings " "changes to take effect!"
    )
    popup_handler(expected_text, button._update_settings)

    menu.request_values = oldfunc

    # Assert a change in the settings
    assert settings[key].get() == new_value
    with open(settings.user_config_path(), "r") as stream:
        assert yaml.safe_load(stream)[key] == new_value


def test_empty_ij_dir_str_prevention(popup_handler, gui_widget: NapariImageJMenu):
    """Change ij_dir_or_endpoint to an empty string, assert that it cannot be done"""
    button: SettingsButton = gui_widget.settings_button

    # REQUEST_VALUES MOCK
    oldfunc = menu.request_values

    assert settings["imagej_directory_or_endpoint"].get() == "net.imagej:imagej"

    def newfunc(values={}, title="", **kwargs):
        results = {}
        # Solve each parameter
        for name, options in values.items():
            if name == "imagej_directory_or_endpoint":
                results[name] = ""
                continue
            elif "value" in options:
                results[name] = options["value"]
                continue

            # Otherwise, we don't know how to solve that parameter
            raise NotImplementedError()
        return results

    menu.request_values = newfunc

    # Handle the popup from button._update_settings
    expected_text = (
        "<b>Ignoring selection for setting "
        "<font face='courier'>imagej_directory_or_endpoint</font>:</b><p>"
        "The imagej directory or endpoint cannot be blank! "
        "<p><font face='courier'>net.imagej:imagej</font> "
        "is the default option."
        "<p>Visit "
        '<a href="https://pyimagej.readthedocs.io/en/latest/'
        'api.html#initialization">this site</a> '
        "and check the "
        "<font face='courier'>ij_dir_or_version_or_endpoint</font> "
        "parameter for more options."
    )
    popup_handler(expected_text, button._update_settings)

    menu.request_values = oldfunc

    # Assert no change in the settings
    assert settings["imagej_directory_or_endpoint"].get() == "net.imagej:imagej"


@pytest.mark.skipif(sys.platform != "darwin", reason="Only applies testing on MacOS")
def test_jvm_mode_change_prevention(popup_handler, gui_widget: NapariImageJMenu):
    """Change jvm_mode on mac from headless to interactive, ensure that is prevented"""
    button: SettingsButton = gui_widget.settings_button

    # REQUEST_VALUES MOCK
    oldfunc = menu.request_values

    assert settings["jvm_mode"].get() == "headless"

    def newfunc(values={}, title="", **kwargs):
        results = {}
        # Solve each parameter
        for name, options in values.items():
            if name == "jvm_mode":
                results[name] = "interactive"
                continue
            elif "value" in options:
                results[name] = options["value"]
                continue

            # Otherwise, we don't know how to solve that parameter
            raise NotImplementedError()
        return results

    menu.request_values = newfunc

    # Handle the popup from button._update_settings
    expected_text = (
        "<b>Ignoring selection for setting "
        "<font face='courier'>jvm_mode</font>:</b><p>"
        "ImageJ2 must be run headlessly on MacOS. <p>Visit "
        '<a href="https://pyimagej.readthedocs.io/en/latest/'
        'Initialization.html#interactive-mode">this site</a> '
        "for more information."
    )
    popup_handler(expected_text, button._update_settings)

    menu.request_values = oldfunc

    # Assert no change in the settings
    assert settings["jvm_mode"].get() == "headless"


@pytest.mark.skipif(TESTING_HEADLESS, reason="Only applies when not running headlessly")
@pytest.mark.skipif(
    not settings["include_imagej_legacy"].get(bool), reason="Tests legacy behavior"
)
def test_modification_in_imagej(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    to_button: ToIJButton = gui_widget.to_ij
    from_button: FromIJButton = gui_widget.from_ij

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)

    # Add some data to the viewer
    sample_data = numpy.ones((100, 100, 3), dtype=numpy.uint8)
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)

    # Press the button, handle the Dialog
    qtbot.mouseClick(to_button, Qt.LeftButton, delay=1)

    # Assert that the data is in the legacy UI
    asserter(lambda: ij.WindowManager.getCurrentImage() is not None)
    imp = ij.WindowManager.getCurrentImage()
    assert imp.getTitle() == "test_to"
    # Edit the data
    imp.getProcessor().invert()
    imp.updateAndDraw()

    # Press the button, handle the Dialog
    qtbot.mouseClick(from_button, Qt.LeftButton, delay=1)

    # Assert the returned data is inverted
    asserter(lambda: "test_to [1]" in current_viewer().layers)
    modified_layer = current_viewer().layers["test_to [1]"].data
    assert numpy.all(modified_layer[0, :, :] == 254)
    # NB the original ImageJ only inverts the active slice;
    # all other layers are the same.
    assert numpy.all(modified_layer[1:, :, :] == 1)


@pytest.mark.skipif(TESTING_HEADLESS, reason="Only applies when not running headlessly")
@pytest.mark.skipif(
    not settings["include_imagej_legacy"].get(bool), reason="Tests legacy behavior"
)
def test_image_plus_to_napari(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    from_button: FromIJButton = gui_widget.from_ij

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)

    # Add some data to ImageJ Legacy
    asserter(lambda: ij.WindowManager.getCurrentImage() is None)
    ij.IJ.runPlugIn("ij.plugin.URLOpener", "blobs.gif")
    asserter(lambda: ij.WindowManager.getCurrentImage() is not None)
    imp = ij.WindowManager.getCurrentImage()
    assert imp.getTitle() == "blobs.gif"

    # Press the button, handle the Dialog
    qtbot.mouseClick(from_button, Qt.LeftButton, delay=1)

    # Assert the data is in napari
    asserter(lambda: "blobs.gif" in current_viewer().layers)


@pytest.mark.skipif(TESTING_HEADLESS, reason="Only applies when not running headlessly")
def test_opening_and_closing_gui(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    # Open the GUI
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    # Wait for the Frame to be created
    asserter(lambda: gui_widget._get_AWT_frame() is not None)
    frame = gui_widget._get_AWT_frame()
    # Wait for the Frame to be visible
    asserter(lambda: frame.isVisible())

    # Close the GUI
    ij.thread().queue(
        lambda: frame.dispatchEvent(
            jc.WindowEvent(frame, jc.WindowEvent.WINDOW_CLOSING)
        )
    )
    # Wait for the Frame to be hidden
    asserter(lambda: not frame.isVisible())

    # Open the GUI again
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    # Wait for the Frame to be visible again
    asserter(lambda: frame.isVisible())
