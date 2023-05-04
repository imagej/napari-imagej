from scyjava import get_version, is_version_at_least, jimport

from napari_imagej.java import minimum_versions


def test_java_components(ij):
    """
    Assert that Java components are present, and print their versions.
    """
    version_checks = {
        "net.imagej:imagej-common": "net.imagej.Dataset",
        "net.imagej:imagej-ops": "net.imagej.ops.OpService",
        "net.imglib2:imglib2-unsafe": "net.imglib2.img.unsafe.UnsafeImg",
        "net.imglib2:imglib2-imglyb": "net.imglib2.python.ReferenceGuardingRandomAccessibleInterval",  # noqa: E501
        "org.scijava:scijava-common": "org.scijava.Context",
        "org.scijava:scijava-search": "org.scijava.search.Searcher",
        "net.imagej:imagej-legacy": "net.imagej.legacy.LegacyService",
        "net.imagej:ij": "ij.ImagePlus",
    }

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
