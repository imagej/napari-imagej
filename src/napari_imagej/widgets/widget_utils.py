from magicgui import magicgui
from qtpy.QtCore import Signal

from napari_imagej.java import ij, jc
from napari_imagej.utilities._module_utils import (
    execute_function_modally,
    functionify_module_execution,
    info_for,
)
from napari_imagej.utilities.logging import log_debug


def python_actions_for(result: "jc.SearchResult", output_signal: Signal):
    actions = []
    # Iterate over all available python actions
    searchService = ij().get("org.scijava.search.SearchService")
    for action in searchService.actions(result):
        action_name = str(action.toString())
        # Add buttons for the java action
        if action_name == "Run":
            actions.extend(_run_actions_for(result, output_signal))
        else:
            actions.append((action_name, action.run))
    return actions


def _run_actions_for(result: "jc.SearchResult", output_signal: Signal):
    def execute_result(modal: bool):
        """Helper function to perform module execution."""
        log_debug("Creating module...")

        name = str(result.name())
        moduleInfo = info_for(result)
        if not moduleInfo:
            log_debug(f"Search Result {result} cannot be run!")
            return []

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
