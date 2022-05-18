from typing import List, Optional

import pytest
from inspect import Parameter, _empty
from napari_imagej import _module_utils
from napari_imagej.setup_imagej import JavaClasses
from napari_imagej._ptypes import TypeMappings


class JavaClassesTest(JavaClasses):
    """
    Here we override JavaClasses to get extra test imports
    """

    @JavaClasses.blocking_import
    def ArrayImg(self):
        return "net.imglib2.img.array.ArrayImg"

    @JavaClasses.blocking_import
    def ArrayImgs(self):
        return "net.imglib2.img.array.ArrayImgs"

    @JavaClasses.blocking_import
    def DefaultMutableModuleItem(self):
        return "org.scijava.module.DefaultMutableModuleItem"

    @JavaClasses.blocking_import
    def DefaultMutableModuleInfo(self):
        return "org.scijava.module.DefaultMutableModuleInfo"

    @JavaClasses.blocking_import
    def DoubleArray(self):
        return "org.scijava.util.DoubleArray"

    @JavaClasses.blocking_import
    def EuclideanSpace(self):
        return "net.imglib2.EuclideanSpace"

    @JavaClasses.blocking_import
    def ItemIO(self):
        return "org.scijava.ItemIO"

    @JavaClasses.blocking_import
    def System(self):
        return "java.lang.System"


jc = JavaClassesTest()


class DummyModuleInfo:
    """
    A mock of org.scijava.module.ModuleInfo that is created much easier
    Fields can and should be added as needed for tests.
    """

    def __init__(self, inputs=[], outputs=[]):
        self._inputs = inputs
        self._outputs = outputs

    def outputs(self):
        return self._outputs


class DummyModuleItem:
    """
    A mock of org.scijava.module.ModuleItem that is created much easier
    Fields can and should be added as needed for tests.
    """

    def __init__(
        self,
        name="",
        jtype=jc.String,
        isRequired=True,
        isInput=True,
        isOutput=False,
        default=None,
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


direct_match_pairs = [(jtype, ptype) for jtype, ptype in TypeMappings().ptypes.items()]
assignable_match_pairs = [
    (jc.ArrayImg, "napari.types.ImageData")  # ArrayImg -> RAI -> ImageData
]
convertible_match_pairs = [
    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert Integers into DoubleArrays; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    (jc.DoubleArray, int)
]
type_pairs = direct_match_pairs + assignable_match_pairs + convertible_match_pairs


@pytest.mark.parametrize("jtype, ptype", type_pairs)
def test_python_type_of_input_only(jtype, ptype):
    module_item = DummyModuleItem(jtype=jtype, isInput=True, isOutput=False)
    assert _module_utils.python_type_of(module_item) == ptype


direct_match_pairs = [(jtype, ptype) for jtype, ptype in TypeMappings().ptypes.items()]
assignable_match_pairs = [
    (jc.EuclideanSpace, "napari.types.ImageData")  # ImageData -> RAI -> EuclideanSpace
]
convertible_match_pairs = [
    # We want to test that napari could tell that a DoubleArray ModuleItem
    # could be satisfied by a List[float], as napari-imagej knows how to
    # convert that List[float] into a Double[], and imagej knows how to
    # convert that Double[] into a DoubleArray. Unfortunately, DefaultConverter
    # can convert DoubleArrays into strings; because it comes first in
    # TypeMappings, it is the python type that returns.
    # This is really not napari-imagej's fault.
    # Since the goal was just to test that python_type_of uses ij.convert()
    # as an option, we will leave the conversion like this.
    (jc.DoubleArray, str)  # DoubleArray -> String -> str
]
type_pairs = direct_match_pairs + convertible_match_pairs


@pytest.mark.parametrize("jtype, ptype", type_pairs)
def test_python_type_of_output_only(jtype, ptype):
    module_item = DummyModuleItem(jtype=jtype, isInput=False, isOutput=True)
    assert _module_utils.python_type_of(module_item) == ptype


direct_match_pairs = [(jtype, ptype) for jtype, ptype in TypeMappings().ptypes.items()]
convertible_match_pairs = [(jc.DoubleArray, List[float])]
type_pairs = direct_match_pairs + convertible_match_pairs


@pytest.mark.parametrize("jtype, ptype", type_pairs)
def test_python_type_of_IO(jtype, ptype):
    module_item = DummyModuleItem(jtype=jtype, isInput=True, isOutput=True)
    assert _module_utils.python_type_of(module_item) == ptype


parameterizations = [([], None), ([jc.Double], float), ([jc.Double, jc.Double], dict)]


@pytest.mark.parametrize("outputs, expected_module_return", parameterizations)
def test_return_type(outputs, expected_module_return):
    # Construct dummy ModuleInfos from outTypes
    outItems = [DummyModuleItem(jtype=o) for o in outputs]
    testInfo = DummyModuleInfo(outputs=outItems)

    actual = _module_utils._return_type(testInfo)
    assert expected_module_return == actual


@pytest.fixture
def example_info(ij):
    return ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )


def test_preprocess_non_inputs(ij, example_info):
    module = ij.module().createModule(example_info)
    all_inputs = module.getInfo().inputs()
    # We expect the log and opService to be resolved with _preprocess_non_inputs
    non_input_names = [ij.py.to_java(s) for s in ["opService", "log"]]
    expected = filter(lambda x: x.getName() in non_input_names, all_inputs)
    # Get the list of acutally resolved inputs
    _module_utils._preprocess_non_inputs(module)
    actual = filter(lambda x: module.isResolved(x.getName()), all_inputs)

    for e, a in zip(expected, actual):
        assert e == a


@pytest.fixture
def preresolved_module(ij, example_info):
    """A module with its meta-inputs (e.g. LogService) resolved."""
    module = ij.module().createModule(example_info)

    # Resolve Logger
    log = ij.context().getService("org.scijava.log.LogService")
    module.setInput("log", log)
    module.resolveInput("log")
    # Resolve OpService
    op = ij.context().getService("net.imagej.ops.OpService")
    module.setInput("opService", op)
    module.resolveInput("opService")

    return module


def test_filter_unresolved_inputs(ij, preresolved_module):
    all_inputs = preresolved_module.getInfo().inputs()
    actual = _module_utils._filter_unresolved_inputs(preresolved_module, all_inputs)

    # We expect the log and opService to be resolved with _preprocess_non_inputs
    non_input_names = [ij.py.to_java(s) for s in ["opService", "log"]]
    expected = filter(lambda x: x.getName() not in non_input_names, all_inputs)

    for e, a in zip(expected, actual):
        assert e == a


def test_preprocess_remaining_inputs(preresolved_module):
    all_inputs = preresolved_module.getInfo().inputs()
    # Example user-resolved inputs
    input = jc.ArrayImgs.bytes(10, 10)
    doGauss = True
    spacingString = "1, 1"
    scaleString = "2 5"

    user_inputs = [input, doGauss, spacingString, scaleString]

    unresolved_inputs = _module_utils._filter_unresolved_inputs(
        preresolved_module, all_inputs
    )
    _module_utils._preprocess_remaining_inputs(
        preresolved_module, all_inputs, unresolved_inputs, user_inputs
    )

    for input in all_inputs:
        assert preresolved_module.isInputResolved(input.getName())


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


@pytest.mark.parametrize("input, expected", example_inputs)
def test_resolvable_or_required(input, expected):
    assert expected == _module_utils._resolvable_or_required(input)


is_non_default_example_inputs = [
    # default, required
    (DummyModuleItem(default="foo"), False),
    # default, not required
    (DummyModuleItem(default="foo", isRequired=False), False),
    # not default, required
    (DummyModuleItem(), True),
    # not default, not required
    (DummyModuleItem(isRequired=False), False),
]


@pytest.mark.parametrize("input, expected", is_non_default_example_inputs)
def test_is_non_default(input, expected):
    assert expected == _module_utils._is_optional_arg(input)


def test_sink_optional_inputs():
    inputs = [
        DummyModuleItem(default="foo"),
        DummyModuleItem(),
        DummyModuleItem(default="bar"),
    ]
    sorted = _module_utils._sink_optional_inputs(inputs)
    # Ensure that foo went below
    assert sorted[0].getDefaultValue() == None
    assert sorted[1].getDefaultValue() == "foo"
    assert sorted[2].getDefaultValue() == "bar"


def assert_new_window_checkbox_for_type(type, expected):
    info = jc.DefaultMutableModuleInfo()
    item = jc.DefaultMutableModuleItem(info, "out", type)
    info.addOutput(item)

    has_option = (
        "display_results_in_new_window"
        in _module_utils._napari_module_param_additions(info)
    )
    assert expected == has_option


def test_napari_param_new_window_checkbox():
    ptypes = TypeMappings()

    types_absent = ptypes._napari_layer_types

    for t in types_absent:
        assert_new_window_checkbox_for_type(t, False)

    types_present = list(set(ptypes.ptypes.keys()) - set(ptypes._napari_layer_types))
    for t in types_present:
        assert_new_window_checkbox_for_type(t, True)


def assert_item_annotation(jtype, ptype, isRequired):
    module_item = DummyModuleItem(jtype=jtype, isRequired=isRequired)
    param_type = _module_utils._type_hint_for_module_item(module_item)
    assert param_type == ptype


def test_param_annotation(imagej_widget):
    # -- TEST CONVERTABLE ITEM --
    assert_item_annotation(jc.String, str, True)
    assert_item_annotation(jc.String, Optional[str], False)


module_param_inputs = [
    # default, required
    (
        DummyModuleItem(name="foo"),
        Parameter(name="foo", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
    ),
    # default, not required
    (
        DummyModuleItem(name="foo", default="bar", isRequired=False),
        Parameter(
            name="foo",
            default="bar",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Optional[str],
        ),
    ),
]


@pytest.mark.parametrize("input, expected", module_param_inputs)
def test_module_param(input, expected):
    actual = _module_utils._module_param(input)
    assert actual == expected


def test_modify_functional_signature():
    """
    We first create a module info, and then assert that _modify_function_signature
    creates a signature that describes all parameters that we'd want for both
    napari-imagej and for the module.
    """
    info = jc.DefaultMutableModuleInfo()

    # INPUTS
    # The first argument will be optional, so that we can test it sinking
    in1 = jc.DefaultMutableModuleItem(info, "in1", jc.String)
    in1.setRequired(False)
    in1.setDefaultValue("foo")
    # The second argument will be required
    in2 = jc.DefaultMutableModuleItem(info, "in2", jc.String)
    inputs = [in1, in2]
    for input in inputs:
        input.setIOType(jc.ItemIO.INPUT)
        info.addInput(input)

    # OUTPUTS
    outputs = [jc.DefaultMutableModuleItem(info, "out", jc.String)]
    for out in outputs:
        out.setIOType(jc.ItemIO.OUTPUT)
        info.addOutput(out)

    def func(*inputs):
        print("This is a function")

    _module_utils._modify_function_signature(func, inputs, info)
    sig = func.__signature__

    napari_param_map = _module_utils._napari_module_param_additions(info)

    expected_names = ["in2", "in1"]
    expected_types = [str, Optional[str]]
    expected_defaults = [_empty, "foo"]

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
