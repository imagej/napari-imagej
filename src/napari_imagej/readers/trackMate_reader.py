"""
A napari reader plugin for importing TrackMate data stored in XML
"""

import xml.etree.ElementTree as ET

from napari.utils import progress
from scyjava import jimport

from napari_imagej import nij
from napari_imagej.java import jc
from napari_imagej.types.converters.trackmate import (
    model_and_image_to_tracks,
    trackmate_present,
)


def napari_get_reader(path):
    """Returns the reader if it is suitable for the file described at path"""
    if isinstance(path, list):
        # reader plugins may be handed single path, or a list of paths.
        # if it is a list, it is assumed to be an image stack...
        # so we are only going to look at the first file.
        path = path[0]

    # if we know we cannot read the file, we immediately return None.
    if not path.endswith(".xml"):
        return None

    # Determine whether TrackMate available
    if not trackmate_present():
        return None

    # Ensure that the xml file is a TrackMate file
    if not ET.parse(path).getroot().tag == "TrackMate":
        return None

    # otherwise we return the *function* that can read ``path``.
    return reader_function


def reader_function(path):
    pbr = progress(total=4, desc="Importing TrackMate XML: Starting JVM")
    ij = nij.ij
    TmXMLReader = jimport("fiji.plugin.trackmate.io.TmXmlReader")
    pbr.update()

    pbr.set_description("Importing TrackMate XML: Building Model")
    instance = TmXMLReader(jc.File(path))
    model = instance.getModel()
    imp = instance.readImage()
    pbr.update()

    pbr.set_description("Importing TrackMate XML: Converting Image")
    py_imp = ij.py.from_java(imp)
    pbr.update()

    pbr.set_description("Importing TrackMate XML: Converting Tracks and ROIs")
    py_tracks, py_labels = model_and_image_to_tracks(model, imp)
    pbr.update()

    # Return data
    pbr.close()
    return [
        (py_imp.data, {"name": py_imp.name}, "image"),
        (py_tracks.data, {"name": py_tracks.name}, "tracks"),
        (py_labels.data, {"name": py_labels.name}, "labels"),
    ]
