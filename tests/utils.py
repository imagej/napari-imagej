from napari_imagej.java import JavaClasses


class JavaClassesTest(JavaClasses):
    """
    Here we override JavaClasses to get extra test imports
    """

    @JavaClasses.blocking_import
    def ArrayImg(self):
        return "net.imglib2.img.array.ArrayImg"

    @JavaClasses.blocking_import
    def ArrayImgs(self):
        return "net.imglib2.img.array.ArrayImgs"

    @JavaClasses.blocking_import
    def ClassSearchResult(self):
        return "org.scijava.search.classes.ClassSearchResult"

    @JavaClasses.blocking_import
    def DefaultMutableModuleItem(self):
        return "org.scijava.module.DefaultMutableModuleItem"

    @JavaClasses.blocking_import
    def DefaultMutableModuleInfo(self):
        return "org.scijava.module.DefaultMutableModuleInfo"

    @JavaClasses.blocking_import
    def DoubleArray(self):
        return "org.scijava.util.DoubleArray"

    @JavaClasses.blocking_import
    def EuclideanSpace(self):
        return "net.imglib2.EuclideanSpace"

    @JavaClasses.blocking_import
    def ItemIO(self):
        return "org.scijava.ItemIO"

    @JavaClasses.blocking_import
    def ScriptInfo(self):
        return "org.scijava.script.ScriptInfo"

    @JavaClasses.blocking_import
    def System(self):
        return "java.lang.System"


jc = JavaClassesTest()


jc = JavaClassesTest()


class DummySearcher:
    def __init__(self, title: str):
        self._title = title

    def search(self, text: str, fuzzy: bool):
        pass

    def title(self):
        return self._title


class DummyModuleInfo:
    """
    A mock of org.scijava.module.ModuleInfo that is created much easier
    Fields can and should be added as needed for tests.
    """

    def __init__(self, inputs=[], outputs=[]):
        self._inputs = inputs
        self._outputs = outputs

    def outputs(self):
        return self._outputs


class DummyModuleItem:
    """
    A mock of org.scijava.module.ModuleItem that is created much easier
    Fields can and should be added as needed for tests.
    """

    def __init__(
        self,
        name="",
        jtype=jc.String,
        isRequired=True,
        isInput=True,
        isOutput=False,
        default=None,
    ):
        self._name = name
        self._jtype = jtype
        self._isRequired = isRequired
        self._isInput = isInput
        self._isOutput = isOutput
        self._default = default

    def getName(self):
        return self._name

    def getType(self):
        return self._jtype

    def isRequired(self):
        return self._isRequired

    def isInput(self):
        return self._isInput

    def isOutput(self):
        return self._isOutput

    def getDefaultValue(self):
        return self._default

    def getMaximumValue(self):
        return self._maximumValue

    def setMaximumValue(self, val):
        self._maximumValue = val

    def getMinimumValue(self):
        return self._minimumValue

    def setMinimumValue(self, val):
        self._minimumValue = val

    def getStepSize(self):
        return self._stepSize

    def setStepSize(self, val):
        self._stepSize = val

    def getLabel(self):
        return self._label

    def setLabel(self, val):
        self._label = val

    def getDescription(self):
        return self._description

    def setDescription(self, val):
        self._description = val

    def getChoices(self):
        return self._choices

    def setChoices(self, val):
        self._choices = val

    def getWidgetStyle(self):
        return self._style

    def setWidgetStyle(self, val):
        self._style = val
