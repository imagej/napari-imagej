import pytest
import numpy as np
from napari_imagej._ntypes import _labeling_to_layer, _layer_to_labeling
from labeling.Labeling import Labeling


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

    exp_data = vars(exp_data)
    print(exp_data)
    act_data = vars(act_data)
    print(act_data)

    assert exp_data == act_data
