from inspect import Parameter, _empty
from typing import Any, Dict, List, Optional

import numpy
import pytest
from magicgui.widgets import (
    Container,
    FloatSlider,
    FloatSpinBox,
    Label,
    LineEdit,
    RadioButtons,
    Select,
    Slider,
    SpinBox,
    Widget,
)
from napari import Viewer
from napari.layers import Image, Layer

from napari_imagej import _module_utils
from napari_imagej._ptypes import OutOfBoundsFactory, TypeMappings, _supported_styles
from napari_imagej.setup_imagej import JavaClasses
from napari_imagej.widget import ImageJWidget


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
    def ScriptInfo(self):
        return "org.scijava.script.ScriptInfo"

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

    def getMaximumValue(self):
        return self._maximumValue

    def setMaximumValue(self, val):
        self._maximumValue = val

    def getMinimumValue(self):
        return self._minimumValue

    def setMinimumValue(self, val):
        self._minimumValue = val

    def getStepSize(self):
        return self._stepSize

    def setStepSize(self, val):
        self._stepSize = val

    def getLabel(self):
        return self._label

    def setLabel(self, val):
        self._label = val

    def getDescription(self):
        return self._description

    def setDescription(self, val):
        self._description = val

    def getChoices(self):
        return self._choices

    def setChoices(self, val):
        self._choices = val

    def getWidgetStyle(self):
        return self._style

    def setWidgetStyle(self, val):
        self._style = val


direct_match_pairs = [(jtype, ptype) for jtype, ptype in TypeMappings().ptypes.items()]
assignable_match_pairs = [
    (jc.ArrayImg, "napari.layers.Image")  # ArrayImg -> RAI -> ImageData
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
    # ImageData -> RAI -> EuclideanSpace
    (jc.EuclideanSpace, "napari.types.ImageData")
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


def test_python_type_of_placeholder_IO():
    # Test that a pure input matches
    module_item = DummyModuleItem(
        jtype=jc.OutOfBoundsFactory, isInput=True, isOutput=False
    )
    assert _module_utils.python_type_of(module_item) == OutOfBoundsFactory

    # Test that a mutable input does not match
    module_item._isOutput = True
    try:
        _module_utils.python_type_of(module_item)
        pytest.fail()
    except ValueError:
        pass

    # Test that a pure output does not match the enum
    module_item._isInput = False
    assert _module_utils.python_type_of(module_item) == str


@pytest.fixture
def example_info(ij):
    return ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )


def test_preprocess_to_harvester(ij, example_info):
    module = ij.module().createModule(example_info)
    all_inputs = module.getInfo().inputs()
    # We expect the log and opService to be resolved with
    # _preprocess_to_harvester; the harvested input should not be resolved.
    non_input_names = [ij.py.to_java(s) for s in ["opService", "log"]]
    expected = filter(lambda x: x.getName() in non_input_names, all_inputs)
    # Get the list of acutally resolved inputs
    _module_utils._preprocess_to_harvester(module)
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

    # We expect the log and opService to be resolved with
    # _preprocess_non_inputs
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

    # In this scenario, we don't care about the remaining harvesters
    remaining_preprocessors = []

    _module_utils._preprocess_remaining_inputs(
        preresolved_module,
        all_inputs,
        unresolved_inputs,
        user_inputs,
        remaining_preprocessors,
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
    assert sorted[0].getDefaultValue() is None
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
    # required, no default
    (
        DummyModuleItem(name="foo"),
        Parameter(name="foo", kind=Parameter.POSITIONAL_OR_KEYWORD, annotation=str),
    ),
    # not required, default
    (
        DummyModuleItem(name="foo", default="bar", isRequired=False),
        Parameter(
            name="foo",
            default="bar",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Optional[str],
        ),
    ),
    # not required, no default
    (
        DummyModuleItem(name="foo", isRequired=False),
        Parameter(
            name="foo",
            default=None,
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Optional[str],
        ),
    ),
]


@pytest.mark.parametrize("input, expected", module_param_inputs)
def test_module_param(input, expected):
    actual = _module_utils._module_param(input)
    assert actual == expected


def test_add_param_metadata():
    # Test successful addition
    metadata = {}
    key = "good"
    value = jc.Double(4)
    _module_utils._add_param_metadata(metadata, key, value)
    assert metadata[key] == 4.0

    # Test an inconvertible type
    key = "bad"
    value = jc.ArrayImgs
    _module_utils._add_param_metadata(metadata, key, value)
    # If we cannot convert, it will not be inserted
    assert key not in metadata


@pytest.fixture
def metadata_module_item(ij) -> DummyModuleItem:
    item: DummyModuleItem = DummyModuleItem(name="foo", jtype=jc.Double)
    maxVal = ij.py.to_java(20.0)
    item.setMaximumValue(maxVal)
    minVal = ij.py.to_java(10.0)
    item.setMinimumValue(minVal)
    stepSize = ij.py.to_java(2.0)
    item.setStepSize(stepSize)
    label = ij.py.to_java("bar")
    item.setLabel(label)
    description = ij.py.to_java("The foo.")
    item.setDescription(description)
    choices = ij.py.to_java(["a", "b", "c"])
    item.setChoices(choices)
    style = ij.py.to_java("spinner")
    item.setWidgetStyle(style)

    return item


def test_add_scijava_metadata(metadata_module_item: DummyModuleItem):
    metadata: Dict[str, Dict[str, Any]] = _module_utils._add_scijava_metadata(
        [metadata_module_item], {"foo": float}
    )

    # Assert only 'foo' key in metadata
    assert len(metadata.keys()) == 1
    assert "foo" in metadata.keys()

    # Assert each metadata
    param_map: Dict[str, Any] = metadata["foo"]
    assert param_map["max"] == 20.0
    assert param_map["min"] == 10.0
    assert param_map["step"] == 2.0
    assert param_map["label"] == "bar"
    assert param_map["tooltip"] == "The foo."
    assert param_map["choices"] == ["a", "b", "c"]
    assert param_map["widget_type"] == "FloatSpinBox"


choiceList = [
    [],
    None,
]


@pytest.mark.parametrize("choices", choiceList)
def test_add_scijava_metadata_empty_choices(
    ij, choices, metadata_module_item: DummyModuleItem
):
    # set the choices
    empty_list = ij.py.to_java(choices)
    metadata_module_item.setChoices(empty_list)

    metadata: Dict[str, Dict[str, Any]] = _module_utils._add_scijava_metadata(
        [metadata_module_item], {"foo": float}
    )

    # Assert only 'foo' key in metadata
    assert len(metadata.keys()) == 1
    assert "foo" in metadata.keys()

    # Assert each metadata
    param_map: Dict[str, Any] = metadata["foo"]
    assert param_map["max"] == 20.0
    assert param_map["min"] == 10.0
    assert param_map["step"] == 2.0
    assert param_map["label"] == "bar"
    assert param_map["tooltip"] == "The foo."
    assert "choices" not in param_map


parameterizations = [
    ("listBox", str, "Select", Select),
    ("radioButtonHorizontal", str, "RadioButtons", RadioButtons),
    ("radioButtonVertical", str, "RadioButtons", RadioButtons),
    ("slider", int, "Slider", Slider),
    ("slider", float, "FloatSlider", FloatSlider),
    ("spinner", int, "SpinBox", SpinBox),
    ("spinner", float, "FloatSpinBox", FloatSpinBox),
]


@pytest.mark.parametrize(
    argnames=["style", "type_hint", "widget_type", "widget_class"],
    argvalues=parameterizations,
)
def test_widget_for_style_and_type(style, type_hint, widget_type, widget_class):
    """
    Tests that a style and type are mapped to the corresponding widget_class
    :param style: the SciJava style
    :param type_hint: the PYTHON type of a parameter
    :param widget_type: the name of a magicgui widget
    :param widget_class: the class corresponding to name
    """
    # We only need item for the getWidgetStyle() function
    item: DummyModuleItem = DummyModuleItem()
    item.setWidgetStyle(style)
    actual = _module_utils._widget_for_item_and_type(item, type_hint)
    assert widget_type == actual

    def func(foo):
        print(foo, "bar")

    func.__annotation__ = {"foo": type_hint}
    import magicgui

    widget = magicgui.magicgui(
        function=func, call_button=False, foo={"widget_type": actual}
    )
    assert len(widget._list) == 1
    assert isinstance(widget._list[0], widget_class)


def test_helper_widgets_for_item_and_type():
    from napari_imagej._helper_widgets import MutableOutputWidget

    # MutableOutputWidget
    item: DummyModuleItem = DummyModuleItem(
        jtype=jc.ArrayImg, isInput=True, isOutput=True
    )
    type_hint = "napari.layers.Image"
    actual = _module_utils._widget_for_item_and_type(item, type_hint)
    assert "napari_imagej._helper_widgets.MutableOutputWidget" == actual

    def func(foo):
        print(foo, "bar")

    func.__annotation__ = {"foo": type_hint}
    import magicgui

    widget = magicgui.magicgui(
        function=func, call_button=False, foo={"widget_type": actual}
    )
    assert len(widget._list) == 1
    assert isinstance(widget._list[0], MutableOutputWidget)


def test_all_styles_in_parameterizations():
    """
    Tests that all style mappings declared in _supported_styles
    are tested in test_wiget_for_style_and_type
    """
    _parameterizations = [p[:-1] for p in parameterizations]
    all_styles = []
    for style in _supported_styles:
        for type_hint, widget_type in _supported_styles[style].items():
            all_styles.append((style, type_hint, widget_type))
    assert all_styles == _parameterizations


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

    # assert the modified signature contains everything in expected_names AND
    # everything in expected_names, in that order.
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

    # assert return annotation is None
    assert sig.return_annotation is None


def run_module_from_script(ij, tmp_path, script):
    # Write the script to a file
    p = tmp_path / "script.py"
    p.write_text(script)

    info: "jc.ScriptInfo" = jc.ScriptInfo(ij.context(), str(p))
    module = info.createModule()
    ij.context().inject(module)
    remaining_preprocessors = _module_utils._preprocess_to_harvester(module)
    _module_utils._preprocess_remaining_inputs(
        module, [], [], [], remaining_preprocessors
    )
    _module_utils._run_module(module)
    _module_utils._postprocess_module(module)
    unresolved_inputs = _module_utils._filter_unresolved_inputs(module, info.inputs())
    unresolved_inputs = _module_utils._sink_optional_inputs(unresolved_inputs)
    return _module_utils._pure_module_outputs(module, unresolved_inputs)


script_zero_layer_zero_widget: str = """
c = 1
"""

script_one_layer_zero_widget: str = """
#@OUTPUT Img d

from net.imglib2.img.array import ArrayImgs

d = ArrayImgs.unsignedBytes(10, 10)
"""

script_two_layer_zero_widget: str = """
#@OUTPUT Img d
#@OUTPUT Img e

from net.imglib2.img.array import ArrayImgs

d = ArrayImgs.unsignedBytes(10, 10)
e = ArrayImgs.unsignedBytes(10, 10)
"""

script_zero_layer_one_widget: str = """
#@OUTPUT Long a
a = 4
"""

script_one_layer_one_widget: str = """
#@OUTPUT Long a
#@OUTPUT Img d

from net.imglib2.img.array import ArrayImgs

a = 4
d = ArrayImgs.unsignedBytes(10, 10)
"""

script_two_layer_one_widget: str = """
#@OUTPUT Long a
#@OUTPUT Img d
#@OUTPUT Img e

from net.imglib2.img.array import ArrayImgs

a = 1
d = ArrayImgs.unsignedBytes(10, 10)
e = ArrayImgs.unsignedBytes(10, 10)
"""

script_zero_layer_two_widget: str = """
#@OUTPUT Long a
#@OUTPUT Long b
a = 4
b = 1
"""

script_one_layer_two_widget: str = """
#@OUTPUT Long a
#@OUTPUT Long b
#@OUTPUT Img d

from net.imglib2.img.array import ArrayImgs

a = 4
b = 4
d = ArrayImgs.unsignedBytes(10, 10)
"""

script_two_layer_two_widget: str = """
#@OUTPUT Long a
#@OUTPUT Long b
#@OUTPUT Img d
#@OUTPUT Img e

from net.imglib2.img.array import ArrayImgs

a = 1
b = 1
d = ArrayImgs.unsignedBytes(10, 10)
e = ArrayImgs.unsignedBytes(10, 10)
"""

script_both_but_optional: str = """
#@BOTH Img(required=false) d

from net.imglib2.img.array import ArrayImgs

if d is None:
    d = ArrayImgs.unsignedBytes(10, 10)
"""

script_both_but_required: str = """
#@BOTH Img(required=true) d

from net.imglib2.img.array import ArrayImgs
"""

widget_parameterizations = [
    (script_zero_layer_zero_widget, 0, 0),
    (script_one_layer_zero_widget, 1, 0),
    (script_two_layer_zero_widget, 2, 0),
    (script_zero_layer_one_widget, 0, 1),
    (script_one_layer_one_widget, 1, 1),
    (script_two_layer_one_widget, 2, 1),
    (script_zero_layer_two_widget, 0, 2),
    (script_one_layer_two_widget, 1, 2),
    (script_two_layer_two_widget, 2, 2),
    # No layers returned, the required BOTH is just updated
    (script_both_but_required, 0, 0),
    # One layer returned as we create the optional input internally
    (script_both_but_optional, 1, 0),
]


@pytest.mark.parametrize(
    argnames="script, num_layer, num_widget", argvalues=widget_parameterizations
)
def test_module_outputs_number(ij, tmp_path, script, num_layer, num_widget):
    layer_outputs, widget_outputs = run_module_from_script(ij, tmp_path, script)
    if num_layer == 0:
        assert layer_outputs is None
    else:
        assert num_layer == len(layer_outputs)
        for layer in layer_outputs:
            assert isinstance(layer, Layer)
    assert num_widget == len(widget_outputs)


out_type_params = [
    (script_zero_layer_one_widget, None),
    (script_one_layer_one_widget, List[Layer]),
    (script_two_layer_one_widget, List[Layer]),
    (script_both_but_optional, List[Layer]),
    (script_both_but_required, None),
]


@pytest.mark.parametrize(argnames="script, type", argvalues=out_type_params)
def test_module_output_type(ij, tmp_path, script, type):
    # Write the script to a file
    p = tmp_path / "script.py"
    p.write_text(script)

    info: "jc.ScriptInfo" = jc.ScriptInfo(ij.context(), str(p))
    module = info.createModule()
    unresolved_inputs = _module_utils._filter_unresolved_inputs(module, info.inputs())
    unresolved_inputs = _module_utils._sink_optional_inputs(unresolved_inputs)
    assert _module_utils._widget_return_type(info, unresolved_inputs) == type


def test_non_layer_widget():
    results = [("a", 1), ("b", 2)]
    widget: Widget = _module_utils._non_layer_widget(results)
    # Assert the return is a container
    assert isinstance(widget, Container)
    # Assert the nth subwidget reports the nth name and (stringified) value
    for result, subwidget in zip(results, widget):
        assert isinstance(subwidget, Container)
        # Assert the label is 'a'
        assert isinstance(subwidget[0], Label)
        assert subwidget[0].value == result[0]
        # Assert the value is '1' (stringified 1)
        assert isinstance(subwidget[1], LineEdit)
        assert subwidget[1].value == str(result[1])


def test_mutable_layers():
    # 4 inputs, only the last is a mutable layer
    unresolved_inputs = [
        DummyModuleItem(name="a", isOutput=False),
        DummyModuleItem(name="b", isOutput=True),
        DummyModuleItem(name="c", isOutput=False),
        DummyModuleItem(name="d", isOutput=True),
        DummyModuleItem(name="e", isOutput=False, isRequired=False),
        DummyModuleItem(name="f", isOutput=True, isRequired=False),
        DummyModuleItem(name="g", isOutput=False, isRequired=False),
        DummyModuleItem(name="h", isOutput=True, isRequired=False),
    ]
    user_resolved_inputs = [
        1,
        2,
        Image(data=numpy.ones((4, 4))),
        Image(data=numpy.ones((4, 4))),
        1,
        2,
        Image(data=numpy.ones((4, 4))),
        Image(data=numpy.ones((4, 4))),
    ]
    mutable_layers = _module_utils._mutable_layers(
        unresolved_inputs, user_resolved_inputs
    )
    assert 2 == len(mutable_layers)
    assert user_resolved_inputs[3] in mutable_layers
    assert user_resolved_inputs[7] in mutable_layers


def test_request_values_args():
    import napari

    def foo(
        a,
        b: str,
        c: Image,
        d: "napari.layers.Image",
        e="default",
        f: str = "also default",
    ):
        return "I didn't use any of my parameters"

    param_options = {}
    param_options["a"] = {}
    param_options["a"]["tooltip"] = "We don't use this"

    args: dict = _module_utils._request_values_args(foo, param_options)

    import inspect

    assert "a" in args
    assert args["a"]["annotation"] == inspect._empty
    assert args["a"]["options"] == dict(tooltip="We don't use this")
    assert "value" not in args["a"]

    assert "b" in args
    assert args["b"]["annotation"] == str
    assert "options" not in args["b"]
    assert "value" not in args["b"]

    assert "c" in args
    assert args["c"]["annotation"] == Image
    assert args["c"]["options"] == dict(choices=_module_utils._get_layers_hack)
    assert "value" not in args["c"]

    assert "d" in args
    assert args["d"]["annotation"] == "napari.layers.Image"
    assert args["d"]["options"] == dict(choices=_module_utils._get_layers_hack)
    assert "value" not in args["d"]

    assert "e" in args
    assert args["e"]["annotation"] == inspect._empty
    assert "options" not in args["e"]
    assert args["e"]["value"] == "default"

    assert "f" in args
    assert args["f"]["annotation"] == str
    assert "options" not in args["f"]
    assert args["f"]["value"] == "also default"


def test_execute_function_with_params(make_napari_viewer, ij):
    viewer: Viewer = make_napari_viewer()
    info = ij.module().getModuleById(
        "command:net.imagej.ops.commands.filter.FrangiVesselness"
    )
    func, _ = _module_utils.functionify_module_execution(
        viewer, info.createModule(), info
    )
    params: Dict[str, Any] = dict(
        input=numpy.ones((100, 100)),
        doGauss=False,
        spacingString="1, 1",
        scaleString="2, 5",
    )
    # Ensure that a None params does nothing
    _module_utils._execute_function_with_params(viewer, None, func)
    assert len(viewer.layers) == 0

    _module_utils._execute_function_with_params(viewer, params, func)
    assert len(viewer.layers) == 1


def test_convert_searchResult_to_info(imagej_widget: ImageJWidget, ij):
    for i in range(imagej_widget.results.topLevelItemCount()):
        searcher = imagej_widget.results.topLevelItem(i)._searcher
        result = searcher.search("f", True)[0]
        info = _module_utils.convert_searchResult_to_info(result)
        assert isinstance(info, jc.ModuleInfo)
