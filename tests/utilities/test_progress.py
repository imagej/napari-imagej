import pytest
from napari.utils import progress

from napari_imagej.java import jc
from napari_imagej.utilities.progress_manager import pm


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
