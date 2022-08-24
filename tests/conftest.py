import os
from typing import Callable, Generator

import pytest
from napari import Viewer

from napari_imagej import widget_IJ2
from napari_imagej.widget import ImageJWidget
from napari_imagej.widget_IJ2 import GUIWidget


@pytest.fixture(scope="module")
def ij():
    from napari_imagej.setup_imagej import ij

    return ij()


@pytest.fixture()
def viewer(make_napari_viewer) -> Generator[Viewer, None, None]:
    yield make_napari_viewer()


@pytest.fixture
def imagej_widget(viewer) -> Generator[ImageJWidget, None, None]:
    # Create widget
    ij_widget: ImageJWidget = ImageJWidget(viewer)

    yield ij_widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    ij_widget.close()


@pytest.fixture
def gui_widget(viewer) -> Generator[GUIWidget, None, None]:
    def mock_setting(value: str):
        return {"imagej_installation": None, "choose_active_layer": True}[value]

    widget_IJ2.setting = mock_setting

    # Create widget
    widget: GUIWidget = GUIWidget(viewer)

    yield widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    widget.close()


@pytest.fixture
def gui_widget_chooser(viewer) -> Generator[GUIWidget, None, None]:

    # monkeypatch settings
    def mock_setting(value: str):
        return {"imagej_installation": None, "choose_active_layer": False}[value]

    widget_IJ2.setting = mock_setting

    # Create widget
    widget: GUIWidget = GUIWidget(viewer)

    yield widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    widget.close()


@pytest.fixture()
def asserter(qtbot) -> Callable[[Callable[[], bool]], None]:
    if "NAPARI_IMAGEJ_TEST_TIMEOUT" in os.environ:
        timeout = int(os.environ["NAPARI_IMAGEJ_TEST_TIMEOUT"])
    else:
        timeout = 5000  # 5 seconds

    def assertFunc(func: Callable[[], bool]):
        # Let things run for up to a minute
        qtbot.waitUntil(func, timeout=timeout)

    return assertFunc
