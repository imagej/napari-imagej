import importlib

import napari
import numpy as np
import pytest
from magicgui.widgets import ComboBox, PushButton
from napari import current_viewer
from napari.layers import Image

from napari_imagej._helper_widgets import MutableOutputWidget


@pytest.fixture
def mutable_output_widget(make_napari_viewer):
    make_napari_viewer()

    def func(output: "napari.layers.Image", input: "napari.layers.Image"):
        print(output.name, input.name)

    import magicgui

    widget = magicgui.magicgui(
        function=func,
        call_button=False,
        output={"widget_type": "napari_imagej._helper_widgets.MutableOutputWidget"},
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
    assert isinstance(children[0], ComboBox)
    assert isinstance(children[1], PushButton)
    assert children[1].max_width == 53
    assert output_widget.current_choice == ""
    assert output_widget.layout == "horizontal"
    assert output_widget.margins == (0, 0, 0, 0)


def test_mutable_output_default_shape(
    input_widget: ComboBox, output_widget: MutableOutputWidget
):
    """
    Tests that MutableOutputWidget's default size changes based on the
    choice of input widget
    """

    # Assert when no selection, output shape is default
    assert input_widget.current_choice == ""
    assert output_widget._default_new_shape() == [512, 512]

    # Add new image
    shape = (128, 128, 3)
    import numpy as np

    current_viewer().add_image(data=np.ones(shape), name="img")
    assert input_widget.current_choice == "img"
    assert output_widget._default_new_shape() == shape


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
