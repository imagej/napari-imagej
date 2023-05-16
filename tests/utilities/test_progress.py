import pytest
from napari.utils import progress

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

    ij.event().publish(jc.ModuleExecutingEvent(example_module))
    asserter(lambda: pbr.n == 1)

    ij.event().publish(jc.ModuleExecutedEvent(example_module))
    asserter(lambda: pbr.n == 2)

    ij.event().publish(jc.ModuleFinishedEvent(example_module))
    asserter(lambda: pbr.n == 3)
    asserter(lambda: example_module not in pm.prog_bars)


def test_progress_cancel_via_events(imagej_widget, ij, example_module, asserter):
    pm.init_progress(example_module)
    asserter(lambda: example_module in pm.prog_bars)
    pbr = pm.prog_bars[example_module]
    asserter(lambda: pbr.n == 0)

    ij.event().publish(jc.ModuleExecutingEvent(example_module))
    asserter(lambda: pbr.n == 1)

    ij.event().publish(jc.ModuleExecutedEvent(example_module))
    asserter(lambda: pbr.n == 2)

    ij.event().publish(jc.ModuleCanceledEvent(example_module))
    asserter(lambda: example_module not in pm.prog_bars)


@pytest.mark.qt_no_exception_capture
def test_progress_error_via_events(imagej_widget, ij, example_module, asserter, qtbot):
    pm.init_progress(example_module)
    asserter(lambda: example_module in pm.prog_bars)
    pbr = pm.prog_bars[example_module]
    asserter(lambda: pbr.n == 0)

    ij.event().publish(jc.ModuleExecutingEvent(example_module))
    asserter(lambda: pbr.n == 1)

    ij.event().publish(jc.ModuleExecutedEvent(example_module))
    asserter(lambda: pbr.n == 2)

    with qtbot.capture_exceptions() as exceptions:
        ij.event().publish(
            jc.ModuleErroredEvent(example_module, jc.IllegalArgumentException("Yay"))
        )
        asserter(lambda: example_module not in pm.prog_bars)
    assert len(exceptions) == 1
    assert exceptions[0][0] == jc.IllegalArgumentException
    assert exceptions[0][1].getMessage() == "Yay"
