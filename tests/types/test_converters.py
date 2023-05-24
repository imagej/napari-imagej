"""
A module testing napari_imagej.types.converters
"""
from typing import Any, Dict, List

import numpy as np
import pytest
from jpype import JArray, JDouble
from labeling.Labeling import Labeling
from napari.layers import Image, Labels, Points, Shapes, Surface

from napari_imagej.types.converters.labels import _labeling_to_layer, _layer_to_labeling
from napari_imagej.types.enum_likes import OutOfBoundsFactory
from napari_imagej.types.enums import _ENUMS, py_enum_for
from napari_imagej.types.type_conversions import type_hint_for
from tests.utils import DummyModuleItem, jc


def assert_labels_equality(
    exp: Dict[str, Any], act: Dict[str, Any], ignored_keys: List[str]
):
    for key in exp.keys():
        if key in ignored_keys:
            continue
        assert exp[key] == act[key]


@pytest.fixture(scope="module")
def py_labeling() -> Labeling:
    a = np.zeros((4, 4), np.int32)
    a[:2] = 1
    example1_images = []
    example1_images.append(a)
    b = a.copy()
    b[:2] = 2
    example1_images.append(np.flip(b.transpose()))
    c = a.copy()
    c[:2] = 3
    example1_images.append(np.flip(c))
    d = a.copy()
    d[:2] = 4
    example1_images.append(d.transpose())

    merger = Labeling.fromValues(np.zeros((4, 4), np.int32))
    merger.iterate_over_images(example1_images, source_ids=["a", "b", "c", "d"])
    return merger


@pytest.fixture(scope="module")
def labels_with_metadata(py_labeling: Labeling) -> Labels:
    img, data = py_labeling.get_result()
    return Labels(img, metadata={"pyLabelingData": data})


@pytest.fixture(scope="module")
def labels_without_metadata(py_labeling: Labeling) -> Labels:
    img, _ = py_labeling.get_result()
    return Labels(img)


@pytest.fixture(scope="module")
def imgLabeling(ij):
    img = np.zeros((4, 4), dtype=np.int32)
    img[:2, :2] = 6
    img[:2, 2:] = 3
    img[2:, :2] = 7
    img[2:, 2:] = 4
    img_java = ij.py.to_java(img)
    sets = [[], [1], [2], [1, 2], [2, 3], [3], [1, 4], [3, 4]]
    sets = [set(i) for i in sets]
    sets_java = ij.py.to_java(sets)

    return jc.ImgLabeling.fromImageAndLabelSets(img_java, sets_java)


def test_labeling_circular_equality(py_labeling):
    expected: Labeling = py_labeling
    actual: Labeling = _layer_to_labeling(_labeling_to_layer(py_labeling))

    exp_img, exp_data = expected.get_result()
    act_img, act_data = actual.get_result()

    assert np.array_equal(exp_img, act_img)

    assert_labels_equality(vars(exp_data), vars(act_data), ["numSources", "indexImg"])


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


def test_labels_with_metadata_to_imgLabeling(ij, labels_with_metadata):
    converted: "jc.ImgLabeling" = ij.py.to_java(labels_with_metadata)
    act_img: Image = ij.py.from_java(converted.getIndexImg())
    assert np.array_equal(labels_with_metadata.data, act_img.data)


def test_labels_with_metadata_circular(ij, labels_with_metadata):
    converted: "jc.ImgLabeling" = ij.py.to_java(labels_with_metadata)
    converted_back: Labels = ij.py.from_java(converted)
    exp_img: np.ndarray = labels_with_metadata.data
    act_img: np.ndarray = converted_back.data
    assert np.array_equal(exp_img, act_img)


def test_labels_without_metadata_to_imgLabeling(ij, labels_without_metadata):
    converted: "jc.ImgLabeling" = ij.py.to_java(labels_without_metadata)
    act_img: np.ndarray = ij.py.from_java(converted.getIndexImg())
    np.array_equal(labels_without_metadata.data, act_img.data)


def test_labels_without_metadata_circular(ij, labels_without_metadata):
    converted: "jc.ImgLabeling" = ij.py.to_java(labels_without_metadata)
    converted_back: Labels = ij.py.from_java(converted)
    exp_img: np.ndarray = labels_without_metadata.data
    act_img: np.ndarray = converted_back.data
    np.array_equal(exp_img, act_img)


def test_imgLabeling_to_labels(ij, imgLabeling):
    converted: Labels = ij.py.from_java(imgLabeling)
    exp_img: np.ndarray = ij.py.from_java(imgLabeling.getIndexImg())
    np.array_equal(exp_img.data, converted.data)


# -- SHAPES / ROIS -- #


def _assert_ROITree_conversion(ij, layer):
    roitree = ij.py.to_java(layer)
    assert isinstance(roitree, jc.ROITree)
    return roitree.children()


def _point_assertion(mask, pt: list, expected: bool) -> None:
    arr = JArray(JDouble)(len(pt))
    arr[:] = pt
    r = jc.RealPoint(arr)
    assert mask.test(r) == expected


# -- ELLIPSES -- #


@pytest.fixture
def ellipse_mask(ij):
    return jc.ClosedWritableEllipsoid([20, 20], [10, 10])


@pytest.fixture
def ellipse_layer():
    shp = Shapes()
    data = np.zeros((2, 2))
    data[0, :] = [30, 30]  # ceter
    data[1, :] = [10, 10]  # axes
    shp.add_ellipses(data)
    return shp


def test_ellipse_mask_to_layer(ij, ellipse_mask):
    py_mask = ij.py.from_java(ellipse_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == "ellipse"
    data = py_mask.data
    assert len(data) == 1
    ellipse_data = data[0]
    assert len(ellipse_data) == 4
    assert np.array_equal(ellipse_data[0], np.array([10, 10]))
    assert np.array_equal(ellipse_data[1], np.array([30, 10]))
    assert np.array_equal(ellipse_data[2], np.array([30, 30]))
    assert np.array_equal(ellipse_data[3], np.array([10, 30]))


def test_ellipse_layer_to_mask(ij, ellipse_layer):
    # Assert shapes conversion to ellipse
    children = _assert_ROITree_conversion(ij, ellipse_layer)
    assert children.size() == 1
    j_mask = children.get(0).data()
    assert isinstance(j_mask, jc.ClosedWritableEllipsoid)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Assert center position
    j_center = j_mask.center().positionAsDoubleArray()
    py_center = ij.py.from_java(j_center)
    assert np.array_equal(j_center, py_center)
    # Assert semi-axis lengths
    assert j_mask.semiAxisLength(0) == 10
    assert j_mask.semiAxisLength(1) == 10


# -- RECTANGLES -- #


@pytest.fixture
def rectangle_mask():
    return jc.ClosedWritableBox([20, 20], [40, 40])


@pytest.fixture
def rectangle_layer_axis_aligned():
    shp = Shapes()
    data = np.zeros((2, 2))
    data[0, :] = [10, 10]  # min. corner
    data[1, :] = [30, 30]  # max. corner
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


def test_rectangle_mask_to_layer(ij, rectangle_mask):
    py_mask = ij.py.from_java(rectangle_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == "rectangle"
    data = py_mask.data
    assert len(data) == 1
    box_data = data[0]
    assert len(box_data) == 4
    assert np.array_equal(box_data[0], np.array([20, 20]))
    assert np.array_equal(box_data[1], np.array([40, 20]))
    assert np.array_equal(box_data[2], np.array([40, 40]))
    assert np.array_equal(box_data[3], np.array([20, 40]))


def test_rectangle_layer_to_mask_box(ij, rectangle_layer_axis_aligned):
    # Assert shapes conversion to ellipse
    children = _assert_ROITree_conversion(ij, rectangle_layer_axis_aligned)
    assert children.size() == 1
    j_mask = children.get(0).data()
    assert isinstance(j_mask, jc.ClosedWritableBox)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Assert center position
    j_center = j_mask.center().positionAsDoubleArray()
    py_center = ij.py.from_java(j_center)
    assert np.array_equal(j_center, py_center)
    # Assert side lengths
    assert j_mask.sideLength(0) == 20
    assert j_mask.sideLength(1) == 20


def test_rectangle_layer_to_mask_polygon(ij, rectangle_layer_rotated):
    # Assert shapes conversion to ellipse
    children = _assert_ROITree_conversion(ij, rectangle_layer_rotated)
    assert children.size() == 1
    j_mask = children.get(0).data()
    assert isinstance(j_mask, jc.ClosedWritablePolygon2D)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Test some points
    _point_assertion(j_mask, [0, 0], True)
    _point_assertion(j_mask, [5, 5], True)
    _point_assertion(j_mask, [5, 6], False)


# -- POLYGONS -- #


@pytest.fixture
def polygon_mask():
    DoubleArr = JArray(JDouble)
    x = DoubleArr(3)
    y = DoubleArr(3)
    x[:] = [0, -3, 0]
    y[:] = [0, 0, -4]
    return jc.ClosedWritablePolygon2D(x, y)


@pytest.fixture
def polygon_layer():
    shp = Shapes()
    data = np.zeros((3, 2))
    data[0, :] = [0, 0]
    data[1, :] = [3, 0]
    data[2, :] = [0, 4]
    shp.add_polygons(data)
    return shp


def test_polygon_mask_to_layer(ij, polygon_mask):
    py_mask = ij.py.from_java(polygon_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == "polygon"
    data = py_mask.data
    assert len(data) == 1
    polygon_data = data[0]
    assert len(polygon_data) == 3
    assert np.array_equal(polygon_data[0], np.array([0, 0]))
    assert np.array_equal(polygon_data[1], np.array([-3, 0]))
    assert np.array_equal(polygon_data[2], np.array([0, -4]))


def test_polygon_layer_to_mask(ij, polygon_layer):
    # Assert shapes conversion to ellipse
    children = _assert_ROITree_conversion(ij, polygon_layer)
    assert children.size() == 1
    j_mask = children.get(0).data()
    assert isinstance(j_mask, jc.ClosedWritablePolygon2D)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Test some points
    _point_assertion(j_mask, [0, 0], True)
    _point_assertion(j_mask, [3, 0], True)
    _point_assertion(j_mask, [2, 1], True)
    _point_assertion(j_mask, [5, 6], False)


# -- LINES -- #


@pytest.fixture
def line_mask():
    DoubleArr = JArray(JDouble)
    p1 = DoubleArr(2)
    p2 = DoubleArr(2)
    p1[:] = [0, 0]
    p2[:] = [4, 4]
    return jc.DefaultWritableLine(p1, p2, True)


@pytest.fixture
def line_layer():
    shp = Shapes()
    data = np.zeros((2, 2))
    data[0, :] = [0, 0]
    data[1, :] = [4, -4]
    shp.add_lines(data)
    return shp


def test_line_mask_to_layer(ij, line_mask):
    py_mask = ij.py.from_java(line_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == "line"
    data = py_mask.data
    assert len(data) == 1
    line_data = data[0]
    assert len(line_data) == 2
    assert np.array_equal(line_data[0], np.array([0, 0]))
    assert np.array_equal(line_data[1], np.array([4, 4]))


def test_line_layer_to_mask(ij, line_layer):
    # Assert shapes conversion to ellipse
    children = _assert_ROITree_conversion(ij, line_layer)
    assert children.size() == 1
    j_mask = children.get(0).data()
    assert isinstance(j_mask, jc.DefaultWritableLine)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Assert endpoints
    arr = JArray(JDouble)(2)
    j_mask.endpointOne().localize(arr)
    assert np.array_equal(ij.py.from_java(arr), arr)
    j_mask.endpointTwo().localize(arr)
    assert np.array_equal(ij.py.from_java(arr), arr)
    # Test some points
    _point_assertion(j_mask, [0, 0], True)
    _point_assertion(j_mask, [4, -4], True)
    _point_assertion(j_mask, [2, -2], True)
    _point_assertion(j_mask, [5, 6], False)


# -- PATHS -- #


@pytest.fixture
def path_mask():
    p1 = JArray(JDouble)(2)
    p1[:] = [0, 0]
    p2 = JArray(JDouble)(2)
    p2[:] = [1, 1]
    p3 = JArray(JDouble)(2)
    p3[:] = [2, 0]
    pts = [jc.RealPoint(p) for p in [p1, p2, p3]]
    ptList = jc.ArrayList()
    ptList.addAll(pts)
    return jc.DefaultWritablePolyline(ptList)


@pytest.fixture
def path_layer():
    shp = Shapes()
    data = np.zeros((3, 2))
    data[0, :] = [0, 0]
    data[1, :] = [4, -4]
    data[2, :] = [8, 0]
    shp.add_paths(data)
    return shp


def test_path_mask_to_layer(ij, path_mask):
    py_mask = ij.py.from_java(path_mask)
    assert isinstance(py_mask, Shapes)
    types = py_mask.shape_type
    assert len(types) == 1
    assert types[0] == "path"
    data = py_mask.data
    assert len(data) == 1
    path_data = data[0]
    assert len(path_data) == 3
    assert np.array_equal(path_data[0], np.array([0, 0]))
    assert np.array_equal(path_data[1], np.array([1, 1]))
    assert np.array_equal(path_data[2], np.array([2, 0]))


def test_path_layer_to_mask(ij, path_layer):
    # Assert shapes conversion to ellipse
    children = _assert_ROITree_conversion(ij, path_layer)
    assert children.size() == 1
    j_mask = children.get(0).data()
    assert isinstance(j_mask, jc.DefaultWritablePolyline)
    # Assert dimensionality
    assert j_mask.numDimensions() == 2
    # Assert endpoints
    arr = JArray(JDouble)(2)
    expected = [[0, 0], [4, -4], [8, 0]]
    actual = j_mask.vertices()
    for e, a in zip(expected, actual):
        a.localize(arr)
        assert np.array_equal(ij.py.from_java(arr), e)
    # Test some points
    _point_assertion(j_mask, [0, 0], True)
    _point_assertion(j_mask, [2, -2], True)
    _point_assertion(j_mask, [4, -4], True)
    _point_assertion(j_mask, [6, -2], True)
    _point_assertion(j_mask, [8, 0], True)
    _point_assertion(j_mask, [5, 6], False)


# -- ROITrees -- #


@pytest.fixture
def multiple_masks(ellipse_mask, rectangle_mask):
    return [ellipse_mask, rectangle_mask]


@pytest.fixture
def multiple_layer():
    shp = Shapes()
    # Add an ellipse
    data = np.zeros((2, 2))
    data[0, :] = [30, 30]  # ceter
    data[1, :] = [10, 10]  # axes
    shp.add_ellipses(data)
    # Add a rectangle
    data = np.zeros((2, 2))
    data[0, :] = [10, 10]  # min. corner
    data[1, :] = [30, 30]  # max. corner
    shp.add_rectangles(data)
    return shp


def test_multiple_masks_to_layer(ij, multiple_masks):
    # Make a tree frmo an ellipse and a rectangle
    mask_list = jc.ArrayList(multiple_masks)
    tree = jc.DefaultROITree()
    tree.addROIs(mask_list)
    # Convert the tree to a napari shapes layer
    shapes = ij.py.from_java(tree)
    # Assert two shapes in the layer
    types = shapes.shape_type
    assert len(types) == 2
    assert types[0] == "ellipse"
    assert types[1] == "rectangle"
    data = shapes.data
    assert len(data) == 2
    # Assert ellipse data is as expected
    ellipse_data = data[0]
    assert len(ellipse_data) == 4
    assert np.array_equal(ellipse_data[0], np.array([10, 10]))
    assert np.array_equal(ellipse_data[1], np.array([30, 10]))
    assert np.array_equal(ellipse_data[2], np.array([30, 30]))
    assert np.array_equal(ellipse_data[3], np.array([10, 30]))
    # Assert rectangle data is as expected
    box_data = data[1]
    assert len(box_data) == 4
    assert np.array_equal(box_data[0], np.array([20, 20]))
    assert np.array_equal(box_data[1], np.array([40, 20]))
    assert np.array_equal(box_data[2], np.array([40, 40]))
    assert np.array_equal(box_data[3], np.array([20, 40]))


def test_multiple_layer_to_masks(ij, multiple_layer):
    # Convert the napari shapes layer into a tree
    masks = ij.py.to_java(multiple_layer)
    assert isinstance(masks, jc.ROITree)
    rois = [child.data() for child in masks.children()]
    # Assert ellipsoid of first child
    assert isinstance(rois[0], jc.SuperEllipsoid)
    # Assert dimensionality
    assert rois[0].numDimensions() == 2
    # Assert center position
    j_center = rois[0].center().positionAsDoubleArray()
    py_center = ij.py.from_java(j_center)
    assert np.array_equal(py_center, j_center)
    # Assert semi-axis lengths
    assert rois[0].semiAxisLength(0) == 10
    assert rois[0].semiAxisLength(1) == 10
    # Assert Box of second child
    assert isinstance(rois[1], jc.Box)
    # Assert dimensionality
    assert rois[1].numDimensions() == 2
    # Assert center position
    j_center = rois[1].center().positionAsDoubleArray()
    py_center = ij.py.from_java(j_center)
    assert np.array_equal(py_center, j_center)
    # Assert side lengths
    assert rois[1].sideLength(0) == 20
    assert rois[1].sideLength(1) == 20


# -- Points / RealPointCollections -- #


@pytest.fixture
def real_point_collection():
    p1 = JArray(JDouble)(2)
    p1[:] = [0, 0]
    p2 = JArray(JDouble)(2)
    p2[:] = [1, 1]
    p3 = JArray(JDouble)(2)
    p3[:] = [2, 0]
    pts = [jc.RealPoint(p) for p in [p1, p2, p3]]
    ptList = jc.ArrayList()
    ptList.addAll(pts)
    return jc.DefaultWritableRealPointCollection(ptList)


@pytest.fixture
def points():
    data = np.zeros((3, 2))
    data[0, :] = [0, 0]
    data[1, :] = [4, -4]
    data[2, :] = [8, 0]
    return Points(data=data)


def test_realpointcollection_to_points(ij, real_point_collection):
    py_mask = ij.py.from_java(real_point_collection)
    assert isinstance(py_mask, Points)
    data = py_mask.data
    assert len(data) == 3
    assert np.array_equal(data[0], np.array([0, 0]))
    assert np.array_equal(data[1], np.array([1, 1]))
    assert np.array_equal(data[2], np.array([2, 0]))


def test_points_to_realpointcollection(ij, points):
    # Assert shapes conversion to ellipse
    collection = ij.py.to_java(points)
    assert isinstance(collection, jc.RealPointCollection)
    p1 = JArray(JDouble)(2)
    p1[:] = [0, 0]
    p2 = JArray(JDouble)(2)
    p2[:] = [4, -4]
    p3 = JArray(JDouble)(2)
    p3[:] = [8, 0]
    pts = [jc.RealPoint(p) for p in [p1, p2, p3]]
    for e, a in zip(pts, collection.points()):
        assert e == a


# -- Surfaces/Meshes -- #


@pytest.fixture
def surface() -> Surface:
    vertices = np.array([0, 0, 0, 10, 0, 0, 10, 20, 0, 0, 20, 0]).reshape((4, 3))
    triangles = np.array([0, 1, 2, 2, 3, 0]).reshape(2, 3)
    return Surface(data=(vertices, triangles))


@pytest.fixture
def mesh() -> "jc.Mesh":
    mesh = jc.NaiveDoubleMesh()
    mesh.vertices().add(0.0, 0.0, 0.0)
    mesh.vertices().add(5.0, 5.0, 0.0)
    mesh.vertices().add(5.0, 0.0, 0.0)
    mesh.vertices().add(5.0, -5.0, 0.0)
    mesh.triangles().add(3, 0, 2)
    mesh.triangles().add(2, 0, 1)
    return mesh


def test_surface_to_mesh(ij, surface: Surface):
    p_vertices, p_triangles, _ = surface.data
    mesh = ij.py.to_java(surface)
    assert isinstance(mesh, jc.Mesh)
    position = JArray(JDouble)(3)
    for j_vertex, p_vertex in zip(mesh.vertices(), p_vertices):
        j_vertex.localize(position)
        # Note that the dimensions are reversed across the language barrier
        assert np.array_equal(p_vertex, position[::-1])
    for j_triangle, p_triangle in zip(mesh.triangles(), p_triangles):
        assert p_triangle[0] == j_triangle.vertex0()
        assert p_triangle[1] == j_triangle.vertex1()
        assert p_triangle[2] == j_triangle.vertex2()


def test_mesh_to_surface(ij, mesh: "jc.Mesh"):
    surface = ij.py.from_java(mesh)
    p_vertices, p_triangles, _ = surface.data
    assert isinstance(mesh, jc.Mesh)
    position = JArray(JDouble)(3)
    for j_vertex, p_vertex in zip(mesh.vertices(), p_vertices):
        j_vertex.localize(position)
        # Note that the dimensions are reversed across the language barrier
        assert np.array_equal(p_vertex, position[::-1])
    for j_triangle, p_triangle in zip(mesh.triangles(), p_triangles):
        assert p_triangle[0] == j_triangle.vertex0()
        assert p_triangle[1] == j_triangle.vertex1()
        assert p_triangle[2] == j_triangle.vertex2()


def test_surface_wrong_dimensions(ij, surface: Surface):
    # Test 2D data
    py_vertices, py_triangles, _ = surface.data
    py_vertices_2D = py_vertices[:, :2]
    surface2 = Surface(data=(py_vertices_2D, py_triangles))
    try:
        ij.py.to_java(surface2)
        pytest.fail()
    except ValueError as exc:
        assert str(exc) == "Can only convert 3D Surfaces to Meshes!"

    # Test 4D data
    py_vertices, py_triangles, _ = surface.data
    new_col = np.array([0, 0, 0, 0]).reshape((4, 1))
    py_vertices_4D = np.concatenate((py_vertices, new_col), 1)
    surface4 = Surface(data=(py_vertices_4D, py_triangles))
    try:
        ij.py.to_java(surface4)
        pytest.fail()
    except ValueError as exc:
        assert str(exc) == "Can only convert 3D Surfaces to Meshes!"


# -- Enum(like)s -- #


def test_enum_conversion_regression(ij):
    """
    Ensures that all values of an enum can be converted bidirectionally
    """
    # We use ItemIO for fun!
    j_enum = jc.ItemIO
    py_enum = py_enum_for(j_enum.class_)
    for j, p in zip(j_enum.values(), py_enum):
        assert ij.py.to_java(p) == j
        assert ij.py.from_java(j) == p


def test_enum_conversion_on_the_fly(ij):
    """
    Ensures that an enum can be converted without calling py_enum_for first!
    """
    j_enum = jc.ItemVisibility.NORMAL
    assert j_enum.getClass() not in _ENUMS.values()
    py_enum = ij.py.from_java(j_enum)
    assert py_enum.__class__.__name__ == "ItemVisibility"
    assert py_enum.name == "NORMAL"


def test_OutOfBoundsFactory_conversion(ij):
    # Test python_type_of
    assert (
        type_hint_for(DummyModuleItem(jtype=jc.OutOfBoundsFactory))
        == OutOfBoundsFactory
    )
    # Test conversion
    assert isinstance(
        ij.py.to_java(OutOfBoundsFactory.BORDER), jc.OutOfBoundsBorderFactory
    )
    assert isinstance(
        ij.py.to_java(OutOfBoundsFactory.MIRROR_EXP_WINDOWING),
        jc.OutOfBoundsMirrorExpWindowingFactory,
    )
    assert isinstance(
        ij.py.to_java(OutOfBoundsFactory.MIRROR_SINGLE), jc.OutOfBoundsMirrorFactory
    )
    assert isinstance(
        ij.py.to_java(OutOfBoundsFactory.MIRROR_DOUBLE), jc.OutOfBoundsMirrorFactory
    )
    assert isinstance(
        ij.py.to_java(OutOfBoundsFactory.PERIODIC), jc.OutOfBoundsPeriodicFactory
    )


# -- Images -- #


@pytest.fixture
def test_binary_dataset(ij) -> "jc.Dataset":
    name = "test.foo"
    dataset: jc.Dataset = ij.dataset().create(
        ij.py.to_java(np.ones((10, 10), dtype=np.bool_))
    )
    assert "net.imglib2.type.logic.NativeBoolType" == str(
        dataset.getType().getClass().getName()
    )
    dataset.setName(name)
    return dataset


@pytest.fixture
def test_dataset(ij) -> "jc.Dataset":
    name = "test.foo"
    dataset: jc.Dataset = ij.dataset().create(ij.py.to_java(np.ones((10, 10))))
    dataset.setName(name)
    return dataset


@pytest.fixture
def test_dataset_view(ij, test_dataset) -> "jc.DatasetView":
    view: jc.DatasetView = ij.get(
        "net.imagej.display.ImageDisplayService"
    ).createDataView(test_dataset)
    view.rebuild()
    view.resetColorTables(True)
    yield view
    # dispose of the view so it does not affect later tests
    view.dispose()


def _assert_equal_color_maps(j_map: "jc.ColorTable", p_map):
    p_color = p_map.map([x / 255 for x in range(256)])
    # Assert color table "equality"
    for i in range(j_map.getLength()):
        for j in range(j_map.getComponentCount()):
            assert j_map.get(j, i) == int(round(p_color[i, j] * 255))


def test_image_layer_to_dataset(ij):
    """Test conversion of an Image layer with a default colormap"""
    name = "test_foo"
    image = Image(data=np.ones((10, 10)), name=name)
    j_img = ij.py.to_java(image)
    assert isinstance(j_img, jc.Dataset)
    assert name == j_img.getName()
    assert 0 == j_img.getColorTableCount()

    assert 0 == j_img.dimensionIndex(jc.Axes.X)
    assert 1 == j_img.dimensionIndex(jc.Axes.Y)


def test_binary_image_layer_to_dataset(ij):
    """Test conversion of an Image layer of booleans with a default colormap"""
    name = "test_foo"
    image = Image(data=np.ones((10, 10), dtype=np.bool_), name=name)
    j_img = ij.py.to_java(image)
    assert isinstance(j_img, jc.Dataset)
    assert isinstance(j_img.cursor().next(), jc.BooleanType)
    assert name == j_img.getName()
    assert 0 == j_img.getColorTableCount()

    assert 0 == j_img.dimensionIndex(jc.Axes.X)
    assert 1 == j_img.dimensionIndex(jc.Axes.Y)


def test_colormap_image_layer_to_dataset(ij):
    """Test conversion of an Image layer with a chosen colormap"""
    name = "test_foo"
    image = Image(data=np.ones((10, 10)), name=name, colormap="red")
    j_img = ij.py.to_java(image)
    assert isinstance(j_img, jc.Dataset)
    assert name == j_img.getName()
    assert 1 == j_img.getColorTableCount()
    _assert_equal_color_maps(j_img.getColorTable(0), image.colormap)


def test_dataset_to_image_layer(ij, test_dataset):
    """Test conversion of a Dataset with no colormap"""
    p_img = ij.py.from_java(test_dataset)
    assert isinstance(p_img, Image)
    assert test_dataset.getName() == p_img.name
    assert "gray" == p_img.colormap.name


def test_binary_dataset_to_image_layer(ij, test_binary_dataset):
    """Test conversion of a binary Dataset with no colormap"""
    p_img = ij.py.from_java(test_binary_dataset)
    assert isinstance(p_img, Image)
    assert isinstance(p_img.dtype, type(np.dtype("bool")))
    assert test_binary_dataset.getName() == p_img.name
    assert "gray" == p_img.colormap.name


def test_colormap_dataset_to_image_layer(ij, test_dataset):
    """Test conversion of a Dataset with a colormap"""
    test_dataset.initializeColorTables(1)
    test_dataset.setColorTable(jc.ColorTables.CYAN, 0)
    p_img = ij.py.from_java(test_dataset)
    assert isinstance(p_img, Image)
    assert test_dataset.getName() == p_img.name
    assert "gray" != p_img.colormap.name
    _assert_equal_color_maps(test_dataset.getColorTable(0), p_img.colormap)


def test_dataset_view_to_image_layer(ij, test_dataset_view):
    """Test conversion of a Dataset with no colormap"""
    p_img = ij.py.from_java(test_dataset_view)
    assert isinstance(p_img, Image)
    assert test_dataset_view.getData().getName() == p_img.name
    assert "gray" == p_img.colormap.name


def test_colormap_dataset_view_to_image_layer(ij, test_dataset_view):
    """Test conversion of a Dataset with a colormap"""
    test_dataset_view.setColorTable(jc.ColorTables.CYAN, 0)
    p_img = ij.py.from_java(test_dataset_view)
    assert isinstance(p_img, Image)
    assert test_dataset_view.getData().getName() == p_img.name
    assert "gray" != p_img.colormap.name
    _assert_equal_color_maps(test_dataset_view.getColorTables().get(0), p_img.colormap)
