import logging
import os
import sys
from multiprocessing.pool import AsyncResult, ThreadPool
from typing import Callable

import imagej
import yaml
from jpype import JClass
from scyjava import config, jimport

# -- LOGGER CONFIG -- #

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)  # TEMP

# -- PUBLIC API -- #


def log_debug(msg: str):
    """
    Provides a debug message to the logger, prefaced by 'napari-imagej: '
    """
    debug_msg = "napari-imagej: " + msg
    _logger.debug(debug_msg)


def get_mode() -> str:
    """
    Returns the mode ImageJ will be run in
    """
    return "headless" if sys.platform == "darwin" else "interactive"


def running_headless() -> bool:
    return get_mode() == "headless"


def imagej_init():
    # Initialize ImageJ
    log_debug("Initializing ImageJ2")

    # -- IMAGEJ CONFIG -- #

    # TEMP: Avoid issues caused by
    # https://github.com/imagej/pyimagej/issues/160
    config.add_repositories(
        {"scijava.public": "https://maven.scijava.org/content/groups/public"}
    )
    config.add_option(f"-Dimagej2.dir={os.getcwd()}")  # TEMP
    config.endpoints.append("io.scif:scifio:0.43.1")
    log_debug("Completed JVM Configuration")

    # Parse imagej settings
    settings: dict = yaml.safe_load(open("settings.yml", "r"))
    ij_dir = settings.get("imagej_installation", None)

    _ij = imagej.init(ij_dir_or_version_or_endpoint=ij_dir, mode=get_mode())
    log_debug(f"Initialized at version {_ij.getVersion()}")

    # Final configuration
    _disable_jvm_shutdown_on_gui_quit(_ij)

    # Return the ImageJ gateway
    return _ij


def _disable_jvm_shutdown_on_gui_quit(ij_instance):
    # We can't quit the gui running headlessly!
    if running_headless():
        return
    # Prevent quitting from the ImageJ Legacy GUI
    if ij_instance.legacy and ij_instance.legacy.isActive():
        ij_instance.IJ.getInstance().exitWhenQuitting(False)
    # Prevent quitting from the ImageJ2 GUI
    else:
        raise NotImplementedError("Cannot yet block quitting of ImageJ2")


# There is a good debate to be had whether to multithread or multiprocess.
# From what I (Gabe) have read, it seems that threading is preferrable for
# network / IO bottlenecking, while multiprocessing is preferrable for CPU
# bottlenecking.
# While multiprocessing might theoretically be a better choice for JVM startup,
# there are two reasons we instead choose multithreading:
# 1) Multiprocessing is not supported without additional libraries on MacOS.
# See https://docs.python.org/3/library/multiprocessing.html#introduction
# 2) JPype items cannot (currently) be passed between processes due to an
# issue with pickling. See
# https://github.com/imagej/napari-imagej/issues/27#issuecomment-1130102033
threadpool: ThreadPool = ThreadPool(processes=1)
ij_instance: AsyncResult = threadpool.apply_async(func=imagej_init)


def ensure_jvm_started() -> None:
    ij_instance.wait()


def ij():
    """
    Returns the ImageJ instance.
    If it isn't ready yet, blocks until it is ready.
    """
    return ij_instance.get()


def logger():
    return _logger


class JavaClasses(object):
    def blocking_import(func: Callable[[], str]) -> Callable[[], JClass]:
        """
        A decorator used to lazily evaluate a java import.
        func is a function of a Python class that takes no arguments and
        returns a string identifying a Java class by name.

        Using that function, this decorator creates a property
        that when called:
        * Blocks until the ImageJ gateway has been created
        * Imports the class identified by the function
        """

        @property
        def inner(self):
            ensure_jvm_started()
            return jimport(func(self))

        return inner

    # Java Primitives

    @blocking_import
    def Boolean(self):
        return "java.lang.Boolean"

    @blocking_import
    def Byte(self):
        return "java.lang.Byte"

    @blocking_import
    def Character(self):
        return "java.lang.Character"

    @blocking_import
    def Double(self):
        return "java.lang.Double"

    @blocking_import
    def Float(self):
        return "java.lang.Float"

    @blocking_import
    def Integer(self):
        return "java.lang.Integer"

    @blocking_import
    def Long(self):
        return "java.lang.Long"

    @blocking_import
    def Short(self):
        return "java.lang.Short"

    @blocking_import
    def String(self):
        return "java.lang.String"

    # Java Array Primitives

    @blocking_import
    def Boolean_Arr(self):
        return "[Z"

    @blocking_import
    def Byte_Arr(self):
        return "[B"

    @blocking_import
    def Character_Arr(self):
        return "[C"

    @blocking_import
    def Double_Arr(self):
        return "[D"

    @blocking_import
    def Float_Arr(self):
        return "[F"

    @blocking_import
    def Integer_Arr(self):
        return "[I"

    @blocking_import
    def Long_Arr(self):
        return "[J"

    @blocking_import
    def Short_Arr(self):
        return "[S"

    # Vanilla Java Classes

    @blocking_import
    def ArrayList(self):
        return "java.util.ArrayList"

    @blocking_import
    def BigInteger(self):
        return "java.math.BigInteger"

    @blocking_import
    def Date(self):
        return "java.util.Date"

    @blocking_import
    def Enum(self):
        return "java.lang.Enum"

    @blocking_import
    def File(self):
        return "java.io.File"

    @blocking_import
    def Path(self):
        return "java.nio.file.Path"

    # SciJava Types

    @blocking_import
    def DisplayPostprocessor(self):
        return "org.scijava.module.process.PostprocessorPlugin"

    @blocking_import
    def InputHarvester(self):
        return "org.scijava.widget.InputHarvester"

    @blocking_import
    def Module(self):
        return "org.scijava.module.Module"

    @blocking_import
    def ModuleInfo(self):
        return "org.scijava.module.ModuleInfo"

    @blocking_import
    def ModuleItem(self):
        return "org.scijava.module.ModuleItem"

    @blocking_import
    def ModuleSearcher(self):
        return "org.scijava.search.module.ModuleSearcher"

    @blocking_import
    def PostprocessorPlugin(self):
        return "org.scijava.module.process.PostprocessorPlugin"

    @blocking_import
    def PreprocessorPlugin(self):
        return "org.scijava.module.process.PreprocessorPlugin"

    @blocking_import
    def Searcher(self):
        return "org.scijava.search.Searcher"

    @blocking_import
    def SearchEvent(self):
        return "org.scijava.search.SearchEvent"

    @blocking_import
    def SearchListener(self):
        return "org.scijava.search.SearchListener"

    @blocking_import
    def SearchResult(self):
        return "org.scijava.search.SearchResult"

    @blocking_import
    def Table(self):
        return "org.scijava.table.Table"

    @blocking_import
    def Types(self):
        return "org.scijava.util.Types"

    # ImgLib2 Types

    @blocking_import
    def BooleanType(self):
        return "net.imglib2.type.BooleanType"

    @blocking_import
    def ColorTable(self):
        return "net.imglib2.display.ColorTable"

    @blocking_import
    def ComplexType(self):
        return "net.imglib2.type.numeric.ComplexType"

    @blocking_import
    def IntegerType(self):
        return "net.imglib2.type.numeric.IntegerType"

    @blocking_import
    def IterableInterval(self):
        return "net.imglib2.IterableInterval"

    @blocking_import
    def OutOfBoundsFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsFactory"

    @blocking_import
    def OutOfBoundsBorderFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsBorderFactory"

    @blocking_import
    def OutOfBoundsMirrorExpWindowingFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsMirrorExpWindowingFactory"

    @blocking_import
    def OutOfBoundsMirrorFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsMirrorFactory"

    @blocking_import
    def OutOfBoundsPeriodicFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsPeriodicFactory"

    @blocking_import
    def OutOfBoundsRandomValueFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsRandomValueFactory"

    @blocking_import
    def RandomAccessible(self):
        return "net.imglib2.RandomAccessible"

    @blocking_import
    def RandomAccessibleInterval(self):
        return "net.imglib2.RandomAccessibleInterval"

    @blocking_import
    def RealPoint(self):
        return "net.imglib2.RealPoint"

    @blocking_import
    def RealType(self):
        return "net.imglib2.type.numeric.RealType"

    # ImgLib2-algorithm Types

    @blocking_import
    def StructuringElement(self):
        return "net.imglib2.algorithm.labeling.ConnectedComponents.StructuringElement"

    # ImgLib2-roi Types

    @blocking_import
    def Box(self):
        return "net.imglib2.roi.geom.real.Box"

    @blocking_import
    def ClosedWritableBox(self):
        return "net.imglib2.roi.geom.real.ClosedWritableBox"

    @blocking_import
    def ClosedWritableEllipsoid(self):
        return "net.imglib2.roi.geom.real.ClosedWritableEllipsoid"

    @blocking_import
    def ClosedWritablePolygon2D(self):
        return "net.imglib2.roi.geom.real.ClosedWritablePolygon2D"

    @blocking_import
    def DefaultWritableLine(self):
        return "net.imglib2.roi.geom.real.DefaultWritableLine"

    @blocking_import
    def DefaultWritablePolyline(self):
        return "net.imglib2.roi.geom.real.DefaultWritablePolyline"

    @blocking_import
    def DefaultWritableRealPointCollection(self):
        return "net.imglib2.roi.geom.real.DefaultWritableRealPointCollection"

    @blocking_import
    def ImgLabeling(self):
        return "net.imglib2.roi.labeling.ImgLabeling"

    @blocking_import
    def Line(self):
        return "net.imglib2.roi.geom.real.Line"

    @blocking_import
    def PointMask(self):
        return "net.imglib2.roi.geom.real.PointMask"

    @blocking_import
    def Polygon2D(self):
        return "net.imglib2.roi.geom.real.Polygon2D"

    @blocking_import
    def Polyline(self):
        return "net.imglib2.roi.geom.real.Polyline"

    @blocking_import
    def RealPointCollection(self):
        return "net.imglib2.roi.geom.real.RealPointCollection"

    @blocking_import
    def SuperEllipsoid(self):
        return "net.imglib2.roi.geom.real.SuperEllipsoid"

    # ImageJ2 Types

    @blocking_import
    def DefaultROITree(self):
        return "net.imagej.roi.DefaultROITree"

    @blocking_import
    def Mesh(self):
        return "net.imagej.mesh.Mesh"

    @blocking_import
    def NaiveDoubleMesh(self):
        return "net.imagej.mesh.naive.NaiveDoubleMesh"

    @blocking_import
    def ROITree(self):
        return "net.imagej.roi.ROITree"

    # ImageJ-Ops Types

    @blocking_import
    def Initializable(self):
        return "net.imagej.ops.Initializable"

    @blocking_import
    def OpInfo(self):
        return "net.imagej.ops.OpInfo"

    @blocking_import
    def OpSearcher(self):
        return "net.imagej.ops.search.OpSearcher"

    # Scifio-Labeling Types

    @blocking_import
    def LabelingIOService(self):
        return "io.scif.labeling.LabelingIOService"


jc = JavaClasses()
