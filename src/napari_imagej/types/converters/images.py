"""
scyjava Converters for converting between ImageJ ecosystem image types
(referred to collectively as "java image"s) and napari Image layers
"""

from typing import Any

from imagej.convert import java_to_xarray
from jpype import JArray, JByte
from napari.layers import Image
from napari.utils.colormaps import Colormap
from numpy import ones
from scyjava import Priority
from xarray import DataArray

from napari_imagej import nij
from napari_imagej.java import jc
from napari_imagej.types.converters import java_to_py_converter, py_to_java_converter
from napari_imagej.utilities.logging import log_debug


@java_to_py_converter(
    predicate=lambda obj: nij.ij.convert().supports(obj, jc.DatasetView),
    priority=Priority.VERY_HIGH + 1,
)
def _java_image_to_image_layer(image: Any) -> Image:
    """
    Converts a java image (i.e. something that can be converted into a DatasetView)
    into a napari Image layer.

    TODO: Pass xarray axis labels, coordinates to the Layer, once the Layer
    can understand them. See https://github.com/imagej/napari-imagej/issues/253.
    :param image: a java image
    :return: a napari Image layer
    """
    # Construct a DatasetView from the Java image
    view = nij.ij.convert().convert(image, jc.DatasetView)
    # Construct an xarray from the DatasetView
    xarr: DataArray = java_to_xarray(nij.ij, view.getData())
    # Construct a map of Image layer parameters
    kwargs = dict(
        data=xarr,
        metadata=getattr(xarr, "attrs", {}),
        name=view.getData().getName(),
    )
    if view.getColorTables() and view.getColorTables().size() > 0:
        if not jc.ColorTables.isGrayColorTable(view.getColorTables().get(0)):
            kwargs["colormap"] = _color_table_to_colormap(view.getColorTables().get(0))
    return Image(**kwargs)


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Image), priority=Priority.VERY_HIGH
)
def _image_layer_to_dataset(image: Image, **kwargs) -> "jc.Dataset":
    """
    Converts a napari Image layer into a Dataset.

    :param image: a napari Image layer
    :return: a Dataset
    """
    # Construct a dataset from the data
    dataset: "jc.Dataset" = nij.ij.py.to_dataset(image.data, **kwargs)

    # Clean up the axes
    axes = [
        x for x in [jc.Axes.X, jc.Axes.Y, jc.Axes.Z] if dataset.dimensionIndex(x) == -1
    ]
    for i in range(dataset.numDimensions()):
        axis = dataset.axis(i)
        # Overwrite EnumeratedAxes with LinearAxes
        if isinstance(axis, (jc.EnumeratedAxis, jc.DefaultLinearAxis)):
            # Copy the dim name, unless it's unnamed
            # in that case, assign it with X/Y/Z, if they aren't used already
            if any(x in axis.type().getLabel() for x in ["dim", "Unknown"]) and len(
                axes
            ):
                type = axes.pop(0)
            else:
                type = axis.type()
            # Use 1 for scale, and 0 for origin
            axis = jc.DefaultLinearAxis(type, 1, 0)
            dataset.setAxis(axis, i)
        # Set pixels as the unit, for lack of a better option
        axis.setUnit("pixels")

    # Add name
    dataset.setName(image.name)
    # Add color table, if the image uses a custom colormap
    if image.colormap.name != "gray":
        color_table = _colormap_to_color_table(image.colormap)
        dataset.initializeColorTables(1)
        dataset.setColorTable(color_table, 0)
    # Add properties
    properties = dataset.getProperties()
    for k, v in image.metadata.items():
        try:
            properties.put(nij.ij.py.to_java(k), nij.ij.py.to_java(v))
        except Exception:
            log_debug(f"Could not add property ({k}, {v}) to dataset {dataset}:")
    return dataset


def _colormap_to_color_table(cmap: Colormap):
    """
    Converts a napari Colormap into a SciJava ColorTable.
    :param cmap: The napari Colormap
    :return: A "equivalent" SciJava ColorTable
    """
    controls = [x / 255 for x in range(256)]
    py_values = cmap.map(controls)
    shape = py_values.shape
    j_values = JArray(JArray(JByte))(shape[1])
    for i in range(shape[1]):
        j_values[i] = JArray(JByte)(shape[0])
        for j in range(shape[0]):
            value = int(round(py_values[j, i] * 255))
            # map unsigned value to signed
            j_values[i][j] = value if value < 128 else value - 256

    return jc.ColorTable8(j_values)


def _color_table_to_colormap(ctable: "jc.ColorTable"):
    """
    Converts a SciJava ColorTable into a napari Colormap.
    :param ctable: The SciJava ColorTable
    :return: An "equivalent" napari Colormap
    """
    components = ctable.getComponentCount()
    bins = ctable.getLength()
    data = ones((bins, 4), dtype=float)
    for component in range(components):
        for bin in range(bins):
            data[bin, component] = float(ctable.get(component, bin)) / 255.0
    return Colormap(colors=data)
