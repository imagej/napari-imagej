============
Installation
============

napari-imagej is still in its infancy; until we reach 0.1.0, the only way to install napari-imagej is install from source by cloning the napari_imagej_ repository.

Installing From Source
======================
Steps for installing napari-imagej from source are described below:

Using Mamba (Recommended)
-------------------------

Mamba_ is the easiest way to install napari-imagej. To install Mamba, follow the instructions `here <https://mamba.readthedocs.io/en/latest/installation.html>`_.

#. Clone the napari-imagej repository

   From a suitable location, use the following command to clone the napari-imagej repository:

   .. code-block:: bash

      git clone https://github.com/imagej/napari-imagej
      cd napari-imagej

#. Install napari-imagej

   The following line will download all necessary components to run napari-imagej, installing them into a mamba environment named ``napari-imagej``.

   .. code-block:: bash

      mamba env create

Using pip
---------
napari-imagej can also be installed using ``pip``, however it requires more steps. You'll need Python3_ if you don't have it already.

We recommend using virtualenv_ to isolate napari-imagej from your system-wide or user-wide Python environments. Alternatively, you can use Mamba_ purely for its virtual environment capabilities, and then ``pip install`` everything into that environment:

.. code-block:: bash

   mamba create -n napari-imagej python pip
   mamba activate napari-imagej

#. Install OpenJDK 8 or OpenJDK 11. 

   napari-imagej should work with whichever distribution of OpenJDK you prefer; we recommend `zulu jdk+fx 8 <https://www.azul.com/downloads/zulu-community/?version=java-8-lts&package=jdk-fx>`_. You can also install OpenJDK from your platform's package manager.

#. Install Maven. 

   You can either `download it manually <https://maven.apache.org/>`_ or install it via your platform's package manager. The ``mvn --version`` command can be used to verify installation.

#. Install napari-imagej

   The following code section will **clone the napari-imagej source into a subfolder of the local directory** and install all Python components necessary for napari-imagej.

   .. code-block:: bash

      git clone https://github.com/imagej/napari-imagej
      cd napari-imagej
      pip install .

.. _Mamba: https://mamba.readthedocs.io/en/latest/
.. _napari_imagej: https://github.com/imagej/napari-imagej
.. _Python3: https://www.python.org/
.. _virtualenv: https://virtualenv.pypa.io/en/latest/

.. There are two supported ways to install PyImageJ: via
.. [conda](https://conda.io/)/[mamba](https://mamba.readthedocs.io/) or via
.. [pip](https://packaging.python.org/guides/tool-recommendations/).
.. Although both tools are great
.. [for different reasons](https://www.anaconda.com/blog/understanding-conda-and-pip),
.. if you have no strong preference then we suggest using mamba because it will
.. manage PyImageJ's non-Python dependencies
.. [OpenJDK](https://en.wikipedia.org/wiki/OpenJDK) (a.k.a. Java) and
.. [Maven](https://maven.apache.org/). If you use pip, you will need to install
.. those two things separately.

.. ## Installing via conda/mamba

.. Note: We strongly recommend using
.. [Mamba](https://mamba.readthedocs.io/en/latest/user_guide/mamba.html) rather
.. than plain Conda, because Conda is unfortunately terribly slow at configuring
.. environments.

.. 1. [Install Mambaforge](https://github.com/conda-forge/miniforge#mambaforge).

.. 2. Install PyImageJ into a new environment:
..    ```
..    mamba create -n pyimagej pyimagej openjdk=8
..    ```

..    This command will install PyImageJ with OpenJDK 8. If you would rather use
..    OpenJDK 11, you can write `openjdk=11` instead, or even just leave off the
..    `openjdk` part altogether to get the latest version of OpenJDK. PyImageJ
..    has been tested most thoroughly with OpenJDK 8, but it is also known to
..    work with OpenJDK 11, and likely later OpenJDK versions as well.

.. 3. Whenever you want to use PyImageJ, activate its environment:
..    ```
..    mamba activate pyimagej
..    ```

.. ## Installing via pip

.. If installing via pip, we recommend using a
.. [virtualenv](https://virtualenv.pypa.io/) to avoid cluttering up or mangling
.. your system-wide or user-wide Python environment. Alternately, you can use
.. mamba just for its virtual environment feature (`mamba create -n pyimagej
.. python=3.8; mamba activate pyimagej`) and then simply `pip install` everything
.. into that active environment.

.. There are several ways to install things via pip, but we will not enumerate
.. them all here; these instructions will assume you know what you are doing if
.. you chose this route over conda/mamba above.

.. 1. Install [Python 3](https://python.org/). As of this writing, PyImageJ has
..    been tested with Python 3.6, 3.7, 3.8, 3.9, and 3.10.
..    You might have issues with Python 3.10 on Windows.

.. 2. Install OpenJDK 8 or OpenJDK 11. PyImageJ should work with whichever
..    distribution of OpenJDK you prefer; we recommend
..    [Zulu JDK+FX 8](https://www.azul.com/downloads/zulu-community/?version=java-8-lts&package=jdk-fx).
..    Another option is to install openjdk from your platform's package manager.

.. 3. Install Maven. You can either
..    [download it manually](https://maven.apache.org/) or install it via your
..    platform's package manager, if available there. The `mvn` command must be
..    available on your system path.

.. 4. Install pyimagej via pip:
..    ```
..    pip install pyimagej
..    ```

.. ## Testing your installation

.. Here's one way to test that it works:
.. ```
.. python -c 'import imagej; ij = imagej.init("2.5.0"); print(ij.getVersion())'
.. ```
.. Should print `2.5.0` on the console.

.. ## Dynamic installation within Jupyter

.. It is possible to dynamically install PyImageJ from within a Jupyter notebook.

.. For your first cell, write:
.. ```
.. import sys, os
.. !mamba install --yes --prefix {sys.prefix} pyimagej openjdk=8
.. os.environ['JAVA_HOME'] = os.sep.join(sys.executable.split(os.sep)[:-2] + ['jre'])
.. ```

.. This approach is useful for [JupyterHub](https://jupyter.org/hub) on the cloud,
.. e.g. [Binder](https://mybinder.org/), to utilize PyImageJ in select notebooks
.. without advance installation. This reduces time needed to create and launch the
.. environment, at the expense of a longer startup time the first time a
.. PyImageJ-enabled notebook is run. See [this itkwidgets example
.. notebook](https://github.com/InsightSoftwareConsortium/itkwidgets/blob/v0.24.2/examples/ImageJImgLib2.ipynb)
.. for an example.
