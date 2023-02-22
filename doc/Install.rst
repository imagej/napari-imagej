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
