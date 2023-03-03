"""
A module testing napari_imagej.widgets.searchbar
"""
import pytest
from qtpy.QtWidgets import QHBoxLayout, QLineEdit

from napari_imagej.widgets.napari_imagej import NapariImageJWidget
from napari_imagej.widgets.searchbar import JLineEdit


@pytest.fixture
def searchbar(imagej_widget: NapariImageJWidget):
    return imagej_widget.search


def test_searchbar_widget_layout(searchbar):
    """Tests the number and expected order of search widget children"""
    subwidgets = searchbar.children()
    assert len(subwidgets) == 2
    assert isinstance(subwidgets[0], QHBoxLayout)
    assert isinstance(subwidgets[1], QLineEdit)


def test_searchbar_regression():
    bar = JLineEdit()
    assert bar.text() == "Initializing ImageJ...Please Wait"
    assert not bar.isEnabled()
