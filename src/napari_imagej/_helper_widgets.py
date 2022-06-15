import os
from enum import Enum
from pathlib import Path
from typing import Any, List, Sequence

from magicgui.types import ChoicesType, FileDialogMode, PathLike
from magicgui.widgets import ComboBox, Container, PushButton, request_values
from napari import current_viewer
from napari.utils._magicgui import get_layers


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

        self.layer_select = ComboBox(choices=choices, **kwargs)
        self.choose_btn = PushButton(text="New")
        self._nullable = nullable
        kwargs["widgets"] = [self.choose_btn, self.layer_select]
        kwargs["labels"] = False
        kwargs["layout"] = "horizontal"
        super().__init__(**kwargs)
        self.margins = (0, 0, 0, 0)
        self.choose_btn.changed.disconnect()
        self.choose_btn.changed.connect(self._spawn_new_image_widget)

    @property
    def _btn_text(self) -> str:
        return "New Image"

    def _spawn_new_image_widget(self) -> None:
        """
        Creates a dialog to add an image to viewer.


        Parameters
        ----------
        viewer : napari.components.ViewerModel
            Napari viewer containing the rendered scene, layers, and controls.
        """

        # Define an enum for array type selection
        class BackingData(Enum):
            NumPy = "NumPy"
            Zarr = "Zarr"

        # Define the magicgui widget for parameter harvesting
        params = request_values(
            title="New Image",
            name=dict(
                annotation=str,
                value="",
                options=dict(tooltip="If blank, a name will be generated"),
            ),
            dimensions=dict(
                annotation=List[int],
                value=[512, 512],
                options=dict(tooltip="The starting size of the new image"),
            ),
            array_type=dict(
                annotation=BackingData,
                value=BackingData.NumPy,
                options=dict(tooltip="The backing data array implementation"),
            ),
            fill_value=dict(
                annotation=float,
                value=0.0,
                options=dict(tooltip="Starting value for all pixels"),
            ),
        )
        if params is not None:
            if params["array_type"] is BackingData.NumPy:
                import numpy as np

                data = np.full(tuple(params["dimensions"]), params["fill_value"])

            elif params["array_type"] is BackingData.Zarr:
                # Zarr is not shipped by default, but we can try to support it
                import zarr

                data = zarr.full(params["dimensions"], params["fill_value"])

            # give the data array to the viewer.
            # Replace blank names with None so the Image class generates a name
            current_viewer().add_image(
                name=params["name"] if len(params["name"]) else None,
                data=data,
            )

    @property
    def value(self) -> tuple[Path, ...] | Path | None:
        """Return current value of the widget.  This may be interpreted by backends."""
        text = self.layer_select.value
        if self._nullable and not text:
            return None
        if self.mode is FileDialogMode.EXISTING_FILES:
            return tuple(Path(p) for p in text.split(", ") if p.strip())
        return Path(text)

    @value.setter
    def value(self, value: Sequence[PathLike] | PathLike | None):
        """Set current file path."""
        if value is None and self._nullable:
            value = ""
        elif isinstance(value, (list, tuple)):
            value = ", ".join(os.fspath(Path(p).expanduser().absolute()) for p in value)
        elif isinstance(value, (str, Path)):
            value = os.fspath(Path(value).expanduser().absolute())
        else:
            raise TypeError(
                f"value must be a string, or list/tuple of strings, got {type(value)}"
            )
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
