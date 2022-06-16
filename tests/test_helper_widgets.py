import napari
from magicgui.widgets import ComboBox, Container, PushButton
from napari import current_viewer

from napari_imagej._helper_widgets import MutableOutputWidget


def test_mutable_output_widget_chosen():

    widget = MutableOutputWidget()
    assert isinstance(widget, Container)
    children = [w for w in widget]
    assert len(children) == 2
    assert isinstance(children[0], ComboBox)
    assert isinstance(children[1], PushButton)
    assert children[1].max_width == 53
    assert widget.current_choice == ""
    assert widget.layout == "horizontal"
    assert widget.margins == (0, 0, 0, 0)


def test_mutable_output_default_shape(make_napari_viewer):
    """Tests that MutableOutputWidget's default size changes based on"""
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

    # Assert when no selection, output shape is default
    assert input_widget.current_choice == ""
    assert output_widget._default_new_shape() == [512, 512]

    # Add new image
    shape = (128, 128, 3)
    import numpy as np

    current_viewer().add_image(data=np.ones(shape), name="img")
    assert input_widget.current_choice == "img"
    assert output_widget._default_new_shape() == shape
