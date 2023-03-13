"""
Cross-platform entry point into napari-imagej-enabled
napari viewer, with GUI support, even on macOS.
"""

import sys

import napari.__main__

from .java import init_ij


def main():
    print("==> Initializing ImageJ2...")
    init_ij(force_gui=True)
    print("==> Initializing napari...")
    napari.__main__.main()
    print("==> READY")


if __name__ == "__main__":
    sys.exit(main())
