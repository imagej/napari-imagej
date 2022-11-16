"""
A module encapsulating access to Java functionality.

Notable functions included in the module:
    * init_ij()
        - used to create the ImageJ instance.
    * init_ij_async()
        - used to asynchronously create the ImageJ instance.
    * ij()
        - used to access the ImageJ instance. Calls init_ij() if necessary.

Notable fields included in the module:
    * jc
        - object whose fields are lazily-loaded Java Class instances.
"""
from threading import Lock
from typing import Callable, List, Tuple

import imagej
from jpype import JClass
from qtpy.QtCore import QObject, QThread, Signal
from scyjava import config, get_version, is_version_at_least, jimport, jvm_started

from napari_imagej import settings
from napari_imagej.utilities.logging import log_debug

# -- ImageJ API -- #


def init_ij() -> None:
    """
    Starts creating our ImageJ instance, and waits until it is ready.
    """
    init_ij_async()
    initializer.wait()


def init_ij_async():
    """
    Starts creating our ImageJ instance.
    """
    initializer.start()


def ij():
    """
    Returns the ImageJ instance.
    If it isn't ready yet, blocks until it is ready.
    """
    init_ij()
    return initializer.ij


class ImageJInitializer(QThread):
    """
    A QThread responsible for initializing ImageJ
    """

    # Tools used to ensure this QThread only initializes ImageJ once.
    started: bool = False
    lock: Lock = Lock()
    # Used as a placeholder for the ImageJ instance
    ij = None

    def run(self):
        """
        Main QThread loop.

        Well, okay, it isn't really a loop.

        Responsible for ensuring that initialize is only called once.
        """
        # Double-checked lock
        if not self.started:
            with self.lock:
                if not self.started:
                    self.started = True
                    # Try to initialize ImageJ
                    try:
                        self.initialize()
                        # Report completion
                        java_signals._startup_complete.emit()
                    # We failed!
                    except Exception as exc:
                        # Report failure
                        java_signals._startup_error.emit(exc)

    def initialize(self):
        """
        Creates the ImageJ instance
        """
        # Initialize ImageJ
        log_debug("Initializing ImageJ2")

        # -- IMAGEJ CONFIG -- #

        # ScyJava configuration
        # TEMP: Avoid issues caused by
        # https://github.com/imagej/pyimagej/issues/160
        config.add_repositories(
            {"scijava.public": "https://maven.scijava.org/content/groups/public"}
        )
        config.add_option(f"-Dimagej2.dir={settings['imagej_base_directory'].get(str)}")

        # PyImageJ configuration
        ij_settings = {}
        ij_settings["ij_dir_or_version_or_endpoint"] = settings[
            "imagej_directory_or_endpoint"
        ].get(str)
        if hasattr(imagej, "gateway") and imagej.gateway:
            ij_settings["mode"] = (
                "headless" if imagej.gateway.ui().isHeadless() else "gui"
            )
            ij_settings["add_legacy"] = (
                imagej.gateway.legacy and imagej.gateway.legacy.isActive()
            )
        else:
            ij_settings["mode"] = settings["jvm_mode"].get(str)
            ij_settings["add_legacy"] = settings["include_imagej_legacy"].get(bool)

        # napari-imagej configuration
        from napari_imagej.types.converters import install_converters

        install_converters()

        log_debug("Completed JVM Configuration")

        # Launch PyImageJ
        self.ij = (
            imagej.gateway
            if hasattr(imagej, "gateway") and imagej.gateway
            else imagej.init(**ij_settings)
        )
        # Validate PyImageJ
        self._validate_imagej()
        # Log initialization
        log_debug(f"Initialized at version {self.ij.getVersion()}")

    def _validate_imagej(self):
        """
        Helper function to ensure minimum requirements on java component versions
        """
        # If we want to require a minimum version for a java component, we need to
        # be able to find our current version. We do that by querying a Java class
        # within that component. Thus for each component-version pair, we also need
        # a class to query
        component_requirements: List[Tuple[JClass, str, str]] = [
            (jc.Dataset, "net.imagej:imagej-common", "0.35.0"),
            (jc.Module, "org.scijava:scijava-common", "2.89.0"),
            (jc.OpInfo, "net.imagej:imagej-ops", "0.48.0"),
        ]

        # Find version that violate the minimum
        violations = []
        for cls, component, min_version in component_requirements:
            # Get component's version
            component_version = get_version(cls)
            # Compare
            if not is_version_at_least(component_version, min_version):
                violations.append(
                    f"{component} : {min_version} (Installed: {component_version})"
                )

        # If there are version requirements, throw an error
        if len(violations):
            failure_str = "napari-imagej requires the following component versions:"
            violations.insert(0, failure_str)
            failure_str = "\n\t".join(violations)
            failure_str += (
                "\n\nPlease ensure your ImageJ2 endpoint is correct within the settings"
            )
            raise RuntimeError(failure_str)


class ImageJ_Callbacks(QObject):
    """
    An access point for registering ImageJ-related callbacks.
    """

    # Qt Signals - should not be called directly!
    _startup_error: Signal = Signal(Exception)
    _startup_complete: Signal = Signal()

    # -- CALLBACK-ACCEPTING FUNCTIONS -- #

    def when_ij_ready(self, func: Callable[[], None]):
        """
        Registers behavior (encapsulated as a function) that should be called
        when ImageJ is ready to be used.

        If ImageJ has not yet been initialized, the passed function is registered
        as a callback.

        If ImageJ is ready, the passed function is executed immediately.

        :param func: The behavior to execute
        """
        if not initializer.isFinished():
            self._startup_complete.connect(func)
        else:
            func()

    def when_initialization_fails(self, func: Callable[[Exception], None]):
        """
        Registers behavior (encapsulated as a function) that should be called
        when ImageJ fails to initialize.

        If ImageJ has not yet been initialized, the passed function is registered
        as a callback.

        If ImageJ setup has already failed, the passed function will not be called.

        :param func: The behavior to execute
        """
        self._startup_error.connect(func)


# -- SINGLETON INSTANCES -- #

initializer = ImageJInitializer()
java_signals = ImageJ_Callbacks()


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
            if not jvm_started():
                raise Exception()
            try:
                return jimport(func(self))
            except TypeError:
                return None

        return inner

    # Java Primitives

    @blocking_import
    def Boolean(self):
        return "java.lang.Boolean"

    @blocking_import
    def Byte(self):
        return "java.lang.Byte"

    @blocking_import
    def Class(self):
        return "java.lang.Class"

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

    @blocking_import
    def Window(self):
        return "java.awt.Window"

    # SciJava Types

    @blocking_import
    def DisplayPostprocessor(self):
        return "org.scijava.module.process.PostprocessorPlugin"

    @blocking_import
    def FileWidget(self):
        return "org.scijava.widget.FileWidget"

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

    @blocking_import
    def UIComponent(self):
        return "org.scijava.widget.UIComponent"

    @blocking_import
    def UserInterface(self):
        return "org.scijava.ui.UserInterface"

    # ImgLib2 Types

    @blocking_import
    def BitType(self):
        return "net.imglib2.type.logic.BitType"

    @blocking_import
    def BooleanType(self):
        return "net.imglib2.type.BooleanType"

    @blocking_import
    def ColorTable(self):
        return "net.imglib2.display.ColorTable"

    @blocking_import
    def ColorTable8(self):
        return "net.imglib2.display.ColorTable8"

    @blocking_import
    def ColorTables(self):
        return "net.imagej.display.ColorTables"

    @blocking_import
    def ComplexType(self):
        return "net.imglib2.type.numeric.ComplexType"

    @blocking_import
    def DoubleType(self):
        return "net.imglib2.type.numeric.real.DoubleType"

    @blocking_import
    def Img(self):
        return "net.imglib2.img.Img"

    @blocking_import
    def IntegerType(self):
        return "net.imglib2.type.numeric.IntegerType"

    @blocking_import
    def IterableInterval(self):
        return "net.imglib2.IterableInterval"

    @blocking_import
    def LongType(self):
        return "net.imglib2.type.numeric.integer.LongType"

    @blocking_import
    def NumericType(self):
        return "net.imglib2.type.numeric.NumericType"

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
    def CenteredRectangleShape(self):
        return "net.imglib2.algorithm.neighborhood.CenteredRectangleShape"

    @blocking_import
    def DiamondShape(self):
        return "net.imglib2.algorithm.neighborhood.DiamondShape"

    @blocking_import
    def DiamondTipsShape(self):
        return "net.imglib2.algorithm.neighborhood.DiamondTipsShape"

    @blocking_import
    def HorizontalLineShape(self):
        return "net.imglib2.algorithm.neighborhood.HorizontalLineShape"

    @blocking_import
    def HyperSphereShape(self):
        return "net.imglib2.algorithm.neighborhood.HyperSphereShape"

    @blocking_import
    def PairOfPointsShape(self):
        return "net.imglib2.algorithm.neighborhood.PairOfPointsShape"

    @blocking_import
    def PeriodicLineShape(self):
        return "net.imglib2.algorithm.neighborhood.PeriodicLineShape"

    @blocking_import
    def RectangleShape(self):
        return "net.imglib2.algorithm.neighborhood.RectangleShape"

    @blocking_import
    def Shape(self):
        return "net.imglib2.algorithm.neighborhood.Shape"

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
    def Dataset(self):
        return "net.imagej.Dataset"

    @blocking_import
    def DatasetView(self):
        return "net.imagej.display.DatasetView"

    @blocking_import
    def DefaultROITree(self):
        return "net.imagej.roi.DefaultROITree"

    @blocking_import
    def ImageDisplay(self):
        return "net.imagej.display.ImageDisplay"

    @blocking_import
    def ImgPlus(self):
        return "net.imagej.ImgPlus"

    @blocking_import
    def Mesh(self):
        return "net.imagej.mesh.Mesh"

    @blocking_import
    def NaiveDoubleMesh(self):
        return "net.imagej.mesh.naive.NaiveDoubleMesh"

    @blocking_import
    def ROITree(self):
        return "net.imagej.roi.ROITree"

    # ImageJ Types

    @blocking_import
    def ImagePlus(self):
        return "ij.ImagePlus"

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
