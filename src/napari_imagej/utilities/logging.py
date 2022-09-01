"""
A module for standarized logging in napari-imagej

Notable functions included in the module:
    * log_debug()
        - used for logging in a standardized way
"""
import logging

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)  # TEMP


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
    debug_msg = "napari-imagej: " + msg
    _logger.debug(debug_msg)
