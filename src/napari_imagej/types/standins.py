"""
The definitive set of "standin"s for Java types.
A standin can be created for any Enum-like Java types.

We define an Enum-like Java type as either:
1. An enum constant
2. An object with a no-args constructor

The standin are designed for a rather narrow use case, described as follows:

Some Java functionality requires an Object implementing a particular interface.
That Object is usually chosen from a set of established implementations,
each created without variation (giving rise to the above constraints).

In such cases, we can abstract the interface to a standin and the implementations
to enumerations of that standin, as done below.

PythonStandins are NOT intended for direct use. Instead, use standin_for() to obtain
the correct PythonStandin for a Java enum-like!
"""
from enum import Enum, auto
from typing import List

from napari_imagej.java import jc


class PythonStandin(Enum):
    """An Enum that is mocking a Java class"""

    def __init__(self, _):
        # Make ourselves aware of this enum
        enum_type = type(self)
        if enum_type not in STANDINS:
            STANDINS.append(enum_type)

    @staticmethod
    def java_type():
        """Obtains the backing Java type this enum is mocking"""


STANDINS: List[PythonStandin] = []


def standin_for(java_type, default=None) -> type:
    """
    Checks for a standin for java_type

    NB we use == instead of "is" to check backing types.
    "is" ensures two variables point to the same memory,
    whereas "==" checks equality. We want the latter when checking classes.
    :param java_type: the type we'd like a standin for
    :param default: the return when we can't find a standin
    :return: a standin for java_type, or default if we can't find one.
    """
    # # First, check for an Enum
    # py_enum = py_enum_for(java_type)
    # if py_enum:
    #     return py_enum

    # Then, check for an EnumLike

    for standin in STANDINS:
        if java_type == standin.java_type():
            return standin
    return default


class OutOfBoundsFactory(PythonStandin):
    BORDER = auto()
    MIRROR_EXP_WINDOWING = auto()
    MIRROR_SINGLE = auto()
    MIRROR_DOUBLE = auto()
    PERIODIC = auto()

    @staticmethod
    def java_type():
        return jc.OutOfBoundsFactory
