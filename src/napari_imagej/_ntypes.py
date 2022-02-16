from napari.layers import Labels
from labeling.Labeling import Labeling


def _labeling_to_layer(labeling: Labeling):
    """Converts a Labeling to a Labels layer"""
    img, data = labeling.get_result()
    layer = Labels(img, metadata={"pyLabelingData": data})
    return layer

def _layer_to_labeling(layer: Labels):
    """Converts a Labels layer to a Labeling"""
    if layer.metadata["pyLabelingData"] is not None:
        metadata = vars(layer.metadata["pyLabelingData"])
        labeling = Labeling()
        labeling.result_image = layer.data
        labeling.image_resolution = layer.data.shape
        labeling.label_sets = metadata["labelSets"]
        labeling.img_filename = metadata["indexImg"]
        labeling.segmentation_source = dict.fromkeys(range(metadata["numSources"]), range(metadata["numSources"]))
        labeling.metadata = metadata["metadata"]
        return labeling
    else :
        return Labeling.fromValues(layer.data)
    