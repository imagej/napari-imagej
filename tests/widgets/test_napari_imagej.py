"""
A module testing napari_imagej.widgets.napari_imagej
"""
from napari import Viewer
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QVBoxLayout

from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.napari_imagej import NapariImageJ, SearchActionDisplay
from napari_imagej.widgets.result_tree import SearchResultTree
from napari_imagej.widgets.searchbar import JVMEnabledSearchbar
from tests.widgets.widget_utils import _populate_tree


def test_widget_subwidget_layout(imagej_widget: NapariImageJ):
    """Tests the number and expected order of imagej_widget children"""
    subwidgets = imagej_widget.children()
    assert len(subwidgets) == 5
    assert isinstance(imagej_widget.layout(), QVBoxLayout)
    assert isinstance(subwidgets[0], QVBoxLayout)

    assert isinstance(subwidgets[1], NapariImageJMenu)
    assert isinstance(subwidgets[2], JVMEnabledSearchbar)
    assert isinstance(subwidgets[3], SearchResultTree)
    assert isinstance(subwidgets[4], SearchActionDisplay)


def test_keymaps(make_napari_viewer, qtbot):
    """Tests that 'Ctrl+L' is added to the keymap by ImageJWidget"""
    viewer: Viewer = make_napari_viewer()
    assert "Control-L" not in viewer.keymap
    NapariImageJ(viewer)
    assert "Control-L" in viewer.keymap
    # TODO: I can't seem to figure out how to assert that pressing 'L'
    # sets the focus of the search bar.
    # Typing viewer.keymap['L'](viewer) does nothing. :(


def test_result_single_click(imagej_widget: NapariImageJ, qtbot, asserter):
    # Assert that there are initially no buttons
    imagej_widget.results.wait_for_setup()
    assert len(imagej_widget.focuser.focused_action_buttons) == 0
    # Search something, then wait for the results to populate
    imagej_widget.results.search("Frangi")
    tree = imagej_widget.results
    asserter(lambda: tree.topLevelItemCount() > 0)
    asserter(lambda: tree.topLevelItem(0).childCount() > 0)
    buttons = imagej_widget.focuser.focused_action_buttons
    # Test single click spawns buttons
    item = tree.topLevelItem(0).child(0)
    rect = tree.visualItemRect(item)
    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=rect.center())
    asserter(lambda: len(buttons) > 0)
    # Test single click on searcher hides buttons
    item = tree.topLevelItem(0)
    rect = tree.visualItemRect(item)
    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=rect.center())
    # Ensure we don't see any text in the focuser
    asserter(
        lambda: imagej_widget.focuser.focused_module_label.isHidden()
        or imagej_widget.focuser.focused_module_label.text() == ""
    )
    # Ensure we don't see any buttons in the focuser
    asserter(lambda: len(buttons) == 0 or all(button.isHidden() for button in buttons))


def test_searchbar_results_transitions(imagej_widget: NapariImageJ, asserter, qtbot):
    """
    Ensures that the arrow keys can be used to transfer focus between
    the searchbar and the results table
    """
    tree: SearchResultTree = imagej_widget.results
    _populate_tree(tree, asserter)

    # Ensure that no element is highlighted to start out
    asserter(lambda: tree.currentItem() is None)

    # Then, press down from the search bar
    # and ensure that the first item is highlighted
    qtbot.keyPress(imagej_widget.search.bar, Qt.Key_Down)
    asserter(lambda: tree.currentItem() is tree.topLevelItem(0))

    # Then, press up and ensure that the search bar is highlighted
    qtbot.keyPress(tree, Qt.Key_Up)
    # HACK: In practice, we should expect focus on imagej_widget.search.bar.
    # But because it isn't visible, QApplication.focusWidget() will become None.
    # See https://doc.qt.io/qt-5/qwidget.html#setFocus
    asserter(lambda: not imagej_widget.search.bar.isVisible())
    asserter(lambda: QApplication.focusWidget() is None)
