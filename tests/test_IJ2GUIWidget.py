import numpy
import pytest
from napari.layers import Image
from napari.viewer import current_viewer
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QApplication, QDialog, QHBoxLayout, QMessageBox, QPushButton

from napari_imagej.setup_imagej import JavaClasses, running_headless
from napari_imagej.widget_IJ2 import FromIJButton, GUIButton, GUIWidget, ToIJButton


class JavaClassesTest(JavaClasses):
    """
    Here we override JavaClasses to get extra test imports
    """

    @JavaClasses.blocking_import
    def ArrayImgs(self):
        return "net.imglib2.img.array.ArrayImgs"

    @JavaClasses.blocking_import
    def ImageDisplay(self):
        return "net.imagej.display.ImageDisplay"


jc = JavaClassesTest()


@pytest.fixture(autouse=True)
def clean_layers_and_Displays(qtbot, ij):

    # Test pre-processing

    # Test processing
    yield

    # Test post-processing

    # After each test runs, clear all layers from napari
    viewer = current_viewer()
    if viewer is not None:
        print(f"There are {viewer.layers.__len__} layers")
        viewer.layers.clear()
        print(f"There are {viewer.layers.__len__} layers")

    # After each test runs, clear all displays from ImageJ2
    while ij.display().getActiveDisplay() is not None:
        current_display = ij.display().getActiveDisplay()
        current_display.close()
        qtbot.waitUntil(lambda: ij.display().getActiveDisplay() is not current_display)

    # After each test runs, clear all ImagePlus objects from ImageJ
    if ij.legacy and ij.legacy.isActive():
        while ij.WindowManager.getCurrentImage():
            imp = ij.WindowManager.getCurrentImage()
            imp.changes = False
            imp.close()


def test_widget_layout(gui_widget: GUIWidget):
    """Tests the number and expected order of imagej_widget children"""
    subwidgets = gui_widget.children()
    assert len(subwidgets) == 4
    assert isinstance(subwidgets[0], QHBoxLayout)

    assert isinstance(subwidgets[1], FromIJButton)
    assert not subwidgets[1].isEnabled()

    assert isinstance(subwidgets[2], ToIJButton)
    assert not subwidgets[2].isEnabled()

    assert isinstance(subwidgets[3], GUIButton)


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_GUIButton_layout_headful(qtbot, ij, gui_widget: GUIWidget):
    """Tests headful-specific settings of GUIButton"""
    button: GUIButton = gui_widget.gui_button

    expected: QPixmap = QPixmap("resources/16x16-flat.png")
    actual: QPixmap = button.icon().pixmap(expected.size())
    assert expected.toImage() == actual.toImage()

    assert "" == button.text()

    # Sometimes ImageJ2 can take a little while to be ready
    expected_toolTip = "Display ImageJ2 GUI"
    qtbot.waitUntil(lambda: expected_toolTip == button.toolTip())

    # Test showing UI
    assert not ij.ui().isVisible()
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(ij.ui().isVisible)


class _HandleChecker:
    """Class used to wrap a boolean"""

    def __init__(self):
        self.handled = False

    def done_handling(self) -> None:
        self.handled = True

    def has_been_handled(self) -> bool:
        return self.handled


@pytest.mark.skipif(
    not running_headless(), reason="Only applies when running headlessly"
)
def test_GUIButton_layout_headless(qtbot, gui_widget: GUIWidget):
    """Tests headless-specific settings of GUIButton"""
    button: GUIButton = gui_widget.gui_button

    expected: QPixmap = QPixmap("resources/16x16-flat-disabled.png")
    actual: QPixmap = button.icon().pixmap(expected.size())
    assert expected.toImage() == actual.toImage()

    assert "" == button.text()

    expected_text = "ImageJ2 GUI unavailable!"
    assert expected_text == button.toolTip()

    handled = _HandleChecker()

    # Test popup when running headlessly
    def handle_dialog(handled: _HandleChecker):
        qtbot.waitUntil(lambda: isinstance(QApplication.activeWindow(), QMessageBox))
        msg = QApplication.activeWindow()
        expected_text = (
            "The ImageJ2 user interface cannot be opened "
            "when running PyImageJ headlessly. Visit "
            '<a href="https://pyimagej.readthedocs.io/en/latest/'
            'Initialization.html#interactive-mode">this site</a> '
            "for more information."
        )
        assert expected_text == msg.text()
        assert Qt.RichText == msg.textFormat()
        assert Qt.TextBrowserInteraction == msg.textInteractionFlags()

        ok_button = msg.button(QMessageBox.Ok)
        qtbot.mouseClick(ok_button, Qt.LeftButton, delay=1)
        handled.done_handling()

    # Start the handler in a new thread
    QTimer.singleShot(100, lambda: handle_dialog(handled))
    # Click the button
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)
    # Assert that we are back to the original window i.e. that the popup was handled
    qtbot.waitUntil(handled.has_been_handled)


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_active_data_send(qtbot, ij, gui_widget: GUIWidget):
    button: ToIJButton = gui_widget.to_ij
    assert not button.isEnabled()

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(lambda: button.isEnabled())

    # Add some data to the viewer
    sample_data = numpy.ones((100, 100, 3))
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)

    # Press the button, handle the Dialog
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)

    # Assert that the data is now in Fiji
    active_display = ij.display().getActiveDisplay()
    assert isinstance(active_display, jc.ImageDisplay)
    assert "test_to" == active_display.getName()


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_active_data_receive(qtbot, ij, gui_widget: GUIWidget):
    button: FromIJButton = gui_widget.from_ij
    assert not button.isEnabled()

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(lambda: button.isEnabled())

    # Add some data to ImageJ
    sample_data = jc.ArrayImgs.bytes(10, 10, 10)
    ij.ui().show("test_from", sample_data)

    # Press the button, handle the Dialog
    assert 0 == len(button.viewer.layers)
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)

    # Assert that the data is now in napari
    assert 1 == len(button.viewer.layers)
    layer = button.viewer.layers[0]
    assert isinstance(layer, Image)
    assert (10, 10, 10) == layer.data.shape


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_chosen_data_send(qtbot, ij, gui_widget_chooser):
    button: ToIJButton = gui_widget_chooser.to_ij
    assert not button.isEnabled()

    # Show the button
    qtbot.mouseClick(gui_widget_chooser.gui_button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(lambda: button.isEnabled())

    # Add some data to the viewer
    sample_data = numpy.ones((100, 100, 3))
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)

    handler = _HandleChecker()

    def handle_dialog(handler: _HandleChecker):
        qtbot.waitUntil(lambda: isinstance(QApplication.activeWindow(), QDialog))
        dialog = QApplication.activeWindow()
        buttons = dialog.findChildren(QPushButton)
        assert 2 == len(buttons)
        for button in buttons:
            if "ok" in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton, delay=1)
                handler.done_handling()
                return
        pytest.fail("Could not find the Ok button!")

    # Start the handler in a new thread
    QTimer.singleShot(100, lambda: handle_dialog(handler))
    # Click the button
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)
    # Assert that we are back to the original window i.e. that the popup was handled
    qtbot.waitUntil(handler.has_been_handled)

    # Assert that the data is now in Fiji
    active_display = ij.display().getActiveDisplay()
    assert isinstance(active_display, jc.ImageDisplay)
    assert "test_to" == active_display.getName()


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_chosen_data_receive(qtbot, ij, gui_widget: GUIWidget):
    button: FromIJButton = gui_widget.from_ij
    assert not button.isEnabled()

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(lambda: button.isEnabled())

    # Add some data to ImageJ
    sample_data = jc.ArrayImgs.bytes(10, 10, 10)
    ij.ui().show("test_from", sample_data)

    handler = _HandleChecker()

    def handle_dialog(handler: _HandleChecker):
        qtbot.waitUntil(lambda: isinstance(QApplication.activeWindow(), QDialog))
        dialog = QApplication.activeWindow()
        buttons = dialog.findChildren(QPushButton)
        assert 2 == len(buttons)
        for button in buttons:
            if "ok" in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton, delay=1)
                handler.done_handling()
                return
        pytest.fail("Could not find the Ok button!")

    # Press the button, handle the Dialog
    assert 0 == len(button.viewer.layers)
    # Start the handler in a new thread
    QTimer.singleShot(100, lambda: handle_dialog(handler))
    # Click the button
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)
    # Assert that we are back to the original window i.e. that the popup was handled
    qtbot.waitUntil(handler.has_been_handled)

    # Assert that the data is now in napari
    assert 1 == len(button.viewer.layers)
    layer = button.viewer.layers[0]
    assert isinstance(layer, Image)
    assert (10, 10, 10) == layer.data.shape
