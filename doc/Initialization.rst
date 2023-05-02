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

.. _Fiji: https://imagej.net/software/fiji/
.. _ImageJ2: https://imagej.net/software/imagej2/
.. _napari: https://napari.org
