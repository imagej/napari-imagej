"""
A module testing napari-imagej settings
"""
from scyjava import jimport


def test_java_cli_args():
    """
    Asserts that cli arguments defined in confuse settings are passed to the JVM.
    The foo system property is set in pyproject.toml's pytest section
    """
    assert jimport("java.lang.System").getProperty("foo") == "bar"
