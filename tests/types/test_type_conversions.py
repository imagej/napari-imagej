"""
A module testing napari_imagej.types.type_conversions
"""
from typing import List

import pytest
from jpype import JObject

from napari_imagej.types.enum_likes import OutOfBoundsFactory
from napari_imagej.types.type_hints import type_hints
from napari_imagej.utilities import _module_utils
from tests.utils import DummyModuleItem, jc


def test_direct_match_pairs():
    for hint in type_hints():
        # Test that jtype inputs convert to ptype inputs
        input_item = DummyModuleItem(jtype=hint.type, isInput=True, isOutput=False)
        assert _module_utils.type_hint_for(input_item) == hint.hint
        # Test that jtype outputs convert to ptype outputs
        output_item = DummyModuleItem(jtype=hint.type, isInput=False, isOutput=True)
        assert _module_utils.type_hint_for(output_item) == hint.hint
        # Test that jtype boths convert to ptype boths
        IO_item = DummyModuleItem(jtype=hint.type, isInput=True, isOutput=True)
        assert _module_utils.type_hint_for(IO_item) == hint.hint


def test_assignable_match_pairs():
    hint_domain = list(filter(lambda hint: hint.type, type_hints()))
    # Suppose you need a hint for a Java parameter a that is NOT in hint_map,
    # but type b <: a IS in hint_map. That hint would apply then to inputs,
    # due to argument covariance.
    #
    # For example, suppose you need the type hint for EuclidenSpace. It is not in the
    # hint map, BUT Img is. Since an Img IS a EuclideanSpace, the type hint would also
    # apply to EuclideanSpace INPUTS because of argument covariance.
    assert jc.EuclideanSpace not in hint_domain
    input_item = DummyModuleItem(jtype=jc.EuclideanSpace, isInput=True, isOutput=False)
    assert _module_utils.type_hint_for(input_item) == "napari.layers.Labels"

    # Suppose you need a hint for a Java parameter a that is NOT in hint_map,
    # but type b :> a IS in hint_map. That hint would apply then to returns,
    # due to return contravariance.
    #
    # For example, suppose you need the type hint for ArrayImg. It is not in the
    # hint map, BUT Img is. Since an ArrayImg IS an Img, the type hint would also
    # apply to ArrayImg OUTPUTS because of return contravariance.
    assert jc.ArrayImg not in hint_domain
    output_item = DummyModuleItem(jtype=jc.ArrayImg, isInput=False, isOutput=True)
    assert _module_utils.type_hint_for(output_item) == "napari.layers.Image"


def test_convertible_match_pairs():
    hint_domain = list(map(lambda hint: hint.type, type_hints()))
    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert Integers into DoubleArrays; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    assert jc.DoubleArray not in hint_domain
    input_item = DummyModuleItem(jtype=jc.DoubleArray, isInput=True, isOutput=False)
    assert _module_utils.type_hint_for(input_item) == int

    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert Boolean[]s into DoubleArrays; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    assert jc.DoubleArray not in hint_domain
    input_item = DummyModuleItem(jtype=jc.DoubleArray, isInput=False, isOutput=True)
    assert _module_utils.type_hint_for(input_item) == List[bool]

    # Test that a java both NOT in ptypes but convertible to/from some type in ptypes
    # gets converted to a ptype
    assert jc.DoubleArray not in hint_domain
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

    # Test that a pure output does not match the enum - it matches Boolean[] instead
    # because the DefaultConverter can convert an OutOfBoundsFactory into a Boolean[].
    module_item._isInput = False
    assert _module_utils.type_hint_for(module_item) == List[bool]


def test_enum():
    p_type = _module_utils.type_hint_for(DummyModuleItem(jtype=jc.ItemIO))
    assert p_type.__name__ == "ItemIO"


def test_shape():
    p_type = _module_utils.type_hint_for(DummyModuleItem(jtype=jc.Shape))
    assert p_type == JObject
