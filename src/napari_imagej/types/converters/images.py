"""
scyjava Converters for converting between ImgLib2 Imgs
and napari Images
"""

from napari.layers import Image
from scyjava import Priority

from napari_imagej.java import ij, jc
from napari_imagej.types.converters import py_to_java_converter


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Image), priority=Priority.VERY_HIGH
)
def _image_to_img(image: Image) -> "jc.Img":
    data = image.data
    return ij().py.to_java(data)
