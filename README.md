# napari-imagej

***EARLY AND EXPERIMENTAL PROTOTYPE***

See the [project roadmap](https://github.com/orgs/imagej/projects/2), still under construction.

[![License](https://img.shields.io/pypi/l/napari-imagej.svg?color=green)](https://github.com/imagej/napari-imagej/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-imagej.svg?color=green)](https://pypi.org/project/napari-imagej)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-imagej.svg?color=green)](https://python.org)
[![tests](https://github.com/imagej/napari-imagej/workflows/tests/badge.svg)](https://github.com/imagej/napari-imagej/actions)
[![codecov](https://codecov.io/gh/imagej/napari-imagej/branch/main/graph/badge.svg)](https://codecov.io/gh/imagej/napari-imagej)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-imagej)](https://napari-hub.org/plugins/napari-imagej)

Use ImageJ functionality from napari

----------------------------------

This [napari] plugin was generated with [Cookiecutter] using [@napari]'s [cookiecutter-napari-plugin] template.

<!--
Don't miss the full getting started guide to set up your new package:
https://github.com/napari/cookiecutter-napari-plugin#getting-started

and review the napari docs for plugin developers:
https://napari.org/plugins/stable/index.html
-->

## Installation

Currently, the only way to install napari-imagej is by downloading this repository. You can then use [conda] to install the environment. We prefer using [mamba] over conda for drastically shorter setup times:

    conda install mamba -n base -c conda-forge
    mamba env create -f environment.yml
    pip install -e .

For developers, please instead use `dev-environment.yml`. Using this environment file will also install the developer tools:

    conda install mamba -n base -c conda-forge
    mamba env create -f dev-environment.yml
    pip install -e .

Once napari-imagej is ready for an initial release, it will be installable from [PyPI] and conda-forge.

## Contributing

Contributions are very welcome. Tests can be run with [tox], please ensure
the coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-imagej" is free and open source software

## Issues

If you encounter any problems, please [file an issue] along with a detailed description.

[napari]: https://github.com/napari/napari
[conda]: https://docs.conda.io/projects/conda/en/latest/index.html
[conda-forge]: https://conda-forge.org/#page-top
[mamba]: https://mamba.readthedocs.io/en/latest/user_guide/mamba.html
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[@napari]: https://github.com/napari
[MIT]: http://opensource.org/licenses/MIT
[BSD-3]: http://opensource.org/licenses/BSD-3-Clause
[GNU GPL v3.0]: http://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: http://www.gnu.org/licenses/lgpl-3.0.txt
[Apache Software License 2.0]: http://www.apache.org/licenses/LICENSE-2.0
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin

[file an issue]: https://github.com/imagej/napari-imagej/issues

[napari]: https://github.com/napari/napari
[tox]: https://tox.readthedocs.io/en/latest/
[pip]: https://pypi.org/project/pip/
[PyPI]: https://pypi.org/
