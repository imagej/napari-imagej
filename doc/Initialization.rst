==============
Initialization
==============

This document assumes familiarity with napari_.

Starting napari-imagej
----------------------

With napari running, napari-imagej can be found through ``Plugins->ImageJ2 (napari-imagej)``. If you don't see this menu option, return to the 
`installation guide <./Install.html>`_ and ensure you are launching napari from a python environment with the napari-imagej plugin installed. If you're still having trouble, please see the `troubleshooting section <./Troubleshooting.html#napari-imagej-does-not-appear-in-the-plugins-menu-of-napari>`_.

Once triggered, napari-imagej will start up the JVM, and then the ImageJ2 gateway. This setup can take a few seconds, and is complete when the napari-imagej searchbar is cleared and enabled.

**On the first initialization, napari-imagej must download an ImageJ2 distribution. This download can take minutes, depdending on the user's bandwidth.**

.. figure:: https://media.imagej.net/napari-imagej/startup.gif

Once napari-imagej is fully initilized, you can see the `Use Cases <./Use_Cases.html>`_ page for examples of available functionality. Alternatively, if you're new to ImageJ, you may want to start with a `high-level overview <https://imagej.net/learn/>`_.

**Note**: napari-imagej always downloads the latest version of ImageJ2_, along with classic ImageJ functionality. To launch a *different* ImageJ2 distribution, such as Fiji_, please see the `Configuration <./Configuration.html>`_ page

Starting the ImageJ GUI
----------------------

While all ImageJ2 functionality should be accessible direclty through the napari-imagej widget, many original ImageJ functions require the ImageJ graphical user interface (GUI) to be visible.

If you try to run one of these commands through the napari-imagej search bar you will receive a message indicating the GUI is required, with an option to show it. Alternatively, at any point you can launch the ImageJ GUI via the GUI button in the napari-imagej menu.

.. figure:: https://media.imagej.net/napari-imagej/settings_gui_button.png
    
    The GUI is launched through the ImageJ button on the napari-imagej menu

If your ImageJ GUI button is greyed out, see the `troubleshooting section <./Troubleshooting.html#the-imagej2-gui-button-is-greyed-out>`_.

.. _Fiji: https://imagej.net/software/fiji/
.. _ImageJ2: https://imagej.net/software/imagej2/
.. _napari: https://napari.org
