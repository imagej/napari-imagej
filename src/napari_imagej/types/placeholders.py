"""
The definitive set of "placeholder"s for Java types.
This map allows us to determine the best placeholder for
Enum-like Java types. We define an Enum-like Java type as either:
1. An enum constant
2. An object with a no-args constant
"""
from enum import Enum, auto
from typing import List

from napari_imagej.setup_imagej import jc


class PythonStandin(Enum):
    """An Enum that is mocking a Java class"""

    def __init__(self, _):
        # Make ourselves aware of this enum
        enum_type = type(self)
        if enum_type not in PLACEHOLDERS:
            PLACEHOLDERS.append(enum_type)

    @staticmethod
    def backing_type():
        """Obtains the backing Java type this enum is mocking"""


PLACEHOLDERS: List[PythonStandin] = []


def get_placeholder(java_type, default=None) -> type:
    """
    Checks for a placeholder for java_type

    NB we use == instead of "is" to check backing types.
    "is" ensures two variables point to the same memory,
    whereas "==" checks equality. We want the latter when checking classes.
    :param java_type: the type we'd like a placeholder for
    :param default: the return when we can't find a placeholder
    :return: a placeholder for java_type, or default if we can't find one.
    """
    for placeholder in PLACEHOLDERS:
        if java_type == placeholder.backing_type():
            return placeholder
    return default


class StructuringElement(PythonStandin):
    FOUR_CONNECTED = auto()
    EIGHT_CONNECTED = auto()

    @staticmethod
    def backing_type():
        return jc.StructuringElement


class OutOfBoundsFactory(PythonStandin):
    BORDER = auto()
    MIRROR_EXP_WINDOWING = auto()
    MIRROR_SINGLE = auto()
    MIRROR_DOUBLE = auto()
    PERIODIC = auto()

    @staticmethod
    def backing_type():
        return jc.OutOfBoundsFactory
