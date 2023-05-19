=============
Configuration
=============

This document explains how to augment napari-imagej to configure available functionality.

We assume familiarity in launching napari-imagej. Please see `this page <./Initialization.html>`_ for more information on launching napari-imagej

Accessing napari-imagej settings
--------------------------------

As soon as you launch napari-imagej, you can access napari-imagej's configuration dialog by clicking on the gear in the napari-imagej menu:

.. figure:: https://media.imagej.net/napari-imagej/settings_wheel.png
    
    The configuration dialog is accessed through the gear button on the napari-imagej menu

Configuring settings
---------------------

Within this modal dialog are many different settings, many pertaining to the underlying ImageJ2 instance.

Note that many of these settings **pertain to the underlying ImageJ2 instance**, requiring a restart of napari to take effect.

*imagej directory or endpoint*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This setting allows users to provide a string identifying *which Java components* should be used to form the ImageJ2 instance. This line is passed directly to PyImageJ.

If you pass a **directory**, PyImageJ will look in that directory for *an existing ImageJ2 instance*.

If you pass one or more **components** in `Maven coordinate <https://maven.apache.org/pom.html#Maven_Coordinates>`_ form, PyImageJ will launch an ImageJ2 instance from those components, *downloading them if necessary*.

Below are a couple examples of ways to construct different ImageJ2 instances:

.. list-table:: endpoint options
    :header-rows: 1

    * - To use:
      - ``imagej directory or endpoint``
      - Reproducible?
    * - Newest available ImageJ2
      - ``net.imagej:imagej``
      - NO
    * - Specific version of ImageJ2
      - ``net.imagej:imagej:2.9.0``
      - YES
    * - Newest available Fiji
      - ``sc.fiji:fiji``
      - NO
    * - Newest available ImageJ2 PLUS Specific Plugins
      - ``net.imagej:imagej+net.preibisch:BigStitcher``
      - NO


*imagej base directory*
^^^^^^^^^^^^^^^^^^^^^^^^^

Path to the ImageJ base directory on your local machine. Defaults to the current working directory.

This directory is most commonly used for discovering SciJava scripts; ImageJ2 will search the provided directory for a `scripts` folder, automatically exposing any scripts within.

*include imagej legacy*
^^^^^^^^^^^^^^^^^^^^^^^^^

This button is used to declare whether original ImageJ functionality should be exposed.

If active, all original ImageJ functionality (ij.* packages) will be available, and the napari-imagej GUI button will launch the classic ImageJ user interface.

If disabled, only ImageJ2 functionality will be availabe, and the napari-imagej GUI button will launch the ImageJ2 user interface.

*jvm mode*
^^^^^^^^^^^^

Designates the mode of execution for ImageJ2.

Selecting ``headless`` prevents ImageJ ecosystem functionality from launching graphical components; the napari-imagej widget becomes the only way to interact with the ImageJ ecosystem.

Selecting ``interactive`` allows ImageJ ecosystem functionality to launch graphical components.

``interactive`` **mode is unavailable on MacOS**. More details can be found `here <https://pyimagej.readthedocs.io/en/latest/Initialization.html#interactive-mode>`_. If napari-imagej is launched on MacOS with this setting set to ``interactive``, the setting will silently be reassigned to ``headless``.

*use active layer*
^^^^^^^^^^^^^^^^^^^^

Defines which layer gets transferred when pressing the data transfer buttons in the napari-imagej menu.

If active, napari-imagej will transfer highlighted napari layers to ImageJ, and will transfer the currently selected Image window to napari. This choice aligns best with ImageJ2 ecosystem layer selection.

If inactive, napari-imagej will prompt the user with a modal dialog, asking for the name of the layer to transfer.

*jvm command line arguments*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Used to define command line arguments that should be passed to the JVM at startup.

One common use case for this feature is to increase the maximum heap space available to the JVM, as shown below:

.. figure:: https://media.imagej.net/napari-imagej/benchmarking_settings.png

    Specifying 32GB of memory available to ImageJ ecosystem routines in the JVM.


.. _Fiji: https://imagej.net/software/fiji/
.. _ImageJ2: https://imagej.net/software/imagej2/
.. _napari: https://napari.org
