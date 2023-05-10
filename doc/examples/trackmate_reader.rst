Viewing TrackMate Data in the napari Viewer
===========================================

The `TrackMate <https://imagej.net/plugins/trackmate/>`_ plugin for ImageJ2 provides a streamlined interface for object tracking. This example shows napari-imagej's capability to view TrackMate tracks in napari, including segmentation labels, *without opening the ImageJ UI*

TrackMate XML
-------------

TrackMate can store generated models in XML. For information on obtaining an XML file from generated Tracks, please see the TrackMate `documentation <https://imagej.net/plugins/trackmate/index#online-tutorials>`_.

Obtaining Sample data
---------------------

For this example, we use data from the following publication: |zenodo badge|

.. |zenodo badge| image:: https://zenodo.org/badge/DOI/10.5281/zenodo.5864646.svg
   :target: https://doi.org/10.5281/zenodo.5864646

This data tracks breast cancer cells, taken as a 2D image with time and channel dimensions. The data was segmented using `Cellpose <https://www.cellpose.org/>`_.

The XML can be downloaded using `this link <https://zenodo.org/record/5864646/files/BreastCancerCells_multiC.xml?download=1>`_.

Opening the data
-------------------

Once napari is running, you can open the data within napari through ``File>Open``, or by dragging and dropping the XML file onto the napari window.

Opening tracks can be an expensive operation as we require a running JVM and conversion of the TrackMate ``Model`` into napari ``Layers``, however the reader plugin displayes a progress bar in the ``Activity`` pane.

.. image:: https://media.imagej.net/napari-imagej/trackmate_reader.gif
    :align: center