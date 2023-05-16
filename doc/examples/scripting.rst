Puncta Segmentation with SciJava Scripts (headless)
===================================================

Using `SciJava Scripts`_ we can automate the execution of sequential calls to ImageJ ecosystem functionality. Scripts written in any of SciJava's `supported scripting languages <https://imagej.net/scripting/#supported-languages>`_ will be automatically discovered and exposed by napari-imagej within the napari-imagej searching interface.

*Notably*, all SciJava Scripts can be run headlessly; since SciJava Scripts can headlessly call classic ImageJ functionality, **SciJava Scripts allow running classic ImageJ functionality without the ImageJ GUI**.

In this example, we will transform PyImageJ's `Puncta Segmentation`_ example into a SciJava Script. This SciJava Script can then be executed in napari-imagej **or** in ImageJ2, increasing portability!

For more information on the use case itself, please visit the PyImageJ Puncta Segmentation example.

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

    from ij import IJ, ImagePlus
    from ij.measure import ResultsTable
    from ij.plugin.filter import ParticleAnalyzer
    from net.imglib2.algorithm.neighborhood import HyperSphereShape
    from net.imglib2.img.display.imagej import ImageJFunctions
    from org.scijava.table import Table

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


Note that the code is entirely the same, with the following exceptions:

#. Calls to ImageJ Services using the ImageJ Gateway (e.g. ``ij.convert``) are replaced with Scripting Parameters (e.g. ``#@ ConvertService convert``)
#. Java Classes are imported using the ``from...import`` syntax, instead of using ``sj.jimport``.
#. Calls to ``ij.py.show`` are removed - automating the process means we don't want to see these.
#. The output is a ``org.scijava.table.Table``, **not** a pandas ``DataFrame``. We don't need to perform this conversion in napari-imagej; napari-imagej takes care of that for us!

Installing the script
---------------------

The rules for `adding SciJava Scripts to ImageJ2 <https://imagej.net/scripting/#adding-scripts-to-the-plugins-menu>`_ also apply when adding scripts to napari-imagej, **with one exception**:

When napari-imagej is not provided with a local ImageJ2 instance, it must `download one implicitly <../Configuration.html#imagej-directory-or-endpoint>`_. This ImageJ2 can be tucked away, so napari-imagej will *by default* look within **the current directory** for a ``scripts`` subdirectory. This behavior can be changed by altering the `imagej base directory <../Configuration.html#imagej-base-directory>`_ in napari-imagej's settings. 

*Without changing these settings*, placing ``Puncta_Segmentation.py`` in ``./scripts`` allows napari-imagej to discover the script.

*If* ``imagej base directory`` *has been changed*, instead place the script in ``<imagej base directory>/scripts``.


Running the script
------------------

With napari-imagej running, the first step is to open the input data. The sample images used in the original PyImageJ document are available on the PyImageJ GitHub repository `here <https://github.com/imagej/pyimagej/blob/main/doc/sample-data/test_still.tif>`_

The second step is to find our script within napari-imagej. Discovered SciJava Scripts can be found under *their* `filename <https://imagej.net/scripting/#adding-scripts-to-the-plugins-menu>`_; we can find ``Puncta_Segmemtation.py`` by searching "puncta segmentation"

.. figure:: https://media.imagej.net/napari-imagej/puncta_search.png
    
    ``Puncta_Segmentation.py`` exposed within the napari-imagej searchbar as ``PunctaSegmentation``.

Double-clicking on ``PunctaSegmentation`` will bring a modal dialog, prompting the user for input data. The dialog also offers the user to spawn the resulting table in a new window, which may be preferred for large result tables.

Once the "OK" button is clicked, the resuling table is displayed in a new napari widget:

.. figure:: https://media.imagej.net/napari-imagej/puncta_results.png

.. _Puncta Segmentation: https://pyimagej.readthedocs.io/en/latest/Puncta-Segmentation.html
.. _SciJava Scripts: https://imagej.net/scripting/
