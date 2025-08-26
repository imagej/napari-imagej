Developer's Guide
=================

This document describes how to contribute to the napari-imagej source.

If your goal is only to *use* napari-imagej to call ImageJ ecosystem routines in napari, see `this page <./Install.html>`_.

Configuring a uv environment for development
--------------------------------------------

Developers should all use uv_ to manage a shared Python environment for napari-imagej development.

First, clone the repository:

.. code-block:: bash

    git clone https://github.com/imagej/napari-imagej
    cd napari-imagej

Then, set up your environment using ``uv``:

.. code-block:: bash

    uv sync

Testing
-------

napari-imagej uses pytest_ to automate testing. By installing the development environment above, ``pytest`` will be available.

To test napari-imagej, simply run:

.. code-block:: bash

    uv run pytest

Documentation
-------------

napari-imagej uses `Read the Docs`_ for user-facing documentation. If you make front-end changes to napari-imagej, please describe your changes with the files in the ``doc`` folder of the napari-imagej source.

Once you've made your changes, run the following:

.. code-block:: bash

    uv run make html

This will build the documentation into HTML files locally, stored in the ``doc/_build/html`` folder. You can then view the documentation locally by loading ``doc/_build/html/index.html`` in the browser of your choice.

Production documentation is available online at https://napari-imagej.readthedocs.io/

Formatting
----------

black_, flake8_, and isort_ are used to lint and standardize the napari-imagej source.

To manually format the source, run (macOS/Linux):

.. code-block:: bash

    uv run make clean

napari-imagej also includes pre-commit_ configuration for those who want it. By using pre-commit, staged changes will be formatted before they can be commited to a repository. pre-commit can be set up using:

.. code-block:: bash

    uv run pre-commit install

Building Distribution Bundles
-----------------------------

You can run the following to bundle napari-imagej (macOS/Linux):

.. code-block:: bash

    uv run make dist

.. _black: https://black.readthedocs.io/en/stable/
.. _flake8: https://flake8.pycqa.org/en/latest/
.. _isort: https://pycqa.github.io/isort/
.. _uv: https://docs.astral.sh/uv/
.. _Read the Docs: https://readthedocs.org/
.. _pre-commit: https://pre-commit.com/
.. _pytest: https://docs.pytest.org
