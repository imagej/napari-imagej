import os
from jpype import JClass
import logging
import imagej
from scyjava import config, jimport
from multiprocessing.pool import AsyncResult, ThreadPool

# -- LOGGER CONFIG -- #

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)  # TEMP

# -- PUBLIC API -- #
def imagej_init():
    # Initialize ImageJ
    _logger.debug("Initializing ImageJ2")

    # -- IMAGEJ CONFIG -- #

    # TEMP: Avoid issues caused by https://github.com/imagej/pyimagej/issues/160
    config.add_repositories(
        {"scijava.public": "https://maven.scijava.org/content/groups/public"}
    )
    config.add_option(f"-Dimagej.dir={os.getcwd()}")  # TEMP
    config.endpoints.append("io.scif:scifio:0.43.1")

    _logger.debug("Completed JVM Configuration")
    # TODO: change 'headless=True' -> 'mode=imagej.Mode.HEADLESS'
    # This change is waiting on a new pyimagej release
    # TODO: remove 'add_legacy=False' -> struggles with LegacyService
    # This change is waiting on a new pyimagej release
    _ij = imagej.init(headless=True)

    _logger.debug(f"Initialized at version {_ij.getVersion()}")
    return _ij

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
ij_instance: AsyncResult = threadpool.apply_async(func = imagej_init)

def ensure_jvm_started()->None:
    ij_instance.wait()


def ij():
    """
    Returns the ImageJ instance.
    If it isn't ready yet, blocks until it is ready.
    """
    return ij_instance.get()


def logger():
    return _logger


def java_import(class_name: str) -> JClass:
    """
    Imports class_name, while ensuring
    the parallel initialization of ImageJ has completed.
    """
    ij_instance.wait()
    return jimport(class_name)
