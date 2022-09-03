"""
scyjava Converters for converting PythonStandins into their java equivalents.
"""
from napari_imagej.java import jc
from napari_imagej.types.converters import py_to_java_converter
from napari_imagej.types.standins import OutOfBoundsFactory


@py_to_java_converter(predicate=lambda obj: isinstance(obj, OutOfBoundsFactory))
def _py_to_java_outOfBoundsFactory(obj: OutOfBoundsFactory) -> "jc.OutOfBoundsFactory":
    """
    Converts OutOfBoundsFactory standins into actual OutOfBoundsFactories
    :param obj: the OutOfBoundsFactory PythonStandin
    :return: the actual OutOfBoundsFactory
    """
    if obj == OutOfBoundsFactory.BORDER:
        return jc.OutOfBoundsBorderFactory()
    if obj == OutOfBoundsFactory.MIRROR_EXP_WINDOWING:
        return jc.OutOfBoundsMirrorExpWindowingFactory()
    if obj == OutOfBoundsFactory.MIRROR_SINGLE:
        return jc.OutOfBoundsMirrorFactory(jc.OutOfBoundsMirrorFactory.Boundary.SINGLE)
    if obj == OutOfBoundsFactory.MIRROR_DOUBLE:
        return jc.OutOfBoundsMirrorFactory(jc.OutOfBoundsMirrorFactory.Boundary.DOUBLE)
    if obj == OutOfBoundsFactory.PERIODIC:
        return jc.OutOfBoundsPeriodicFactory()
    raise ValueError(f"{obj} is not a StructuringElement!")
