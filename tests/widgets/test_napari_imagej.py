"""
A module testing napari_imagej.widgets.napari_imagej
"""

from napari import Viewer
from napari.layers import Image
from numpy import ones
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QPushButton, QVBoxLayout

from napari_imagej.java import ij, jc
from napari_imagej.utilities.events import subscribers
from napari_imagej.widgets.info_bar import InfoBox
from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.napari_imagej import (
    NapariEventSubscriber,
    NapariImageJWidget,
    ResultRunner,
)
from napari_imagej.widgets.result_tree import SearchResultTree
from napari_imagej.widgets.searchbar import JVMEnabledSearchbar
from tests.widgets.widget_utils import _searcher_tree_named


def test_widget_subwidget_layout(imagej_widget: NapariImageJWidget):
    """Tests the number and expected order of imagej_widget children"""
    subwidgets = imagej_widget.children()
    assert len(subwidgets) == 6
    assert isinstance(imagej_widget.layout(), QVBoxLayout)
    assert isinstance(subwidgets[0], QVBoxLayout)

    assert isinstance(subwidgets[1], NapariImageJMenu)
    assert isinstance(subwidgets[2], JVMEnabledSearchbar)
    assert isinstance(subwidgets[3], SearchResultTree)
    assert isinstance(subwidgets[4], ResultRunner)
    assert isinstance(subwidgets[5], InfoBox)


def test_keymaps(make_napari_viewer, qtbot):
    """Tests that 'Ctrl+L' is added to the keymap by ImageJWidget"""
    viewer: Viewer = make_napari_viewer()
    assert "Control-L" not in viewer.keymap
    NapariImageJWidget(viewer)
    assert "Control-L" in viewer.keymap
    # TODO: I can't seem to figure out how to assert that pressing 'L'
    # sets the focus of the search bar.
    # Typing viewer.keymap['L'](viewer) does nothing. :(


def _run_buttons(imagej_widget: NapariImageJWidget):
    return imagej_widget.result_runner.button_pane.findChildren(QPushButton)


def _ensure_searchers_available(imagej_widget: NapariImageJWidget, asserter):
    tree = imagej_widget.result_tree
    # Find the ModuleSearcher
    numSearchers = len(ij().plugin().getPluginsOfType(jc.Searcher))
    try:
        asserter(lambda: tree.topLevelItemCount() == numSearchers)
    except Exception:
        # HACK: Sometimes (especially on CI), not all Searchers make it into
        # the tree.
        # For our purposes of removing those items, though, we don't care how
        # many make it in. All that matters is that no more will be added.
        # So, if we timeout, we assume no more will be added, and carry on.
        pass


def test_result_single_click(imagej_widget: NapariImageJWidget, qtbot, asserter):
    # Assert that there are initially no buttons
    assert len(_run_buttons(imagej_widget)) == 0
    # Wait for the tree to be ready
    tree = imagej_widget.result_tree
    _ensure_searchers_available(imagej_widget, asserter)
    # Find the ModuleSearcher
    searcher_item = _searcher_tree_named(tree, "Command")
    assert searcher_item is not None
    searcher_item.setCheckState(0, Qt.Checked)
    asserter(lambda: searcher_item.checkState(0) == Qt.Checked)
    # Search something, then wait for the results to populate
    imagej_widget.result_tree.search("Frangi")
    asserter(lambda: searcher_item.childCount() > 0)
    # Test single click spawns buttons
    item = searcher_item.child(0)
    rect = tree.visualItemRect(item)
    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=rect.center())

    def assert_buttons():
        expected = len(imagej_widget.result_runner._buttons_for(item.result))
        actual = len(_run_buttons(imagej_widget))
        return expected == actual

    asserter(assert_buttons)
    # Test single click on searcher hides buttons
    item = searcher_item
    rect = tree.visualItemRect(item)
    qtbot.mouseClick(tree.viewport(), Qt.LeftButton, pos=rect.center())
    # Ensure we don't see any text in the runner widget
    asserter(
        lambda: imagej_widget.result_runner.selected_module_label.isHidden()
        or imagej_widget.result_runner.selected_module_label.text() == ""
    )

    # Ensure we don't see any buttons in the runner widget
    def assert_no_buttons():
        expected = 0
        actual = len(_run_buttons(imagej_widget))
        return expected == actual

    asserter(assert_no_buttons)


def test_searchbar_results_transitions(
    imagej_widget: NapariImageJWidget, asserter, qtbot
):
    """
    Ensures that the arrow keys can be used to transfer focus between
    the searchbar and the results table
    """
    tree: SearchResultTree = imagej_widget.result_tree
    _ensure_searchers_available(imagej_widget, asserter)

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


def test_search_tree_ordering(imagej_widget: NapariImageJWidget, asserter):
    """
    Ensures that the Searchers appear in priority order in
    the search tree
    """

    # Ensure that the tree is fully populated
    _ensure_searchers_available(imagej_widget, asserter)

    # Define the correct ordering
    def ordering(s1: "jc.Searcher", s2: "jc.Searcher") -> bool:
        # Higher priority items come before lower ones
        return s1.priority >= s2.priority

    # Ensure the ordering applies
    results = imagej_widget.result_tree
    for i in range(results.topLevelItemCount() - 1):
        asserter(lambda: ordering(results.topLevelItem(i), results.topLevelItem(i + 1)))


def test_imagej_search_tree_disable(ij, imagej_widget: NapariImageJWidget, asserter):
    # Grab an arbitratry enabled Searcher
    asserter(lambda: imagej_widget.result_tree.topLevelItemCount() > 0)
    searcher_item = imagej_widget.result_tree.topLevelItem(0)
    searcher_item.setCheckState(0, Qt.Checked)
    asserter(lambda: searcher_item.checkState(0) == Qt.Checked)
    asserter(lambda: searcher_item.childCount() == 0)

    # Disable the searcher, assert the proper ImageJ response
    searcher_item.setCheckState(0, Qt.Unchecked)
    asserter(
        lambda: not ij.get("org.scijava.search.SearchService").enabled(
            searcher_item._searcher
        )
    )

    # Enabled the searcher, assert the proper ImageJ response
    searcher_item.setCheckState(0, Qt.Checked)
    asserter(
        lambda: ij.get("org.scijava.search.SearchService").enabled(
            searcher_item._searcher
        )
    )


def test_widget_finalization(ij, imagej_widget: NapariImageJWidget, asserter):
    # Ensure that we have the handle on a non-null SearchOperation
    assert imagej_widget.result_tree._searchOperation is not None

    # Ensure that all Searchers are represented in the tree with a top level item
    numSearchers = len(ij.plugin().getPluginsOfType(jc.Searcher))
    asserter(lambda: imagej_widget.result_tree.topLevelItemCount() == numSearchers)


def test_widget_clearing(imagej_widget: NapariImageJWidget, qtbot, asserter):
    """
    Ensures that searching something clears the result runner
    """

    # Ensure that the tree is fully populated
    _ensure_searchers_available(imagej_widget, asserter)

    # Find the ModuleSearcher
    searcher_item = _searcher_tree_named(imagej_widget.result_tree, "Command")
    assert searcher_item is not None
    searcher_item.setCheckState(0, Qt.Checked)
    asserter(lambda: searcher_item.checkState(0) == Qt.Checked)
    # Search something, then wait for the results to populate
    imagej_widget.search.bar.insert("Frangi")
    asserter(lambda: searcher_item.childCount() > 0)
    # Test single click spawns buttons
    item = searcher_item.child(0)
    rect = imagej_widget.result_tree.visualItemRect(item)
    qtbot.mouseClick(
        imagej_widget.result_tree.viewport(), Qt.LeftButton, pos=rect.center()
    )
    asserter(lambda: len(_run_buttons(imagej_widget)) > 0)

    # Search something else
    imagej_widget.search.bar.insert("Add")

    # Wait for the buttons to disappear
    asserter(imagej_widget.result_runner.selected_module_label.isHidden)
    asserter(lambda: len(_run_buttons(imagej_widget)) == 0)


def test_info_validity(imagej_widget: NapariImageJWidget, qtbot, asserter):
    """
    Ensures that searching something clears the result runner
    """

    # Wait for the info to populate
    ij()

    # Check the version
    info_box = imagej_widget.info_box

    asserter(lambda: info_box.version_bar.text() == f"ImageJ2 v{ij().getVersion()}")


def test_handle_output_layer(imagej_widget: NapariImageJWidget, qtbot, asserter):
    output_handler = getattr(imagej_widget, "output_handler")
    viewer = imagej_widget.napari_viewer
    asserter(lambda: len(viewer.layers) == 0)

    img = Image(data=ones((3, 3, 3)), name="test")
    output_handler.emit(img)
    asserter(lambda: len(viewer.layers) == 1)


def test_handle_output_non_layer(imagej_widget: NapariImageJWidget, asserter):
    output_handler = getattr(imagej_widget, "output_handler")
    viewer = imagej_widget.napari_viewer
    existing_widget_names = [k for k in viewer.window._dock_widgets.keys()]

    data = {"data": [("b", 4)], "name": "test", "external": False}
    output_handler.emit(data)

    def check_for_new_widget():
        current_widget_names = [k for k in viewer.window._dock_widgets.keys()]
        return "test" not in existing_widget_names and "test" in current_widget_names

    asserter(check_for_new_widget)


def test_event_subscriber_registered(ij, imagej_widget: NapariImageJWidget, asserter):
    """
    Ensure that a NapariEventSubscriber is registered to capture SciJavaEvents.
    """
    subs = subscribers(ij, jc.SciJavaEvent.class_)
    assert any(isinstance(sub, NapariEventSubscriber) for sub in subs)
