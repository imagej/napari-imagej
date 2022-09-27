"""
scyjava Converters for converting between ImgLib2 Imgs
and napari Images
"""

from jpype import JArray, JByte
from napari.layers import Image
from napari.utils.colormaps import Colormap
from scyjava import Priority

from napari_imagej.java import ij, jc
from napari_imagej.types.converters import py_to_java_converter


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Image), priority=Priority.VERY_HIGH
)
def _image_to_dataset(image: Image) -> "jc.Dataset":
    # Construct a dataset from the data
    data = image.data
    dataset: "jc.Dataset" = ij().py._numpy_to_dataset(data)
    # Add name
    dataset.setName(image.name)
    # Add color table, if the image uses a custom colormap
    if image.colormap.name != "gray":
        color_table = _colormap_to_colorTable(image.colormap)
        dataset.initializeColorTables(1)
        dataset.setColorTable(color_table, 0)
    return dataset


def _colormap_to_colorTable(cmap: Colormap):
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
