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

By default, napari-imagej does not inlcude Fiji *or* TrackMate. To use the TrackMate plugin, we must first configure napari-imagej to enable TrackMate access.

We can configure napari-imagej to use a Fiji installation by opening the settings dialog and changing ``imagej distribution_or_endpoint`` (described `here <../Configuration.html#imagej-directory-or-endpoint>`_) to ``sc.fiji:fiji``.

.. figure:: https://media.imagej.net/napari-imagej/use_fiji.gif

    Configuring napari-imagej to use Fiji instead of pure ImageJ2. With Fiji, we gain access to many popular plugins, including TrackMate.

**Note that napari must be restarted for these changes to take effect!**

Preparing the Data
------------------

.. |ImageJ2| image:: ../../src/napari_imagej/resources/imagej2-16x16-flat.png

Once napari is running again, activate the napari-imagej plugin by selecting the ``ImageJ2`` plugin from the Plugins menu.

To run TrackMate, we first need data. TrackMate will only work on image data that are open in the ImageJ UI. napari-imagej provides two pathways for you to open data within the ImageJ UI:

Opening Data in ImageJ
^^^^^^^^^^^^^^^^^^^^^^

If your data is not yet in napari, it is easiest to open it in ImageJ directly. Press |ImageJ2| in the napari-imagej menu to launch the ImageJ UI, and then locate the  ``File>Open File(s)...`` menu option to open your data. With your data open, you are now ready to `run Trackmate <./trackmate.html#nuclei-tracking>`_.

Transferring Data from napari
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you already have data open in napari, you can transfer data to the ImageJ UI by utilizing the transfer buttons in the napari-imagej menu to transfer the active (highlighted in blue) napari layer.

<<<<<<< HEAD

..  We might want to consider a better gif here later, ESPECIALLY if we link users to some example data.
.. figure:: https://media.imagej.net/napari-imagej/trackmate_1.gif
=======
.. figure:: https://media.imagej.net/napari-imagej/trackmate_1.gif
>>>>>>> 278ce85 (Replace virus tracking TrackMate example)

    Images open in napari can be easily transferred to the ImageJ UI with the transfer buttons.

Internally, napari does not utilize image dimension labels (*i.e.* ``X``, ``Y``, *etc...*) and instead assumes that the *n*-dimensional arrays (*i.e* images) conform to the `scikit-image dimension order`_ convention.
ImageJ2 however *does* care about dimension labels and uses them to define certain operations. In this case, ImageJ2 assumes the first two dimensions are *always* ``X`` and ``Y``. The third dimension in this use case is ``Time``, but
if we examine the transferred image's properties we will discover that ImageJ2 has confused the ``Time`` dimension with ``Channel``. Here it thinks our data has 40 channels. The reason this happens is because ImageJ2 has no
information about what the third dimension should be. When an image is opened directly with ImageJ2, the image reader will read the dimension order in the metadata of the image file (if its present) and apply the correct
dimensions order to the image. When ImageJ2 has no information on the dimension order (*e.g.* when we transfer a napari image to ImageJ) then the ``(X, Y, C, Z, T)`` dimension order is applied. Taking this into account we can see why
the transferred image in imagej has 40 channels instead of frames.

To fix this, simply right click (or ``CTRL+SHIFT+P``) on the open image in the ImageJ UI and select ``Properties...``. In the properties window change the value in the ``Channels`` field to 1 and the ``Frames`` field to 40 (or however many frames your data has).
Click ``Ok`` to apply the change. TrackMate will now process this image data correctly. Without this change, TrackMate thinks the data has only one time point and 40 channels. Instead of tracking across time it only provides a detection for a single frame
across 40 channels.

.. figure:: https://media.imagej.net/napari-imagej/trackmate_2.gif

    Reshape the image dimensions by swapping the number of *channels* with the number of *frames*.

Nuclei tracking
-----------------------

Running TrackMate
^^^^^^^^^^^^^^^^^

**Note:** if you haven't started the ImageJ GUI yet, `do so now <../Initialization.html#starting-the-imagej-gui>`_. You *can* search for TrackMate in the napari-imagej search bar, but it will just tell you to open the ImageJ GUI.

Once your image data is open and has the correct dimension order, start TrackMate by either searching in the ImageJ search bar or via the menu selection ``Plugins>Tracking>TrackMate``.

Once TrackMate has loaded, walk
through the TrackMate tracking options to generate tracks. Using the sample data, we used the following settings for successful tracking:

- **Detector**: LoG (Laplacian of Gaussian) detector
    - *Estimated object diameter*: 50 pixels
    - *Quality threshold*: 0
    - *Pre-process with media filter*: Yes
    - *sub-pixel localization*: Yes
- **Initial thresholding**: Select all spots
- **Tracker**: Simple LAP tracker
    - *Linking max distance*: 25.0 pixels
    - *Gap-closing max distance*: 15.0 pixels
    - *Gap-closing max frame gap*: 2

Once the tracks and spots have been generated use left napari-imagej transfer button to transfer the image data and the tracks back to napari.

.. figure:: https://media.imagej.net/napari-imagej/trackmate_3.gif

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
