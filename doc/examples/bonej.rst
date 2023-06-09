Using BoneJ2
========================================

Here we adapt a workflow from the BoneJ2 paper (https://wellcomeopenresearch.org/articles/6-37) for use with napari-imagej.

napari Setup
----------------------

We will install one additional plugin to support this use case: https://github.com/haesleinhuepf/napari-segment-blobs-and-things-with-membranes

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

Processing Data in napari with nsbatwm
^^^^^^^^^^^^^^^^^^^^^^

Now we need to process the image.

1. First, we will blur the image to smooth intensity values and filter noise.

Within napari's menus choose: `Tools` > `Filtering / noise removal` > `Gaussian (scikit image, nsbatwm)`

When the widget comes up, change the `sigma` value to 2 and ensure that the image layer is correctly set to the image that was opened.

2. Now we will threshold the image to make it binary.

Within napari's menus choose: `Tools` > `Segmentation / binarization` > `Threshold (Li et al 1993, scikit image, nsbatwm)`

When the widget comes up, ensure that the layer that is selected is the result of step 1.

3. The result of thresholding is a Label layer, but we will convert it to an Image layer to work with BoneJ2.

Right click on the layer that was created by step 2 and select `Convert to Image`.

Processing Data in napari with BoneJ2 and napari-imagej
^^^^^^^^^^^^^^^^^^^^^^

Calculating the degree of anisotropy:

1. In the napari-imagej search bar type `Anisotropy`

2. Click `Run`

Select the `inputImage` that corresponds to the theshold layer created previously.

Check the `Recommended minimums` box.
Enter `1.73` as the samplingInterval.

This will output the degree of anisotropy measurement for the image.


Calculating the Area/Volume Fraction:

1. In the napari-imagej search bar type `Volume Fraction`

2. Click `Run`

Select the `inputImage` that corresponds to the theshold layer created previously.

This will output the Bone Volume Fraction (BV/TV) measurement for the image.


Calculating the Connectivity:

1. In the napari-imagej search bar type `Connectivity`

2. Click `Run`

Select the `inputImage` that corresponds to the theshold layer created previously.

This will output the Euler characteristic and Conn.D for the image.


