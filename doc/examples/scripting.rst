Puncta Segmentation with SciJava Scripts (headless)
===================================================

Using `SciJava Scripts`_ we can automate the execution of sequential calls to ImageJ ecosystem functionality. Scripts written in any of SciJava's `supported scripting languages <https://imagej.net/scripting/#supported-languages>`_ will be automatically discovered and searchable within napari-imagej, just like other commands.

*Notably*, all SciJava Scripts can be run headlessly; since SciJava Scripts can headlessly call classic ImageJ functionality, **SciJava Scripts allow running classic ImageJ functionality without the ImageJ GUI**.

For this example, we translated PyImageJ's `Puncta Segmentation`_ into a SciJava Script. This SciJava Script can be executed in napari-imagej **or** in ImageJ2, increasing portability!

For more information on the use case itself, please see the original PyImageJ Puncta Segmentation example.

Configuration
-------------

To run this use case, the following settings were used. For information on configuring napari-imagej, please see `here <../Configuration.html>`__.

.. figure:: https://media.imagej.net/napari-imagej/settings_fiji.png

    Configuration for the Puncta Segmentation use case

The Code
--------

The script for Puncta Segmentation is written below:

.. code-block:: python
    :caption: Puncta_Segmentation.py

    #@ Img ds_src
    #@ ConvertService convert
    #@ DatasetService ds
    #@ OpService ops
    #@output org.scijava.table.Table sci_table

    from ij import IJ, ImagePlus, Prefs
    from ij.measure import ResultsTable
    from ij.plugin.filter import ParticleAnalyzer
    from net.imglib2.algorithm.neighborhood import HyperSphereShape
    from net.imglib2.img.display.imagej import ImageJFunctions
    from org.scijava.table import Table

    # save the ImageJ settings since we need to ensure black background is checked
    blackBackground = Prefs.blackBackground

    # if using a dataset with a light background and dark data, you can comment this line out
    # otherwise, the background will be measured instead of the points
    Prefs.blackBackground = True

    # convert image to 32-bit
    ds_src = ops.convert().int32(ds_src)

    # supress background noise
    mean_radius = HyperSphereShape(5)
    ds_mean = ds.create(ds_src.copy())
    ops.filter().mean(ds_mean, ds_src.copy(), mean_radius)
    ds_mul = ops.math().multiply(ds_src, ds_mean)

    # use gaussian subtraction to enhance puncta
    img_blur = ops.filter().gauss(ds_mul.copy(), 1.2)
    img_enhanced = ops.math().subtract(ds_mul, img_blur)

    # apply threshold
    img_thres = ops.threshold().renyiEntropy(img_enhanced)

    # convert ImgPlus to ImagePlus
    impThresholded=ImageJFunctions.wrap(img_thres, "wrapped")

    # get ResultsTable and set ParticleAnalyzer
    rt = ResultsTable.getResultsTable()
    ParticleAnalyzer.setResultsTable(rt)

    # set measurements
    IJ.run("Set Measurements...", "area center shape")

    # run the analyze particle plugin
    IJ.run(impThresholded, "Analyze Particles...", "clear");

    # convert results table -> scijava table -> pandas dataframe
    sci_table = convert.convert(rt, Table)

    # restore the settings to their original values
    Prefs.blackBackground = blackBackground


Note that the code is mostly the same, with the following exceptions:

#. Calls to ImageJ Services using the ImageJ Gateway (e.g. ``ij.convert``) are replaced with Scripting Parameters (e.g. ``#@ ConvertService convert``)
#. Java Classes are imported using the ``from...import`` syntax, instead of using ``sj.jimport``.
#. Calls to ``ij.py.show`` are removed - automating the process means we don't want to see these.
#. The output is a ``org.scijava.table.Table``, **not** a pandas ``DataFrame``. We don't need to perform this conversion in napari-imagej; napari-imagej takes care of that for us!

Installing the script
---------------------

Copy the code block above and paste it into a new file called ``Puncta_Segmentation.py``. As for where to put that file, the rules for `adding SciJava Scripts to ImageJ2 <https://imagej.net/scripting/#adding-scripts-to-the-plugins-menu>`_ also apply when adding scripts to napari-imagej if you are using a local ImageJ2 (e.g. a subdirectory of ``Fiji.app/scripts/``).

**However**, when napari-imagej is *not* provided with a local ImageJ2 instance, it must `download one <../Configuration.html#imagej-directory-or-endpoint>`_. This ImageJ2 can be tucked away, so napari-imagej will *by default* look within the **ImageJ base directory** for a ``scripts`` subdirectory, which must then have further subdirectories that contain your scripts. This behavior can be controlled via the `imagej base directory <../Configuration.html#imagej-base-directory>`_ in napari-imagej's settings. 

*Without changing this setting*, placing ``Puncta_Segmentation.py`` in a subdirectory of ``<path-to-napari-imagej-git-repo>/scripts`` allows napari-imagej to discover the script.

*If the imagej base directory has been changed*, instead place the script in a subdirectory of ``<imagej base directory>/scripts``.


Running the script
------------------

**Note**: this example was tested running with a `ImageJ directory or endpoint <../Configuration.html#imagej-directory-or-endpoint>`_ of ``sc.fiji:fiji:2.13.1``.

With napari-imagej running, the first step is to open the input data. We'll download the same sample data as the original PyImageJ example, `available here <https://github.com/imagej/pyimagej/blob/main/doc/sample-data/test_still.tif>`_.

The second step is to find our script within napari-imagej. Discovered SciJava Scripts can be found under their `filename <https://imagej.net/scripting/#adding-scripts-to-the-plugins-menu>`_; so we search for "puncta segmentation"

.. figure:: https://media.imagej.net/napari-imagej/puncta_search.png
    
    ``Puncta_Segmentation.py`` exposed within the napari-imagej searchbar as ``PunctaSegmentation``.

Double-clicking on ``PunctaSegmentation`` will bring a modal dialog, prompting the user for input data. The dialog also offers to display the resulting table in a new window, which may be preferred for large result tables.

Once the "OK" button is clicked, the resuling table is displayed in a new window, or a new napari widget, based on the option you selected above:

.. figure:: https://media.imagej.net/napari-imagej/puncta_results.png

.. _Puncta Segmentation: https://pyimagej.readthedocs.io/en/latest/Puncta-Segmentation.html
.. _SciJava Scripts: https://imagej.net/scripting/
