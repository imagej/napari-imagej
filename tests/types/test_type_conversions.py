"""
A module testing napari_imagej.types.type_conversions
"""
from typing import List

import pytest
from jpype import JObject

from napari_imagej.types.enum_likes import OutOfBoundsFactory
from napari_imagej.types.type_hints import hint_map
from napari_imagej.utilities import _module_utils
from tests.utils import DummyModuleItem, jc


def test_direct_match_pairs():
    for jtype, ptype in hint_map().items():
        # Test that jtype inputs convert to ptype inputs
        input_item = DummyModuleItem(jtype=jtype, isInput=True, isOutput=False)
        assert _module_utils.type_hint_for(input_item) == ptype
        # Test that jtype outputs convert to ptype outputs
        output_item = DummyModuleItem(jtype=jtype, isInput=False, isOutput=True)
        assert _module_utils.type_hint_for(output_item) == ptype
        # Test that jtype boths convert to ptype boths
        IO_item = DummyModuleItem(jtype=jtype, isInput=True, isOutput=True)
        assert _module_utils.type_hint_for(IO_item) == ptype


def test_assignable_match_pairs():
    # Test that a java input NOT in ptypes but assignable to some type in ptypes
    # gets converted to a ptype
    assert jc.ArrayImg not in hint_map().items()
    input_item = DummyModuleItem(jtype=jc.ArrayImg, isInput=True, isOutput=False)
    assert _module_utils.type_hint_for(input_item) == "napari.layers.Image"

    # Test that a java output NOT in ptypes but assignable from some type in ptypes
    # gets converted to a ptype
    assert jc.EuclideanSpace not in hint_map().items()
    output_item = DummyModuleItem(jtype=jc.EuclideanSpace, isInput=False, isOutput=True)
    assert _module_utils.type_hint_for(output_item) == "napari.layers.Shapes"


def test_convertible_match_pairs():
    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert Integers into DoubleArrays; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    assert jc.DoubleArray not in hint_map().items()
    input_item = DummyModuleItem(jtype=jc.DoubleArray, isInput=True, isOutput=False)
    assert _module_utils.type_hint_for(input_item) == int

    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert DoubleArrays into strings; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    assert jc.DoubleArray not in hint_map().items()
    input_item = DummyModuleItem(jtype=jc.DoubleArray, isInput=False, isOutput=True)
    assert _module_utils.type_hint_for(input_item) == str

    # Test that a java both NOT in ptypes but convertible to/from some type in ptypes
    # gets converted to a ptype
    assert jc.DoubleArray not in hint_map().items()
    input_item = DummyModuleItem(jtype=jc.DoubleArray, isInput=True, isOutput=True)
    assert _module_utils.type_hint_for(input_item) == List[float]


def test_python_type_of_enum_like_IO():
    # Test that a pure input matches
    module_item = DummyModuleItem(
        jtype=jc.OutOfBoundsFactory, isInput=True, isOutput=False
    )
    assert _module_utils.type_hint_for(module_item) == OutOfBoundsFactory

    # Test that a mutable input does not match
    module_item._isOutput = True
    try:
        _module_utils.type_hint_for(module_item)
        pytest.fail()
    except ValueError:
        pass

    # Test that a pure output does not match the enum
    module_item._isInput = False
    assert _module_utils.type_hint_for(module_item) == str


def test_enum():
    p_type = _module_utils.type_hint_for(DummyModuleItem(jtype=jc.ItemIO))
    assert p_type.__name__ == "ItemIO"


def test_shape():
    p_type = _module_utils.type_hint_for(DummyModuleItem(jtype=jc.Shape))
    assert p_type == JObject
