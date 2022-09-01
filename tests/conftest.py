import os
from typing import Callable, Generator

import pytest
from napari import Viewer

from napari_imagej.widgets import menu
from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.napari_imagej import NapariImageJ


@pytest.fixture(scope="module")
def ij():
    """Fixture providing the ImageJ2 Gateway"""
    from napari_imagej.java import ij

    return ij()


@pytest.fixture()
def viewer(make_napari_viewer) -> Generator[Viewer, None, None]:
    """Fixture providing a napari Viewer"""
    yield make_napari_viewer()


@pytest.fixture
def imagej_widget(viewer) -> Generator[NapariImageJ, None, None]:
    """Fixture providing an ImageJWidget"""
    # Create widget
    ij_widget: NapariImageJ = NapariImageJ(viewer)

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
    def mock_setting(value: str):
        return {"imagej_installation": None, "choose_active_layer": True}[value]

    menu.setting = mock_setting

    # Create widget
    widget: NapariImageJMenu = NapariImageJMenu(viewer)

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
    def mock_setting(value: str):
        return {"imagej_installation": None, "choose_active_layer": False}[value]

    menu.setting = mock_setting

    # Create widget
    widget: NapariImageJMenu = NapariImageJMenu(viewer)

    yield widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    widget.close()


@pytest.fixture()
def asserter(qtbot) -> Callable[[Callable[[], bool]], None]:
    """Wraps qtbot.waitUntil with a standardized timeout"""

    # Determine timeout length
    if "NAPARI_IMAGEJ_TEST_TIMEOUT" in os.environ:
        timeout = int(os.environ["NAPARI_IMAGEJ_TEST_TIMEOUT"])
    else:
        timeout = 5000  # 5 seconds

    # Define timeout function
    def assertFunc(func: Callable[[], bool]):
        # Let things run for up to a minute
        qtbot.waitUntil(func, timeout=timeout)

    # Return the timeout function
    return assertFunc
