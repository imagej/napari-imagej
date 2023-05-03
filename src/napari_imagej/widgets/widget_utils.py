from magicgui import magicgui
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QMessageBox, QWidget

from napari_imagej.java import ij, jc
from napari_imagej.utilities._module_utils import (
    execute_function_modally,
    functionify_module_execution,
    info_for,
)
from napari_imagej.utilities.logging import log_debug


def python_actions_for(
    result: "jc.SearchResult", output_signal: Signal, parent_widget: QWidget = None
):
    actions = []
    # Iterate over all available python actions
    searchService = ij().get("org.scijava.search.SearchService")
    for action in searchService.actions(result):
        action_name = str(action.toString())
        # Add buttons for the java action
        if action_name == "Run":
            actions.extend(_run_actions_for(result, output_signal, parent_widget))
        else:
            actions.append((action_name, action.run))
    return actions


def _run_actions_for(
    result: "jc.SearchResult", output_signal: Signal, parent_widget: QWidget
):
    def execute_result(modal: bool):
        """Helper function to perform module execution."""
        log_debug("Creating module...")

        name = str(result.name())
        moduleInfo = info_for(result)
        if not moduleInfo:
            log_debug(f"Search Result {result} cannot be run!")
            return []

        if (
            ij().legacy
            and ij().legacy.isActive()
            and isinstance(moduleInfo, jc.LegacyCommandInfo)
        ):
            reply = QMessageBox.question(
                parent_widget,
                "Warning: ImageJ PlugIn",
                (
                    f'"{name}" is an original ImageJ PlugIn "\
                        "and should be run from the ImageJ UI. " \
                    "Would you like to launch the ImageJ UI?'
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                ij().ui().showUI()
            return

        module = ij().module().createModule(moduleInfo)

        # preprocess using napari GUI
        func, param_options = functionify_module_execution(
            lambda o: output_signal.emit(o),
            module,
            moduleInfo,
        )
        if modal:
            execute_function_modally(
                name=name,
                func=func,
                param_options=param_options,
            )
        else:
            widget = magicgui(function=func, **param_options)
            widget.name = name
            output_signal.emit(widget)

    run_actions = [
        ("Run", lambda: execute_result(modal=True)),
        ("Widget", lambda: execute_result(modal=False)),
    ]

    return run_actions
