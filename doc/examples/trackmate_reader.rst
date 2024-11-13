Viewing TrackMate Data in the napari Viewer
===========================================

The `TrackMate <https://imagej.net/plugins/trackmate/>`_ plugin for ImageJ2 provides a streamlined interface for object tracking. This example shows napari-imagej's capability to view TrackMate tracks in napari, including segmentation labels, *without opening the ImageJ UI*.

**Note:** TrackMate is not included by default with ImageJ. To set up napari-imagej with TrackMate, see `these instructions <./trackmate.html#trackmate-plugin-setup>`_.

.. important::

    This Use Case was run with the following Mamba environment::

        mamba env create -n ex-track-read -y -c conda-forge python=3.11 openjdk=11.0 napari=0.5.0 napari-imagej=0.2.0

    and napari-imagej was configured to use the following endpoint::
        
        sc.fiji:fiji:2.15.0

TrackMate Setup
---------------

By default, napari-imagej does not include TrackMate. To use the TrackMate plugin, we must first configure napari-imagej to enable TrackMate access.

We can configure napari-imagej to use a `Fiji`_ installation as follows:

.. |ImageJ2| image:: ../../src/napari_imagej/resources/imagej2-16x16-flat.png

1. Activate the napari-imagej plugin by selecting the ``ImageJ2`` plugin from the Plugins menu.

2. Open the settings dialog by clicking the rightmost toolbar button, the gear symbol.

3. Change the ``ImageJ directory or endpoint`` (described `here <../Configuration.html#imagej-directory-or-endpoint>`_) to include Fiji, which bundles many popular plugins including TrackMate. Change this setting to the napari-imagej endpoint listed above.

.. figure:: https://media.imagej.net/napari-imagej/0.2.0/settings_fiji.png

4. **Restart napari** for the changes to take effect.

5. Activate the napari-imagej plugin again, as described in step (1) above.

6. If you wish, you may verify that Fiji is enabled by pasting the following code into napari's IPython console:

.. code-block:: python

   from napari_imagej.java import _ij as ij
   ij.app().getApps().keys()

And if ``Fiji`` is in the list, you're good!

TrackMate XML
-------------

TrackMate can store generated models in XML. For information on obtaining an XML file from generated Tracks, please see the `TrackMate documentation <https://imagej.net/plugins/trackmate/index#online-tutorials>`_.

Obtaining sample data
---------------------

For this example, we use data from the following publication: |zenodo badge|

.. |zenodo badge| image:: https://zenodo.org/badge/DOI/10.5281/zenodo.5864646.svg
   :target: https://doi.org/10.5281/zenodo.5864646

This data tracks breast cancer cells, taken as a 2D image with time and channel dimensions. The data was segmented using `Cellpose <https://www.cellpose.org/>`_.

You will need to download two files:
  #. `BreastCancerCells_multiC.xml <https://zenodo.org/record/5864646/files/BreastCancerCells_multiC.xml?download=1>`_
  #. `BreastCancerCells_multiC.tif <https://zenodo.org/record/5864646/files/BreastCancerCells_multiC.tif?download=1>`_

Opening the data
-------------------

Once napari is running, you can open the data within napari through ``File>Open File(s)...``, and selecting the ``.xml`` sample file that was downloaded.

There might be a slight delay while the files open. This process can be an expensive operation as we require a running JVM and conversion of the TrackMate ``Model`` into napari ``Layers``; however, the reader plugin displays a progress bar in the ``Activity`` pane.

When complete, you should see the image, track and label layers in napari:

.. figure:: https://media.imagej.net/napari-imagej/0.2.0/trackmate_reader.gif
    :align: center

.. _Fiji: https://fiji.sc/