============
Installation
============

If you're looking to use napari-imagej, there are a few ways to get it running.

Installing within napari
========================

If you have napari installed already, you can install napari-imagej by following these steps:

#. Install napari-imagej with napari

   With napari running, `navigate <https://napari.org/stable/plugins/find_and_install_plugin.html#installing-plugins-with-napari>`_ to the plugins menu ``Plugins>Install/Uninstall Plugins`` and type into the search bar ``napari-imagej``. Click ``Install`` to install napari-imagej!

Once the installation is complete, napari-imagej is ready to use!

Installing from Mamba
=====================

Mamba_ is the easiest way to install napari-imagej. To install Mamba, follow the instructions `here <https://mamba.readthedocs.io/en/latest/installation.html>`_.

#. Create a Mamba environment:

   .. code-block:: bash

      mamba create -n napari-imagej -y -c conda-forge napari-imagej

   This command installs napari-imagej and napari into an environment named ``napari-imagej``.

#. Activate the Mamba environment:

   This step must be done every time that you'd like to use napari-imagej:

   .. code-block:: bash

      mamba activate napari-imagej

Installing from pip
===================

napari-imagej can also be installed using ``pip``; however, it requires more steps. You'll need Python3_ if you don't have it already.

We recommend using virtualenv_ to isolate napari-imagej from your system-wide or user-wide Python environments. Alternatively, you can use Mamba_ purely for its virtual environment capabilities, and then ``pip install`` everything into that environment:

.. code-block:: bash

   mamba create -n napari-imagej -y -c conda-forge python==3.12 pip
   mamba activate napari-imagej

#. Install OpenJDK 8 or OpenJDK 11

   napari-imagej should work with whichever distribution of OpenJDK you prefer; we recommend `zulu jdk+fx 8 <https://www.azul.com/downloads/zulu-community/?version=java-8-lts&package=jdk-fx>`_. You can also install OpenJDK from your platform's package manager.

#. Install Maven

   You can either `download it manually <https://maven.apache.org/>`_ or install it via your platform's package manager. The ``mvn --version`` command can be used to verify installation.

#. Install napari-imagej

   Using pip, we can install napari-imagej:

   .. code-block:: bash

      pip install napari-imagej "napari[all]"


Installing from Source
======================

If you're looking to develop napari-imagej, you'll likely want to install from source.

Using pip
---------
napari-imagej can also be installed using ``pip``; however, it requires more steps. You'll need Python3_ if you don't have it already.

We recommend using virtualenv_ to isolate napari-imagej from your system-wide or user-wide Python environments. Alternatively, you can use Mamba_ purely for its virtual environment capabilities, and then ``pip install`` everything into that environment:

.. code-block:: bash

   mamba create -n napari-imagej -y -c conda-forge python==3.12 pip
   mamba activate napari-imagej

#. Install OpenJDK 8 or OpenJDK 11

   napari-imagej should work with whichever distribution of OpenJDK you prefer; we recommend `zulu jdk+fx 8 <https://www.azul.com/downloads/zulu-community/?version=java-8-lts&package=jdk-fx>`_. You can also install OpenJDK from your platform's package manager.

#. Install Maven

   You can either `download it manually <https://maven.apache.org/>`_ or install it via your platform's package manager. The ``mvn --version`` command can be used to verify installation.

#. Install napari-imagej

   The following code section will **clone the napari-imagej source into a subfolder of the local directory** and install all Python components necessary for napari-imagej.

   .. code-block:: bash

      git clone https://github.com/imagej/napari-imagej
      cd napari-imagej
      pip install "napari[all]" .

.. _Mamba: https://mamba.readthedocs.io/en/latest/
.. _napari_imagej: https://github.com/imagej/napari-imagej
.. _Python3: https://www.python.org/
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
