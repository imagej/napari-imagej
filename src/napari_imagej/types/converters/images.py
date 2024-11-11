"""
scyjava Converters for converting between ImageJ ecosystem image types
(referred to collectively as "java image"s) and napari Image layers
"""

from logging import getLogger
from typing import Any, List, Union

from imagej.convert import java_to_xarray
from jpype import JArray, JByte
from napari.layers import Image
from napari.utils.colormaps import Colormap
from numpy import ones, uint8
from scyjava import Priority
from xarray import DataArray

from napari_imagej import nij
from napari_imagej.java import jc
from napari_imagej.types.converters import java_to_py_converter, py_to_java_converter


@java_to_py_converter(
    predicate=lambda obj: nij.ij.convert().supports(obj, jc.DatasetView),
    priority=Priority.VERY_HIGH + 1,
)
def _java_image_to_image_layer(image: Any) -> Union[Image, List[Image]]:
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
    existing_ctables = view.getColorTables() and view.getColorTables().size() > 0
    data = view.getData()
    # Construct an xarray from the DatasetView
    xarr: DataArray = java_to_xarray(nij.ij, data)
    # General layer parameters
    kwargs = dict()
    kwargs["name"] = data.getName()
    kwargs["metadata"] = getattr(xarr, "attrs", {})

    # Channel-less data
    if "ch" not in xarr.dims:
        if existing_ctables:
            cmap = _color_table_to_colormap(view.getColorTables().get(0))
            kwargs["colormap"] = cmap
        pass
    # RGB data - set RGB flag
    elif xarr.sizes["ch"] in [3, 4]:
        kwargs["rgb"] = True
    # Channel data - but not RGB - need one layer per channel
    else:
        kwargs["blending"] = "additive"
        channels = []
        for d in range(xarr.sizes["ch"]):
            kw = kwargs.copy()
            kw["name"] = f"{kwargs['name']}[{d}]"
            if existing_ctables:
                cmap = _color_table_to_colormap(view.getColorTables().get(d))
                kw["colormap"] = cmap
            channels.append(Image(data=xarr.sel(ch=d), **kw))
        return channels
    return Image(data=xarr, **kwargs)


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Image), priority=Priority.VERY_HIGH
)
def _image_layer_to_dataset(image: Image, **kwargs) -> "jc.Dataset":
    """
    Converts a napari Image layer into a Dataset.

    :param image: a napari Image layer
    :return: a Dataset
    """
    # Define dimension order if necessary
    data = image.data
    if not hasattr(data, "dims") and "dim_order" not in kwargs:
        # NB "dim_i"s will be overwritten later
        dim_order = [f"dim_{i}" for i in range(len(data.shape))]
        # if RGB, last dimension is Channel
        if image.rgb:
            dim_order[-1] = "Channel"

        kwargs["dim_order"] = dim_order

    # Construct a dataset from the data
    dataset: "jc.Dataset" = nij.ij.py.to_dataset(data, **kwargs)

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

    # Set RGB
    if (
        image.rgb
        and dataset.dimensionIndex(jc.Axes.CHANNEL) > -1
        and image.dtype == uint8
    ):
        dataset.setRGBMerged(True)
    # or add color table, if the image uses a custom colormap
    elif image.colormap.name != "gray":
        color_table = _colormap_to_color_table(image.colormap)
        dataset.initializeColorTables(1)
        dataset.setColorTable(color_table, 0)
    # Add properties
    properties = dataset.getProperties()
    for k, v in image.metadata.items():
        try:
            properties.put(nij.ij.py.to_java(k), nij.ij.py.to_java(v))
        except Exception:
            getLogger("napari-imagej").debug(
                f"Could not add property ({k}, {v}) to dataset {dataset}:"
            )
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
    builtins = {
        jc.ColorTables.RED: "red",
        jc.ColorTables.GREEN: "green",
        jc.ColorTables.BLUE: "blue",
        jc.ColorTables.CYAN: "cyan",
        jc.ColorTables.MAGENTA: "magenta",
        jc.ColorTables.YELLOW: "yellow",
        jc.ColorTables.GRAYS: "gray",
    }
    if ctable in builtins:
        return builtins[ctable]

    components = ctable.getComponentCount()
    bins = ctable.getLength()
    data = ones((bins, 4), dtype=float)
    for component in range(components):
        for bin in range(bins):
            data[bin, component] = float(ctable.get(component, bin)) / 255.0
    cmap = Colormap(colors=data)
    # NB prevents napari from using cached colormaps
    cmap.name = str(ctable)

    return cmap
