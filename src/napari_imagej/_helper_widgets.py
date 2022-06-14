from enum import Enum
import os
from pathlib import Path
from typing import Any, List, Sequence
from magicgui import magicgui
from magicgui.types import FileDialogMode, PathLike, ChoicesType
from magicgui.widgets import Container, ComboBox, PushButton
from napari.utils._magicgui import get_layers, find_viewer_ancestor

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
        
        self.line_edit = ComboBox(choices=choices,**kwargs)
        self.choose_btn = PushButton(text="New Image")
        self._nullable = nullable
        kwargs["widgets"] = [self.line_edit, self.choose_btn]
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
            NumPy = 'NumPy'
            Zarr = 'Zarr'

        # Define the magicgui widget for parameter harvesting
        @magicgui(
            call_button="Create",
            name={'tooltip': "If blank, a name will be generated"},
            dimensions={'tooltip': "The size of the new image"},
            array_type={'tooltip': "The backing data array implementation"},
            fill_value={'tooltip': "Starting value for all pixels"},
        )
        def _new_image_widget(
            name: str = "",
            dimensions: List[int] = [512, 512],
            array_type: BackingData = BackingData.NumPy,
            fill_value: float = 0.0,
        ) -> None:

            if array_type is BackingData.NumPy:
                import numpy as np

                data = np.full(tuple(dimensions), fill_value)

            elif array_type is BackingData.Zarr:
                # Zarr is not shipped by default, but we can try to support it
                import zarr

                data = zarr.full(dimensions, fill_value)

            # give the data array to the viewer.
            # Replace blank names with None so the Image class generates a name
            find_viewer_ancestor(self.native).add_image(
                name=name if len(name) else None,
                data=data,
            )

        # Once called (i.e. "Create"  is clicked), the widget will be destroyed
        # This means one click of "New image layer" will produce exactly one image,
        # Which is consistent with the other new layer buttons.
        _new_image_widget.called.connect(_new_image_widget.close)
        # _new_image_widget.native.setParent(viewer.window._qt_window)

        # Show the widget (as a modal dialog, outside of the napari window)
        _new_image_widget.show()

    @property
    def value(self) -> tuple[Path, ...] | Path | None:
        """Return current value of the widget.  This may be interpreted by backends."""
        text = self.line_edit.value
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
        self.line_edit.value = value

    def __repr__(self) -> str:
        """Return string representation."""
        return f"FileEdit(mode={self.mode.value!r}, value={self.value!r})"

    # -- CategoricalWidget functions -- #

    @property
    def value(self):
        """Return current value of the widget."""
        return self.line_edit.value

    @value.setter
    def value(self, value):
        self.line_edit.value = value

    @property
    def options(self) -> dict:
        return self.line_edit.options

    def reset_choices(self, *_: Any):
        """Reset choices to the default state.

        If self._default_choices is a callable, this may NOT be the exact same set of
        choices as when the widget was instantiated, if the callable relies on external
        state.
        """
        self.line_edit.reset_choices()

    @property
    def current_choice(self) -> str:
        """Return the text of the currently selected choice."""
        return self.line_edit.current_choice

    def __len__(self) -> int:
        """Return the number of choices."""
        return self.line_edit.__len__()

    def get_choice(self, choice_name: str):
        """Get data for the provided ``choice_name``."""
        return self.line_edit.get_choice(choice_name)

    def set_choice(self, choice_name: str, data: Any = None):
        """Set data for the provided ``choice_name``."""
        return self.line_edit.set_choice(choice_name, data)

    def del_choice(self, choice_name: str):
        """Delete the provided ``choice_name`` and associated data."""
        return self.line_edit.del_choice(choice_name)

    @property
    def choices(self):
        """Available value choices for this widget."""
        return self.line_edit.choices

    @choices.setter
    def choices(self, choices: ChoicesType):
        self.line_edit.choices = choices
