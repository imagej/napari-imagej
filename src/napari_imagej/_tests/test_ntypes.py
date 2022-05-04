from typing import Any, Dict, List
import pytest
import numpy as np
from napari_imagej._ntypes import _labeling_to_layer, _layer_to_labeling
from labeling.Labeling import Labeling
from napari.layers import Labels

def assert_labels_equality(
    exp: Dict[str, Any], act: Dict[str, Any], ignored_keys: List[str]
):
    for key in exp.keys():
        if key in ignored_keys:
            continue
        assert exp[key] == act[key]

@pytest.fixture(scope="module")
def py_labeling():

    a = np.zeros((4,4), np.int32)
    a[:2] = 1
    example1_images = []
    example1_images.append(a)
    b = a.copy()
    b[:2] =2
    example1_images.append(np.flip(b.transpose()))
    c = a.copy()
    c[:2] =3
    example1_images.append(np.flip(c))
    d = a.copy()
    d[:2] =4
    example1_images.append(d.transpose())

    merger = Labeling.fromValues(np.zeros((4, 4), np.int32))
    merger.iterate_over_images(example1_images, source_ids=['a', 'b', 'c', 'd'])
    return merger

def test_labeling_circular_equality(py_labeling):
    expected: Labeling = py_labeling
    actual: Labeling = _layer_to_labeling(_labeling_to_layer(py_labeling))

    exp_img, exp_data = expected.get_result()
    act_img, act_data = actual.get_result()

    assert np.array_equal(exp_img, act_img)

    assert_labels_equality(
        vars(exp_data),
        vars(act_data),
        ["numSources", "indexImg"]
    )

def test_labeling_to_labels(py_labeling):
    """Tests data equality after conversion from labeling to labels"""
    labels: Labels = _labeling_to_layer(py_labeling)
    # For a labeling, we need to persist image and metadata
    exp_img, exp_data = py_labeling.get_result()
    act_img = labels.data
    act_data = labels.metadata["pyLabelingData"]
    assert np.array_equal(exp_img, act_img)
    assert exp_data == act_data

def test_labels_to_labeling(py_labeling):
    """Tests data equality after conversion from labels to labeling"""
    labels: Labels = _labeling_to_layer(py_labeling)
    labeling: Labeling = _layer_to_labeling(labels)
    # For a labels, we need to persist image
    exp_img = labels.data
    act_img, _ = labeling.get_result()
    assert np.array_equal(exp_img, act_img)
