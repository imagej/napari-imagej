"""
napari-imagej brings the power of ImageJ, ImageJ2, and Fiji to the napari viewer.

With napari-imagej, users can call headless functionality from any of these applications
on napari data structures. Users can also call SciJava scripts on data in napari,
automatically discoverable within the plugin. Users can launch the ImageJ or ImageJ2
user interfaces from napari-imagej and can explicitly transfer data to and from the
napari user interface. Most importantly, all of this functionality is accessible WITHOUT
any explicit conversion between the two ecosystems!

napari-imagej is NOT designed to be used on its own; instead, it should be launched
from within the napari application. Please see (https://napari.org/stable/#installation)
to get started using the napari application. Once napari is installed, you can then
add napari-imagej as a plugin. Please see (https://www.napari-hub.org/) for a list
of available plugins, including napari-imagej.

napari-imagej is built upon the PyImageJ project:
https://pyimagej.readthedocs.io/en/latest/
"""
import os
import sys
from typing import Any

import confuse

from napari_imagej.utilities.logging import log_debug

__version__ = "0.0.1.dev0"

default_java_components = [
    "net.imagej:imagej:2.11.0",
    "org.scijava:scijava-search:2.0.3",
]


class _NapariImageJSettings(confuse.Configuration):
    """Napari-ImageJ Settings object"""

    def __init__(self, read=True, **kwargs):
        super().__init__(appname="napari-imagej", modname=__name__, read=read)

    def read(self, user: bool = True, defaults: bool = True):
        """Override of Configuration.read(), performs validation on each setting"""
        # Don't use user settings during the tests
        testing = os.environ.get("NAPARI_IMAGEJ_TESTING", "no") == "yes"
        super().read(user=user and not testing, defaults=defaults)
        # Allow setting configuration using environment variables
        super().set_env(prefix="NAPARI_IMAGEJ_")
        # -- VALIDATE SETTINGS -- #
        for key, value in self.items():
            self._validate_setting(key, value.get(), strict=False)

    def _validate_setting(self, setting: str, value: Any, strict=True):
        """
        Helper function to perform validation on a particular setting.
        By and large, this validation consists of an if block for each setting,
        checking the specifics of that setting.

        :param setting: The setting (key) to check
        :param value: The value assigned to a particular setting
        :param strict: If true, raise an Error. If false, assign a reasonable default.
        """
        if setting == "imagej_directory_or_endpoint":
            # Ensure a valid endpoint/directory
            if not value:
                endpoint = "+".join(default_java_components)
                if strict:  # Report the failure
                    raise ValueError(
                        "The imagej directory or endpoint cannot be blank! "
                        f"<p><font face='courier'>{endpoint}</font> "
                        "is the default option."
                        "<p>Visit "
                        '<a href="https://pyimagej.readthedocs.io/en/latest/'
                        'api.html#initialization">this site</a> '
                        "and check the "
                        "<font face='courier'>ij_dir_or_version_or_endpoint</font> "
                        "parameter for more options."
                    )
                else:  # Assign a reasonable default
                    log_debug(
                        "No provided imagej directory or endpoint. Setting endpoint "
                        f"to {endpoint}"
                    )
                    self["imagej_directory_or_endpoint"] = endpoint
        if setting == "jvm_mode":
            # Ensure a valid jvm mode choice
            self["jvm_mode"].as_choice(["interactive", "headless"])
            # Ensure headless chosen on MacOS
            if value == "interactive" and sys.platform == "darwin":
                if strict:  # Report the failure
                    raise ValueError(
                        "ImageJ2 must be run headlessly on MacOS. <p>Visit "
                        '<a href="https://pyimagej.readthedocs.io/en/latest/'
                        'Initialization.html#interactive-mode">this site</a> '
                        "for more information."
                    )
                else:  # Assign a reasonable default
                    log_debug(
                        "ImageJ2 must be run headlessly on MacOS. Reconfiguring "
                        "jvm_mode to headless"
                    )
                    self["jvm_mode"] = "headless"
        if setting == "imagej_base_directory":
            # Overwrite default setting with the current directory
            if value == ".":
                self["imagej_base_directory"] = os.getcwd()
            # Ensure a valid directory
            if not os.path.exists(value):
                if strict:
                    raise ValueError("ImageJ base directory must be a valid path.")
                else:
                    log_debug(
                        "ImageJ base directory must be a valid path. Reconfiguring "
                        "imagej_base_directory to the current working directory."
                    )
                    self["imagej_base_directory"] = os.getcwd()


# napari-imagej uses confuse (https://confuse.readthedocs.io/en/latest/) to configure
# user settings.
settings = _NapariImageJSettings()
