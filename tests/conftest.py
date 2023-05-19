"""
A module containing pytest configuration and globally-used fixtures
"""
import os
import sys
from typing import Callable, Generator

import pytest
from napari import Viewer

import napari_imagej
from napari_imagej.java import init_ij
from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.napari_imagej import NapariImageJWidget


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
    napari_imagej.settings.clear()
    napari_imagej.settings.read()


@pytest.fixture(scope="session", autouse=True)
def preserve_user_settings():
    """Fixture allowing the saving settings without disrupting user's settings"""
    # Obtain prior user settings
    user_path = napari_imagej.settings.user_config_path()

    if os.path.exists(user_path):
        # If they existed, read in the settings and delete the file
        with open(user_path, "r") as f:
            existing_settings = f.read()
        os.remove(user_path)

        yield

        # After the test, restore the file
        with open(user_path, "w") as f:
            f.write(existing_settings)
    else:
        yield

        # After the test, remove the file
        if os.path.exists(user_path):
            os.remove(user_path)


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
    napari_imagej.settings["use_active_layer"] = True

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
    napari_imagej.settings["use_active_layer"] = False

    # Create widget
    widget: NapariImageJMenu = NapariImageJMenu(viewer)

    # Wait for ImageJ initialization
    init_ij()

    # Finalize widget
    widget.finalize()

    yield widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    widget.close()
