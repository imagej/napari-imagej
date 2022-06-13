from labeling.Labeling import Labeling
from napari.layers import Labels


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
