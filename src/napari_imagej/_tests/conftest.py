from typing import Generator
import pytest
import imagej

from napari_imagej._function import ImageJWidget
from napari import Viewer
# This import is mistakenly considered unused; we need it for imagej_widget!
from napari.utils._testsupport import make_napari_viewer

@pytest.fixture(scope="module")
def ij():
    return imagej.init()

@pytest.fixture
def imagej_widget(make_napari_viewer) -> Generator[ImageJWidget, None, None]:
    # Create widget
    viewer: Viewer = make_napari_viewer()
    ij_widget: ImageJWidget = ImageJWidget(viewer)

    yield ij_widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    ij_widget.close()