"""
A module testing napari_imagej.widgets.menu
"""
import numpy
import pytest
from napari import Viewer
from napari.layers import Image, Layer
from napari.viewer import current_viewer
from qtpy.QtCore import QRunnable, Qt, QThreadPool
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QApplication, QHBoxLayout, QMessageBox

from napari_imagej.java import JavaClasses, running_headless
from napari_imagej.widgets import menu
from napari_imagej.widgets.menu import (
    FromIJButton,
    GUIButton,
    NapariImageJMenu,
    ToIJButton,
)
from napari_imagej.widgets.resources import resource_path


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
def napari_mocker(viewer: Viewer):
    """Fixture allowing the mocking of napari utilities"""

    # REQUEST_VALUES MOCK
    oldfunc = menu.request_values

    def newfunc(values=(), title="", **kwargs):
        results = {}
        # Solve each parameter
        for name, options in kwargs.items():
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


@pytest.mark.skipif(
    not running_headless(), reason="Only applies when running headlessly"
)
def test_GUIButton_layout_headless(asserter, gui_widget: NapariImageJMenu):
    """Tests headless-specific settings of GUIButton"""
    button: GUIButton = gui_widget.gui_button

    expected: QPixmap = QPixmap(resource_path("imagej2-16x16-flat-disabled"))
    actual: QPixmap = button.icon().pixmap(expected.size())
    assert expected.toImage() == actual.toImage()

    assert "" == button.text()

    expected_text = "ImageJ2 GUI unavailable!"
    assert expected_text == button.toolTip()

    # # Start the handler in a new thread
    class Handler(QRunnable):

        # Test popup when running headlessly
        def run(self) -> None:
            asserter(lambda: isinstance(QApplication.activeWindow(), QMessageBox))
            msg = QApplication.activeWindow()
            expected_text = (
                "The ImageJ2 user interface cannot be opened "
                "when running PyImageJ headlessly. Visit "
                '<a href="https://pyimagej.readthedocs.io/en/latest/'
                'Initialization.html#interactive-mode">this site</a> '
                "for more information."
            )
            if expected_text != msg.text():
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
    button.clicked.emit()
    # Wait for the popup to be handled
    asserter(QThreadPool.globalInstance().waitForDone)
    assert runnable.passed()


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
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
    asserter(lambda: ij.display().getActiveDisplay() is not None)
    active_display = ij.display().getActiveDisplay()
    assert isinstance(active_display, jc.ImageDisplay)
    assert "test_to" == active_display.getName()


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
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


@pytest.mark.skipif(
    running_headless(), reason="Only applies when not running headlessly"
)
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
    asserter(lambda: isinstance(ij.display().getActiveDisplay(), jc.ImageDisplay))
    assert "test_to" == ij.display().getActiveDisplay().getName()

    # Use the chooser to transfer that data back
    button_from.clicked.emit()

    # Assert that the data is now in napari
    asserter(lambda: 2 == len(button_to.viewer.layers))
