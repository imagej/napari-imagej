from typing import Any, Dict, List
from jpype import JArray, JDouble
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
def box_mask(ij_fixture):
    ClosedWritableBox = jimport('net.imglib2.roi.geom.real.ClosedWritableBox')
    return ClosedWritableBox([20, 20], [40, 40])

@pytest.fixture
def polygon_mask(ij_fixture):
    ClosedWritablePolygon2D = jimport('net.imglib2.roi.geom.real.ClosedWritablePolygon2D')
    DoubleArr = JArray(JDouble)
    x = DoubleArr(3)
    y = DoubleArr(3)
    x[:] = [0, -3, 0]
    y[:] = [0, 0, -4]
    return ClosedWritablePolygon2D(x, y)

@pytest.fixture
def ellipse_layer():
    shp = Shapes()
    data = np.zeros((2, 2))
    data[0, :] = [30, 30] # ceter
    data[1, :] = [10, 10] # axes
    shp.add_ellipses(data)
    return shp

@pytest.fixture
def rectangle_layer_axis_aligned():
    shp = Shapes()
    data = np.zeros((2, 2))
    data[0, :] = [10, 10] # min. corner
    data[1, :] = [30, 30] # max. corner
    shp.add_rectangles(data)
    return shp

@pytest.fixture
def rectangle_layer_rotated():
    shp = Shapes()
    data = np.zeros((4, 2))
    data[0, :] = [0, 10]
    data[1, :] = [10, 0]
    data[2, :] = [0, -10]
    data[3, :] = [-10, 0]
    shp.add_rectangles(data)
    return shp

@pytest.fixture
def polygon_layer():
    shp = Shapes()
    data = np.zeros((3, 2))
    data[0, :] = [0, 0]
    data[1, :] = [3, 0]
    data[2, :] = [0, 4]
    shp.add_polygons(data)
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

def test_box_to_shapes(ij_fixture, box_mask):
    py_mask = ij_fixture.py.from_java(box_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == 'rectangle'
    data = py_mask.data
    assert len(data) == 1
    box_data = data[0]
    assert len(box_data) == 4
    assert np.array_equal(box_data[0], np.array([20, 20]))
    assert np.array_equal(box_data[1], np.array([40, 20]))
    assert np.array_equal(box_data[2], np.array([40, 40]))
    assert np.array_equal(box_data[3], np.array([20, 40]))

def assert_ROITree_conversion(ij, layer):
    roitree = ij.py.to_java(layer)
    ROITree = jimport('net.imagej.roi.ROITree')
    assert isinstance(roitree, ROITree)
    return roitree.children()


def test_shapes_to_ellipse(ij_fixture, ellipse_layer):
    # Assert shapes conversion to ellipse
    children = assert_ROITree_conversion(ij_fixture, ellipse_layer)
    assert children.size() == 1
    j_mask = children.get(0).data()
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

    
def test_shapes_to_rectangle_axis_aligned(ij_fixture, rectangle_layer_axis_aligned):
    # Assert shapes conversion to ellipse
    children = assert_ROITree_conversion(ij_fixture, rectangle_layer_axis_aligned)
    assert children.size() == 1
    j_mask = children.get(0).data()
    ClosedWritableBox = jimport('net.imglib2.roi.geom.real.ClosedWritableBox')
    assert isinstance(j_mask, ClosedWritableBox)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Assert center position
    center = j_mask.center().positionAsDoubleArray()
    center = ij_fixture.py.from_java(center)
    assert center == [20, 20]
    # Assert side lengths   
    assert j_mask.sideLength(0) == 20
    assert j_mask.sideLength(1) == 20

def point_assertion(mask, pt: list, expected: bool) -> None:
    arr = JArray(JDouble)(len(pt))
    arr[:] = pt
    RealPoint = jimport('net.imglib2.RealPoint')
    r = RealPoint(arr)
    assert mask.test(r) == expected


def test_shapes_to_rectangle_rotated(ij_fixture, rectangle_layer_rotated):
    # Assert shapes conversion to ellipse
    children = assert_ROITree_conversion(ij_fixture, rectangle_layer_rotated)
    assert children.size() == 1
    j_mask = children.get(0).data()
    ClosedWritablePolygon2D = jimport('net.imglib2.roi.geom.real.ClosedWritablePolygon2D')
    assert isinstance(j_mask, ClosedWritablePolygon2D)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Test some points
    point_assertion(j_mask, [0, 0], True)
    point_assertion(j_mask, [5, 5], True)
    point_assertion(j_mask, [5, 6], False)


def test_shapes_to_polygon(ij_fixture, polygon_layer):
    # Assert shapes conversion to ellipse
    children = assert_ROITree_conversion(ij_fixture, polygon_layer)
    assert children.size() == 1
    j_mask = children.get(0).data()
    ClosedWritablePolygon2D = jimport('net.imglib2.roi.geom.real.ClosedWritablePolygon2D')
    assert isinstance(j_mask, ClosedWritablePolygon2D)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Test some points
    point_assertion(j_mask, [0, 0], True)
    point_assertion(j_mask, [3, 0], True)
    point_assertion(j_mask, [2, 1], True)
    point_assertion(j_mask, [5, 6], False)


def test_polygon_to_shapes(ij_fixture, polygon_mask):
    py_mask = ij_fixture.py.from_java(polygon_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == 'polygon'
    data = py_mask.data
    assert len(data) == 1
    polygon_data = data[0]
    assert len(polygon_data) == 3
    assert np.array_equal(polygon_data[0], np.array([0, 0]))
    assert np.array_equal(polygon_data[1], np.array([-3, 0]))
    assert np.array_equal(polygon_data[2], np.array([0, -4]))
