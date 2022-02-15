from typing import Any, Dict, List
import pytest
import numpy as np
from scyjava import jimport
import imagej
from napari_imagej._ntypes import _labeling_to_layer, _layer_to_labeling
from labeling.Labeling import Labeling
from napari.layers import Labels, Shapes

@pytest.fixture()
def ij_fixture():
    return imagej.init()

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

@pytest.fixture
def ellipse_mask(ij_fixture):
    ClosedWritableEllipsoid = jimport('net.imglib2.roi.geom.real.ClosedWritableEllipsoid')
    return ClosedWritableEllipsoid([20, 20], [10, 10])

@pytest.fixture
def ellipse_layer():
    shp = Shapes()
    data = np.zeros((2, 2))
    data[0, :] = [30, 30] # ceter
    data[1, :] = [10, 10] # axes
    shp.add_ellipses(data)
    return shp

def test_ellipse_to_shapes(ij_fixture, ellipse_mask):
    py_mask = ij_fixture.py.from_java(ellipse_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == 'ellipse'
    data = py_mask.data
    assert len(data) == 1
    ellipse_data = data[0]
    assert len(ellipse_data) == 4
    assert np.array_equal(ellipse_data[0], np.array([10, 10]))
    assert np.array_equal(ellipse_data[1], np.array([30, 10]))
    assert np.array_equal(ellipse_data[2], np.array([30, 30]))
    assert np.array_equal(ellipse_data[3], np.array([10, 30]))

def test_shapes_to_ellipse(ij_fixture, ellipse_layer):
    # Assert shapes conversion to ellipse
    j_mask = ij_fixture.py.to_java(ellipse_layer)
    ClosedWritableEllipsoid = jimport('net.imglib2.roi.geom.real.ClosedWritableEllipsoid')
    assert isinstance(j_mask, ClosedWritableEllipsoid)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Assert center position
    center = j_mask.center().positionAsDoubleArray()
    center = ij_fixture.py.from_java(center)
    assert center == [30, 30]
    # Assert semi-axis lengths   
    assert j_mask.semiAxisLength(0) == 10
    assert j_mask.semiAxisLength(1) == 10

    
