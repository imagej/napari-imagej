import numpy as np
from napari.layers import Labels, Tracks
from scyjava import Priority

from napari_imagej.java import JavaClasses, ij
from napari_imagej.types.converters import java_to_py_converter


def trackmate_present():
    """
    Returns True iff TrackMate is on the classpath
    """
    try:
        jc.TrackMate
        return True
    except ImportError:
        return False


def track_overlay_predicate(obj):
    """
    Returns True iff obj is a TrackMate Overlay, wrapped into a ROITree.
    """
    # Prevent ImportErrors by ensuring TrackMate is on the classpath
    if not trackmate_present():
        return False
    # TrackMate data is wrapped in ImageJ Rois - we need ImageJ Legacy
    if not (ij().legacy and ij().legacy.isActive()):
        return False
    # TrackMate data will be wrapped within a ROITree
    if not isinstance(obj, jc.ROITree):
        return False
    # Where each child is a IJRoiWrapper
    children = [child.data() for child in obj.children()]
    for child in children:
        if not isinstance(child, jc.IJRoiWrapper):
            return False
    # More specifically, there must be (at least) two IJRoiWrapper children.
    if len(children) < 2:
        return False
    # One must be a SpotOverlay
    if not any(isinstance(child.getRoi(), jc.SpotOverlay) for child in children):
        return False
    # And another is a TrackOverlay
    if not any(isinstance(child.getRoi(), jc.TrackOverlay) for child in children):
        return False
    return True


@java_to_py_converter(
    predicate=track_overlay_predicate, priority=Priority.EXTREMELY_HIGH
)
def _trackMate_model_to_tracks(obj: "jc.ROITree"):
    """
    Converts a TrackMate overlay into a napari Tracks layer
    """
    trackmate_plugins = ij().object().getObjects(jc.TrackMate)
    if len(trackmate_plugins) == 0:
        raise IndexError("Expected a TrackMate instance, but there was none!")
    model: jc.Model = trackmate_plugins[-1].getModel()
    neighbor_index = model.getTrackModel().getDirectedNeighborIndex()

    src_image = obj.children()[0].data().getRoi().getImage()
    cal = jc.TMUtils.getSpatialCalibration(src_image)

    spots = []
    graph = {}
    branch_ids = {}
    index = 0
    for track_id in model.getTrackModel().unsortedTrackIDs(True):
        # Decompose the track into branches
        branch_decomposition = jc.ConvexBranchesDecomposition.processTrack(
            track_id, model.getTrackModel(), neighbor_index, True, False
        )
        branch_graph = jc.ConvexBranchesDecomposition.buildBranchGraph(
            branch_decomposition
        )
        # Pass 1 - assign an id to each branch, and add the spots
        for branch in branch_graph.vertexSet():
            branch_ids[branch] = index
            for spot in branch:
                x = spot.getFeature(jc.Spot.POSITION_X)
                y = spot.getFeature(jc.Spot.POSITION_Y)
                z = spot.getFeature(jc.Spot.POSITION_Z)
                t = spot.getFeature(jc.Spot.FRAME).intValue()
                spots.append([index, t, z / cal[2], y / cal[1], x / cal[0]])

            index += 1
        # Pass 2 - establish parent-child relationships
        for branch in branch_graph.vertexSet():
            branch_id = branch_ids[branch]
            graph[branch_id] = []
            parent_edges = branch_graph.incomingEdgesOf(branch)
            for parent_edge in parent_edges:
                parent_branch = branch_graph.getEdgeSource(parent_edge)
                graph[branch_id].append(branch_ids[parent_branch])

    spot_data = np.array(spots)
    if "Z" not in src_image.dims:
        spot_data = np.delete(spot_data, 2, 1)
        # rois = [np.delete(roi, 2, 1) for roi in rois]

    tracks_name = f"{src_image.getTitle()}-tracks"
    tracks = Tracks(data=spot_data, graph=graph, name=tracks_name)
    rois_name = f"{src_image.getTitle()}-rois"
    java_label_img = jc.LabelImgExporter.createLabelImagePlus(
        trackmate_plugins[-1], False, False, False
    )
    py_label_img = ij().py.from_java(java_label_img)
    labels = Labels(data=py_label_img.data, name=rois_name)

    return (tracks, labels)


class TrackMateClasses(JavaClasses):
    # TrackMate Types

    @JavaClasses.blocking_import
    def BranchTableView(self):
        return "fiji.plugin.trackmate.visualization.table.BranchTableView"

    @JavaClasses.blocking_import
    def ConvexBranchesDecomposition(self):
        return "fiji.plugin.trackmate.graph.ConvexBranchesDecomposition"

    @JavaClasses.blocking_import
    def LabelImgExporter(self):
        return "fiji.plugin.trackmate.action.LabelImgExporter"

    @JavaClasses.blocking_import
    def Model(self):
        return "fiji.plugin.trackmate.Model"

    @JavaClasses.blocking_import
    def Spot(self):
        return "fiji.plugin.trackmate.Spot"

    @JavaClasses.blocking_import
    def SpotOverlay(self):
        return "fiji.plugin.trackmate.visualization.hyperstack.SpotOverlay"

    @JavaClasses.blocking_import
    def TMUtils(self):
        return "fiji.plugin.trackmate.util.TMUtils"

    @JavaClasses.blocking_import
    def TrackMate(self):
        return "fiji.plugin.trackmate.TrackMate"

    @JavaClasses.blocking_import
    def TrackOverlay(self):
        return "fiji.plugin.trackmate.visualization.hyperstack.TrackOverlay"


jc = TrackMateClasses()
