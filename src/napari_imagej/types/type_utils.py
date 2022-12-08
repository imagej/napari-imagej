"""
A module containing useful functions for operating on python types
"""
from napari_imagej.types import type_hints


def _napari_layer_types():
    """A hardcoded set of types that should be displayable in napari"""
    layer_hints = [
        *type_hints.images(),
        *type_hints.points(),
        *type_hints.shapes(),
        *type_hints.surfaces(),
        *type_hints.labels(),
    ]

    return list(map(lambda hint: hint.type, layer_hints))


def displayable_in_napari(data):
    """Determines whether data should be displayable in napari"""
    return any(filter(lambda x: isinstance(data, x), _napari_layer_types()))


def type_displayable_in_napari(type):
    """Determines whether an object of the given type could be displayed in napari"""
    return any(filter(lambda x: issubclass(type, x), _napari_layer_types()))
