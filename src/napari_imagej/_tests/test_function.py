from typing import Generator
from napari import Viewer

import pytest
from napari_imagej._function import ImageJWidget
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QAbstractItemView,
    QLineEdit,
)

@pytest.fixture
def imagej_widget(make_napari_viewer) -> Generator[ImageJWidget, None, None]:
    # Create widget
    viewer: Viewer = make_napari_viewer()
    ij_widget: ImageJWidget = ImageJWidget(viewer)

    yield ij_widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    ij_widget.close()

def test_widget_layout(imagej_widget: ImageJWidget):
    """Ensures a vertical widget layout."""
    assert isinstance(imagej_widget.layout(), QVBoxLayout)

def test_widget_searchbar_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the searchbar widget."""
    searchbar:QWidget = imagej_widget._search_widget
    assert isinstance(searchbar.layout(), QHBoxLayout)
    search_widget: QLineEdit = searchbar.findChild(QLineEdit)

def test_widget_table_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the search results table."""
    table:QTableWidget = imagej_widget.findChild(QTableWidget)
    assert 12 == table.rowCount()
    assert 1 == table.columnCount()
    assert QAbstractItemView.SelectRows == table.selectionBehavior()
    assert False == table.showGrid()