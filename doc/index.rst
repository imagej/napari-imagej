.. napari-imagej documentation master file, created by
   sphinx-quickstart on Tue Feb  7 14:11:33 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

napari-imagej: ImageJ ecosystem access within napari
====================================================

The `napari <https://napari.org/>`_ application has brought n-dimensional image browsing and analysis to the Python ecosystem. At the same time, the ImageJ software ecosystem, including `ImageJ <https://imagej.net/ij/index.html>`_, `ImageJ2 <https://imagej.net/software/imagej2>`_, `Fiji <https://fiji.sc/>`_ and `thousands of community plugins <https://imagej.net/list-of-extensions>`_, have been curated over decades, and are utilized by a highly active community of their own.

The napari-imagej plugin strives to unite these communities by providing access to an ImageJ2 instance within a napari widget. From this widget, users can launch the ImageJ user interface to run **any** ImageJ ecosystem functionality, and can additionally access **ImageJ2** framework functionality directly.

napari-imagej handles the burden of data transfer between these two applications, enabling accessible, convenient, synergistic workflows.

.. figure:: https://media.imagej.net/napari-imagej/front_page.png

   Using ImageJ's `Analyze Particles <https://imagej.net/imaging/particle-analysis>`_ routine within napari

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   Install

   Initialization

   Configuration

   Troubleshooting

   Use_Cases

   Development

   Architecture

   Benchmarking
