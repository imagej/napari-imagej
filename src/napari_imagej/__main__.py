"""
Cross-platform entry point into napari-imagej-enabled
napari viewer, with GUI support, even on macOS.
"""

import sys

import napari.__main__
from imagej import init, when_imagej_starts

from napari_imagej import settings
from napari_imagej.java import _configure_imagej, init_ij, jc
from napari_imagej.utilities.event_subscribers import UIShownListener


def main():
    print("==> Initializing ImageJ2...")
    settings.enable_imagej_gui = True
    settings._gui_mode = "gui"
    when_imagej_starts(configure_imagej)
    # NB this must be the LAST callback to run, as it blocks
    when_imagej_starts(_init_napari)
    init(**_configure_imagej())


def configure_imagej(ij):
    init_ij()

    UIShownListener().onEvent(jc.UIShownEvent(ij.ui().getDefaultUI()))


def _init_napari(ij):
    print("==> Initializing napari...")
    # The following call will block until napari is closed
    sys.argv.extend(["--with", "napari-imagej"])
    napari.__main__.main()
    # Once napari is closed, close ImageJ2
    print("==> Disposing ImageJ2...")
    # The gateway will block so long as there is a visible UI.
    # We closed napari, so we also want to close imagej.
    # Thus we dispose all visible UIs.
    for ui in ij.ui().getVisibleUIs():
        ui.dispose()


if __name__ == "__main__":
    sys.exit(main())
