"""
napari-imagej provides a graphical wrapper for the PyImageJ project, exposed as a
plugin for the napari application.

There are two advantages to using napari-imagej over PyImageJ. The obvious advantage
is the graphical interface, easing the use of PyImageJ functionality.

The secondary advantage of napari-imagej is its ability to automatically convert
data between equivalent Java and Python data types;
the plugin assumes the responsibility of converting napari Layers, numpy arrays,
Python primitives, etc. into Java equivalents right before any calls to ImageJ2
(Java) functionality, and takes care to convert any Java outputs back into Python
for display.

napari-imagej is NOT designed to be used on its own; instead, it should be launched
from within the napari application. Please see (https://napari.org/stable/#installation)
to get started using the napari application. Once napari is installed, you can then
add napari-imagej as a plugin. Please see (https://www.napari-hub.org/) for a list
of available plugins, including napari-imagej.
"""
__version__ = "0.0.1.dev0"
