__version__ = "0.0.1.dev0"

from napari_imagej._napari_converters import init_napari_converters
from scyjava import when_jvm_starts

# Install napari <-> java converters
when_jvm_starts(lambda: init_napari_converters())
