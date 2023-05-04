from scyjava import get_version, jimport


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
        version = "NOT PRESENT" if jcls is None else get_version(jcls)
        print(f"{coord} {version}")
    print("======== END JAVA VERSIONS ========")
