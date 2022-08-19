from typing import Generator

import pytest
from napari import Viewer

import napari_imagej.widget_IJ2
from napari_imagej.widget import ImageJWidget
from napari_imagej.widget_IJ2 import GUIWidget


@pytest.fixture(scope="module")
def ij():
    from napari_imagej.setup_imagej import ij

    return ij()


@pytest.fixture()
def viewer(make_napari_viewer) -> Generator[Viewer, None, None]:
    yield make_napari_viewer()


# HACK: Something about the ImageJ2 GUI causes these unit tests to hang.
# Let's force it to close, for now.


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

    napari_imagej.widget_IJ2.setting = mock_setting

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

    napari_imagej.widget_IJ2.setting = mock_setting

    # Create widget
    widget: GUIWidget = GUIWidget(viewer)

    yield widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    widget.close()
