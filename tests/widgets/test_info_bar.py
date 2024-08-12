"""
A module testing napari_imagej.widgets.info_bar
"""

import pytest
from qtpy.QtWidgets import QLabel, QVBoxLayout

from napari_imagej.widgets.info_bar import InfoBox


@pytest.fixture
def info_bar():
    return InfoBox()


def test_widget_layout(info_bar: InfoBox):
    """Tests the number and expected order of InfoBar children"""
    subwidgets = info_bar.children()
    assert len(subwidgets) == 2
    assert isinstance(info_bar.layout(), QVBoxLayout)
    assert isinstance(subwidgets[0], QVBoxLayout)

    assert isinstance(subwidgets[1], QLabel)
    assert subwidgets[1].text() == ""
