"""
A module testing script discovery and wrapping
"""
from magicgui import magicgui

from napari_imagej.java import JavaClasses
from napari_imagej.utilities._module_utils import functionify_module_execution


class JavaClassesTest(JavaClasses):
    """
    Here we override JavaClasses to get extra test imports
    """

    @JavaClasses.blocking_import
    def DefaultModuleService(self):
        return "org.scijava.module.DefaultModuleService"


jc = JavaClassesTest()


def test_example_script_exists(ij):
    """
    Asserts that Example_Script.js in the local scripts/examples directory can be found
    from the module service, AND that it can be converted into a magicgui widget.
    """
    module_info = ij.module().getModuleById("script:examples/Example_Script.js")
    assert module_info is not None

    module = ij.module().createModule(module_info)

    func, magic_kwargs = functionify_module_execution(None, None, module, module_info)

    # Normally we'd assign the call to a variable, but we aren't using it..
    magicgui(function=func, **magic_kwargs)
