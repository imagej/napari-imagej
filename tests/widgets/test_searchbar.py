from qtpy.QtWidgets import QHBoxLayout, QLineEdit

from napari_imagej.widgets.napari_imagej import NapariImageJ
from napari_imagej.widgets.searchbar import ImageJSearchbar, JLineEdit


def test_searchbar_widget_layout(imagej_widget: NapariImageJ):
    """Tests the number and expected order of search widget children"""
    searchbar: ImageJSearchbar = imagej_widget.findChild(ImageJSearchbar)
    subwidgets = searchbar.children()
    assert len(subwidgets) == 2
    assert isinstance(subwidgets[0], QHBoxLayout)
    assert isinstance(subwidgets[1], QLineEdit)


def test_searchbar_regression():
    bar = JLineEdit()
    assert bar.text() == "Initializing ImageJ...Please Wait"
    assert not bar.isEnabled()