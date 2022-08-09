import numpy
import pytest
from napari.layers import Image
from napari.viewer import current_viewer
from qtpy.QtCore import Qt, QTimer
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QApplication, QDialog, QMessageBox, QPushButton, QVBoxLayout

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
    assert isinstance(subwidgets[0], QVBoxLayout)
    assert isinstance(subwidgets[1], GUIButton)
    assert isinstance(subwidgets[2], ToIJButton)
    assert isinstance(subwidgets[3], FromIJButton)


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_GUIButton_layout_headful(qtbot, ij, gui_widget: GUIWidget):
    """Tests headless-specific settings of GUIButton"""
    button: GUIButton = gui_widget.gui_button

    expected: QPixmap = QPixmap("resources/16x16-flat.png")
    actual: QPixmap = button.icon().pixmap(expected.size())
    assert expected.toImage() == actual.toImage()

    expected_text = "Display ImageJ2 GUI"
    assert expected_text == button.text()

    expected_toolTip = "Open ImageJ2 in a new window!"
    assert expected_toolTip == button.toolTip()

    # Test showing UI
    assert not ij.ui().isVisible()
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(ij.ui().isVisible)


@pytest.mark.skipif(
    not running_headless(), reason="Only applies when running headlessly"
)
def test_GUIButton_layout_headless(qtbot, gui_widget: GUIWidget):
    """Tests headless-specific settings of GUIButton"""
    button: GUIButton = gui_widget.gui_button

    expected: QPixmap = QPixmap("resources/16x16-flat-disabled.png")
    actual: QPixmap = button.icon().pixmap(expected.size())
    assert expected.toImage() == actual.toImage()

    expected_text = "Display ImageJ2 GUI (disabled)"
    assert expected_text == button.text()

    expected_toolTip = "Not available when running PyImageJ headlessly!"
    assert expected_toolTip == button.toolTip()

    # Test popup when running headlessly
    def handle_dialog():
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

        assert isinstance(msg, QMessageBox)
        ok_button = msg.button(QMessageBox.Ok)
        qtbot.mouseClick(ok_button, Qt.LeftButton, delay=1)

    original = QApplication.activeWindow()
    QTimer.singleShot(100, handle_dialog)
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(lambda: QApplication.activeWindow() == original)


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_data_to_ImageJ(qtbot, ij, gui_widget: GUIWidget):
    button: ToIJButton = gui_widget.to_ij
    assert button.isHidden()

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(lambda: not button.isHidden())

    # Add some data to the viewer
    sample_data = numpy.ones((100, 100, 3))
    image: Image = Image(data=sample_data, name="test_to")
    current_viewer().add_layer(image)

    def handle_dialog():
        qtbot.waitUntil(lambda: isinstance(QApplication.activeWindow(), QDialog))
        dialog = QApplication.activeWindow()
        buttons = dialog.findChildren(QPushButton)
        assert 2 == len(buttons)
        for button in buttons:
            if "ok" in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton, delay=1)
                return
        pytest.fail("Could not find the Ok button!")

    # Press the button, handle the Dialog
    QTimer.singleShot(100, handle_dialog)
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)

    # Assert that the data is now in Fiji
    active_display = ij.display().getActiveDisplay()
    assert isinstance(active_display, jc.ImageDisplay)
    assert "test_to" == active_display.getName()


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
def test_data_from_ImageJ(qtbot, ij, gui_widget: GUIWidget):
    button: FromIJButton = gui_widget.from_ij
    assert button.isHidden()

    # Show the button
    qtbot.mouseClick(gui_widget.gui_button, Qt.LeftButton, delay=1)
    qtbot.waitUntil(lambda: not button.isHidden())

    # Add some data to ImageJ
    sample_data = jc.ArrayImgs.bytes(10, 10, 10)
    ij.ui().show("test_from", sample_data)

    def handle_dialog():
        qtbot.waitUntil(lambda: isinstance(QApplication.activeWindow(), QDialog))
        dialog = QApplication.activeWindow()
        buttons = dialog.findChildren(QPushButton)
        assert 2 == len(buttons)
        for button in buttons:
            if "ok" in button.text().lower():
                qtbot.mouseClick(button, Qt.LeftButton, delay=1)
                return
        pytest.fail("Could not find the Ok button!")

    # Press the button, handle the Dialog
    assert 0 == len(button.viewer.layers)
    QTimer.singleShot(100, handle_dialog)
    qtbot.mouseClick(button, Qt.LeftButton, delay=1)

    # Assert that the data is now in napari
    assert 1 == len(button.viewer.layers)
    layer = button.viewer.layers[0]
    assert isinstance(layer, Image)
    assert (10, 10, 10) == layer.data.shape
