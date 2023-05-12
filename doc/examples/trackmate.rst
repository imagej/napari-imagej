Tracking HeLa cell nuclei with TrackMate
========================================

The `TrackMate`_ plugin for ImageJ2 provides a streamlined interface for object tracking. 
This use case demonstrates how you can use napari-imagej to run the TrackMate plugin on 3D data **(X, Y, Time)** view the results with napari and
also process them with the `napari-stracking`_ plugin.

For this use case we will analyze live cell wide-field microscopy data of HeLa cell nuclei (Hoechst stain), imaged every 30 minutes for 40 frames.
The data used in this use case is available in the `napari-imagej repository`_ on GitHub.

.. image:: ../doc-images/napari-imagej_trackmate_0.gif
    :align: center

|

TrackMate plugin Setup
----------------------

By default, napari-imagej does not inlcude Fiji *or* TrackMate. To use the TrackMate plugin, we must first configure napari-imagej to enable TrackMate access.

We can configure napari-imagej to use a Fiji installation by opening the settings dialog and changing ``imagej distribution_or_endpoint`` (described `here <../Configuration.html#imagej-directory-or-endpoint>`_) to ``sc.fiji:fiji``.

.. figure:: ../doc-images/napari-imagej_use_fiji.gif

    Configuring napari-imagej to use Fiji instead of pure ImageJ2. With Fiji, we gain access to many popular plugins, including TrackMate.

**Note that napari must be restarted for these changes to take effect!**

Launching TrackMate
-------------------

Once napari is running again, activate the napari-imagej plugin by selecting the ``ImageJ2`` plugin from the Plugins menu. Open the image data by dragging and dropping the file into the napari window or via ``File>Open File(s)...`` menu option.

TrackMate will only work on image data that are open in the ImageJ UI. You can transfer data from napari to the ImageJ UI by utilizing the transfer buttons in the napari-imagej menu to transfer the active
image layer. Alternatively the ImageJ UI could be called first by clicking the ImageJ2 button and opening the image data with the ImageJ UI (``File>Open...``). This approach would avoid the need to transfer the data from
napari to the ImageJ UI.

.. figure:: ../doc-images/napari-imagej_trackmate_1.gif

    Images open in napari can be easily transferred to the ImageJ UI with the transfer buttons.

Nuclei tracking
-----------------------

**Note**: If you transferred your image data from napari to the ImageJ UI with the transfer buttons, than an additional step is required to make the image data compatible with TrackMate.
If the data was opened with ImageJ then these steps are not necessary and you can proceed to `Running Trackmate <./trackmate.html#running-trackmate>`_.

Modifying image dimensions
^^^^^^^^^^^^^^^^^^^^^^^^^^

Internally, napari does not utilize image dimension labels (*i.e.* ``X``, ``Y``, *etc...*) and instead assumes that the *n*-dimensional arrays (*i.e* images) conform to the `scikit-image dimension order`_ convention.
ImageJ2 however *does* care about dimension labels and uses them to define certain operations. In this case, ImageJ2 assumes the first two dimensions are *always* ``X`` and ``Y``. The third dimension in this use case is ``Time``, but
if we examine the transferred image's properties we will discover that ImageJ2 has confused the ``Time`` dimension with ``Channel``. Here it thinks our data has 40 channels. The reason this happens is because ImageJ2 has no
information about what the third dimension should be. When an image is opened directly with ImageJ2, the image reader will read the dimension order in the metadata of the image file (if its present) and apply the correct
dimensions order to the image. When ImageJ2 has no information on the dimension order (*e.g.* when we transfer a napari image to ImageJ) then the ``(X, Y, C, Z, T)`` dimension order is applied. Taking this into account we can see why
the transferred image in imagej has 40 channels instead of frames.

To fix this, simply right click (or ``CTRL+SHIFT+P``) on the open image in the ImageJ UI and select ``Properties...``. In the properties window change the value in the ``Channels`` field to 1 and the ``Frames`` field to 40 (or however many frames your data has).
Click ``Ok`` to apply the change. TrackMate will now process this image data correctly. Without this change, TrackMate thinks the data has only one time point and 40 channels. Instead of tracking across time it only provides a detection for a single frame
across 40 channels.

.. figure:: ../doc-images/napari-imagej_trackmate_2.gif

    Reshape the image dimensions by swapping the number of *channels* with the number of *frames*.

Running TrackMate
^^^^^^^^^^^^^^^^^

Once your image data is open and has the correct dimension order start TrackMate by either searching in the napari-imagej search bar or via the ImageJ UI. Once TrackMate has loaded, walk
through the TrackMate tracking options to generate tracks. For this use case the following settings were used:

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

.. figure:: ../doc-images/napari-imagej_trackmate_3.gif

    Transferring TrackMate results back to napari converts TrackMate's tracks into napari tracks and TrackMate's spots/detections into napari labels.

Processing tracks with napari-stracking
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While the `napari-stracking`_ plugin is capable of performing its own particle tracking, it also comes with some track processing tools.
To use napari-stracking, install the plugin from ``Install/Uninstall Plugins...`` menu in napari. After transferring TrackMate's tracks and spots to napari select the kind of track
processing you want from the napari-stracking plugin menu.

In this example, we can use napari-stracking to measure the **length** and **distance** of the tracks generated from TrackMate:

.. figure:: ../doc-images/napari-imagej_trackmate_4.gif

|

You can also filter tracks. Here we filter for tracks that exist in all 40 frames:

.. figure:: ../doc-images/napari-imagej_trackmate_5.gif

.. _TrackMate: https://imagej.net/plugins/trackmate
.. _napari-imagej repository: https://github.com/imagej/napari-imagej/tree/main/doc/sample-data/trackmate_example_data.tif
.. _napari-stracking: https://www.napari-hub.org/plugins/napari-stracking
.. _scikit-image dimension order: https://scikit-image.org/docs/stable/user_guide/numpy_images.html#a-note-on-the-time-dimension
