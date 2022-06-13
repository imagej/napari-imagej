from qtpy.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from napari_imagej.widget import (
    FocusWidget,
    ImageJWidget,
    ResultsWidget,
    SearchbarWidget,
)


def test_widget_layout(imagej_widget: ImageJWidget):
    """Ensures a vertical widget layout."""
    assert isinstance(imagej_widget.layout(), QVBoxLayout)


def test_widget_searchbar_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the searchbar widget."""
    searchbar: QWidget = imagej_widget.search
    assert isinstance(searchbar.layout(), QHBoxLayout)
    search_widget: QLineEdit = searchbar.findChild(QLineEdit)
    assert search_widget is not None


def test_widget_table_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the search results table."""
    table: QTableWidget = imagej_widget.findChild(QTableWidget)
    assert 12 == table.rowCount()
    assert 1 == table.columnCount()
    assert QAbstractItemView.SelectRows == table.selectionBehavior()
    assert table.showGrid() is False


def test_widget_subwidget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of imagej_widget children"""
    subwidgets = imagej_widget.children()
    assert len(subwidgets) == 4
    assert isinstance(subwidgets[0], QVBoxLayout)
    assert isinstance(subwidgets[1], SearchbarWidget)
    assert isinstance(subwidgets[2], ResultsWidget)
    assert isinstance(subwidgets[3], FocusWidget)


def test_searchbar_widget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of search widget children"""
    searchbar: SearchbarWidget = imagej_widget.findChild(SearchbarWidget)
    subwidgets = searchbar.children()
    assert len(subwidgets) == 2
    assert isinstance(subwidgets[0], QHBoxLayout)
    assert isinstance(subwidgets[1], QLineEdit)


def test_results_widget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of results widget children"""
    results: ResultsWidget = imagej_widget.findChild(ResultsWidget)
    subwidgets = results.children()
    assert len(subwidgets) == 3
    assert isinstance(subwidgets[0], QVBoxLayout)
    assert isinstance(subwidgets[1], QTableWidget)
    assert isinstance(subwidgets[2], QTableWidget)


def test_focus_widget_layout(imagej_widget: ImageJWidget):
    """Tests the number and expected order of focus widget children"""
    focuser: FocusWidget = imagej_widget.findChild(FocusWidget)
    subwidgets = focuser.children()
    # Note: This is BEFORE any module is focused.
    assert len(subwidgets) == 2
    assert isinstance(subwidgets[0], QVBoxLayout)
    assert isinstance(subwidgets[1], QLabel)
