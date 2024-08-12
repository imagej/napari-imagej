"""
A module testing napari-imagej settings
"""

from scyjava import jimport

from napari_imagej import settings


def test_java_cli_args():
    """
    Assert that cli arguments defined in confuse settings are passed to the JVM.
    The foo system property is set in pyproject.toml's pytest section
    """
    assert jimport("java.lang.System").getProperty("foo") == "bar"


def test_validate_imagej_base_directory():
    """
    Assert that non-existent imagej_base_directory is noticed by the validate function.
    """
    settings.imagej_base_directory = "a-file-path-that-is-unlikely-to-exist"
    settings._is_macos = False

    errors = validation_errors()
    assert len(errors) == 1
    assert errors[0].startswith("ImageJ base directory is not a valid directory.")


def test_validate_enable_imagej_gui():
    """
    Assert that enable_imagej_gui=True on macOS is noticed by the validate function.
    """
    settings.enable_imagej_gui = True
    settings._is_macos = True

    errors = validation_errors()
    assert len(errors) == 1
    assert errors[0].startswith("The ImageJ GUI is not available on macOS systems.")


def test_validate_multiple_problems():
    """
    Assert that multiple issues are reported as expected by the validate function.
    """
    settings.imagej_base_directory = "another-file-path-that-is-unlikely-to-exist"
    settings.enable_imagej_gui = True
    settings._is_macos = True

    errors = validation_errors()
    assert len(errors) == 2
    assert errors[0].startswith("ImageJ base directory is not a valid directory.")
    assert errors[1].startswith("The ImageJ GUI is not available on macOS systems.")


def test_validate_default_settings_not_macos():
    """
    Assert that the validate function succeeds with default settings on non-Mac
    """
    settings._is_macos = False

    errors = validation_errors()
    assert len(errors) == 0


def test_validate_default_settings_macos():
    """
    Assert that the validate function yields a warnig with default settings on Mac
    """
    settings._is_macos = True

    errors = validation_errors()
    assert len(errors) == 1
    assert errors[0].startswith("The ImageJ GUI is not available on macOS systems.")


def validation_errors():
    try:
        settings.validate()
    except ValueError as e:
        return e.args
    return []
