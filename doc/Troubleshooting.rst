Troubleshooting
===============


napari-imagej does not appear in the Plugins menu of napari!
------------------------------------------------------------

npe2_ is a useful tool for validating a napari plugin's setup. When running napari-imagej within Mamba_, use:

.. code-block:: bash

    mamba activate napari-imagej
    mamba install npe2 -c conda-forge
    npe2 validate napari-imagej

If ``npe2 validate`` returns an error, this indicates that napari-imagej was not installed correctly. In this case, please ensure that you have followed `Installation <./Install.html>`_ instructions.

The search bar is disabled with the message "Initializing ImageJ..."
--------------------------------------------------------------------

Since napari-imagej is calling Java code under the hood, it must launch a Java Virtual Machine (JVM). The JVM is not launched until the user starts napari-imagej. As we cannot search Java functionality *until the JVM is running*, the search bar is not enabled until the JVM is ready.

The first launch of napari-imagej can take significantly longer than subsequent launches while the underlying framework downloads the Java artifacts needed to run ImageJ2. **Downloading these libraries can take minutes**. These libraries are cached, however, so subsequent launches should not take more than a couple of seconds.

The ImageJ2 GUI button is greyed out!
-------------------------------------

There are two common cases for a disabled ImageJ2 GUI button:

#. When napari-imagej is first launched, the button will be disabled until the ImageJ2 Gateway is ready to process data. Please see `here <#The-search-bar-is-disabled-with-the-message-"Initializing-ImageJ...">`_

#. On some systems (namely **MacOS**), PyImageJ can **only** be run headlessly. In headless PyImageJ environments, the ImageJ2 GUI cannot be launched. Please see `this page <https://pyimagej.readthedocs.io/en/latest/Initialization.html#interactive-mode>`_ for more information.

.. _Mamba: https://mamba.readthedocs.io/en/latest/
.. _npe2: https://github.com/napari/npe2