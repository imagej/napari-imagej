from napari.layers import Labels
from labeling.Labeling import Labeling


class NapariTypes():
    """
    Responsible for conversion between the types normally used by pyimagej and the types normally used by napari.
    """
    def __init__(self):
        self._to_converters : Dict[Type, Callable] = {}
        self._from_converters : Dict[Type, Callable] = {}

        # Default converters
        self.add_to_converter(Labeling, _labeling_to_layer)
        self.add_from_converter(Labels, _layer_to_labeling)

    def add_to_converter(self, key: Type, value: Callable):
        """Add a converter from a napari type to a pyimagej type"""
        self._to_converters[key] = value

    def add_from_converter(self, key: Type, value: Callable):
        """Add a converter from a pyimagej type to a napari type"""
        self._from_converters[key] = value
    
    def to_napari(self, object: Any):
        """Return a version of key that napari prefers"""
        return self._convert(object, self._to_converters)

    def from_napari(self, object: Any):
        """Return a version of key that pyimagej prefers"""
        return self._convert(object, self._from_converters)

    def _convert(self, object: Any, map: Dict[Type, Callable]) -> Any:
        """Return a converted object, if a converter exists for its type"""
        key: Type = type(object)
        if key in map:
            converter = map[key]
            object = converter(object)
        return object

def _labeling_to_layer(labeling: Labeling):
    """Converts a Labeling to a Labels layer"""
    img, data = labeling.get_result()
    layer = Labels(img, metadata={"pyLabelingData": data})
    return layer

def _layer_to_labeling(layer: Labels):
    """Converts a Labels layer to a Labeling"""
    if layer.metadata["pyLabelingData"] is not None:
        metadata = vars(layer.metadata["pyLabelingData"])
        labeling = Labeling(shape=layer.data.shape)
        labeling.result_image = layer.data
        labeling.label_sets = metadata["labelSets"]
        labeling.metadata = metadata["metadata"]
        return labeling
    else :
        return Labeling.fromValues(layer.data, layer.data.shape)
    