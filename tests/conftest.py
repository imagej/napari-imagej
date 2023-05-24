"""
A module containing pytest configuration and globally-used fixtures
"""
import os
import sys
from typing import Callable, Generator

import pytest
from napari import Viewer
from qtpy.QtCore import QRunnable, Qt, QThreadPool
from qtpy.QtWidgets import QApplication, QMessageBox

from napari_imagej import settings
from napari_imagej.java import init_ij
from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.napari_imagej import NapariImageJWidget

actual_settings_is_macos = settings._is_macos


@pytest.fixture()
def asserter(qtbot) -> Callable[[Callable[[], bool]], None]:
    """Wraps qtbot.waitUntil with a standardized timeout"""

    # Determine timeout length - defaults to 5
    timeout = int(os.environ.get("NAPARI_IMAGEJ_TEST_TIMEOUT", "5000"))

    # Define timeout function
    def assertFunc(func: Callable[[], bool]):
        # Let things run for up to a minute
        qtbot.waitUntil(func, timeout=timeout)

    # Return the timeout function
    return assertFunc


@pytest.fixture(autouse=True)
def install_default_settings():
    """Fixture ensuring any changes made earlier to the settings are reversed"""
    settings._is_macos = actual_settings_is_macos
    settings.load(False)


@pytest.fixture(scope="session")
def ij():
    """Fixture providing the ImageJ2 Gateway"""
    # BIG HACK: We run into the issue described in
    # https://github.com/imagej/pyimagej/issues/197
    # if we don't add this.
    if sys.platform == "darwin":
        viewer = Viewer()
        ij = init_ij()
        viewer.close()
    else:
        ij = init_ij()

    yield ij

    ij.context().dispose()


@pytest.fixture()
def viewer(make_napari_viewer) -> Generator[Viewer, None, None]:
    """Fixture providing a napari Viewer"""
    yield make_napari_viewer()


@pytest.fixture
def imagej_widget(viewer, asserter) -> Generator[NapariImageJWidget, None, None]:
    """Fixture providing an ImageJWidget"""
    # Create widget
    ij_widget: NapariImageJWidget = NapariImageJWidget(viewer)
    # Wait for imagej to be initialized
    ij_widget.wait_for_finalization()

    yield ij_widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    ij_widget.close()


@pytest.fixture
def gui_widget(viewer) -> Generator[NapariImageJMenu, None, None]:
    """
    Fixture providing a GUIWidget. The returned widget will use active layer selection
    """

    # Define GUIWidget settings for this particular feature.
    # In particular, we want to enforce active layer selection
    settings.use_active_layer = True

    # Create widget
    widget: NapariImageJMenu = NapariImageJMenu(viewer)

    # Wait for ImageJ initialization
    init_ij()

    # Finalize widget
    widget.finalize()

    yield widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    widget.close()


@pytest.fixture
def gui_widget_chooser(viewer) -> Generator[NapariImageJMenu, None, None]:
    """
    Fixture providing a GUIWidget. The returned widget will use user layer selection
    """

    # Define GUIWidget settings for this particular feature.
    # In particular, we want to enforce user layer selection via Dialog
    settings.use_active_layer = False

    # Create widget
    widget: NapariImageJMenu = NapariImageJMenu(viewer)

    # Wait for ImageJ initialization
    init_ij()

    # Finalize widget
    widget.finalize()

    yield widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    widget.close()


@pytest.fixture()
def popup_handler(asserter) -> Callable[[str, Callable[[], None]], None]:
    """Fixture used to handle RichTextPopups"""

    def handle_popup(
        text: str, is_rich: bool, button, popup_generator: Callable[[], None]
    ):
        # # Start the handler in a new thread
        class Handler(QRunnable):
            # Test popup when running headlessly
            def run(self) -> None:
                asserter(lambda: isinstance(QApplication.activeWindow(), QMessageBox))
                msg = QApplication.activeWindow()
                if text != msg.text():
                    print("Text differed")
                    print(text)
                    print(msg.text())
                    self._passed = False
                    return
                if is_rich and Qt.RichText != msg.textFormat():
                    print("Not rich text")
                    self._passed = False
                    return
                if is_rich and Qt.TextBrowserInteraction != msg.textInteractionFlags():
                    print("No browser interaction")
                    self._passed = False
                    return

                ok_button = msg.button(button)
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
