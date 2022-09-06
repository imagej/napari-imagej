"""
A module testing napari_imagej.widgets.searchbar
"""
from qtpy.QtWidgets import QHBoxLayout, QLineEdit

from napari_imagej.widgets.napari_imagej import NapariImageJWidget
from napari_imagej.widgets.searchbar import JLineEdit, JVMEnabledSearchbar


def test_searchbar_widget_layout(imagej_widget: NapariImageJWidget):
    """Tests the number and expected order of search widget children"""
    searchbar: JVMEnabledSearchbar = imagej_widget.findChild(JVMEnabledSearchbar)
    subwidgets = searchbar.children()
    assert len(subwidgets) == 2
    assert isinstance(subwidgets[0], QHBoxLayout)
    assert isinstance(subwidgets[1], QLineEdit)


def test_searchbar_regression():
    bar = JLineEdit()
    assert bar.text() == "Initializing ImageJ...Please Wait"
    assert not bar.isEnabled()
