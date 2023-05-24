import pytest
from napari.utils import progress
from qtpy.QtWidgets import QMessageBox
from scyjava import jstacktrace

from napari_imagej.utilities.progress_manager import pm
from tests.utils import jc


@pytest.fixture
def example_module(ij):
    info = ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )
    return ij.module().createModule(info)


def test_progress(ij, example_module):
    pm.init_progress(example_module)
    example_progress: progress = pm.prog_bars[example_module]
    assert example_progress.n == 0
    pm.update_progress(example_module)
    assert example_progress.n == 1
    pm.update_progress(example_module)
    assert example_progress.n == 2
    pm.update_progress(example_module)
    assert example_progress.n == 3
    pm.close(example_module)
    assert example_module not in pm.prog_bars


def test_progress_update_via_events(imagej_widget, ij, example_module, asserter):
    pm.init_progress(example_module)
    asserter(lambda: example_module in pm.prog_bars)
    pbr = pm.prog_bars[example_module]
    asserter(lambda: pbr.n == 0)

    imagej_widget.progress_handler.emit(jc.ModuleExecutingEvent(example_module))
    asserter(lambda: pbr.n == 1)

    imagej_widget.progress_handler.emit(jc.ModuleExecutedEvent(example_module))
    asserter(lambda: pbr.n == 2)

    imagej_widget.progress_handler.emit(jc.ModuleFinishedEvent(example_module))
    asserter(lambda: pbr.n == 3)
    asserter(lambda: example_module not in pm.prog_bars)


def test_progress_cancel_via_events(imagej_widget, ij, example_module, asserter):
    pm.init_progress(example_module)
    asserter(lambda: example_module in pm.prog_bars)
    pbr = pm.prog_bars[example_module]
    asserter(lambda: pbr.n == 0)

    imagej_widget.progress_handler.emit(jc.ModuleExecutingEvent(example_module))
    asserter(lambda: pbr.n == 1)

    imagej_widget.progress_handler.emit(jc.ModuleExecutedEvent(example_module))
    asserter(lambda: pbr.n == 2)

    imagej_widget.progress_handler.emit(jc.ModuleCanceledEvent(example_module))
    asserter(lambda: example_module not in pm.prog_bars)


def test_progress_error_via_events(
    imagej_widget, ij, example_module, asserter, qtbot, popup_handler
):
    pm.init_progress(example_module)
    asserter(lambda: example_module in pm.prog_bars)
    pbr = pm.prog_bars[example_module]
    asserter(lambda: pbr.n == 0)

    imagej_widget.progress_handler.emit(jc.ModuleExecutingEvent(example_module))
    asserter(lambda: pbr.n == 1)

    imagej_widget.progress_handler.emit(jc.ModuleExecutedEvent(example_module))
    asserter(lambda: pbr.n == 2)

    exception = jc.IllegalArgumentException("Yay")

    def emit():
        imagej_widget.progress_handler.emit(
            jc.ModuleErroredEvent(example_module, exception)
        )

    expected_popup_text = jstacktrace(exception)
    popup_handler(expected_popup_text, False, QMessageBox.Ok, emit)
    asserter(lambda: example_module not in pm.prog_bars)
