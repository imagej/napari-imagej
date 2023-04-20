"""
A module testing napari_imagej.types.converters.trackmate
"""
from typing import Tuple

import numpy as np
import pytest
from napari import Viewer
from napari.layers import Labels, Tracks

from napari_imagej import settings
from napari_imagej.java import JavaClasses
from napari_imagej.types.converters.trackmate import TrackMateClasses


class TestTrackMateClasses(TrackMateClasses):
    @JavaClasses.blocking_import
    def DisplaySettings(self):
        return "fiji.plugin.trackmate.gui.displaysettings.DisplaySettings"

    @JavaClasses.blocking_import
    def HyperStackDisplayer(self):
        return "fiji.plugin.trackmate.visualization.hyperstack.HyperStackDisplayer"

    @JavaClasses.blocking_import
    def SelectionModel(self):
        return "fiji.plugin.trackmate.SelectionModel"


jc = TestTrackMateClasses()


TESTING_LEGACY: bool = settings["include_imagej_legacy"].get(bool)
endpoint = settings["imagej_directory_or_endpoint"].get(str)
TESTING_TRACKMATE = (
    "sc.fiji:trackmate" in endpoint.lower() or "sc.fiji:fiji" in endpoint.lower()
)


@pytest.fixture
def trackMate_example(ij):
    if not (TESTING_LEGACY and TESTING_TRACKMATE):
        pytest.skip("TrackMate functionality requires ImageJ and TrackMate!")

    trackMate: jc.TrackMate = jc.TrackMate()
    model: jc.Model = trackMate.getModel()
    # Build track 1 with 5 spots
    s1 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S1")
    s2 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S2")
    s3 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S3")
    s4 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S4")
    s5a = jc.Spot(-1.0, 0.0, 0.0, 1.0, -1.0, "S5a")
    s6a = jc.Spot(-1.0, 0.0, 0.0, 1.0, -1.0, "S6a")
    s5b = jc.Spot(1.0, 1.0, 1.0, 1.0, -1.0, "S5b")
    s6b = jc.Spot(1.0, 1.0, 1.0, 1.0, -1.0, "S6b")
    # Build track 2 with 2 spots
    s7 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S7")
    s8 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S8")
    # Build track 3 with 2 spots
    s9 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S9")
    s10 = jc.Spot(0.0, 0.0, 0.0, 1.0, -1.0, "S10")

    model.beginUpdate()
    try:
        model.addSpotTo(s1, jc.Integer(0))
        model.addSpotTo(s2, jc.Integer(1))
        model.addSpotTo(s3, jc.Integer(2))
        model.addSpotTo(s4, jc.Integer(3))
        model.addSpotTo(s5a, jc.Integer(4))
        model.addSpotTo(s5b, jc.Integer(4))
        model.addSpotTo(s6a, jc.Integer(5))
        model.addSpotTo(s6b, jc.Integer(5))
        model.addEdge(s1, s2, 0.0)
        model.addEdge(s2, s3, 0.0)
        model.addEdge(s3, s4, 0.0)
        model.addEdge(s4, s5a, 0.0)
        model.addEdge(s4, s5b, 0.0)
        model.addEdge(s5a, s6a, 0.0)
        model.addEdge(s5b, s6b, 0.0)

        model.addSpotTo(s7, jc.Integer(0))
        model.addSpotTo(s8, jc.Integer(1))
        model.addEdge(s7, s8, 0.0)

        model.addSpotTo(s9, jc.Integer(0))
        model.addSpotTo(s10, jc.Integer(1))
        model.addEdge(s9, s10, 0.0)
    finally:
        model.endUpdate()

    ij.object().addObject(trackMate)
    return trackMate


def ui_visible(ij):
    frame = ij.ui().getDefaultUI().getApplicationFrame()
    if isinstance(frame, jc.UIComponent):
        frame = frame.getComponent()
    return frame and frame.isVisible()


@pytest.fixture(autouse=True)
def clean_gui_elements(asserter, ij, viewer: Viewer):
    """Fixture to remove image data from napari and ImageJ2"""

    # Test pre-processing

    # Test processing
    yield

    # Test post-processing

    # After each test runs, clear all layers from napari
    if viewer is not None:
        viewer.layers.clear()

    # After each test runs, clear all ImagePlus objects from ImageJ
    if ij.legacy and ij.legacy.isActive():
        while ij.WindowManager.getCurrentImage():
            imp = ij.WindowManager.getCurrentImage()
            imp.changes = False
            imp.close()

    # After each test runs, clear all displays from ImageJ2
    while not ij.display().getDisplays().isEmpty():
        for display in ij.display().getDisplays():
            display.close()

    # Close the UI if needed
    if ui_visible(ij):
        frame = ij.ui().getDefaultUI().getApplicationFrame()
        if isinstance(frame, jc.UIComponent):
            frame = frame.getComponent()
        ij.thread().queue(
            lambda: frame.dispatchEvent(
                jc.WindowEvent(frame, jc.WindowEvent.WINDOW_CLOSING)
            )
        )
        # Wait for the Frame to be hidden
        asserter(lambda: not ui_visible(ij))


pytest.mark.skipif(
    not (TESTING_TRACKMATE and TESTING_LEGACY),
    "TrackMate functionality requires ImageJ and TrackMate!",
)


def test_Model_to_Tracks(ij, trackMate_example):
    # Convert the TrackMate instance into a Dataset with Rois
    # this is what we'd convert in practice.
    model = trackMate_example.getModel()
    selection_model = jc.SelectionModel(model)
    imp = ij.convert().convert(ij.py.to_java(np.zeros((10, 10))), jc.ImagePlus)
    display_settings = jc.DisplaySettings()

    hyper_stack_displayer = jc.HyperStackDisplayer(
        model, selection_model, imp, display_settings
    )
    hyper_stack_displayer.render()

    dataset = ij.convert().convert(imp, jc.Dataset)

    # Convert the dataset's rois into its Python equivalent
    layers = ij.py.from_java(dataset.getProperties()["rois"])
    # Assert we receive a Tracks Layer
    assert isinstance(layers, Tuple)
    tracks, labels = layers
    assert isinstance(tracks, Tracks)
    assert isinstance(labels, Labels)
    # Assert there are 5 branches
    assert len(tracks.graph) == 5
    # Assert that tracks 1 and 2 split from track 0
    assert tracks.graph == {0: [], 1: [0], 2: [0], 3: [], 4: []}
    expected_data = np.array(
        [
            [0.0, 0.0, 0.0, 0.0],  # S1
            [0.0, 1.0, 0.0, 0.0],  # S2
            [0.0, 2.0, 0.0, 0.0],  # S3
            [0.0, 3.0, 0.0, 0.0],  # S4
            [1.0, 4.0, 0.0, -1.0],  # S5a
            [1.0, 5.0, 0.0, -1.0],  # S5b
            [2.0, 4.0, 1.0, 1.0],  # S6a
            [2.0, 5.0, 1.0, 1.0],  # S6b
            [3.0, 0.0, 0.0, 0.0],  # S7
            [3.0, 1.0, 0.0, 0.0],  # S8
            [4.0, 0.0, 0.0, 0.0],  # S9
            [4.0, 1.0, 0.0, 0.0],
        ]
    )  # S11

    assert np.array_equal(tracks.data, expected_data)
