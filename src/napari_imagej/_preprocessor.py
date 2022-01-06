from qtpy.QtWidgets import QWidget
from jpype import JOverride, JImplements
from scyjava import jimport

def popup_window():
    print('processing in napari!')
    # popup = QWidget()
    # popup.show()


@JImplements(('org.scijava.module.process.PreprocessorPlugin', 'org.scijava.Contextual'), deferred=True)
class NapariPreprocessor():
    def __init__(self) -> None:
        self.cancelReason = None
        self.context = None
    
    @JOverride
    def process(self, module):
        popup_window()
        for input in module.getInfo().inputs():
            if module.isInputResolved(input.getName()):
                continue
        
    
    # Contextual Methods
            
    @JOverride
    def context(self):
        if self.context == None:
            NullContextException = jimport('org.scijava.NullContextException')
            raise NullContextException()
        return self.context
    
    @JOverride
    def getContext(self):
        return self.context

    # Cancellable Methods
    
    @JOverride
    def isCanceled(self):
        return self.cancelReason != None
    
    @JOverride
    def cancel(self, reason: str = "") -> None:
        self.cancelReason = reason
    
    @JOverride
    def getCancelReason(self) -> str:
        return self.cancelReason