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
    If true, original ImageJ functionality (ij.* packages) will be available.
    If false, many ImageJ2 rewrites of original ImageJ functionality are available.
    Defaults to true as the ImageJ legacy UI is most popular and familiar.

jvm_mode: str = "headless"
    Designates the mode of execution for ImageJ2.
    Allowed options are 'headless' and 'interactive'.
    NB 'interactive' mode is unavailable on MacOS. More details can be found at
    https://pyimagej.readthedocs.io/en/latest/Initialization.html#interactive-mode
    If napari-imagej is launched on MacOS with this setting set to "interactive",
    the setting will silently be reassigned to "headless".
    Defaults to 'interactive'.

use_active_layer: bool = True
    This can be used to identify whether transferred data between ImageJ2 and napari
    should be selected via activation or by user selection via a dialog.
    If true, the active layer/window is always used for transfer between applications.
    If false, a popup will be shown, prompting the user to select data for transfer.
    Defaults to true.

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
    "jvm_mode": "interactive",
    "use_active_layer": True,
    "jvm_command_line_arguments": "",
}

# -- Configuration options --

imagej_directory_or_endpoint: str = defaults["imagej_directory_or_endpoint"]
imagej_base_directory: str = defaults["imagej_base_directory"]
include_imagej_legacy: bool = defaults["include_imagej_legacy"]
jvm_mode: str = defaults["jvm_mode"]
use_active_layer: bool = defaults["use_active_layer"]
jvm_command_line_arguments: str = defaults["jvm_command_line_arguments"]

_test_mode = bool(os.environ.get("NAPARI_IMAGEJ_TESTING", None))


def endpoint() -> str:
    """
    Get the validated endpoint string to use for initializing PyImageJ.
    """
    return imagej_directory_or_endpoint or "+".join(default_java_components)


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


def asdict() -> Dict[str, Any]:
    """
    Gets the settings as a dictionary.
    :return: Dictionary containing key/value pair for each setting.
    """
    settings = {}
    _copy_settings(dest_set=settings.__setitem__)
    return settings


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


def save() -> None:
    """
    Persist settings to a YAML configuration file on disk.
    """
    if _test_mode:
        return

    # Populate confuse configuration values.
    config = _confuse_config()
    _copy_settings(dest_set=config.__setitem__)

    # Write configuration to disk.
    output = config.dump()
    with open(config.user_config_path(), "w") as f:
        f.write(output)


def validate():
    """
    Validate settings.
    """
    # Validate jvm_mode.
    global jvm_mode
    if jvm_mode not in ("interactive", "headless"):
        warn(f"Invalid JVM mode '{jvm_mode}'; defaulting to headless mode.")
        jvm_mode = "headless"
    if jvm_mode == "interactive" and sys.platform == "darwin":
        raise ValueError(
            "ImageJ2 must be run headlessly on MacOS. <p>Visit "
            '<a href="https://pyimagej.readthedocs.io/en/latest/'
            'Initialization.html#interactive-mode">this site</a> '
            "for more information."
        )

    # Ensure base directory is valid.
    if not os.path.exists(os.path.abspath(imagej_base_directory)):
        raise ValueError("ImageJ base directory must be a valid path.")


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

    # For each item in defaults dict, copy the entry from source to destination.
    any_changed = False
    for k, dv in defaults.items():
        new_value = src_get(k, dv)
        if new_value is None:
            # No updated value to copy.
            continue
        vtype = type(dv)
        if not isinstance(new_value, vtype):
            # Coerce non-conforming types.
            new_value = vtype(new_value)
        old_value = dest_get(k)
        if old_value != new_value and new_value is not None:
            dest_set(k, new_value)
            any_changed = True
    return any_changed


load()
