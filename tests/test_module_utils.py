from typing import Generator, Optional
from napari import Viewer

import pytest
from napari_imagej.widget import ImageJWidget
from napari_imagej.setup_imagej import JavaClasses
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QAbstractItemView,
    QLineEdit,
)

class JavaClassesTest(JavaClasses):
    """
    Here we override JavaClasses to get extra test imports
    """
    @JavaClasses.blocking_import
    def ArrayImgs(self): return "net.imglib2.img.array.ArrayImgs"

    @JavaClasses.blocking_import
    def DefaultMutableModuleItem(self): return "org.scijava.module.DefaultMutableModuleItem"

    @JavaClasses.blocking_import
    def DefaultMutableModuleInfo(self): return "org.scijava.module.DefaultMutableModuleInfo"

    @JavaClasses.blocking_import
    def ItemIO(self): return "org.scijava.ItemIO"

    @JavaClasses.blocking_import
    def System(self): return "java.lang.System"


jc = JavaClassesTest()


@pytest.fixture
def imagej_widget(make_napari_viewer) -> Generator[ImageJWidget, None, None]:
    # Create widget
    viewer: Viewer = make_napari_viewer()
    ij_widget: ImageJWidget = ImageJWidget(viewer)

    yield ij_widget

    # Cleanup -> Close the widget, trigger ImageJ shutdown
    ij_widget.close()

def test_widget_layout(imagej_widget: ImageJWidget):
    """Ensures a vertical widget layout."""
    assert isinstance(imagej_widget.layout(), QVBoxLayout)

def test_widget_searchbar_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the searchbar widget."""
    searchbar:QWidget = imagej_widget._search_widget
    assert isinstance(searchbar.layout(), QHBoxLayout)
    search_widget: QLineEdit = searchbar.findChild(QLineEdit)

def test_widget_table_layout(imagej_widget: ImageJWidget):
    """Tests basic features of the search results table."""
    table:QTableWidget = imagej_widget.findChild(QTableWidget)
    assert 12 == table.rowCount()
    assert 1 == table.columnCount()
    assert QAbstractItemView.SelectRows == table.selectionBehavior()
    assert False == table.showGrid()

from napari_imagej._ptypes import TypeMappings
from napari_imagej._module_utils import python_type_of

class DummyModuleInfo:
    def __init__(self, inputs=[], outputs=[]):
        self._inputs = inputs
        self._outputs = outputs
    
    def outputs(self):
        return self._outputs

class DummyModuleItem:
    def __init__(
        self,
        name='',
        jtype=jc.String,
        isRequired=True,
        isInput=True,
        isOutput=False,
        default=None
    ):
        self._name = name
        self._jtype = jtype
        self._isRequired = isRequired
        self._isInput = isInput
        self._isOutput = isOutput
        self._default = default

    def getName(self):
        return self._name

    def getType(self):
        return self._jtype
    
    def isRequired(self):
        return self._isRequired

    def isInput(self):
        return self._isInput

    def isOutput(self):
        return self._isOutput

    def getDefaultValue(self):
        return self._default

def test_ptype():
    ptypes = TypeMappings()

    for jtype, ptype in ptypes.ptypes.items():
        assert python_type_of(DummyModuleItem(jtype=jtype)) == ptype

from napari_imagej._module_utils import _return_type

def test_return_type():
    outTypes = [
        [],
        [jc.Double],
        [jc.Double, jc.Double],
    ]
    expecteds = [None, float, dict]
    # Construct dummy ModuleInfos from outTypes
    outItems = [[DummyModuleItem(jtype=i) for i in arr] for arr in outTypes]
    testInfos = [DummyModuleInfo(outputs=items) for items in outItems]

    for info, expected in zip(testInfos, expecteds):
        actual = _return_type(info)
        assert expected == actual

@pytest.fixture
def example_info(ij):
    return ij.module().getModuleById('command:net.imagej.ops.commands.filter.FrangiVesselness')

from napari_imagej._module_utils import _preprocess_non_inputs

def test_preprocess_non_inputs(ij, example_info):
    module = ij.module().createModule(example_info)
    all_inputs = module.getInfo().inputs()
    # We expect the log and opService to be resolved with _preprocess_non_inputs
    non_input_names = [ij.py.to_java(s) for s in ['opService', 'log']]
    expected = filter(lambda x: x.getName() in non_input_names, all_inputs)
    # Get the list of 
    _preprocess_non_inputs(module)
    actual = filter(lambda x: module.isResolved(x.getName()), all_inputs)

    for e, a in zip(expected, actual):
        assert e == a

from napari_imagej._module_utils import _filter_unresolved_inputs

def preresolved_module(ij, module_info):
    module = ij.module().createModule(module_info)

    # Resolve Logger
    log = ij.context().getService('org.scijava.log.LogService')
    module.setInput("log", log)
    module.resolveInput("log")
    # Resolve OpService
    op = ij.context().getService('net.imagej.ops.OpService')
    module.setInput("opService", op)
    module.resolveInput("opService")

    return module

def test_filter_unresolved_inputs(ij, example_info):
    module = preresolved_module(ij, example_info)
    all_inputs = module.getInfo().inputs()
    actual = _filter_unresolved_inputs(module, all_inputs)

    # We expect the log and opService to be resolved with _preprocess_non_inputs
    non_input_names = [ij.py.to_java(s) for s in ['opService', 'log']]
    expected = filter(lambda x: x.getName() not in non_input_names, all_inputs)

    for e, a in zip(expected, actual):
        assert e == a

from napari_imagej._module_utils import _preprocess_remaining_inputs
    
def test_preprocess_remaining_inputs(ij, example_info):
    module = preresolved_module(ij, example_info)
    all_inputs = module.getInfo().inputs()
    # Example user-resolved inputs
    input = jc.ArrayImgs.bytes(10, 10)
    doGauss = True
    spacingString = '1, 1'
    scaleString = '2 5'

    user_inputs = [input, doGauss, spacingString, scaleString]

    unresolved_inputs = _filter_unresolved_inputs(module, all_inputs)
    _preprocess_remaining_inputs(module, all_inputs, unresolved_inputs, user_inputs)

    for input in all_inputs:
        assert module.isInputResolved(input.getName())

from napari_imagej._module_utils import _resolvable_or_required

example_inputs = [
    # Resolvable, required
    (DummyModuleItem(), True),
    # Resolvable, not required
    (DummyModuleItem(isRequired=False), True),
    # Not resolvable, required
    (DummyModuleItem(jtype=jc.System), True),
    # Not resolvable, not required
    (DummyModuleItem(jtype=jc.System, isRequired=False), False),
]

@pytest.mark.parametrize('input, expected', example_inputs)
def test_resolvable_or_required(input, expected):
    assert expected == _resolvable_or_required(input)

from napari_imagej._module_utils import _is_optional_arg

is_non_default_example_inputs = [
    # default, required
    (DummyModuleItem(default='foo'), False),
    # default, not required
    (DummyModuleItem(default='foo', isRequired=False), False),
    # not default, required
    (DummyModuleItem(), True),
    # not default, not required
    (DummyModuleItem(isRequired=False), False),
]
@pytest.mark.parametrize('input, expected', is_non_default_example_inputs)
def test_is_non_default(input, expected):
    assert expected == _is_optional_arg(input)

from napari_imagej._module_utils import _sink_optional_inputs

def test_sink_optional_inputs():
    inputs = [
        DummyModuleItem(default='foo'),
        DummyModuleItem(),
        DummyModuleItem(default='bar')
    ]
    sorted = _sink_optional_inputs(inputs)
    # Ensure that foo went below
    assert sorted[0].getDefaultValue() == None
    assert sorted[1].getDefaultValue() == 'foo'
    assert sorted[2].getDefaultValue() == 'bar'

from napari_imagej._module_utils import _napari_module_param_additions
from jpype import JArray, JObject

def assert_new_window_checkbox_for_type(type, expected):
    info = jc.DefaultMutableModuleInfo()
    item = jc.DefaultMutableModuleItem(info, 'out', type)
    info.addOutput(item)

    has_option = "display_results_in_new_window" in _napari_module_param_additions(info)
    assert expected == has_option

def test_napari_param_new_window_checkbox(imagej_widget):
    ptypes = TypeMappings()

    types_absent = ptypes._napari_layer_types

    for t in types_absent:
        assert_new_window_checkbox_for_type(t, False)

    types_present = list(set(ptypes.ptypes.keys()) - set(ptypes._napari_layer_types))
    for t in types_present:
        assert_new_window_checkbox_for_type(t, True)


from napari_imagej._module_utils import _type_hint_for_module_item


def assert_item_annotation(jtype, ptype, isRequired):
    module_item = DummyModuleItem(jtype=jtype, isRequired=isRequired)
    param_type = _type_hint_for_module_item(module_item)
    assert param_type == ptype


def test_param_annotation(imagej_widget):
    # -- TEST CONVERTABLE ITEM --
    assert_item_annotation(jc.String, str, True)
    assert_item_annotation(jc.String, Optional[str], False)


from napari_imagej._module_utils import _module_param
from inspect import Parameter

module_param_inputs = [
    # default, required
    (
        DummyModuleItem(name='foo'),
        Parameter(name='foo', kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
    ),
    # default, not required
    (
        DummyModuleItem(name='foo', default='bar', isRequired=False),
        Parameter(name='foo', default='bar', kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=Optional[str])
    )
]
@pytest.mark.parametrize('input, expected', module_param_inputs)
def test_module_param(input, expected):
    actual = _module_param(input)
    assert actual == expected


from napari_imagej._module_utils import _modify_function_signature


def test_modify_functional_signature(imagej_widget):
    """
    We first create a module info, and then assert that _modify_function_signature
    creates a signature that describes all parameters that we'd want for both 
    napari-imagej and for the module.
    """
    info = jc.DefaultMutableModuleInfo()

    # INPUTS
    # The first argument will be optional, so that we can test it sinking
    in1 = jc.DefaultMutableModuleItem(info, 'in1', jc.String)
    in1.setRequired(False)
    in1.setDefaultValue('foo')
    # The second argument will be required
    in2 = jc.DefaultMutableModuleItem(info, 'in2', jc.String)
    inputs = [in1, in2]
    for input in inputs:
        input.setIOType(jc.ItemIO.INPUT)
        info.addInput(input)

    # OUTPUTS
    outputs = [
        jc.DefaultMutableModuleItem(info, 'out', jc.String)
    ]
    for out in outputs:
        out.setIOType(jc.ItemIO.OUTPUT)
        info.addOutput(out)

    def func(*inputs):
        print('This is a function')
    _modify_function_signature(func, inputs, info)   
    sig = func.__signature__


    napari_param_map = _napari_module_param_additions(info)

    import inspect
    expected_names = ['in2', 'in1']
    expected_types = [str, Optional[str]]
    expected_defaults = [inspect._empty, 'foo']

    # assert the modified signature contains everything in expected_names AND everything in expected_names, in that order. 
    sig_params = sig.parameters
    for i, key in enumerate(sig_params):
        if i < len(expected_names):
            assert expected_names[i] == sig_params[key].name
            assert expected_types[i] == sig_params[key].annotation
            assert expected_defaults[i] == sig_params[key].default
        else:
            assert key in napari_param_map
            param = napari_param_map[key]
            assert param[0] == sig_params[key].annotation
            assert param[1] == sig_params[key].default
    
    assert len(sig_params) == len(expected_names) + len(napari_param_map)

    # assert return annotation
    assert sig.return_annotation == str
