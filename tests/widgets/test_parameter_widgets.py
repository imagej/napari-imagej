"""
A module testing napari_imagej.widgets.parameter_widgets
"""

import importlib

import napari
import numpy as np
import pytest
from imagej.images import _imglib2_types
from magicgui.types import FileDialogMode
from magicgui.widgets import (
    CheckBox,
    ComboBox,
    Container,
    ListEdit,
    PushButton,
    SpinBox,
)
from napari import current_viewer
from napari.layers import Image
from scyjava import numeric_bounds

from napari_imagej.widgets.parameter_widgets import (
    DirectoryWidget,
    MutableOutputWidget,
    OpenFileWidget,
    SaveFileWidget,
    ShapeWidget,
    number_widget_for,
    numeric_type_widget_for,
)
from tests.utils import jc


@pytest.fixture
def mutable_output_widget(make_napari_viewer):
    make_napari_viewer()

    def func(output: "napari.layers.Image", input: "napari.layers.Image"):
        print(output.name, input.name)

    import magicgui

    widget = magicgui.magicgui(
        function=func,
        call_button=False,
        output={
            "widget_type": "napari_imagej.widgets.parameter_widgets.MutableOutputWidget"
        },
    )
    current_viewer().window.add_dock_widget(widget)

    output_widget = widget._list[0]
    input_widget = widget._list[1]
    assert isinstance(output_widget, MutableOutputWidget)
    assert isinstance(input_widget, ComboBox)
    return widget


@pytest.fixture
def output_widget(mutable_output_widget):
    widget = mutable_output_widget._list[0]
    assert isinstance(widget, MutableOutputWidget)
    return widget


@pytest.fixture
def input_widget(mutable_output_widget):
    widget = mutable_output_widget._list[1]
    assert isinstance(widget, ComboBox)
    return widget


def test_mutable_output_widget_layout(output_widget):
    children = [w for w in output_widget]
    assert len(children) == 2
    assert isinstance(children[0], PushButton)
    assert isinstance(children[1], ComboBox)
    assert children[0].tooltip == "Create a new output container"
    assert children[0].max_width == 53
    assert (
        children[1].tooltip
        == "Optional - produces a new layer unless an output container is provided"
    )
    assert output_widget.current_choice == ""
    assert output_widget.layout == "horizontal"
    assert output_widget.margins == (0, 0, 0, 0)


def test_mutable_output_default_parameters(
    input_widget: ComboBox, output_widget: MutableOutputWidget
):
    """
    Tests that MutableOutputWidget's default size and type change based on the
    choice of input widget
    """

    # Assert when no selection, output shape is default
    assert input_widget.current_choice == ""
    assert output_widget._default_new_shape() == [512, 512]
    assert output_widget._default_new_type() == "float64"

    # Add new image
    shape = (128, 128, 3)
    import numpy as np

    current_viewer().add_image(data=np.ones(shape, dtype=np.int32), name="img")
    assert input_widget.current_choice == "img"
    assert output_widget._default_new_shape() == shape
    assert output_widget._default_new_type() == "int32"


def test_mutable_output_dtype_choices(
    input_widget: ComboBox, output_widget: MutableOutputWidget
):
    """
    Tests that MutableOutputWidget's data type choices
    are all types supported by pyimagej
    """
    supported = output_widget._dtype_choices()
    for ptype in _imglib2_types.values():
        assert np.dtype(ptype) in supported


# these types are always included
backing_types = [
    ("NumPy", np.ndarray),
]
# these types are sometimes included
if importlib.util.find_spec("zarr"):
    from zarr.core import Array

    backing_types.append(("Zarr", Array))
if importlib.util.find_spec("xarray"):
    from xarray import DataArray

    backing_types.append(("xarray", DataArray))


@pytest.mark.parametrize(argnames=["choice", "type"], argvalues=backing_types)
def test_mutable_output_add_new_image(
    input_widget: ComboBox, output_widget: MutableOutputWidget, choice, type
):
    """Tests that MutableOutputWidget can add a new image from params"""

    params = {
        "name": "foo",
        "array_type": choice,
        "shape": (100, 100, 3),
        "fill_value": 3.0,
        "data_type": np.int32,
    }

    output_widget._add_new_image(params)

    assert "foo" in current_viewer().layers
    foo: Image = current_viewer().layers["foo"]
    assert "foo" == foo.name
    assert isinstance(foo.data, type)
    assert (100, 100, 3) == foo.data.shape
    assert (3) == np.unique(foo.data)

    assert foo in input_widget.choices
    assert foo in output_widget.choices
    assert foo is output_widget.value


def test_numbers(ij):
    numbers = [
        jc.Byte,
        jc.Short,
        jc.Integer,
        jc.Long,
        jc.Float,
        jc.Double,
        jc.BigInteger,
        jc.BigDecimal,
    ]
    for number in numbers:
        # NB See HACK in number_widget_for
        if number == jc.BigInteger:
            min_val, max_val = numeric_bounds(jc.Long)
        elif number == jc.BigDecimal:
            min_val, max_val = numeric_bounds(jc.Double)
        else:
            min_val, max_val = numeric_bounds(number)

        widget = number_widget_for(number.class_)()
        assert min_val == widget.min
        assert max_val == widget.max
        assert isinstance(widget.value, number)


def test_realType():
    real_types = [
        (jc.BitType),
        (jc.BoolType),
        (jc.ByteType),
        (jc.UnsignedByteType),
        (jc.ShortType),
        (jc.UnsignedShortType),
        (jc.IntType),
        (jc.UnsignedIntType),
        (jc.LongType),
        (jc.UnsignedLongType),
        (jc.FloatType),
        (jc.DoubleType),
    ]
    for real_type in real_types:
        type_instance = real_type.class_.newInstance()
        widget = numeric_type_widget_for(real_type.class_)()
        min_val = type_instance.getMinValue()
        max_val = type_instance.getMaxValue()
        # If the type is not a boolean, it will have min and max values
        if issubclass(real_type.class_, jc.BooleanType):
            assert not hasattr(widget, "min")
            assert not hasattr(widget, "min")
        else:
            # Integer widget has a bound on the minimum and maximum values
            if issubclass(real_type.class_, jc.IntegerType):
                min_val = max(type_instance.getMinValue(), -(2**31))
                max_val = min(type_instance.getMaxValue(), (2**31 - 1))
            assert min_val == widget.min
            assert max_val == widget.max
        assert isinstance(widget.value, real_type)


def test_realType_ifaces():
    iface_impl_tuples = [
        (jc.RealType, jc.DoubleType),
        (jc.IntegerType, jc.LongType),
        (jc.NumericType, jc.DoubleType),
        (jc.BooleanType, jc.BitType),
    ]
    for iface, impl in iface_impl_tuples:
        widget_iface = numeric_type_widget_for(iface.class_)()
        widget_impl = numeric_type_widget_for(impl.class_)()
        if issubclass(iface.class_, jc.BooleanType):
            assert not hasattr(widget_iface, "min")
            assert not hasattr(widget_iface, "max")
        else:
            assert widget_iface.min == widget_impl.min
            assert widget_iface.max == widget_impl.max
        assert isinstance(widget_iface.value, impl)


def test_save_file_widget():
    widget = SaveFileWidget()
    assert widget.mode == FileDialogMode.OPTIONAL_FILE


def test_open_file_widget():
    widget = OpenFileWidget()
    assert widget.mode == FileDialogMode.EXISTING_FILE


def test_directory_file_widget():
    widget = DirectoryWidget()
    assert widget.mode == FileDialogMode.EXISTING_DIRECTORY


def test_shape_widget_regression():
    widget = ShapeWidget()
    # Assert widget type
    assert isinstance(widget, Container)
    # Assert that widget contains a dropdown and shape options
    assert len(widget) == 2
    assert isinstance(widget[0], ComboBox)
    assert isinstance(widget[1], Container)
    # Assert starting value
    assert widget[0].value == "Centered Rectangle"


def test_shape_widget_centered_rectangle():
    # Choose a Centered Rectangle
    widget = ShapeWidget()
    widget[0].value = "Centered Rectangle"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 2
    assert isinstance(widget.shape_options[0], ListEdit)
    assert isinstance(widget.shape_options[1], CheckBox)
    # Assert starting values
    assert widget.shape_options[0].value == [1, 1]
    assert not widget.shape_options[1].value
    # Assert the value returned is a CenteredRectangleShape
    value = widget.value
    assert isinstance(value, jc.CenteredRectangleShape)
    assert np.array_equal(value.getSpan(), np.ones((2)))
    assert not value.isSkippingCenter()


def test_shape_widget_diamond():
    # Choose a Diamond
    widget = ShapeWidget()
    widget[0].value = "Diamond"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 1
    assert isinstance(widget.shape_options[0], SpinBox)
    # Assert starting values
    assert widget.shape_options[0].value == 1
    # Assert the value returned is a DiamondShape
    value = widget.value
    assert isinstance(value, jc.DiamondShape)
    assert value.getRadius() == 1


def test_shape_widget_diamond_tips():
    # Choose a DiamondTips
    widget = ShapeWidget()
    widget[0].value = "Diamond Tips"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 1
    assert isinstance(widget.shape_options[0], SpinBox)
    # Assert starting values
    assert widget.shape_options[0].value == 1
    # Assert the value returned is a DiamondTipsShape
    value = widget.value
    assert isinstance(value, jc.DiamondTipsShape)
    assert value.getRadius() == 1


def test_shape_widget_horizontal_line():
    # Choose a Horizontal Line
    widget = ShapeWidget()
    widget[0].value = "Horizontal Line"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 3
    assert isinstance(widget.shape_options[0], SpinBox)
    assert isinstance(widget.shape_options[1], SpinBox)
    assert isinstance(widget.shape_options[2], CheckBox)
    # Assert starting values
    assert widget.shape_options[0].value == 1
    assert widget.shape_options[1].value == 0
    assert not widget.shape_options[2].value
    # Assert the value returned is a HorizontalLineShape
    value = widget.value
    assert isinstance(value, jc.HorizontalLineShape)
    assert value.getSpan() == 1
    assert value.getLineDimension() == 0
    assert not value.isSkippingCenter()


def test_shape_widget_hypersphere():
    # Choose a Hypersphere
    widget = ShapeWidget()
    widget[0].value = "Hypersphere"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 1
    assert isinstance(widget.shape_options[0], SpinBox)
    # Assert starting values
    assert widget.shape_options[0].value == 1
    # Assert the value returned is a HyperSphereShape
    value = widget.value
    assert isinstance(value, jc.HyperSphereShape)
    assert value.getRadius() == 1


def test_shape_widget_pair_of_points():
    # Choose a Pair of Points
    widget = ShapeWidget()
    widget[0].value = "Pair of Points"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 1
    assert isinstance(widget.shape_options[0], ListEdit)
    # Assert starting values
    assert widget.shape_options[0].value == [1, 1]
    # Assert the value returned is a PairofPointsShape
    value = widget.value
    assert isinstance(value, jc.PairOfPointsShape)
    assert np.array_equal(value.getOffset(), np.ones((2)))


def test_shape_widget_periodic_line():
    # Choose a Periodic Line
    widget = ShapeWidget()
    widget[0].value = "Periodic Line"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 2
    assert isinstance(widget.shape_options[0], SpinBox)
    assert isinstance(widget.shape_options[1], ListEdit)
    # Assert starting values
    assert widget.shape_options[0].value == 1
    assert widget.shape_options[1].value == [1, 1]
    # Assert the value returned is a PeriodicLineShape
    value = widget.value
    assert isinstance(value, jc.PeriodicLineShape)
    assert value.getSpan() == 1
    assert np.array_equal(value.getIncrements(), np.ones((2)))


def test_shape_widget_rectangle():
    # Choose a Rectangle
    widget = ShapeWidget()
    widget[0].value = "Rectangle"
    # Assert parameter option widgets
    assert len(widget.shape_options) == 2
    assert isinstance(widget.shape_options[0], SpinBox)
    assert isinstance(widget.shape_options[1], CheckBox)
    # Assert starting values
    assert widget.shape_options[0].value == 1
    assert not widget.shape_options[1].value
    # Assert the value returned is a RectangleShape
    value = widget.value
    assert isinstance(value, jc.RectangleShape)
    assert value.getSpan() == 1
    assert not value.isSkippingCenter()
