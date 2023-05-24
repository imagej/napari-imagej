"""
This module contains ImageJWidget, the top-level QWidget enabling
graphical access to ImageJ functionality.

This Widget is made accessible to napari through napari.yml
"""
from typing import Callable

from jpype import JArray, JImplements, JOverride
from magicgui.widgets import FunctionGui, Widget
from napari import Viewer
from napari.layers import Layer
from qtpy.QtCore import QThread, Signal, Slot
from qtpy.QtWidgets import QTreeWidgetItem, QVBoxLayout, QWidget
from scyjava import jstacktrace, when_jvm_stops

from napari_imagej.java import ij, init_ij, jc
from napari_imagej.utilities._module_utils import _non_layer_widget
from napari_imagej.utilities.event_subscribers import (
    NapariEventSubscriber,
    ProgressBarListener,
)
from napari_imagej.utilities.events import subscribe
from napari_imagej.utilities.logging import is_debug
from napari_imagej.utilities.progress_manager import pm
from napari_imagej.widgets.info_bar import InfoBox
from napari_imagej.widgets.menu import NapariImageJMenu
from napari_imagej.widgets.result_runner import ResultRunner
from napari_imagej.widgets.result_tree import (
    SearcherTreeItem,
    SearchResultTree,
    SearchResultTreeItem,
)
from napari_imagej.widgets.searchbar import JVMEnabledSearchbar
from napari_imagej.widgets.widget_utils import JavaErrorMessageBox


class NapariImageJWidget(QWidget):
    """The top-level ImageJ widget for napari."""

    output_handler = Signal(object)
    progress_handler = Signal(object)
    ij_error_handler = Signal(object)

    def __init__(self, napari_viewer: Viewer):
        super().__init__()
        self.napari_viewer = napari_viewer
        self.setLayout(QVBoxLayout())

        # -- NapariImageJWidget construction -- #

        # At the top: the napari-imagej menu
        self.menu: NapariImageJMenu = NapariImageJMenu(napari_viewer)
        self.layout().addWidget(self.menu)
        # Next: the search bar
        self.search: JVMEnabledSearchbar = JVMEnabledSearchbar()
        self.layout().addWidget(self.search)
        # Then: The results tree
        self.result_tree: SearchResultTree = SearchResultTree(self.output_handler)
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
        self.progress_handler.connect(self._update_progress)
        self.ij_error_handler.connect(self._handle_ij_error)

        # -- Final setup -- #

        self.ij_initializer: ImageJInitializer = ImageJInitializer(self)

        # Bind L key to search bar.
        # Note the requirement for an input parameter
        napari_viewer.bind_key(
            "Control-L", lambda _: self.search.bar.setFocus(), overwrite=True
        )

        # Put the focus on the search bar
        self.search.bar.setFocus()

        # Start constructing the ImageJ instance
        self.ij_initializer.start()

    def wait_for_finalization(self):
        self.ij_initializer.wait()

    @Slot(object)
    def _handle_output(self, data):
        if isinstance(data, Layer):
            self.napari_viewer.add_layer(data)
        elif isinstance(data, dict):
            widget: Widget = _non_layer_widget(data.get("data", {}))
            if data.get("external", False):
                widget.name = data.get("name", "")
                widget.show(run=True)
            else:
                self.napari_viewer.window.add_dock_widget(
                    widget, name=data.get("name", "")
                )
        elif isinstance(data, (FunctionGui, Callable)):
            self.napari_viewer.window.add_dock_widget(data, name=data.name)
        else:
            raise TypeError(f"Do not know how to display {data}")

    @Slot(object)
    def _update_progress(self, event: "jc.ModuleEvent"):
        """
        Updates the napari progress bar of the given module.

        NB: This MUST be done within this slot, as slot functions
        are run on the GUI thread. The module itself is run on
        Java threads spawned within the ModuleService, and we cannot
        update Qt GUI elements from those threads.
        """
        module = event.getModule()
        # Update progress if we see one of these
        if isinstance(
            event,
            (jc.ModuleExecutingEvent, jc.ModuleExecutedEvent, jc.ModuleFinishedEvent),
        ):
            pm.update_progress(module)
        # Close progress if we see one of these
        if isinstance(
            event,
            (jc.ModuleFinishedEvent, jc.ModuleCanceledEvent, jc.ModuleErroredEvent),
        ):
            pm.close(module)
        if isinstance(event, jc.ModuleErroredEvent):
            if not ij().ui().isVisible():
                # TODO Use napari's error handler once it works better
                # see https://github.com/imagej/napari-imagej/issues/234
                module_title = str(module.getInfo().getTitle())
                title = f"An error occurred in Java while executing {module_title}:"
                exception_str = jstacktrace(event.getException())
                msg = JavaErrorMessageBox(title, exception_str)
                msg.exec()

    @Slot(object)
    def _handle_ij_error(self, exc: Exception):
        """
        Handles errors associated initializing ImageJ.
        Initializing ImageJ can fail for all sorts of reasons,
        so we give it special attention here.

        NB: This MUST be done within this slot, as slot functions
        are run on the GUI thread. napari-imagej runs ImageJ initialization
        on a separate Qt thread, which isn't the GUI thread.
        """
        # Disable the searchbar
        self.search.bar.finalize_on_error()
        # Print thet error
        title = "ImageJ could not be initialized, due to the following error:"
        exception_str = jstacktrace(exc)
        msg: JavaErrorMessageBox = JavaErrorMessageBox(title, exception_str)
        msg.exec()


class ImageJInitializer(QThread):
    """
    QThread responsible for initializing ImageJ, and modifying NapariImageJWidget
    afterwards.
    """

    def __init__(self, napari_imagej_widget: NapariImageJWidget):
        super().__init__()
        self.widget: NapariImageJWidget = napari_imagej_widget

    def run(self):
        """
        Initializes ImageJ, and thenf inalizes components of napari_imagej_widget.

        Functionality partitioned into functions by subwidget.
        """
        try:
            # Initialize ImageJ
            init_ij()
            # Finalize the menu
            self.widget.menu.finalize()
            # Finalize the search bar
            self.widget.search.finalize()
            # Finalize the results tree
            self._finalize_results_tree()
            # Finalize the info bar
            self._finalize_info_bar()
            # Finalize EventSubscribers
            self._finalize_subscribers()
        except Exception as e:
            # Handle the exception on the GUI thread
            self.widget.ij_error_handler.emit(e)

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
        self.widget.info_box.version_bar.setText(f"ImageJ2 v{ij().getVersion()}")

    def _finalize_subscribers(self):
        # Progress bar subscriber
        progress_listener = ProgressBarListener(self.widget.progress_handler)
        subscribe(ij(), jc.ModuleEvent.class_, progress_listener)
        # Debug printer subscriber
        if is_debug():
            subscriber = NapariEventSubscriber()
            subscribe(ij(), jc.SciJavaEvent.class_, subscriber)
