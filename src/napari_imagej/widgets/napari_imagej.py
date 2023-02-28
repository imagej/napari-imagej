"""
This module contains ImageJWidget, the top-level QWidget enabling
graphical access to ImageJ functionality.

This Widget is made accessible to napari through napari.yml
"""
from jpype import JArray, JImplements, JOverride
from magicgui.widgets import Widget
from napari import Viewer
from napari.layers import Layer
from qtpy.QtCore import QThread, Signal, Slot
from qtpy.QtWidgets import QMessageBox, QTreeWidgetItem, QVBoxLayout, QWidget
from scyjava import when_jvm_stops

from napari_imagej.java import ij, init_ij_async, java_signals, jc
from napari_imagej.utilities._module_utils import SubWidgetData, _non_layer_widget
from napari_imagej.utilities.logging import log_debug
from napari_imagej.widgets.info_bar import InfoBox
from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.result_runner import ResultRunner
from napari_imagej.widgets.result_tree import (
    SearcherTreeItem,
    SearchResultTree,
    SearchResultTreeItem,
)
from napari_imagej.widgets.searchbar import JVMEnabledSearchbar


class NapariImageJWidget(QWidget):
    """The top-level ImageJ widget for napari."""

    output_handler = Signal(object)

    def __init__(self, napari_viewer: Viewer):
        super().__init__()
        self.napari_viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        # First things first, let's start up imagej (in the background)
        java_signals.when_initialization_fails(self._handle_error)

        # -- NapariImageJWidget construction -- #

        # At the top: the napari-imagej menu
        self.menu: NapariImageJMenu = NapariImageJMenu(napari_viewer)
        self.layout().addWidget(self.menu)
        # Next: the search bar
        self.search: JVMEnabledSearchbar = JVMEnabledSearchbar()
        self.layout().addWidget(self.search)
        # Then: The results tree
        self.result_tree: SearchResultTree = SearchResultTree()
        self.layout().addWidget(self.result_tree)
        # Second-to-lastly: The SearchResult runner
        self.result_runner: ResultRunner = ResultRunner(
            napari_viewer, self.output_handler
        )
        self.layout().addWidget(self.result_runner)
        # Finally: The InfoBar
        self.info_box: InfoBox = InfoBox()
        self.layout().addWidget(self.info_box)

        # -- Interwidget connections -- #

        # When the text bar changes, update the search results.
        self.search.bar.textEdited.connect(self.result_tree.search)
        self.search.bar.textEdited.connect(self.result_runner.clear)

        # When clicking a result, select it with the ResultRunner
        def click(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, SearchResultTreeItem):
                self.result_runner.select(treeItem.result)
            else:
                self.result_runner.clear()

        # self.results.onClick = clickFunc
        self.result_tree.itemClicked.connect(click)

        # When double clicking a result,
        # select it with the ResultRunner and run the first action
        def double_click(treeItem: QTreeWidgetItem):
            if isinstance(treeItem, SearchResultTreeItem):
                self.result_runner.run(treeItem.result)

        self.result_tree.itemDoubleClicked.connect(double_click)

        # When pressing the up arrow on the topmost row in the results list,
        # go back up to the search bar
        self.result_tree.floatAbove.connect(self.search.bar.setFocus)

        # When pressing the down arrow on the search bar,
        # go to the first result item
        def key_down_from_search_bar():
            self.search.bar.clearFocus()
            self.result_tree.setFocus()
            self.result_tree.setCurrentItem(self.result_tree.topLevelItem(0))

        self.search.bar.floatBelow.connect(key_down_from_search_bar)

        # When pressing return on the search bar, select the first result
        # in the results list and run it
        def return_search_bar():
            """Define the return behavior for this widget"""
            result = self.result_tree._first_result()
            if result is not None:
                self.result_runner.run(result)

        self.search.bar.returnPressed.connect(return_search_bar)

        self.output_handler.connect(self._handle_output)

        # -- Final setup -- #

        self.ij_post_init_setup: WidgetFinalizer = WidgetFinalizer(self)
        java_signals.when_ij_ready(self.ij_post_init_setup.start)

        # Bind L key to search bar.
        # Note the requirement for an input parameter
        napari_viewer.bind_key(
            "Control-L", lambda _: self.search.bar.setFocus(), overwrite=True
        )

        # Put the focus on the search bar
        self.search.bar.setFocus()

        # Start constructing the ImageJ instance
        init_ij_async()

    def wait_for_finalization(self):
        self.ij_post_init_setup.wait()

    def _handle_error(self, exc: Exception):
        msg: QMessageBox = QMessageBox()
        msg.setText(str(exc))
        msg.exec()

    @Slot(object)
    def _handle_output(self, data):
        if isinstance(data, Layer):
            self.napari_viewer.add_layer(data)
        elif isinstance(data, SubWidgetData):
            widget: Widget = _non_layer_widget(
                data.get_data(), widget_name=data.get_name()
            )
            if data.display_external():
                widget.show(run=True)
            else:
                self.napari_viewer.window.add_dock_widget(widget, name=data.get_name())
        else:
            raise TypeError(f"Do not know how to display {data}")


class WidgetFinalizer(QThread):
    """
    QThread responsible for modifying NapariImageJWidget AFTER ImageJ is ready.
    """

    def __init__(self, napari_imagej_widget: NapariImageJWidget):
        super().__init__()
        self.widget: NapariImageJWidget = napari_imagej_widget

    def run(self):
        """
        Finalizes components of napari_imagej_widget.

        Functionality partitioned into functions by subwidget.
        """
        # Finalize the Results Tree
        self._finalize_results_tree()
        # Finalize the info bar
        self._finalize_info_bar()
        # Finalize Exception printer
        self._finalize_exception_printer()

    def _finalize_results_tree(self):
        """
        Finalizes the SearchResultTree starting state once ImageJ2 is ready.
        """

        # Define our SearchListener
        @JImplements("org.scijava.search.SearchListener")
        class NapariImageJSearchListener:
            def __init__(self, event_handler: Signal):
                super().__init__()
                self.handler = event_handler

            @JOverride
            def searchCompleted(self, event: "jc.SearchEvent"):
                self.handler.emit(event)

        # Start the search!
        # NB: SearchService.search takes varargs, so we need an array
        listener_arr = JArray(jc.SearchListener)(
            [NapariImageJSearchListener(self.widget.result_tree.process)]
        )
        self.widget.result_tree._searchOperation = (
            ij().get("org.scijava.search.SearchService").search(listener_arr)
        )
        # Make sure that the search stops when we close napari
        # Otherwise the Java threads like to continue
        when_jvm_stops(self.widget.result_tree._searchOperation.terminate)

        # Add SearcherTreeItems for each Searcher
        searchers = ij().plugin().createInstancesOfType(jc.Searcher)
        for searcher in searchers:
            self.widget.result_tree.insert.emit(
                SearcherTreeItem(
                    searcher,
                    checked=ij()
                    .get("org.scijava.search.SearchService")
                    .enabled(searcher),
                    expanded=False,
                )
            )

    def _finalize_info_bar(self):
        self.widget.info_box.version_bar.setText(
            " ".join(["ImageJ", str(ij().getVersion())])
        )

    def _finalize_exception_printer(self):
        @JImplements(["org.scijava.event.EventSubscriber"], deferred=True)
        class NapariEventSubscriber(object):
            @JOverride
            def onEvent(self, event):
                log_debug(str(event))

            @JOverride
            def getEventClass(self):
                return jc.SciJavaEvent.class_

            @JOverride
            def equals(self, other):
                return isinstance(other, NapariEventSubscriber)

        event_bus_field = ij().event().getClass().getDeclaredField("eventBus")
        event_bus_field.setAccessible(True)
        event_bus = event_bus_field.get(ij().event())
        subscriber = NapariEventSubscriber()
        event_bus.subscribe(jc.SciJavaEvent.class_, subscriber)
