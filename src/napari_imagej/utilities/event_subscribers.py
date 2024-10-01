"""
Module containing various EventSubscribers used by
napari-imagej functionality
"""

from jpype import JImplements, JOverride
from qtpy.QtCore import Signal

from napari_imagej import nij
from napari_imagej.java import jc
from napari_imagej.utilities.logging import log_debug


@JImplements(["org.scijava.event.EventSubscriber"], deferred=True)
class NapariEventSubscriber(object):
    @JOverride
    def onEvent(self, event):
        log_debug(str(event))

    @JOverride
    def getEventClass(self):
        return jc.ModuleEvent.class_

    @JOverride
    def equals(self, other):
        return isinstance(other, NapariEventSubscriber)


@JImplements(["org.scijava.event.EventSubscriber"], deferred=True)
class ProgressBarListener(object):
    def __init__(self, progress_signal: Signal):
        self.progress_signal = progress_signal

    @JOverride
    def onEvent(self, event):
        self.progress_signal.emit(event)

    @JOverride
    def getEventClass(self):
        return jc.ModuleEvent.class_

    @JOverride
    def equals(self, other):
        return isinstance(other, ProgressBarListener)


@JImplements(["org.scijava.event.EventSubscriber"], deferred=True)
class UIShownListener(object):
    def __init__(self):
        self.initialized = False

    @JOverride
    def onEvent(self, event):
        if not self.initialized:
            # add our custom settings to the User Interface
            if nij.ij.legacy and nij.ij.legacy.isActive():
                self._ij1_UI_setup()
            self._ij2_UI_setup(event.getUI())
            self.initialized = True

    @JOverride
    def getEventClass(self):
        return jc.UIShownEvent.class_

    @JOverride
    def equals(self, other):
        return isinstance(other, UIShownListener)

    def _ij1_UI_setup(self):
        """Configure the ImageJ Legacy GUI"""
        nij.ij.IJ.getInstance().exitWhenQuitting(False)

    def _ij2_UI_setup(self, ui: "jc.UserInterface"):
        """Configure the ImageJ2 Swing GUI behavior"""
        # Overwrite the WindowListeners so we control closing behavior
        self._kill_window_listeners(self._get_AWT_frame(ui))

    def _get_AWT_frame(self, ui: "jc.UserInterface"):
        appFrame = ui.getApplicationFrame()
        if isinstance(appFrame, jc.Window):
            return appFrame
        elif isinstance(appFrame, jc.UIComponent):
            return appFrame.getComponent()

    def _kill_window_listeners(self, window):
        """Replace the WindowListeners present on window with our own"""
        # Remove all preset WindowListeners
        for listener in window.getWindowListeners():
            window.removeWindowListener(listener)

        # Add our own behavior for WindowEvents
        @JImplements("java.awt.event.WindowListener")
        class NapariAdapter(object):
            @JOverride
            def windowOpened(self, event):
                pass

            @JOverride
            def windowClosing(self, event):
                # We don't want to shut down anything, we just want to hide the window.
                window.setVisible(False)

            @JOverride
            def windowClosed(self, event):
                pass

            @JOverride
            def windowIconified(self, event):
                pass

            @JOverride
            def windowDeiconified(self, event):
                pass

            @JOverride
            def windowActivated(self, event):
                pass

            @JOverride
            def windowDeactivated(self, event):
                pass

        listener = NapariAdapter()
        nij.ij.object().addObject(listener)
        window.addWindowListener(listener)
