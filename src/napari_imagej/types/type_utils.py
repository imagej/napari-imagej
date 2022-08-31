"""
A module containing utilities on python types.
"""
from napari_imagej.types import mappings


def _napari_layer_types():
    """A hardcoded set of types that should be displayable in napari"""
    return {
        **mappings.images(),
        **mappings.points(),
        **mappings.shapes(),
        **mappings.surfaces(),
        **mappings.labels(),
    }.keys()


def displayable_in_napari(data):
    """Determines whether data should be displayable in napari"""
    return any(filter(lambda x: isinstance(data, x), _napari_layer_types()))


def type_displayable_in_napari(type):
    """Determines whether an object of the given type could be displayed in napari"""
    return any(filter(lambda x: issubclass(type, x), _napari_layer_types()))
