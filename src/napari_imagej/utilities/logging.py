"""
A module for standarized logging in napari-imagej

Notable functions included in the module:
    * log_debug()
        - used for logging in a standardized way
"""

import logging
import os

_logger = logging.getLogger(__name__)

if os.environ.get("DEBUG", None):
    _logger.setLevel(logging.DEBUG)


# -- LOGGER API -- #


def logger() -> logging.Logger:
    """
    Gets the Logger instance
    :return: the Logger instance used by this application
    """
    return _logger


def log_debug(msg: str):
    """
    Provides a debug message to the logger, prefaced by 'napari-imagej: '
    :param msg: The message to output
    """
    _logger.debug("napari-imagej: %s", msg)


def is_debug():
    return _logger.isEnabledFor(logging.DEBUG)


def warn(msg: str):
    """
    Provides a warning message to the logger, prefaced by 'napari-imagej: '
    :param msg: The message to output
    """
    _logger.warning("napari-imagej: %s", msg)
