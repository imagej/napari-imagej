"""
scyjava Converters for converting between ImageJ ecosystem image types
(referred to collectively as "java image"s) and napari Image layers
"""

from typing import Any

from imagej.convert import java_to_xarray
from imagej.dims import _has_axis
from jpype import JArray, JByte
from napari.layers import Image
from napari.utils.colormaps import Colormap
from numpy import ones
from scyjava import Priority, isjava
from xarray import DataArray

from napari_imagej.java import ij, jc
from napari_imagej.types.converters import java_to_py_converter, py_to_java_converter
from napari_imagej.utilities.logging import log_debug


@java_to_py_converter(
    predicate=lambda obj: isjava(obj) and ij().convert().supports(obj, jc.DatasetView),
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
    view = ij().convert().convert(image, jc.DatasetView)
    # Construct an xarray from the DatasetView
    xarr: DataArray = java_to_xarray(ij(), view.getData())
    # Construct metadata
    metadata = getattr(xarr, "attrs", {}).copy()
    metadata["dims"] = xarr.dims
    metadata["coords"] = xarr.coords
    # Construct a map of Image layer parameters
    kwargs = dict(
        data=xarr,
        metadata=metadata,
        name=view.getData().getName(),
    )
    if view.getColorTables() and view.getColorTables().size() > 0:
        if not jc.ColorTables.isGrayColorTable(view.getColorTables().get(0)):
            kwargs["colormap"] = _color_table_to_colormap(view.getColorTables().get(0))
    return Image(**kwargs)


def _can_convert_img_plus(obj: Any):
    can_convert = isjava(obj) and ij().convert().supports(obj, jc.ImgPlus)
    has_axis = _has_axis(obj)
    return can_convert and has_axis


@java_to_py_converter(predicate=_can_convert_img_plus, priority=Priority.VERY_HIGH)
def _dataset_to_image(image: Any) -> Image:
    imgplus = ij().convert().convert(image, jc.ImgPlus)
    # Construct a dataset from the data
    kwargs = dict(
        data=ij().py.from_java(imgplus.getImg()),
        name=imgplus.getName(),
    )
    if imgplus.getColorTableCount() > 0 and imgplus.getColorTable(0):
        kwargs["colormap"] = _color_table_to_colormap(imgplus.getColorTable(0))
    return Image(**kwargs)


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Image), priority=Priority.VERY_HIGH
)
def _image_layer_to_dataset(image: Image) -> "jc.Dataset":
    """
    Converts a napari Image layer into a Dataset.

    :param image: a napari Image layer
    :return: a Dataset
    """
    # Construct a dataset from the data
    dataset: "jc.Dataset" = ij().py.to_dataset(image.data)
    # We need an "X" axis, or ImageJ2 doesn't know how to display the dataset
    if dataset.dimensionIndex(jc.Axes.X) == -1:
        # find the first "unknown" dimension
        for i in range(dataset.numDimensions()):
            axis = dataset.axis(i)
            if "dim" in axis.type().getLabel():
                # and set it to "X"
                axis.setType(jc.Axes.X)
                break
    # We need an "Y" axis, or ImageJ2 doesn't know how to display the dataset
    if dataset.dimensionIndex(jc.Axes.Y) == -1:
        # find the first "unknown" dimension
        for i in range(dataset.numDimensions()):
            axis = dataset.axis(i)
            if "dim" in axis.type().getLabel():
                # and set it to "Y"
                axis.setType(jc.Axes.Y)
                break

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
            properties.put(ij().py.to_java(k), ij().py.to_java(v))
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
