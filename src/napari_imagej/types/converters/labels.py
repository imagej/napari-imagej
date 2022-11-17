"""
scyjava Converters for converting between ImgLib2 ImgLabelings
and napari Labels
"""
from imagej.convert import imglabeling_to_labeling
from labeling.Labeling import Labeling
from napari.layers import Labels
from scyjava import Priority

from napari_imagej.java import ij, jc
from napari_imagej.types.converters import java_to_py_converter, py_to_java_converter


def _labeling_to_layer(labeling: Labeling):
    """Converts a Labeling to a Labels layer"""
    img, data = labeling.get_result()
    layer = Labels(img, metadata={"pyLabelingData": data})
    return layer


def _layer_to_labeling(layer: Labels):
    """Converts a Labels layer to a Labeling"""
    if "pyLabelingData" in layer.metadata:
        metadata = vars(layer.metadata["pyLabelingData"])
        labeling = Labeling(shape=layer.data.shape)
        labeling.result_image = layer.data
        labeling.label_sets = metadata["labelSets"]
        labeling.metadata = metadata["metadata"]
        return labeling
    else:
        return Labeling.fromValues(layer.data)


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.ImgLabeling), priority=Priority.VERY_HIGH
)
def _imglabeling_to_layer(imgLabeling: "jc.ImgLabeling") -> Labels:
    """
    Converts a Java ImgLabeling to a napari Labels layer
    :param imgLabeling: the Java ImgLabeling
    :return: a Labels layer
    """
    labeling: Labeling = imglabeling_to_labeling(ij(), imgLabeling)
    return _labeling_to_layer(labeling)


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Labels), priority=Priority.VERY_HIGH
)
def _layer_to_imglabeling(layer: Labels) -> "jc.ImgLabeling":
    """
    Converts a napari Labels layer to a Java ImgLabeling
    :param layer: a Labels layer
    :return: the Java ImgLabeling
    """
    labeling: Labeling = _layer_to_labeling(layer)
    return ij().py.to_java(labeling)
