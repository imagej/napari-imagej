"""
A module whose submodules contain additional scyjava Converters
that are useful within napari-imagej

All submodules within this module are DYNAMICALLY IMPORTED; this allows
automatic discovery of all Converters.

Notable functions included in the module:
    * install_converters()
        - used to add the napari-imagej Converters to scyjava's conversion framework.
"""

import pkgutil
from importlib.util import module_from_spec
from typing import Any, Callable, List

from scyjava import (
    Converter,
    Priority,
    add_java_converter,
    add_py_converter,
    when_jvm_starts,
)

# PHASE 1 - DEFINE THE CONVERTER DECORATORS

JAVA_TO_PY_CONVERTERS: List = []
PY_TO_JAVA_CONVERTERS: List = []


def java_to_py_converter(
    predicate: Callable[[Any], bool], priority: int = Priority.NORMAL
):
    """
    A decorator used to register a given function as a scyjava Converter.
    Decorated functions will be used to convert JAVA objects into PYTHON objects.
    :param predicate: defines situations in which the Converter should be used.
    :param priority: the scyjava Priority of this Converter, used to break ties.
    :return: the function
    """

    def inner(func: Callable):
        JAVA_TO_PY_CONVERTERS.append(
            Converter(predicate=predicate, converter=func, priority=priority)
        )
        return func

    return inner


def py_to_java_converter(
    predicate: Callable[[Any], bool], priority: int = Priority.NORMAL
):
    """
    A decorator used to register a given function as a scyjava Converter.
    Decorated functions will be used to convert PYTHON objects into JAVA objects.
    :param predicate: defines situations in which the Converter should be used.
    :param priority: the scyjava Priority of this Converter, used to break ties.
    :return: the function
    """

    def inner(func: Callable):
        PY_TO_JAVA_CONVERTERS.append(
            Converter(predicate=predicate, converter=func, priority=priority)
        )
        return func

    return inner


# PHASE 2 - DISCOVER ALL CONVERTERS


# Dynamically import all submodules
# By importing these submodules, top-level functions will be decorated,
# Installing them into the scyjava conversion system.
__all__ = []
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    __all__.append(module_name)
    # Find the module specification
    _spec = loader.find_spec(module_name)
    # Get the module
    _module = module_from_spec(_spec)
    # Execute the module
    _spec.loader.exec_module(_module)
    # Store the module for later
    globals()[module_name] = _module


# PHASE 3 - INSTALL ALL CONVERTERS


def install_converters():
    """Installs napari-imagej specific converters"""

    def _install_converters():
        for converter in JAVA_TO_PY_CONVERTERS:
            add_py_converter(converter)
        for converter in PY_TO_JAVA_CONVERTERS:
            add_java_converter(converter)

    when_jvm_starts(_install_converters)
