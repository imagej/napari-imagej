"""
A module encapsulating access to Java functionality.

Notable functions included in the module:
    * init_ij()
        - used to create the ImageJ instance.

Notable fields included in the module:
    * jc
        - object whose fields are lazily-loaded Java Class instances.
"""

from typing import Any, Dict, List

import imagej
from scyjava import JavaClasses, config, get_version, is_version_at_least, jimport

from napari_imagej import settings
from napari_imagej.utilities.logging import log_debug

# -- Constants -- #

minimum_versions = {
    "io.scif:scifio": "0.45.0",
    "net.imagej:imagej-common": "2.0.2",
    "net.imagej:imagej-legacy": "1.1.0",
    "net.imagej:imagej-ops": "0.49.0",
    "net.imglib2:imglib2-unsafe": "1.0.0",
    "net.imglib2:imglib2-imglyb": "1.1.0",
    "org.scijava:scijava-common": "2.95.0",
    "org.scijava:scijava-search": "2.0.2",
    "sc.fiji:TrackMate": "7.11.0",
}

# Each component listed here should be paired with a comment describing WHY it is here
recommended_versions = {
    # Versions above are easier for inclusion of scifio-labeling
    # https://github.com/imagej/pyimagej/issues/280
    "net.imagej:imagej": "2.10.0",
    # Enable visualizing Datasets with DefaultROITrees
    # https://github.com/imagej/imagej-legacy/pull/300
    "net.imagej:imagej-legacy": "1.2.1",
    # Enables threshold Ops to return Images of BooleanTypes
    # https://github.com/imagej/imagej-ops/pull/651
    "net.imagej:imagej-ops": "2.0.1",
    # Prevents non-empty SciJava Search Results for empty searches
    # https://github.com/scijava/scijava-search/pull/30
    "org.scijava:scijava-search": "2.0.4",
    # Versions above are easier for inclusion of scifio-labeling
    # https://github.com/imagej/pyimagej/issues/280
    "sc.fiji:fiji": "2.10.0",
}


# -- Public functions -- #


def init_ij() -> "jc.ImageJ":
    """
    Create an ImageJ2 gateway.
    """
    log_debug("Initializing ImageJ2")

    # -- CONFIGURATION -- #

    from napari_imagej.types.converters import install_converters

    install_converters()
    log_debug("Completed JVM Configuration")

    # -- INITIALIZATION -- #

    # Launch ImageJ
    ij = (
        imagej.gateway
        if hasattr(imagej, "gateway") and imagej.gateway
        else imagej.init(**_configure_imagej())
    )

    # Log initialization
    log_debug(f"Initialized at version {ij.getVersion()}")

    return ij


def validate_imagej(ij: "jc.ImageJ") -> List[str]:
    """
    Ensures ij is suitable for use within napari-imagej.
    Critical errors result in an exception being thrown by this function.
    Noncritical errors (warnings) are described in the returned list of strings.
    """
    warnings = []

    # If we want to require a minimum version for a java component, we need to
    # be able to find our current version. We do that by querying a Java class
    # within that component.
    ImageJ = jimport("net.imagej.Main")
    RGRAI = jimport("net.imglib2.python.ReferenceGuardingRandomAccessibleInterval")
    SCIFIO = jimport("io.scif.SCIFIO")
    UnsafeImg = jimport("net.imglib2.img.unsafe.UnsafeImg")
    component_requirements = {
        "io.scif:scifio": SCIFIO,
        "net.imagej:imagej": ImageJ,
        "net.imagej:imagej-common": jc.Dataset,
        "net.imagej:imagej-ops": jc.OpInfo,
        "net.imglib2:imglib2-unsafe": UnsafeImg,
        "net.imglib2:imglib2-imglyb": RGRAI,
        "org.scijava:scijava-common": jc.Module,
        "org.scijava:scijava-search": jc.Searcher,
    }
    component_requirements.update(_optional_requirements(ij))
    # Find version that violate the minimum
    violations = []
    for component, cls in component_requirements.items():
        if component not in minimum_versions:
            continue
        min_version = minimum_versions[component]
        component_version = get_version(cls)
        if not is_version_at_least(component_version, min_version):
            violations.append(
                f"{component} : {min_version} (Installed: {component_version})"
            )

    # If version requirements are violated, throw an error
    if violations:
        failure_str = "napari-imagej requires the following component versions:"
        violations.insert(0, failure_str)
        failure_str = "\n\t".join(violations)
        failure_str += (
            "\n\nPlease ensure your ImageJ2 endpoint is correct within the settings"
        )
        raise RuntimeError(failure_str)

    # If verison recommendations are violated, return a warning
    violations = []
    for component, cls in component_requirements.items():
        if component not in recommended_versions:
            continue
        recommended_version = recommended_versions[component]
        component_version = get_version(cls)
        if not is_version_at_least(component_version, recommended_version):
            violations.append(
                f"{component} : {recommended_version} (Installed: {component_version})"
            )

    # If there are older versions, warn the user
    if violations:
        __version__ = get_version("napari-imagej")
        failure_str = (
            f"napari-imagej v{__version__} recommends using "
            "the following component versions:"
        )
        violations.insert(0, failure_str)
        warnings.append("\n\t".join(violations))

    return warnings


# -- Private functions -- #


def _configure_imagej() -> Dict[str, Any]:
    """
    Configure scyjava and pyimagej.
    This function returns the settings that must be passed in the
    actual initialization call.

    :return: kwargs that should be passed to imagej.init()
    """
    # ScyJava configuration
    config.add_option(f"-Dimagej2.dir={settings.basedir()}")

    # Append napari-imagej-specific cli arguments
    cli_args = settings.jvm_command_line_arguments
    if cli_args:
        config.add_option(cli_args)

    # PyImageJ configuration
    init_settings = {
        "ij_dir_or_version_or_endpoint": settings.endpoint(),
        "mode": settings.jvm_mode(),
        "add_legacy": settings.include_imagej_legacy,
    }
    return init_settings


def _optional_requirements(ij: "jc.ImageJ"):
    optionals = {}
    # Add additional minimum versions for legacy components
    if ij.legacy and ij.legacy.isActive():
        optionals["net.imagej:imagej-legacy"] = ij.legacy.getClass()
    # Add additional minimum versions for fiji components
    optional_classes = {
        "sc.fiji:TrackMate": "fiji.plugin.trackmate.TrackMate",
        "sc.fiji:Fiji": "fiji.Main",
    }
    for artifact, cls in optional_classes.items():
        try:
            optionals[artifact] = jimport(cls)
        except Exception:
            pass

    return optionals


class NijJavaClasses(JavaClasses):
    # Java Primitives

    @JavaClasses.java_import
    def Boolean(self):
        return "java.lang.Boolean"

    @JavaClasses.java_import
    def Byte(self):
        return "java.lang.Byte"

    @JavaClasses.java_import
    def Class(self):
        return "java.lang.Class"

    @JavaClasses.java_import
    def Character(self):
        return "java.lang.Character"

    @JavaClasses.java_import
    def Double(self):
        return "java.lang.Double"

    @JavaClasses.java_import
    def Float(self):
        return "java.lang.Float"

    @JavaClasses.java_import
    def Integer(self):
        return "java.lang.Integer"

    @JavaClasses.java_import
    def Long(self):
        return "java.lang.Long"

    @JavaClasses.java_import
    def Number(self):
        return "java.lang.Number"

    @JavaClasses.java_import
    def Short(self):
        return "java.lang.Short"

    @JavaClasses.java_import
    def String(self):
        return "java.lang.String"

    # Java Array Primitives

    @JavaClasses.java_import
    def Boolean_Arr(self):
        return "[Z"

    @JavaClasses.java_import
    def Byte_Arr(self):
        return "[B"

    @JavaClasses.java_import
    def Character_Arr(self):
        return "[C"

    @JavaClasses.java_import
    def Double_Arr(self):
        return "[D"

    @JavaClasses.java_import
    def Float_Arr(self):
        return "[F"

    @JavaClasses.java_import
    def Integer_Arr(self):
        return "[I"

    @JavaClasses.java_import
    def Long_Arr(self):
        return "[J"

    @JavaClasses.java_import
    def Short_Arr(self):
        return "[S"

    # Vanilla Java Classes

    @JavaClasses.java_import
    def ArrayList(self):
        return "java.util.ArrayList"

    @JavaClasses.java_import
    def BigDecimal(self):
        return "java.math.BigDecimal"

    @JavaClasses.java_import
    def BigInteger(self):
        return "java.math.BigInteger"

    @JavaClasses.java_import
    def ByteArrayOutputStream(self):
        return "java.io.ByteArrayOutputStream"

    @JavaClasses.java_import
    def Date(self):
        return "java.util.Date"

    @JavaClasses.java_import
    def Enum(self):
        return "java.lang.Enum"

    @JavaClasses.java_import
    def File(self):
        return "java.io.File"

    @JavaClasses.java_import
    def HashMap(self):
        return "java.util.HashMap"

    @JavaClasses.java_import
    def Path(self):
        return "java.nio.file.Path"

    @JavaClasses.java_import
    def Window(self):
        return "java.awt.Window"

    @JavaClasses.java_import
    def ScriptException(self):
        return "javax.script.ScriptException"

    # SciJava Types

    @JavaClasses.java_import
    def DisplayPostprocessor(self):
        return "org.scijava.display.DisplayPostprocessor"

    @JavaClasses.java_import
    def FileWidget(self):
        return "org.scijava.widget.FileWidget"

    @JavaClasses.java_import
    def InputHarvester(self):
        return "org.scijava.widget.InputHarvester"

    @JavaClasses.java_import
    def Module(self):
        return "org.scijava.module.Module"

    @JavaClasses.java_import
    def ModuleEvent(self):
        return "org.scijava.module.event.ModuleEvent"

    @JavaClasses.java_import
    def ModuleCanceledEvent(self):
        return "org.scijava.module.event.ModuleCanceledEvent"

    @JavaClasses.java_import
    def ModuleErroredEvent(self):
        return "org.scijava.module.event.ModuleErroredEvent"

    @JavaClasses.java_import
    def ModuleExecutedEvent(self):
        return "org.scijava.module.event.ModuleExecutedEvent"

    @JavaClasses.java_import
    def ModuleExecutingEvent(self):
        return "org.scijava.module.event.ModuleExecutingEvent"

    @JavaClasses.java_import
    def ModuleFinishedEvent(self):
        return "org.scijava.module.event.ModuleFinishedEvent"

    @JavaClasses.java_import
    def ModuleInfo(self):
        return "org.scijava.module.ModuleInfo"

    @JavaClasses.java_import
    def ModuleItem(self):
        return "org.scijava.module.ModuleItem"

    @JavaClasses.java_import
    def ModuleStartedEvent(self):
        return "org.scijava.module.event.ModuleStartedEvent"

    @JavaClasses.java_import
    def PostprocessorPlugin(self):
        return "org.scijava.module.process.PostprocessorPlugin"

    @JavaClasses.java_import
    def PreprocessorPlugin(self):
        return "org.scijava.module.process.PreprocessorPlugin"

    @JavaClasses.java_import
    def ResultsPostprocessor(self):
        return "org.scijava.table.process.ResultsPostprocessor"

    @JavaClasses.java_import
    def SciJavaEvent(self):
        return "org.scijava.event.SciJavaEvent"

    @JavaClasses.java_import
    def ScriptREPL(self):
        return "org.scijava.script.ScriptREPL"

    @JavaClasses.java_import
    def ScriptService(self):
        return "org.scijava.script.ScriptService"

    @JavaClasses.java_import
    def Searcher(self):
        return "org.scijava.search.Searcher"

    @JavaClasses.java_import
    def SearchEvent(self):
        return "org.scijava.search.SearchEvent"

    @JavaClasses.java_import
    def SearchListener(self):
        return "org.scijava.search.SearchListener"

    @JavaClasses.java_import
    def SearchResult(self):
        return "org.scijava.search.SearchResult"

    @JavaClasses.java_import
    def Table(self):
        return "org.scijava.table.Table"

    @JavaClasses.java_import
    def Types(self):
        return "org.scijava.util.Types"

    @JavaClasses.java_import
    def UIComponent(self):
        return "org.scijava.widget.UIComponent"

    @JavaClasses.java_import
    def UIShownEvent(self):
        return "org.scijava.ui.event.UIShownEvent"

    @JavaClasses.java_import
    def UserInterface(self):
        return "org.scijava.ui.UserInterface"

    # ImageJ Legacy Types

    @JavaClasses.java_import
    def LegacyCommandInfo(self):
        return "net.imagej.legacy.command.LegacyCommandInfo"

    # ImgLib2 Types

    @JavaClasses.java_import
    def BitType(self):
        return "net.imglib2.type.logic.BitType"

    @JavaClasses.java_import
    def BooleanType(self):
        return "net.imglib2.type.BooleanType"

    @JavaClasses.java_import
    def ColorTable(self):
        return "net.imglib2.display.ColorTable"

    @JavaClasses.java_import
    def ColorTable8(self):
        return "net.imglib2.display.ColorTable8"

    @JavaClasses.java_import
    def ColorTables(self):
        return "net.imagej.display.ColorTables"

    @JavaClasses.java_import
    def ComplexType(self):
        return "net.imglib2.type.numeric.ComplexType"

    @JavaClasses.java_import
    def DoubleType(self):
        return "net.imglib2.type.numeric.real.DoubleType"

    @JavaClasses.java_import
    def Img(self):
        return "net.imglib2.img.Img"

    @JavaClasses.java_import
    def IntegerType(self):
        return "net.imglib2.type.numeric.IntegerType"

    @JavaClasses.java_import
    def IterableInterval(self):
        return "net.imglib2.IterableInterval"

    @JavaClasses.java_import
    def LongType(self):
        return "net.imglib2.type.numeric.integer.LongType"

    @JavaClasses.java_import
    def NumericType(self):
        return "net.imglib2.type.numeric.NumericType"

    @JavaClasses.java_import
    def OutOfBoundsFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsFactory"

    @JavaClasses.java_import
    def OutOfBoundsBorderFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsBorderFactory"

    @JavaClasses.java_import
    def OutOfBoundsMirrorExpWindowingFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsMirrorExpWindowingFactory"

    @JavaClasses.java_import
    def OutOfBoundsMirrorFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsMirrorFactory"

    @JavaClasses.java_import
    def OutOfBoundsPeriodicFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsPeriodicFactory"

    @JavaClasses.java_import
    def OutOfBoundsRandomValueFactory(self):
        return "net.imglib2.outofbounds.OutOfBoundsRandomValueFactory"

    @JavaClasses.java_import
    def RandomAccessible(self):
        return "net.imglib2.RandomAccessible"

    @JavaClasses.java_import
    def RandomAccessibleInterval(self):
        return "net.imglib2.RandomAccessibleInterval"

    @JavaClasses.java_import
    def RealPoint(self):
        return "net.imglib2.RealPoint"

    @JavaClasses.java_import
    def RealType(self):
        return "net.imglib2.type.numeric.RealType"

    # ImgLib2-algorithm Types

    @JavaClasses.java_import
    def CenteredRectangleShape(self):
        return "net.imglib2.algorithm.neighborhood.CenteredRectangleShape"

    @JavaClasses.java_import
    def DiamondShape(self):
        return "net.imglib2.algorithm.neighborhood.DiamondShape"

    @JavaClasses.java_import
    def DiamondTipsShape(self):
        return "net.imglib2.algorithm.neighborhood.DiamondTipsShape"

    @JavaClasses.java_import
    def HorizontalLineShape(self):
        return "net.imglib2.algorithm.neighborhood.HorizontalLineShape"

    @JavaClasses.java_import
    def HyperSphereShape(self):
        return "net.imglib2.algorithm.neighborhood.HyperSphereShape"

    @JavaClasses.java_import
    def PairOfPointsShape(self):
        return "net.imglib2.algorithm.neighborhood.PairOfPointsShape"

    @JavaClasses.java_import
    def PeriodicLineShape(self):
        return "net.imglib2.algorithm.neighborhood.PeriodicLineShape"

    @JavaClasses.java_import
    def RectangleShape(self):
        return "net.imglib2.algorithm.neighborhood.RectangleShape"

    @JavaClasses.java_import
    def Shape(self):
        return "net.imglib2.algorithm.neighborhood.Shape"

    # ImgLib2-roi Types

    @JavaClasses.java_import
    def Box(self):
        return "net.imglib2.roi.geom.real.Box"

    @JavaClasses.java_import
    def ClosedWritableBox(self):
        return "net.imglib2.roi.geom.real.ClosedWritableBox"

    @JavaClasses.java_import
    def ClosedWritableEllipsoid(self):
        return "net.imglib2.roi.geom.real.ClosedWritableEllipsoid"

    @JavaClasses.java_import
    def ClosedWritablePolygon2D(self):
        return "net.imglib2.roi.geom.real.ClosedWritablePolygon2D"

    @JavaClasses.java_import
    def DefaultWritableLine(self):
        return "net.imglib2.roi.geom.real.DefaultWritableLine"

    @JavaClasses.java_import
    def DefaultWritablePolyline(self):
        return "net.imglib2.roi.geom.real.DefaultWritablePolyline"

    @JavaClasses.java_import
    def DefaultWritableRealPointCollection(self):
        return "net.imglib2.roi.geom.real.DefaultWritableRealPointCollection"

    @JavaClasses.java_import
    def ImgLabeling(self):
        return "net.imglib2.roi.labeling.ImgLabeling"

    @JavaClasses.java_import
    def Line(self):
        return "net.imglib2.roi.geom.real.Line"

    @JavaClasses.java_import
    def PointMask(self):
        return "net.imglib2.roi.geom.real.PointMask"

    @JavaClasses.java_import
    def Polygon2D(self):
        return "net.imglib2.roi.geom.real.Polygon2D"

    @JavaClasses.java_import
    def Polyline(self):
        return "net.imglib2.roi.geom.real.Polyline"

    @JavaClasses.java_import
    def RealPointCollection(self):
        return "net.imglib2.roi.geom.real.RealPointCollection"

    @JavaClasses.java_import
    def SuperEllipsoid(self):
        return "net.imglib2.roi.geom.real.SuperEllipsoid"

    # ImageJ2 Types

    @JavaClasses.java_import
    def Axes(self):
        return "net.imagej.axis.Axes"

    @JavaClasses.java_import
    def Dataset(self):
        return "net.imagej.Dataset"

    @JavaClasses.java_import
    def DatasetView(self):
        return "net.imagej.display.DatasetView"

    @JavaClasses.java_import
    def DefaultLinearAxis(self):
        return "net.imagej.axis.DefaultLinearAxis"

    @JavaClasses.java_import
    def DefaultROITree(self):
        return "net.imagej.roi.DefaultROITree"

    @JavaClasses.java_import
    def EnumeratedAxis(self):
        return "net.imagej.axis.EnumeratedAxis"

    @JavaClasses.java_import
    def ImageDisplay(self):
        return "net.imagej.display.ImageDisplay"

    @JavaClasses.java_import
    def ImageJ(self):
        return "net.imagej.ImageJ"

    @JavaClasses.java_import
    def ImgPlus(self):
        return "net.imagej.ImgPlus"

    @JavaClasses.java_import
    def Mesh(self):
        return "net.imagej.mesh.Mesh"

    @JavaClasses.java_import
    def NaiveDoubleMesh(self):
        return "net.imagej.mesh.naive.NaiveDoubleMesh"

    @JavaClasses.java_import
    def ROITree(self):
        return "net.imagej.roi.ROITree"

    # ImageJ Types

    @JavaClasses.java_import
    def ImagePlus(self):
        return "ij.ImagePlus"

    @JavaClasses.java_import
    def Roi(self):
        return "ij.gui.Roi"

    # ImageJ-Legacy Types

    @JavaClasses.java_import
    def IJRoiWrapper(self):
        return "net.imagej.legacy.convert.roi.IJRoiWrapper"

    # ImageJ-Ops Types

    @JavaClasses.java_import
    def Initializable(self):
        return "net.imagej.ops.Initializable"

    @JavaClasses.java_import
    def OpInfo(self):
        return "net.imagej.ops.OpInfo"

    @JavaClasses.java_import
    def OpSearcher(self):
        return "net.imagej.ops.search.OpSearcher"

    # Scifio-Labeling Types

    @JavaClasses.java_import
    def LabelingIOService(self):
        return "io.scif.labeling.LabelingIOService"


jc = NijJavaClasses()
