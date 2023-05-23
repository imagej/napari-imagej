Tracking HeLa cell nuclei with TrackMate
========================================

The `TrackMate`_ plugin for ImageJ2 provides a streamlined interface for object tracking. 
This use case demonstrates how you can use napari-imagej to run the TrackMate plugin on 3D data **(X, Y, Time)** view the results with napari and
also process them with the `napari-stracking`_ plugin.

For this use case we will analyze live cell wide-field microscopy data of HeLa cell nuclei (Hoechst stain), imaged every 30 minutes for 40 frames.
The data used in this use case is available in the `napari-imagej repository`_ on GitHub.

.. image:: https://media.imagej.net/napari-imagej/trackmate_0.gif
    :align: center

|

TrackMate plugin Setup
----------------------

By default, napari-imagej does not include Fiji *or* TrackMate. To use the TrackMate plugin, we must first configure napari-imagej to enable TrackMate access.

We can configure napari-imagej to use a Fiji installation by opening the settings dialog and changing the ``ImageJ directory or endpoint`` (described `here <../Configuration.html#imagej-directory-or-endpoint>`_). This example was created using an endpoint of ``sc.fiji:fiji:2.13.1``.

.. figure:: https://media.imagej.net/napari-imagej/settings_fiji.png

    Configuring napari-imagej to use Fiji instead of pure ImageJ2. With Fiji, we gain access to many popular plugins, including TrackMate.

**Note that napari must be restarted for these changes to take effect!**

Preparing the Data
------------------

.. |ImageJ2| image:: ../../src/napari_imagej/resources/imagej2-16x16-flat.png

Once napari is running again, activate the napari-imagej plugin by selecting the ``ImageJ2`` plugin from the Plugins menu.

To run TrackMate, we first need data. TrackMate will only work on image data that are open in the ImageJ UI. napari-imagej provides two pathways for you to open data within the ImageJ UI:

Opening Data in ImageJ
^^^^^^^^^^^^^^^^^^^^^^

If the sample image is not yet in napari, it is easiest to open it in ImageJ directly. Press |ImageJ2| in the napari-imagej menu to launch the ImageJ UI, and then locate the  ``File>Open File(s)...`` menu option to open the image. With the sample image open, you are now ready to `run Trackmate <./trackmate.html#nuclei-tracking>`_.

Transferring Data from napari
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you already have data open in napari, you can transfer data to the ImageJ UI by utilizing the transfer buttons in the napari-imagej menu to transfer the active (highlighted in blue) napari layer.

.. figure:: https://media.imagej.net/napari-imagej/trackmate_1.gif

    Images open in napari can be easily transferred to the ImageJ UI with the transfer buttons.

Internally, napari does not utilize image dimension labels (*i.e.* ``X``, ``Y``, *etc...*) and instead assumes that the *n*-dimensional arrays (*i.e* images) conform to the `scikit-image dimension order`_ convention.
ImageJ2 however *does* care about dimension labels and uses them to define certain operations. In this case, ImageJ2 assumes the first two dimensions are *always* ``X`` and ``Y``. The third dimension in this use case is ``Time``, but
if we examine the transferred image's properties we will discover that ImageJ2 has confused the ``Time`` dimension with ``Channel``. Here it thinks our data has 40 channels. The reason this happens is because ImageJ2 has no
information about what the third dimension should be. When an image is opened directly with ImageJ2, the image reader will read the dimension order in the metadata of the image file (if its present) and apply the correct
dimensions order to the image. When ImageJ2 has no information on the dimension order (*e.g.* when we transfer a napari image to ImageJ) then the ``(X, Y, C, Z, T)`` dimension order is applied. Taking this into account we can see why
the transferred image in imagej has 40 channels instead of frames.

Furthermore, this sample image has calibrated axes. If the image is opened in ImageJ that metadata is preserved. But when we open the image with the basic napari opener we lose the calibration information, which is simply populated as "1 pixel" in each axis when transferred to ImageJ. TrackMate **does** care about calibrations, so this needs to be fixed as well.

Thankfully we can fix both issues in the same place. Simply right-click on the open image in the ImageJ UI and select ``Properties...`` (or use the shortcut ``CTRL+SHIFT+P``). In the properties window change the value in the ``Channels`` field to `1` and the ``Frames`` field to `40`. Then change the ``Pixel width`` to `0.325` with unit `micron`, the ``Pixel height`` to `0.325`, and the ``Voxel depth`` to `1`.
When your ``Properties`` menu looks like this, click ``Ok`` to apply the change:

.. figure:: https://media.imagej.net/napari-imagej/trackmate_adjust_props.png

    Reshape the image dimensions by swapping the number of *channels* with the number of *frames*; add calibration information

TrackMate will now process this image data correctly. Without these changes, TrackMate thinks the data has only one time point and 40 channels. Instead of tracking across time it only provides a detection for a single frame
across 40 channels, and our object diameters would be too small.

Nuclei tracking
-----------------------

Running TrackMate
^^^^^^^^^^^^^^^^^

**Note:** if you haven't started the ImageJ GUI yet, `do so now <../Initialization.html#starting-the-imagej-gui>`_. You *can* search for TrackMate in the napari-imagej search bar, but it will just tell you to open the ImageJ GUI.

Once your image data is open and has the correct dimension order and calibration, start TrackMate by either searching in the ImageJ search bar or via the menu selection ``Plugins>Tracking>TrackMate``.

TrackMate opens as a wizard to guide you through the tracking process. Steps are advanced with the ``Next`` button, and you can always go back and adjust parameters to tune your tracks. For this example we actually do not need to do all steps of the wizard - just those up through selecting and applying a tracker.
Using the sample data, we used the following properties of these wizard steps:

- **Target image: trackmate_example_data**
    - *No changes*
- **Select a detector**
    - LoG detector
- **LoG detector**
    - *Estimated object diameter*: 17 micron
    - *Quality threshold*: 0
    - *Pre-process with media filter*: Yes (checked)
    - *Sub-pixel localization*: Yes (checked)
- **Initial thresholding**
    - Selected all spots
- **Set filters on spots**
    - *No changes*
- **Select a tracker**
    - Simple LAP tracker
- **Simple LAP tracker**
    - *Linking max distance*: 8.3 micron
    - *Gap-closing max distance*: 5.0 micron
    - *Gap-closing max frame gap*: 2

Once the spots and tracks have been generated, you can return to napari and use the left napari-imagej transfer button to transfer the image data and the tracks back to napari.

.. figure:: https://media.imagej.net/napari-imagej/trackmate_tracks_imported.png

    Transferring TrackMate results back to napari converts TrackMate's tracks into napari tracks and TrackMate's spots/detections into napari labels.

Processing tracks with napari-stracking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While the `napari-stracking`_ plugin is capable of performing its own particle tracking, it also comes with some track processing tools.
To use napari-stracking, install the plugin from ``Install/Uninstall Plugins...`` menu in napari. After transferring TrackMate's tracks and spots to napari select the kind of track
processing you want from the napari-stracking plugin menu.

In this example, we can use napari-stracking to measure the **length** and **distance** of the tracks generated from TrackMate:

.. figure:: https://media.imagej.net/napari-imagej/trackmate_4.gif

|

You can also filter tracks. Here we filter for tracks that exist in all 40 frames:

.. figure:: https://media.imagej.net/napari-imagej/trackmate_5.gif

.. _TrackMate: https://imagej.net/plugins/trackmate
.. _napari-imagej repository: https://media.imagej.net/napari-imagej/trackmate_example_data.tif
.. _napari-stracking: https://www.napari-hub.org/plugins/napari-stracking
.. _scikit-image dimension order: https://scikit-image.org/docs/stable/user_guide/numpy_images.html#a-note-on-the-time-dimension
