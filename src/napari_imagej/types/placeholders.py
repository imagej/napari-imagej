from enum import Enum, auto

from napari_imagej.setup_imagej import jc


class StructuringElement(Enum):
    FOUR_CONNECTED = auto()
    EIGHT_CONNECTED = auto()


class OutOfBoundsFactory(Enum):
    BORDER = auto()
    MIRROR_EXP_WINDOWING = auto()
    MIRROR_SINGLE = auto()
    MIRROR_DOUBLE = auto()
    PERIODIC = auto()


class TypePlaceholders(dict):
    """
    The definitive set of "placeholder"s for Java types.
    This map allows us to determine the best placeholder for
    Enum-like Java types. We define an Enum-like Java type as either:
    1. An enum constant
    2. An object with a no-args constant
    """

    def __init__(self):
        # StructuringElements
        self[jc.StructuringElement] = StructuringElement
        # OutOfBoundsFactories
        self[jc.OutOfBoundsFactory] = OutOfBoundsFactory

    def get(self, key, default):
        """
        Checks if key is in this dictionary.

        We must override this function to ensure that under the hood
        this dictionary checks over its keys with == instead of "is".
        "is" ensures two variables point to the same memory,
        whereas "==" checks equality. We want the latter when checking classes.
        """
        for clazz in self.keys():
            if clazz == key:
                return self[clazz]
        return default
