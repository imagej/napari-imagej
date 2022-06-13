__version__ = "0.0.1.dev0"

from scyjava import when_jvm_starts

from napari_imagej._napari_converters import init_napari_converters

# Install napari <-> java converters
when_jvm_starts(init_napari_converters)
