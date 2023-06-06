from typing import List

from scyjava import get_version, is_version_at_least, jimport

from napari_imagej import settings
from napari_imagej.java import _validate_imagej, minimum_versions
from napari_imagej.utilities.logging import logger

from tests.utils import jc

version_checks = {
    "io.scif:scifio": "io.scif.SCIFIO",
    "net.imagej:ij": "ij.ImagePlus",
    "net.imagej:imagej": "net.imagej.Main",
    "net.imagej:imagej-common": "net.imagej.Dataset",
    "net.imagej:imagej-legacy": "net.imagej.legacy.LegacyService",
    "net.imagej:imagej-ops": "net.imagej.ops.OpService",
    "net.imglib2:imglib2-imglyb": "net.imglib2.python.ReferenceGuardingRandomAccessibleInterval",  # noqa: E501
    "net.imglib2:imglib2-unsafe": "net.imglib2.img.unsafe.UnsafeImg",
    "org.scijava:scijava-common": "org.scijava.Context",
    "org.scijava:scijava-search": "org.scijava.search.Searcher",
    "sc.fiji:fiji": "sc.fiji.Main",
}


def test_java_components(ij):
    """
    Assert that Java components are present, and print their versions.
    """
    print()
    print("======= BEGIN JAVA VERSIONS =======")

    for coord, class_name in version_checks.items():
        try:
            jcls = jimport(class_name)
        except Exception:
            jcls = None

        if jcls is None:
            version = "NOT PRESENT"
        else:
            version = get_version(jcls)
            if coord in minimum_versions:
                assert is_version_at_least(version, minimum_versions[coord])
            else:
                version += " (no minimum)"

        print(f"{coord} {version}")

    print("======== END JAVA VERSIONS ========")


def test_endpoint(ij):
    endpoints: List[str] = settings.endpoint().split("+")
    for endpoint in endpoints:
        gav = endpoint.split(":")
        if len(gav) > 2:
            ga = ":".join(gav[:2])
            if ga in version_checks:
                version = gav[2]
                exp_version = get_version(jimport(version_checks[ga]))
                assert is_version_at_least(version, exp_version)


def test_recommended_version(ij):
    # Save old recommended versions
    import napari_imagej.java

    existing = napari_imagej.java.recommended_versions
    napari_imagej.java.recommended_versions = {"org.scijava:scijava-common": "999.0.0"}

    # Setup log handler to capture warning
    import io
    import logging

    log_capture_string = io.StringIO()
    ch = logging.StreamHandler(log_capture_string)
    ch.setLevel(logging.WARN)
    logger().addHandler(ch)
    # Validate ImageJ - capture lower-than-recommended version
    _validate_imagej(ij)
    log_contents = log_capture_string.getvalue()
    log_capture_string.close()
    # Assert warning given
    nij_version = get_version("napari-imagej")
    sjc_version = get_version(jc.Module)
    assert log_contents == (
        f"napari-imagej: napari-imagej v{nij_version} recommends using the "
        "following component versions:\n\torg.scijava:scijava-common : "
        f"999.0.0 (Installed: {sjc_version})\n"
    )

    # restore recommended versions
    napari_imagej.java.recommended_versions = existing
