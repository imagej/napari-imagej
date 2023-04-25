import pytest
from napari.utils import progress

from napari_imagej.utilities.progress_manager import pm


@pytest.fixture
def example_module(ij):
    info = ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )
    return ij.module().createModule(info)


def test_progress(ij, example_module, asserter):
    pm.init_progress(example_module)
    example_progress: progress = pm.prog_bars[example_module]
    assert example_progress.n == 0
    pm.update_progress(example_module)
    pm.update_progress(example_module)
    pm.update_progress(example_module)
    assert example_module not in pm.prog_bars
