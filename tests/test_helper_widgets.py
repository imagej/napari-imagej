from magicgui.widgets import ComboBox, Container, PushButton

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
