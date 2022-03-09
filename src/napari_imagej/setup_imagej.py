import os
from jpype import JClass
import logging
import imagej
from scyjava import config, jimport
from threading import Thread, current_thread

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
    global _ij
    _ij = imagej.init(headless=True)
    print(_ij)

    _logger.debug(f"Initialized at version {_ij.getVersion()}")

# There is a good debate to be had whether to multithread or multiprocess.
# From what I (Gabe) have read, it seems that threading is preferrable for
# network / IO bottlenecking, while multiprocessing is preferrable for CPU
# bottlenecking 
# (https://timber.io/blog/multiprocessing-vs-multithreading-in-python-what-you-need-to-know/).
# We choose multithreading for two reasons:
# 1) Downloading the JARs for first startup is slow
# 2) Multiprocessing leads to discrepancies in scyjava.config, JPype imports, etc.
# The reasons for switching to multiprocessing:
# 1) ImageJ initialization might be faster if the JARs are available locally
setup_thread: Thread = Thread(target=imagej_init)
setup_thread.start()

def ensure_jvm_started():
    if current_thread() is not setup_thread:
        setup_thread.join()
    return


def ij():
    """
    Returns the ImageJ instance.
    If it isn't ready yet, blocks until it is ready.
    """
    global _ij
    ensure_jvm_started()
    return _ij


def logger():
    return _logger


def java_import(class_name: str) -> JClass:
    """
    Imports class_name, while ensuring
    the parallel initialization of ImageJ has completed.
    """
    ensure_jvm_started()
    return jimport(class_name)
