Using BoneJ2
========================================

Here we adapt a workflow from the BoneJ2 paper (https://wellcomeopenresearch.org/articles/6-37) for use with napari-imagej.

napari Setup
----------------------

We will install one additional plugin to support this use case. Instructions for finding and installing a napari plugin are here: https://napari.org/stable/plugins/find_and_install_plugin.html

Please follow these instructions to install the plugin ``napari-segment-blobs-and-things-with-membranes``. More information
on this plugin can be found here: https://github.com/haesleinhuepf/napari-segment-blobs-and-things-with-membranes.

BoneJ2 Setup
----------------------

We need to first specify the endpoint that we will use to access BoneJ2.

We can configure napari-imagej to use a Fiji installation by opening the settings dialog and changing the ``imagej distribution_or_endpoint`` (described `here <../Configuration.html#imagej-directory-or-endpoint>`_). This example was created using an endpoint of ``sc.fiji:fiji:2.13.0+org.bonej:bonej-ops:MANAGED+org.bonej:bonej-plugins:MANAGED+org.bonej:bonej-utilities:MANAGED``.

**Note that napari must be restarted for these changes to take effect!**

Preparing and Opening the Data
------------------

We will use the same data that was used in the BoneJ2 paper. Go ahead and download umzc_378p_Apteryx_haastii_head.tif.bz2 from doi:10.6084/m9.figshare.7257179. Here is a direct link to the specific image: https://figshare.com/ndownloader/files/13369043

Opening Data in napari
^^^^^^^^^^^^^^^^^^^^^^

If you haven't already unzipped the file, then unzip the file. Once that is complete you can drag-and-drop the image onto napari to open it.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_open_data.png

            A napari viewer showing the example image that we will be working with.

Processing Data in napari with nsbatwm
^^^^^^^^^^^^^^^^^^^^^^

Now we need to process the image.

First, we will blur the image to smooth intensity values and filter noise.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_select_gaussian.png

            Selecting the Gaussian menu entry from the nsbatwm's Tools menu.

1. Within napari's menus choose: ``Tools > Filtering / noise removal > Gaussian (scikit image, nsbatwm)``

.. figure:: https://media.imagej.net/napari-imagej/bonej2_gaussian_parameter.png

            Setting the parameters for the Gaussian.

2. When the widget comes up, change the `sigma` value to 2 and ensure that the image layer is correctly set to the image that was opened.
Run the widget!

Now we will threshold the image to make it binary.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_select_threshold.png

            Selecting the thresholding algorithm developed by Li et al.
   
1. Within napari's menus choose: ``Tools > Segmentation / binarization > Threshold (Li et al 1993, scikit image, nsbatwm)``

2. When the widget comes up, ensure that the layer that is selected is the result of step 1.
Run the widget!

The result of thresholding is a Labels layer, but we will convert it to an Image layer to work with BoneJ2.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_convert_to_image.png

            Converting the Labels layer to an Image layer for processing in BoneJ2.
   
1. Right click on the layer that was created by step 2 and select ``Convert to Image``.

Processing Data in napari with BoneJ2 and napari-imagej
^^^^^^^^^^^^^^^^^^^^^^

Calculating the degree of anisotropy:

1. In the napari-imagej search bar type ``anisotropy``

2. Click ``Run``

3. Select the ``inputImage`` that corresponds to the theshold layer created previously.

4. Check the ``Recommended minimums`` box.
   
5. Enter ``1.73`` as the samplingInterval.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_anisotropy_parameters.png

            Setting the parameters of BoneJ2's Anisotropy command.

This will output the degree of anisotropy measurement for the image.


Calculating the fractal dimension:

1. In the napari-imagej search bar type ``fractal dimension``

2. Click ``Run``

3. Select the ``inputImage`` that corresponds to the theshold layer created previously.

4. Check the ``Automatic parameters`` box.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_fractal_dimension.png

            Setting the parameters of BoneJ2's fractal dimension command.

This will output the fractal dimension of the image.


Calculating the surface area:

1. In the napari-imagej search bar type ``surface area``

2. Click ``Run``

3. Select the ``inputImage`` that corresponds to the theshold layer created previously.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_surface_area.png

            Running BoneJ2's surface area command.
            
This command may take some time, because it runs a computationally costly algorithm called
"Marching Cubes" that creates a surface mesh of the image before computing the surface area.
This will output the surface area of the thresholded regions.


Calculating the area/volume fraction:

1. In the napari-imagej search bar type ``volume fraction``

2. Click ``Run``

3. Select the ``inputImage`` that corresponds to the theshold layer created previously.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_area_volume_fraction.png

            Running BoneJ2's area/volume fraction command.

This will output the Bone Volume Fraction (BV/TV) measurement for the image.


Calculating the connectivity:

1. In the napari-imagej search bar type ``connectivity``

2. Click ``Run``

3. Select the ``inputImage`` that corresponds to the theshold layer created previously.

.. figure:: https://media.imagej.net/napari-imagej/bonej2_connectivity.png

            Running BoneJ2's connectivity command.

This will output the Euler characteristic and Conn.D for the image.


The final measurements
^^^^^^^^^^^^^^^^^^^^^^

We have now quantified our image with a number of methods and can use our resulting
measurements in further scientific analysis!

.. figure:: https://media.imagej.net/napari-imagej/bonej2_all_measurements.png

            The results table for all of the BoneJ2 measurements. 
