"""
A collection of QWidgets, each designed to conveniently harvest a particular input.
They should align with a SciJava ModuleItem that satisfies some set of conditions.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from imagej.images import _imglib2_types
from jpype import JArray, JClass, JInt, JLong
from magicgui.types import ChoicesType
from magicgui.widgets import (
    CheckBox,
    ComboBox,
    Container,
    FileEdit,
    FloatSpinBox,
    ListEdit,
    PushButton,
    SpinBox,
    Widget,
    request_values,
)
from napari import current_viewer
from napari.layers import Layer, Image
from napari.utils._magicgui import get_layers
from numpy import dtype
from scyjava import numeric_bounds

from napari_imagej.java import jc

if TYPE_CHECKING:
    from typing import Sequence


# Generally, Python libraries treat the dimensions i of an array with n
# dimensions as the CONVENTIONAL_DIMS[n][i] axis
# FIXME: Also in widget_utils.py
CONVENTIONAL_DIMS = [
    [],
    ["X"],
    ["Y", "X"],
    ["Z", "Y", "X"],
    ["T", "Y", "X", "C"],
    ["T", "Z", "Y", "X", "C"],
]


def widget_supported_java_types() -> List[JClass]:
    """
    Returns a List of the JAVA types that, for various reasons,
    have dedicated magicgui widgets.

    Usually, this is due to the absence of a corresponding Python type.
    """
    return [jc.Shape]


@lru_cache(maxsize=None)
def numeric_type_widget_for(cls: type):
    # Set sensible defaults for interfaces
    if cls == jc.RealType or cls == jc.NumericType:
        cls = jc.DoubleType.class_
    elif cls == jc.IntegerType:
        cls = jc.LongType.class_
    elif cls == jc.BooleanType:
        cls = jc.BitType.class_

    instance = cls.newInstance()
    # Case logic for implementation-specific attributes
    extra_args = {}
    if issubclass(cls, jc.BooleanType):
        parent = CheckBox
    elif issubclass(cls, jc.IntegerType):
        parent = SpinBox
        extra_args["min"] = max(instance.getMinValue(), -(2**31))
        extra_args["max"] = min(instance.getMaxValue(), (2**31) - 1)
    elif issubclass(cls, jc.RealType):
        parent = FloatSpinBox
        extra_args["min"] = instance.getMinValue()
        extra_args["max"] = instance.getMaxValue()
    else:
        return None

    # Define the new widget
    class Widget(parent):
        def __init__(self, **kwargs):
            for k, v in extra_args.items():
                kwargs.setdefault(k, v)
            super().__init__(**kwargs)

        @property
        def value(self):
            real_type = cls.newInstance()
            real_type.set(super().value)
            return real_type

    return Widget


@lru_cache(maxsize=None)
def number_widget_for(cls: type):
    if not issubclass(cls, jc.Number):
        return None
    # Sensible default for Number iface
    if cls == jc.Number:
        cls = jc.Double

    # NB cls in this instance is jc.Byte.class_, NOT jc.Byte
    # We want the latter for use in numeric_bounds and in the widget subclass
    if cls == jc.Byte:
        cls = ctor = jc.Byte
    if cls == jc.Short:
        cls = ctor = jc.Short
    if cls == jc.Integer:
        cls = ctor = jc.Integer
    if cls == jc.Long:
        cls = ctor = jc.Long
    if cls == jc.Float:
        cls = ctor = jc.Float
    if cls == jc.Double:
        cls = ctor = jc.Double
    if cls == jc.BigInteger:
        cls = jc.BigInteger
        ctor = jc.BigInteger.valueOf
    if cls == jc.BigDecimal:
        cls = jc.BigDecimal
        ctor = jc.BigDecimal.valueOf

    extra_args = {}
    # HACK: Best attempt for BigDecimal/BigInteger
    extra_args["min"], extra_args["max"] = (
        numeric_bounds(jc.Long)
        if cls == jc.BigInteger
        else numeric_bounds(jc.Double)
        if cls == jc.BigDecimal
        else numeric_bounds(cls)
    )
    # Case logic for implementation-specific attributes
    parent = (
        FloatSpinBox
        if issubclass(cls, (jc.Double, jc.Float, jc.BigDecimal))
        else SpinBox
    )

    # Define the new widget
    class Widget(parent):
        def __init__(self, **kwargs):
            for k, v in extra_args.items():
                kwargs.setdefault(k, v)
            super().__init__(**kwargs)

        @property
        def value(self):
            return ctor(parent.value.fget(self))

        @value.setter
        def value(self, value: Any):
            parent.value.fset(self, value)

    return Widget


class MutableDimWidget(Container):
    def __init__(
        self,
        val: int = 256,
        idx: int = 0,
        **kwargs,
    ):
        layer_tooltip = f"Parameters for the dimension of index {idx}"
        self.size_spin = SpinBox(value=val, min=1)
        choices = ["X", "Y", "Z", "C", "T"]
        layer_kwargs = kwargs.copy()
        layer_kwargs["nullable"] = True
        self.layer_select = ComboBox(
            choices=choices, tooltip=layer_tooltip, **layer_kwargs
        )
        self._nullable = True
        kwargs["widgets"] = [self.size_spin, self.layer_select]
        kwargs["labels"] = False
        kwargs["layout"] = "horizontal"
        kwargs.pop("value")
        kwargs.pop("nullable")
        super().__init__(**kwargs)
        self.margins = (0, 0, 0, 0)

    @property
    def value(self) -> tuple[int, str]:
        return (self.size_spin.value, self.layer_select.value)

    @value.setter
    def value(self, v: tuple[int, str]) -> None:
        self.size_spin.value = v[0]
        self.layer_select.value = v[1]


class MutableOutputWidget(Container):
    """
    A ComboBox widget combined with a button that creates new layers.
    Made for preallocated output creation convenience.
    """

    """
    Default constructor

    :param choices: determines how the ComboBox choices are populated
    :param nullable: iff true allows no selection as an option
    :param kwargs: other args
    """

    def __init__(
        self,
        choices: ChoicesType = get_layers,
        nullable=False,
        **kwargs,
    ):
        value = kwargs.pop("value", None)
        if value is None:
            value = ""

        layer_tooltip = (
            "Optional - produces a new layer unless an output container is provided"
        )
        self.layer_select = ComboBox(
            choices=choices, nullable=nullable, tooltip=layer_tooltip, **kwargs
        )
        self.new_btn = PushButton(text="New", tooltip="Create a new output container")
        self.new_btn.max_width = 53
        self._nullable = nullable
        kwargs["widgets"] = [self.layer_select, self.new_btn]
        kwargs["labels"] = False
        kwargs["layout"] = "horizontal"
        super().__init__(**kwargs)
        self.margins = (0, 0, 0, 0)
        self.new_btn.changed.disconnect()
        self.new_btn.changed.connect(self.create_new_image)

    @property
    def _btn_text(self) -> str:
        return "New Image"

    def _default_layer(self) -> Optional[Layer]:
        """
        This widget sets the default size, shape etc. to be the same as
        the (first) input. We find the (first) input in this function.
        """
        # Attempt to guess a good size based off of the first image input
        for widget in self.parent:
            if widget is self:
                continue
            if isinstance(widget, ComboBox) and issubclass(widget.annotation, Layer):
                selection_name = widget.current_choice
                if selection_name != "":
                    return current_viewer().layers[selection_name]
        return None

    def _default_new_shape(self) -> Sequence[tuple[int, str]]:
        guess = self._default_layer()
        if guess:
            data = guess.data
            # xarray has dims, otherwise use conventions
            if hasattr(data, "dims"):
                dims = data.dims
            # Special case: RGB
            elif isinstance(guess, Image) and guess.rgb:
                dims = list(CONVENTIONAL_DIMS[len(data.shape) - 1])
                dims.append("C")
            else:
                dims = list(CONVENTIONAL_DIMS[len(data.shape)])
            return [t for t in zip(data.shape, dims)]
        return [(512, "Y"), (512, "X")]

    def _default_new_type(self) -> str:
        """
        Returns the NAME of the default type choice
        """
        guess = self._default_layer()
        if guess:
            return str(guess.data.dtype)
        # fallback - good ol' float64
        return "float64"

    def _dtype_choices(self) -> List:
        return [dtype(v) for v in set(_imglib2_types.values())]

    def create_new_image(self) -> None:
        """
        Creates a dialog to add an image to viewer.


        Parameters
        ----------
        viewer : napari.components.ViewerModel
            Napari viewer containing the rendered scene, layers, and controls.
        """

        # Array types that are always included
        backing_choices = ["xarray", "NumPy"]
        # Array types that may be present
        if importlib.util.find_spec("zarr"):
            backing_choices.append("Zarr")

        # Define the magicgui widget for parameter harvesting
        params = request_values(
            title="New Image",
            name=dict(
                annotation=str,
                value="",
                options=dict(tooltip="If blank, a name will be generated"),
            ),
            shape=dict(
                annotation=List[MutableDimWidget],
                value=self._default_new_shape(),
                options=dict(
                    layout="vertical",
                    options=dict(
                        widget_type=MutableDimWidget,
                    ),
                    tooltip="The size of each image axis",
                ),
            ),
            array_type=dict(
                annotation=str,
                value="xarray",
                options=dict(
                    tooltip="The backing data array implementation",
                    choices=backing_choices,
                ),
            ),
            data_type=dict(
                annotation=type,
                value=self._default_new_type(),
                options=dict(
                    tooltip="The image element type",
                    choices=dict(
                        choices=self._dtype_choices(),
                        key=str,
                    ),
                ),
            ),
            fill_value=dict(
                annotation=float,
                value=0.0,
                options=dict(tooltip="Starting value for all pixels"),
            ),
        )
        self._add_new_image(params)

    def _add_new_image(self, params: dict):
        if params is None:
            return

        if params["array_type"] == "NumPy":
            import numpy as np

            data = np.full(
                shape=tuple(p[0] for p in params["shape"]),
                fill_value=params["fill_value"],
                dtype=params["data_type"],
            )

        elif params["array_type"] == "Zarr":
            # This choice is only available if we can import
            import zarr

            data = zarr.full(
                shape=tuple(p[0] for p in params["shape"]),
                fill_value=params["fill_value"],
                dtype=params["data_type"],
            )

        elif params["array_type"] == "xarray":
            # This choice is only available if we can import
            import numpy as np
            import xarray

            data = xarray.DataArray(
                data=np.full(
                    shape=tuple(p[0] for p in params["shape"]),
                    fill_value=params["fill_value"],
                    dtype=params["data_type"],
                ),
                dims=tuple(p[1] for p in params["shape"]),
            )

        # give the data array to the viewer.
        # Replace blank names with None so the Image class generates a name
        layer = current_viewer().add_image(
            name=params["name"] if len(params["name"]) else None,
            data=data,
        )

        # Find the "oldest" magicgui ancestor, and reset choices.
        # This allows the new layer to propagate to children.
        mgui = self
        while hasattr(mgui.parent, "_magic_widget"):
            mgui = mgui.parent._magic_widget
        mgui.reset_choices()
        # Specifically for this widget, set this selection
        # to the newly created layer.
        # This is almost definitely what the user wants!
        self.value = layer

    @property
    def value(self) -> Any:
        """Return current value of the widget.  This may be interpreted by backends."""
        return self.layer_select.value

    @value.setter
    def value(self, value: Any):
        self.layer_select.value = value

    # -- CategoricalWidget functions -- #

    @property
    def value(self):
        """Return current value of the widget."""
        return self.layer_select.value

    @value.setter
    def value(self, value):
        self.layer_select.value = value

    @property
    def options(self) -> dict:
        return self.layer_select.options

    def reset_choices(self, *_: Any):
        """Reset choices to the default state.

        If self._default_choices is a callable, this may NOT be the exact same set of
        choices as when the widget was instantiated, if the callable relies on external
        state.
        """
        self.layer_select.reset_choices()

    @property
    def current_choice(self) -> str:
        """Return the text of the currently selected choice."""
        return self.layer_select.current_choice

    def __len__(self) -> int:
        """Return the number of choices."""
        return self.layer_select.__len__()

    def get_choice(self, choice_name: str):
        """Get data for the provided ``choice_name``."""
        return self.layer_select.get_choice(choice_name)

    def set_choice(self, choice_name: str, data: Any = None):
        """Set data for the provided ``choice_name``."""
        return self.layer_select.set_choice(choice_name, data)

    def del_choice(self, choice_name: str):
        """Delete the provided ``choice_name`` and associated data."""
        return self.layer_select.del_choice(choice_name)

    @property
    def choices(self):
        """Available value choices for this widget."""
        return self.layer_select.choices

    @choices.setter
    def choices(self, choices: ChoicesType):
        self.layer_select.choices = choices


# -- FILE WIDGETS -- #


def file_widget_for(item: "jc.ModuleItem"):
    style: str = item.getWidgetStyle()
    if style == jc.FileWidget.OPEN_STYLE:
        return OpenFileWidget
    elif style == jc.FileWidget.SAVE_STYLE:
        return SaveFileWidget
    elif style == jc.FileWidget.DIRECTORY_STYLE:
        return DirectoryWidget


class SaveFileWidget(FileEdit):
    """
    A magicgui FileEdit matching SciJava's FileWidget.SAVE_STYLE
    """

    def __init__(self, **kwargs):
        kwargs["mode"] = "w"
        super().__init__(**kwargs)


class OpenFileWidget(FileEdit):
    """
    A magicgui FileEdit matching SciJava's FileWidget.OPEN_STYLE
    """

    def __init__(self, **kwargs):
        kwargs["mode"] = "r"
        super().__init__(**kwargs)


class DirectoryWidget(FileEdit):
    """
    A magicgui FileEdit matching SciJava's FileWidget.DIRECTORY_STYLE
    """

    def __init__(self, **kwargs):
        kwargs["mode"] = "d"
        super().__init__(**kwargs)


# -- SHAPE WIDGETS -- #


@dataclass
class ShapeParameter:
    """
    Describes one input to a Shape implementation,
    and how that input should be obtained
    """

    # The name of the parameter
    name: str
    # The magicgui Widget type used to harvest this input
    widget_type: Widget
    # The parameter's corresponding Java class
    j_type: JClass = None
    # The starting value for widget_type
    default: Any = None


@dataclass
class ShapeData:
    """Describes the data necessary to contruct a Shape implementation"""

    # The user-facing name of the shape implementation
    name: str
    # The implementation's Java class
    j_class: JClass
    # The constructor parameters
    params: List[ShapeParameter]


class ShapeWidget(Container):
    """
    Widget used to obtain a net.imglib2.algorithm.neighborhood.Shape.
    """

    def __init__(
        self,
        choices: ChoicesType = None,
        nullable=False,
        **kwargs,
    ):
        # Remove the value kwarg - it shouldn't be passed on
        kwargs.pop("value", None)
        # Set choices as the names of all known Shape implementations
        if choices is None:
            choices = list(self.shape_types.keys())
        # Create a ComboBox with the impl names as options
        self.shape_select = ComboBox(choices=choices, nullable=nullable, **kwargs)
        # Create a container to house the pararm widgets for the selected impl
        self.shape_options = Container()
        # Form this widget
        kwargs["widgets"] = [self.shape_select, self.shape_options]
        kwargs["labels"] = False
        kwargs["layout"] = "horizontal"
        super().__init__(**kwargs)
        # Set the default to the first impl
        self._update_options(choices[0])
        # Connect impl selection to param updates
        self.shape_select.changed.connect(self._update_options)

    def _update_options(self, choice):
        """
        Updates the Shape parameter Container with the relevant
        parameter widgets for the selected impl
        :param choice: The selected impl
        """
        # Clear out old widgets
        self.shape_options.clear()
        # Add new widgets
        for p in self.shape_types[choice].params:
            # If the parameter has a default, use it
            if p.default:
                wdgt = p.widget_type(name=p.name, value=p.default)
            else:
                wdgt = p.widget_type(name=p.name)
            # Add widget to container
            self.shape_options.append(wdgt)

    def _param(self, i, p: ShapeParameter):
        """
        Convenience function for obtaining the ith parameter
        from the parameter container.
        Will convert to the parameter type if defined.
        :param i: the parameter index
        :param p: the parameter Dataclass
        """
        wdgt = self.shape_options[i]
        if p.j_type:
            return p.j_type(wdgt.value)
        return wdgt.value

    @property
    def value(self) -> Any:
        """
        Returns the value of this widget, namely a JAVA Shape.
        Constructed on demand.
        """
        choice = self.shape_types[self.shape_select.value]
        cls = choice.j_class
        params = [self._param(i, p) for i, p in enumerate(choice.params)]
        return cls(*params)

    @property
    def shape_types(self) -> Dict[str, ShapeData]:
        """
        Defines the Shape implementations supported by this widget.
        """
        types = [
            ShapeData(
                "Centered Rectangle",
                jc.CenteredRectangleShape,
                [
                    ShapeParameter("span", ListEdit, JArray(JInt), default=[1, 1]),
                    ShapeParameter("skipCenter", CheckBox),
                ],
            ),
            ShapeData(
                "Diamond",
                jc.DiamondShape,
                [
                    ShapeParameter("radius", SpinBox, default=1),
                ],
            ),
            ShapeData(
                "Diamond Tips",
                jc.DiamondTipsShape,
                [
                    ShapeParameter("radius", SpinBox, default=1),
                ],
            ),
            ShapeData(
                "Horizontal Line",
                jc.HorizontalLineShape,
                [
                    ShapeParameter("span", SpinBox, JLong, default=1),
                    ShapeParameter("dimension", SpinBox, JInt, default=0),
                    ShapeParameter("skip center", CheckBox),
                ],
            ),
            ShapeData(
                "Hypersphere",
                jc.HyperSphereShape,
                [
                    ShapeParameter("radius", SpinBox, JLong, default=1),
                ],
            ),
            ShapeData(
                "Pair of Points",
                jc.PairOfPointsShape,
                [
                    ShapeParameter("offset", ListEdit, JArray(JLong), default=[1, 1]),
                ],
            ),
            ShapeData(
                "Periodic Line",
                jc.PeriodicLineShape,
                [
                    ShapeParameter("span", SpinBox, JLong, default=1),
                    ShapeParameter(
                        "increments", ListEdit, JArray(JInt), default=[1, 1]
                    ),
                ],
            ),
            ShapeData(
                "Rectangle",
                jc.RectangleShape,
                [
                    ShapeParameter("span", SpinBox, JInt, default=1),
                    ShapeParameter("skip center", CheckBox),
                ],
            ),
        ]
        return {c.name: c for c in types}
