"""
A module defining Java "Enum-like"s.
An enum-like can be created for any Enum-like Java types.

We define an Enum-like Java type as a Java type that
1. is stateless
2. has a no-args constructor

The enum-likes are designed for a rather narrow use case, described as follows:

Some Java functionality requires an Object implementing a particular interface.
That Object is usually chosen from a set of established implementations,
each created without variation (giving rise to the above constraints).

In such cases, we can abstract the interface to a JavaEnumLike and the implementations
to enumerations of that JavaEnumLike, as done below.

JavaEnumLikes are NOT intended for direct use. Instead, use enum_like() to obtain
the correct JavaEnumLike for a Java enum-like!
"""
from enum import Enum, auto
from typing import List

from napari_imagej.java import jc


class JavaEnumLike(Enum):
    """An Enum that is mocking a Java class"""

    def __init__(self, _):
        # Make ourselves aware of this enum
        enum_type = type(self)
        if enum_type not in _ENUM_LIKES:
            _ENUM_LIKES.append(enum_type)

    @staticmethod
    def java_type():
        """Obtains the backing Java type this enum is mocking"""


_ENUM_LIKES: List[JavaEnumLike] = []


def enum_like(java_type, default=None) -> type:
    """
    Checks for an "enum_like" for java_type

    NB we use == instead of "is" to check backing types.
    "is" ensures two variables point to the same memory,
    whereas "==" checks equality. We want the latter when checking classes.
    :param java_type: the type we'd like an enum-like for
    :param default: the return when we can't find an enum-like
    :return: an enum-like for java_type, or default if we can't find one.
    """
    for enum_like in _ENUM_LIKES:
        if java_type == enum_like.java_type():
            return enum_like
    return default


class OutOfBoundsFactory(JavaEnumLike):
    BORDER = auto()
    MIRROR_EXP_WINDOWING = auto()
    MIRROR_SINGLE = auto()
    MIRROR_DOUBLE = auto()
    PERIODIC = auto()

    @staticmethod
    def java_type():
        return jc.OutOfBoundsFactory
