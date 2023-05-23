"""
Cross-platform entry point into napari-imagej-enabled
napari viewer, with GUI support, even on macOS.
"""

import sys

import napari.__main__
from imagej import when_imagej_starts

from napari_imagej import settings

from .java import init_ij


def main():
    print("==> Initializing ImageJ2...")
    settings.enable_imagej_gui = True
    settings._gui_mode = "gui"
    init_ij()
    when_imagej_starts(_init_napari)


def _init_napari():
    print("==> Initializing napari...")
    napari.__main__.main()
    print("==> READY")


if __name__ == "__main__":
    sys.exit(main())
