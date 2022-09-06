from enum import Enum

from napari_imagej.types.enums import py_enum_for
from tests.utils import jc


def test_py_enum_for():
    """
    A regression test ensuring that py_enum_for produces a Python Enum
    equivalent to SciJava Common's ItemIO Enum.
    """
    java_enum = jc.ItemIO
    py_enum = py_enum_for(java_enum.class_)
    assert issubclass(py_enum, Enum)
    for p, j in zip(py_enum, java_enum.values()):
        assert p.name == str(j.toString())
        assert p.value == j
