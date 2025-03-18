"""
A module testing napari_imagej.widgets.menu
"""

from typing import Callable

import numpy
import pytest
from napari import Viewer
from napari.layers import Image, Layer, Shapes
from napari.viewer import current_viewer
from qtpy.QtCore import QRunnable, Qt, QThreadPool
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QMessageBox,
)
from xarray import DataArray

from napari_imagej import settings
from napari_imagej.resources import resource_path
from napari_imagej.widgets import menu
from napari_imagej.widgets.menu import (
    DetailExportDialog,
    FromIJButton,
    GUIButton,
    NapariImageJMenu,
    REPLButton,
    SettingsButton,
    ToIJButton,
    ToIJDetailedButton,
)
from napari_imagej.widgets.widget_utils import DimsComboBox, _run_actions_for
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


@pytest.fixture()
def popup_handler(asserter) -> Callable[[str, Callable[[], None]], None]:
    """Fixture used to handle RichTextPopups"""

    def handle_popup(
        popup_generator: Callable[[], None], popup_handler: Callable[[QDialog], bool]
    ):
        # # Start the handler in a new thread
        class Handler(QRunnable):
            # Test popup when running headlessly
            def run(self) -> None:
                asserter(lambda: isinstance(QApplication.activeWindow(), QDialog))
                widget = QApplication.activeWindow()
                self._passed = popup_handler(widget)
                asserter(lambda: QApplication.activeModalWidget() is not widget)

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


def _handle_QMessageBox(text: str, button_type: str, is_rich: bool):
    def handle(widget: QDialog) -> bool:
        if not isinstance(widget, QMessageBox):
            return False
        if text != widget.text():
            print("Text differed")
            print(text)
            print(widget.text())
            return False
        if is_rich and Qt.RichText != widget.textFormat():
            print("Not rich text")
            return False
        if is_rich and Qt.TextBrowserInteraction != widget.textInteractionFlags():
            print("No browser interaction")
            return False

        ok_button = widget.button(button_type)
        ok_button.clicked.emit()
        return True

    return handle


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
    assert len(subwidgets) == 7
    assert isinstance(subwidgets[0], QHBoxLayout)

    assert isinstance(subwidgets[1], FromIJButton)
    assert isinstance(subwidgets[2], ToIJButton)
    assert isinstance(subwidgets[3], ToIJDetailedButton)
    assert isinstance(subwidgets[4], GUIButton)
    assert isinstance(subwidgets[5], REPLButton)
    assert isinstance(subwidgets[6], SettingsButton)


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
    expected_toolTip = "Display ImageJ2 UI"
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
    popup_func = _handle_QMessageBox(expected_popup_text, QMessageBox.Ok, True)
    popup_handler(button.clicked.emit, popup_func)


def test_script_repl(asserter, qtbot, ij, viewer: Viewer, gui_widget: NapariImageJMenu):
    repl_button = gui_widget.repl_button

    # Press the button - ensure the script repl appears as a dock widget
    qtbot.mouseClick(repl_button, Qt.LeftButton, delay=1)

    # the Viewer gives us no (public) API to query dock widgets,
    # so the best we can do is to ensure that the parent is set on our widget
    def find_repl() -> bool:
        return repl_button._widget.parent() is not None

    asserter(find_repl)


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
    assert not button.isEnabled()

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    # Add some data to the viewer
    sample_data = numpy.ones((100, 100, 3))
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)
    asserter(lambda: button.isEnabled())

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


def test_advanced_data_transfer(
    popup_handler, asserter, ij, gui_widget: NapariImageJMenu
):
    """Tests the detailed image exporter"""
    if settings.headless():
        pytest.skip("Only applies when not running headlessly")

    button: ToIJDetailedButton = gui_widget.to_ij_detail
    assert not button.isEnabled()

    # Add an image to the viewer
    sample_data = numpy.ones((50, 100, 3), dtype=numpy.uint8)
    # NB: Unnatural data order used for testing in handler
    dims = ("X", "Y", "Z")
    sample_data = DataArray(data=sample_data, dims=dims)
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)
    asserter(lambda: button.isEnabled())

    # Add some rois to the viewer
    sample_data = numpy.zeros((2, 2))
    sample_data[1, :] = 2
    shapes = Shapes(name="test_shapes")
    shapes.add_rectangles(sample_data)
    current_viewer().add_layer(shapes)

    def handle_transfer(widget: QDialog) -> bool:
        if not isinstance(widget, DetailExportDialog):
            print("Not an AdvancedExportDialog")
            return False
        if not widget.img_container.combo.currentText() == "test_to":
            print(widget.img_container.combo.currentText())
            print("Unexpected starting image text")
            return False
        if not widget.roi_container.combo.currentText() == "--------":
            print("Unexpected starting roi text")
            return False
        if shapes not in widget.roi_container.choices:
            print("Shapes layer not available")
            return False
        widget.roi_container.combo.setCurrentText(shapes.name)

        dim_bars = widget.dims_container.findChildren(DimsComboBox.DimSelector)
        if not len(dim_bars) == 3:
            print("Expected more dimension comboboxes")
            return False
        for i, e in enumerate(dims):
            if e != dim_bars[i].combo.currentText():
                return False

        ok_button = widget.buttons.button(QDialogButtonBox.Ok)
        ok_button.clicked.emit()
        return True

    popup_handler(button.clicked.emit, handle_transfer)

    # Assert that the data is now in Fiji
    def check_active_display():
        if not ij.display().getActiveDisplay():
            return False
        dataset = ij.display().getActiveDisplay().getActiveView().getData()
        if not dataset.getName() == "test_to":
            return False
        if dataset.getProperties().get("rois") is None:
            return False
        if dataset.dimension(jc.Axes.X) != 50:
            return False
        if dataset.dimension(jc.Axes.Y) != 100:
            return False
        if dataset.dimension(jc.Axes.Z) != 3:
            return False

        return True

    asserter(check_active_display)


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
            name: (
                new_value
                if name == "imagej_directory_or_endpoint"
                else settings.defaults[name]
            )
            for name in values
        }

    menu.request_values = provide_updated_values

    # Handle the popup from button._update_settings
    expected_text = (
        "Please restart napari for napari-imagej settings changes to take effect!"
    )
    popup_func = _handle_QMessageBox(expected_text, QMessageBox.Ok, True)
    popup_handler(button._update_settings, popup_func)
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
    image: Image = Image(data=sample_data, name="test_to", rgb=False)
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


def test_legacy_directed_to_ij_ui(
    ij, popup_handler, gui_widget: NapariImageJMenu, asserter
):
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
    popup_func = _handle_QMessageBox(expected_popup_text, QMessageBox.No, False)
    popup_handler(actions[0][1], popup_func)
    assert not ui_visible(ij)

    popup_func = _handle_QMessageBox(expected_popup_text, QMessageBox.Yes, False)
    popup_handler(actions[0][1], popup_func)
    asserter(lambda: ui_visible(ij))

    frame = ij.ui().getDefaultUI().getApplicationFrame().getComponent()
    asserter(lambda: 1 == len(frame.getWindowListeners()))
    asserter(lambda: "NapariAdapter" in str(type(frame.getWindowListeners()[0])))
