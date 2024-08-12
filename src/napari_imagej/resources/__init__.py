"""
A module used to help find napari-imagej widget resources
"""

from pathlib import Path

PATH = Path(__file__).parent.resolve()
RESOURCES = {x.stem: str(x) for x in PATH.iterdir() if x.suffix != ".py"}


def resource_path(name: str) -> str:
    """Return path to a resource in this folder."""
    if name not in RESOURCES:
        raise ValueError(
            f"{name} is not a known resource! Known resources: {RESOURCES}"
        )
    return RESOURCES[name]
