"""
A module testing napari_imagej.widgets.menu
"""


import numpy
import pytest
from napari import Viewer
from napari.layers import Image, Layer
from napari.viewer import current_viewer
from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QHBoxLayout, QMessageBox

from napari_imagej import settings
from napari_imagej.resources import resource_path
from napari_imagej.widgets import menu
from napari_imagej.widgets.menu import (
    FromIJButton,
    GUIButton,
    NapariImageJMenu,
    SettingsButton,
    ToIJButton,
)
from napari_imagej.widgets.widget_utils import _run_actions_for
from tests.utils import DummySearchResult, jc


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


def ui_visible(ij):
    frame = ij.ui().getDefaultUI().getApplicationFrame()
    if isinstance(frame, jc.UIComponent):
        frame = frame.getComponent()
    return frame and frame.isVisible()


@pytest.fixture(autouse=True)
def clean_gui_elements(asserter, ij, viewer: Viewer):
    """Fixture to remove image data from napari and ImageJ2"""

    # Test pre-processing

    # Test processing
    yield

    # Test post-processing

    # After each test runs, clear all layers from napari
    if viewer is not None:
        viewer.layers.clear()

    # After each test runs, clear all ImagePlus objects from ImageJ
    if ij.legacy and ij.legacy.isActive():
        while ij.WindowManager.getCurrentImage():
            imp = ij.WindowManager.getCurrentImage()
            imp.changes = False
            imp.close()

    # After each test runs, clear all displays from ImageJ2
    while not ij.display().getDisplays().isEmpty():
        for display in ij.display().getDisplays():
            display.close()

    # Close the UI if needed
    if ui_visible(ij):
        frame = ij.ui().getDefaultUI().getApplicationFrame()
        if isinstance(frame, jc.UIComponent):
            frame = frame.getComponent()
        ij.thread().queue(
            lambda: frame.dispatchEvent(
                jc.WindowEvent(frame, jc.WindowEvent.WINDOW_CLOSING)
            )
        )
        # Wait for the Frame to be hidden
        asserter(lambda: not ui_visible(ij))


def test_widget_layout(gui_widget: NapariImageJMenu):
    """Tests the number and expected order of imagej_widget children"""
    subwidgets = gui_widget.children()
    assert len(subwidgets) == 5
    assert isinstance(subwidgets[0], QHBoxLayout)

    assert isinstance(subwidgets[1], FromIJButton)
    assert isinstance(subwidgets[2], ToIJButton)
    assert isinstance(subwidgets[3], GUIButton)
    assert isinstance(subwidgets[4], SettingsButton)


def test_GUIButton_layout_headful(qtbot, asserter, ij, gui_widget: NapariImageJMenu):
    """Tests headful-specific settings of GUIButton"""
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")

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


def test_GUIButton_layout_headless(popup_handler, gui_widget: NapariImageJMenu):
    """Tests headless-specific settings of GUIButton"""
    if not settings.headless():
        pytest.skip("Only applies when running headlessly")
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
    popup_handler(expected_popup_text, True, QMessageBox.Ok, button.clicked.emit)


def test_active_data_send(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")
    if settings.include_imagej_legacy:
        pytest.skip(
            """HACK: Disabled with ImageJ legacy.
    See https://github.com/imagej/napari-imagej/issues/181
            """
        )

    button: ToIJButton = gui_widget.to_ij
    assert button.isEnabled()

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


def test_active_data_receive(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")
    if settings.include_imagej_legacy:
        pytest.skip(
            """HACK: Disabled with ImageJ legacy.
    See https://github.com/imagej/napari-imagej/issues/181
            """
        )

    button: FromIJButton = gui_widget.from_ij
    assert button.isEnabled()

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


def test_data_choosers(asserter, qtbot, ij, gui_widget_chooser):
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")

    button_to: ToIJButton = gui_widget_chooser.to_ij
    button_from: FromIJButton = gui_widget_chooser.from_ij
    assert button_to.isEnabled()
    assert button_from.isEnabled()

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
    old_settings = settings.asdict()

    # Then update the settings, but select all defaults
    # NB settings handling is done by napari_mocker above
    button._update_settings()
    # Then record the new settings and compare
    new_settings = settings.asdict()
    assert new_settings == old_settings


def test_settings_change(popup_handler, gui_widget: NapariImageJMenu):
    """Change imagej_directory_or_endpoint and ensure that the settings change"""
    button: SettingsButton = gui_widget.settings_button

    # HACK - pretend we aren't on Mac - to avoid extra modal dialogs
    settings._is_macos = False

    # REQUEST_VALUES MOCK
    original_request_values = menu.request_values

    old_value = settings.imagej_directory_or_endpoint
    new_value = "foo"

    assert old_value != new_value

    def provide_updated_values(values={}, title="", **kwargs):
        return {
            name: new_value
            if name == "imagej_directory_or_endpoint"
            else settings.defaults[name]
            for name in values
        }

    menu.request_values = provide_updated_values

    # Handle the popup from button._update_settings
    expected_text = (
        "Please restart napari for napari-imagej settings changes to take effect!"
    )
    popup_handler(expected_text, True, QMessageBox.Ok, button._update_settings)
    assert settings.imagej_directory_or_endpoint == new_value

    menu.request_values = original_request_values


def test_modification_in_imagej(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")
    if not settings.include_imagej_legacy:
        pytest.skip("Tests legacy behavior")

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


def test_image_plus_to_napari(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")
    if not settings.include_imagej_legacy:
        pytest.skip("Tests legacy behavior")

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


def test_opening_and_closing_gui(asserter, qtbot, ij, gui_widget: NapariImageJMenu):
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")

    # Open the GUI
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    frame = ij.ui().getDefaultUI().getApplicationFrame()
    if isinstance(frame, jc.UIComponent):
        frame = frame.getComponent()
    # Wait for the Frame to be visible
    asserter(lambda: ui_visible(ij))

    # Close the GUI
    ij.thread().queue(
        lambda: frame.dispatchEvent(
            jc.WindowEvent(frame, jc.WindowEvent.WINDOW_CLOSING)
        )
    )
    # Wait for the Frame to be hidden
    asserter(lambda: not ui_visible(ij))

    # Open the GUI again
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    # Wait for the Frame to be visible again
    asserter(lambda: ui_visible(ij))


@pytest.fixture
def legacy_module(ij):
    info = ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )
    return ij.module().createModule(info)


def test_legacy_directed_to_ij_ui(ij, popup_handler, gui_widget: NapariImageJMenu):
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")
    if not settings.include_imagej_legacy:
        pytest.skip("Tests legacy behavior")
    info = ij.module().getModuleById("legacy:ij.plugin.filter.GaussianBlur")
    actions = _run_actions_for(DummySearchResult(info), None, gui_widget)

    expected_popup_text = (
        '"This is not a Search Result" is an original ImageJ PlugIn'
        " and should be run from the ImageJ UI."
        " Would you like to launch the ImageJ UI?"
    )
    popup_handler(expected_popup_text, False, QMessageBox.No, actions[0][1])
    assert not ui_visible(ij)

    popup_handler(expected_popup_text, False, QMessageBox.Yes, actions[0][1])
    assert ui_visible(ij)
