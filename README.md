# napari-imagej

### A [napari] plugin for access to [ImageJ2]

[![License](https://img.shields.io/pypi/l/napari-imagej.svg?color=green)](https://github.com/imagej/napari-imagej/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-imagej.svg?color=green)](https://pypi.org/project/napari-imagej)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-imagej.svg?color=green)](https://python.org)
[![tests](https://github.com/imagej/napari-imagej/workflows/tests/badge.svg)](https://github.com/imagej/napari-imagej/actions)
[![codecov](https://codecov.io/gh/imagej/napari-imagej/branch/main/graph/badge.svg)](https://codecov.io/gh/imagej/napari-imagej)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-imagej)](https://napari-hub.org/plugins/napari-imagej)

**napari-imagej** aims to provide access to all [ImageJ2] functionality through the [napari] graphical user interface. It builds on the foundation of [PyImageJ], a project allowing ImageJ2 access from Python.

**With napari-imagej, you can access:**

1. The napari-imagej widget, providing *headless access* to:
   * [ImageJ2 Commands] - 100+ image processing algorithms
   * [ImageJ Ops] - 500+ *functional* image processing algorithms
   * [SciJava Scripts] - migrated from Fiji or ImageJ2, or written yourself!
2. The ImageJ user interface, providing access to *the entire ImageJ ecosystem* within napari.

See the [project roadmap](https://github.com/orgs/imagej/projects/2) for future directions.

## Getting Started

Learn more about the project [here](https://napari-imagej.readthedocs.io/en/latest/), or jump straight to [installation](https://napari-imagej.readthedocs.io/en/latest/Install.html)!

## Usage

* [Image Processing with ImageJ Ops](https://napari-imagej.readthedocs.io/en/latest/examples/ops.html)
* [Puncta Segmentation with SciJava Scripts](https://napari-imagej.readthedocs.io/en/latest/examples/scripting.html)

## Troubleshooting

The [FAQ](https://napari-imagej.readthedocs.io/en/latest/Troubleshooting.html) outlines solutions to many common issues.

For more obscure issues, feel free to reach out on [forum.image.sc](https://forum.image.sc).

If you've found a bug, please [file an issue]!

## Contributing

We welcome any and all contributions made onto the napari-imagej repository.

Development discussion occurs on the [Image.sc Zulip chat](https://imagesc.zulipchat.com/#narrow/stream/328100-scyjava).

For technical details involved with contributing, please see [here](https://napari-imagej.readthedocs.io/en/latest/Development.html)

## License

Distributed under the terms of the [BSD-2] license,
"napari-imagej" is free and open source software.


[Apache Software License 2.0]: https://www.apache.org/licenses/LICENSE-2.0
[black]: https://github.com/psf/black
[BSD-2]: https://opensource.org/licenses/BSD-2-Clause
[Cookiecutter]: https://github.com/audreyr/cookiecutter
[cookiecutter-napari-plugin]: https://github.com/napari/cookiecutter-napari-plugin
[conda]: https://docs.conda.io/
[conda-forge]: https://conda-forge.org/
[file an issue]: https://github.com/imagej/napari-imagej/issues
[flake8]: https://flake8.pycqa.org/
[GNU GPL v3.0]: https://www.gnu.org/licenses/gpl-3.0.txt
[GNU LGPL v3.0]: https://www.gnu.org/licenses/lgpl-3.0.txt
[ImageJ2]: https://imagej.net/software/imagej2
[ImageJ2 Commands]: https://github.com/imagej/imagej-plugins-commands
[ImageJ Ops]: https://imagej.net/libs/imagej-ops
[install mamba]: https://mamba.readthedocs.io/en/latest/installation.html
[isort]: https://pycqa.github.io/isort/
[mamba]: https://mamba.readthedocs.io/
[MIT]: https://opensource.org/licenses/MIT
[Mozilla Public License 2.0]: https://www.mozilla.org/media/MPL/2.0/index.txt
[napari]: https://github.com/napari/napari
[napari hub]: https://www.napari-hub.org/
[npe2]: https://github.com/napari/npe2
[pip]: https://pypi.org/project/pip/
[pull request]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests
[PyImageJ]: https://github.com/imagej/pyimagej
[PyPI]: https://pypi.org/
[SciJava Scripts]: https://imagej.net/scripting
[tox]: https://tox.readthedocs.io/
