# explore.py - Just some code to play around with the
# ImageJ2-provided function widgets programmatically.

import napari
from typing import Dict, Callable
from napari.plugins import plugin_manager as pm

# Discover the plugins.
pm.discover()
pm.discover_widgets()

# Grab the function widgets provided by napari-imagej.
wdgs: Dict[str, Callable] = pm._function_widgets['ImageJ2']

v = napari.Viewer()

# Pick a function widget.
name = next(iter(wdgs))

# Add it to the viewer window.
v.window._add_plugin_function_widget('ImageJ2', name)

# Dig down to the magicgui widget and go nuts from there.
dw = v.window._dock_widgets[f'ImageJ2: {name}']
qw = dw.widget()
mw = qw._magic_widget
