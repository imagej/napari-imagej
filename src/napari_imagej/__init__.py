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

__version__ = "0.0.1.dev0"
