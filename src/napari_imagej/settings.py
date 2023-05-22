"""
Configuration parameters for napari-imagej behavior.

The following fields are supported:

imagej_directory_or_endpoint: str = ""
    Path to a local ImageJ2 installation (e.g. /Applications/Fiji.app),
    OR version of net.imagej:imagej artifact to launch (e.g. 2.12.0),
    OR another artifact built on ImageJ2 (e.g. sc.fiji:fiji),
    OR list of artifacts to include contatenated with plus signs
      (e.g. 'net.imagej:imagej:2.12.0+net.preibisch:BigStitcher').
    Defaults to the empty string, which tells napari-imagej
    to use the currently supported reproducible version of ImageJ2.

imagej_base_directory: str = "."
    Path to the ImageJ base directory on your local machine.
    Defaults to the current working directory.

include_imagej_legacy: bool = True
    This can be used to include original ImageJ functionality.
    If True, original ImageJ functionality (ij.* packages) will be available.
    If False, many ImageJ2 rewrites of original ImageJ functionality are available.
    Defaults to True, as the original ImageJ functionality can be very useful to have.

enable_imagej_gui: bool = True
    Designates whether to make the ImageJ GUI available.
    If True, napari-imagej will attempt to run in graphical mode.
    If False, napari-imagej will run in headless mode.
    Defaults to True. However, the ImageJ GUI is unavailable on macOS; therefore,
    on macOS, napari-imagej will behave as though this setting is False regardless.
    More details can be found at:
    https://pyimagej.readthedocs.io/en/latest/Initialization.html#with-graphical-capabilities

use_active_layer: bool = True
    This can be used to identify whether transferred data between ImageJ2 and napari
    should be selected via activation or by user selection via a dialog.
    If True, the active layer/window is always used for transfer between applications.
    If False, a popup will be shown, prompting the user to select data for transfer.
    Defaults to True.

jvm_command_line_arguments: str = ""
    Additional command line arguments to pass to the Java Virtual Machine (JVM).
    For example, "-Xmx4g" to allow Java to use  4 GB of memory.
    By default, no arguments are passed.
"""

import os
import sys
from typing import Any, Callable, Dict, Optional

import confuse

from napari_imagej.utilities.logging import log_debug, warn

# -- Constants --

default_java_components = [
    "net.imagej:imagej:2.12.0",
    "org.scijava:scijava-common:2.94.0",
]
defaults = {
    "imagej_directory_or_endpoint": "",
    "imagej_base_directory": ".",
    "include_imagej_legacy": True,
    "enable_imagej_gui": True,
    "use_active_layer": True,
    "jvm_command_line_arguments": "",
}

# -- Configuration options --

imagej_directory_or_endpoint: str = defaults["imagej_directory_or_endpoint"]
imagej_base_directory: str = defaults["imagej_base_directory"]
include_imagej_legacy: bool = defaults["include_imagej_legacy"]
enable_imagej_gui: bool = defaults["enable_imagej_gui"]
use_active_layer: bool = defaults["use_active_layer"]
jvm_command_line_arguments: str = defaults["jvm_command_line_arguments"]

_test_mode = bool(os.environ.get("NAPARI_IMAGEJ_TESTING", None))
_is_macos = sys.platform == "darwin"


# -- Public API functions --


def asdict() -> Dict[str, Any]:
    """
    Gets the settings as a dictionary.
    :return: Dictionary containing key/value pair for each setting.
    """
    settings = {}
    _copy_settings(dest_set=settings.__setitem__)
    return settings


def basedir() -> str:
    """
    Get the validated, guaranteed-to-exist ImageJ base directory.
    """
    abs_basedir = os.path.abspath(imagej_base_directory)
    if not os.path.exists(abs_basedir):
        cwd = os.getcwd()
        warn(
            f"Non-existent base directory '{abs_basedir}'; "
            f"falling back to current working directory '{cwd}'"
        )
        abs_basedir = cwd
    return abs_basedir


def endpoint() -> str:
    """
    Get the validated endpoint string to use for initializing PyImageJ.
    """
    return imagej_directory_or_endpoint or "+".join(default_java_components)


def headless() -> bool:
    """
    Get whether ImageJ will be initialized in headless mode with no GUI.

    Note that napari-imagej does not currently support GUI mode on macOS systems;
    more details can be found at:
    https://pyimagej.readthedocs.io/en/latest/Initialization.html#with-graphical-capabilities

    :return:
        False if the platform supports running with GUI and
        the enable_imagej_gui flag is True; True otherwise.
    """
    return _is_macos or not enable_imagej_gui


def jvm_mode() -> str:
    """
    Get the validated JVM mode to use for initializing PyImageJ.

    Note that napari-imagej does not currently support GUI mode on macOS systems;
    more details can be found at:
    https://pyimagej.readthedocs.io/en/latest/Initialization.html#with-graphical-capabilities

    :return:
        'interactive' if the platform supports running with GUI and
        the enable_imagej_gui flag is True; 'headless' otherwise.
    """
    return "headless" if headless() else "interactive"


def load(read_config_file: bool = None) -> None:
    """
    Populate settings from user config file on disk and/or environment variables.
    :param read_config_file: Whether to load settings from user's config file on disk.
    """
    if read_config_file is None:
        # Skip reading user config file by default when running tests.
        read_config_file = not _test_mode

    config = _confuse_config()
    # Import config from persisted YAML file on disk -- if user flag is set.
    config.read(user=read_config_file)
    # Import config from environment variables.
    config.set_env(prefix="NAPARI_IMAGEJ_")

    # Populate configuration values from confuse configuration.
    # If a value is not found in confuse config, assign default value.
    _copy_settings(src_get=lambda k, dv: _confuse_get(config, k, dv))


def save() -> None:
    """
    Persist settings to a YAML configuration file on disk.
    """
    if _test_mode:
        # Skip saving user config file when running tests.
        return

    # Populate confuse configuration values.
    config = _confuse_config()
    _copy_settings(dest_set=config.__setitem__)

    # Write configuration to disk.
    output = config.dump()
    with open(config.user_config_path(), "w") as f:
        f.write(output)


def update(use_dv=True, **kwargs) -> bool:
    """
    Update settings to match the given argument key/value pairs.
    :param use_dv:
        Controls what happens when a needed key/value pair is not given.
        If True, the setting is assigned its default value.
        If False, the setting is left unchanged.
    :param kwargs: Key/value pairs corresponding to settings names+values.
    :return: True if any setting changed in value.
    """
    # Populate configuration values from the given arguments.
    return _copy_settings(src_get=lambda k, dv: kwargs.get(k, dv if use_dv else None))


# -- Validation --


def validate() -> None:
    """
    Perform validation checks on the settings.

    imagej_base_directory
        Check that it's a valid directory.

    enable_imagej_gui
        Check that the ImageJ GUI is available on this platform.
        Specifically: the GUI is not available on macOS systems.

    :raise ValueError: If any problems are noticed with the settings.
    """
    errors = []
    if not os.path.isdir(os.path.abspath(imagej_base_directory)):
        errors.append(
            "ImageJ base directory is not a valid directory. "
            "No scripts will be discovered."
        )
    if enable_imagej_gui and _is_macos:
        errors.append(
            "The ImageJ GUI is not available on macOS systems. "
            "Headless mode will be used."
        )

    if len(errors) >= 1:
        raise ValueError(*errors)


# -- Helper functions --


def _confuse_config() -> confuse.Configuration:
    """
    Construct a confuse configuration object.
    https://confuse.readthedocs.io/
    """
    return confuse.Configuration("napari-imagej")


def _confuse_get(config: confuse.Configuration, name, default_value) -> Any:
    """
    Get the named key's value from the specified confuse config,
    or default_value if the confuse config has no such key.
    """
    try:
        return config[name].get(type(default_value))
    except confuse.ConfigError as e:
        log_debug(e)
        return default_value


def _copy_settings(
    src_get: Optional[Callable] = None,
    dest_set: Optional[Callable] = None,
    dest_get: Optional[Callable] = None,
) -> bool:
    """
    Copy settings from a source to a destination.
    :param src_get: Getter for source values. This module by default.
    :param dest_get: Getter for destination values. This module by default.
    :param dest_set: Setter for destination values. This module by default.
    :return: True iff any destination values changed.
    """
    this = sys.modules[__name__]
    if src_get is None:
        # By default, use fields of this settings module as source.
        src_get = lambda k, dv: getattr(this, k, dv)  # noqa: E731
    if dest_set is None:
        # By default, use fields of this settings module as destination.
        dest_set = lambda k, v: setattr(this, k, v)  # noqa: E731
        dest_get = lambda k: getattr(this, k, None)  # noqa: E731
    if dest_get is None:
        # If no getter for destination is given, just use Nones.
        dest_get = lambda k: None  # noqa: E731

    # Calculate new value for each key.
    any_changed = False
    for k, dv in defaults.items():
        # Retrieve the new value from the source.
        new_value = src_get(k, dv)

        # Ensure there is actually a new value to assign.
        if new_value is None:
            continue

        # Ensure that the new value is the proper type.
        vtype = type(dv)
        if not isinstance(new_value, vtype):
            new_value = vtype(new_value)

        # Verify that the value has actually changed.
        old_value = dest_get(k)
        if old_value == new_value:
            continue

        # Assign the new value to the destination.
        dest_set(k, new_value)
        any_changed = True

    return any_changed


# -- Initialization logic --

load()
