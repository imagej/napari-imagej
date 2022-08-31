from typing import List

import pytest

from napari_imagej.types.mappings import ptypes
from napari_imagej.types.placeholders import OutOfBoundsFactory
from napari_imagej.utilities import _module_utils
from tests.utils import DummyModuleItem, jc

direct_match_pairs = [(jtype, ptype) for jtype, ptype in ptypes().items()]
assignable_match_pairs = [
    (jc.ArrayImg, "napari.layers.Image")  # ArrayImg -> RAI -> ImageData
]
convertible_match_pairs = [
    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert Integers into DoubleArrays; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    (jc.DoubleArray, int)
]
type_pairs = direct_match_pairs + assignable_match_pairs + convertible_match_pairs


@pytest.mark.parametrize("jtype, ptype", type_pairs)
def test_python_type_of_input_only(jtype, ptype):
    module_item = DummyModuleItem(jtype=jtype, isInput=True, isOutput=False)
    assert _module_utils.python_type_of(module_item) == ptype


direct_match_pairs = [(jtype, ptype) for jtype, ptype in ptypes().items()]
assignable_match_pairs = [
    # ImageData -> RAI -> EuclideanSpace
    (jc.EuclideanSpace, "napari.types.ImageData")
]
convertible_match_pairs = [
    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert DoubleArrays into strings; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    (jc.DoubleArray, str)  # DoubleArray -> String -> str
]
type_pairs = direct_match_pairs + convertible_match_pairs


@pytest.mark.parametrize("jtype, ptype", type_pairs)
def test_python_type_of_output_only(jtype, ptype):
    module_item = DummyModuleItem(jtype=jtype, isInput=False, isOutput=True)
    assert _module_utils.python_type_of(module_item) == ptype


direct_match_pairs = [(jtype, ptype) for jtype, ptype in ptypes().items()]
convertible_match_pairs = [(jc.DoubleArray, List[float])]
type_pairs = direct_match_pairs + convertible_match_pairs


@pytest.mark.parametrize("jtype, ptype", type_pairs)
def test_python_type_of_IO(jtype, ptype):
    module_item = DummyModuleItem(jtype=jtype, isInput=True, isOutput=True)
    assert _module_utils.python_type_of(module_item) == ptype


def test_python_type_of_placeholder_IO():
    # Test that a pure input matches
    module_item = DummyModuleItem(
        jtype=jc.OutOfBoundsFactory, isInput=True, isOutput=False
    )
    assert _module_utils.python_type_of(module_item) == OutOfBoundsFactory

    # Test that a mutable input does not match
    module_item._isOutput = True
    try:
        _module_utils.python_type_of(module_item)
        pytest.fail()
    except ValueError:
        pass

    # Test that a pure output does not match the enum
    module_item._isInput = False
    assert _module_utils.python_type_of(module_item) == str
