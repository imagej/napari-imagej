"""
A module containing pytest configuration and globally-used fixtures
"""
import os
from typing import Callable, Generator

import pytest
from napari import Viewer

import napari_imagej
from napari_imagej.java import ensure_jvm_started
from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.napari_imagej import NapariImageJWidget


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


@pytest.fixture(autouse=True)
def launch_imagej():
    """Fixture ensuring that ImageJ is running before any tests run"""
    ensure_jvm_started()
    yield


@pytest.fixture(scope="session")
def ij():
    """Fixture providing the ImageJ2 Gateway"""
    from napari_imagej.java import ij

    return ij()


@pytest.fixture()
def viewer(make_napari_viewer) -> Generator[Viewer, None, None]:
    """Fixture providing a napari Viewer"""
    yield make_napari_viewer()


@pytest.fixture
def imagej_widget(viewer) -> Generator[NapariImageJWidget, None, None]:
    """Fixture providing an ImageJWidget"""
    # Create widget
    ij_widget: NapariImageJWidget = NapariImageJWidget(viewer)
    ij_widget.ij_post_init_setup.wait()

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
    napari_imagej.settings["choose_active_layer"] = True

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
    napari_imagej.settings["choose_active_layer"] = False

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
