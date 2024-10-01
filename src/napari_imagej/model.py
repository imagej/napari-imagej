from jpype import JImplements, JOverride

from napari_imagej.java import init_ij, jc


class NapariImageJ:
    """
    An object offering a central access point to napari-imagej's core business logic.
    """

    def __init__(self):
        self._ij = None
        self._repl = None
        self._repl_callbacks = []

    @property
    def ij(self):
        if self._ij is None:
            self._ij = init_ij()
        return self._ij

    @property
    def repl(self) -> "jc.ScriptREPL":
        if self._repl is None:
            ctx = self.ij.context()
            model = self

            @JImplements("java.util.function.Consumer")
            class REPLOutput:
                @JOverride
                def accept(self, t):
                    s = str(t)
                    for callback in model._repl_callbacks:
                        callback(s)

            scriptService = ctx.service(jc.ScriptService)
            # Find a Pythonic script language (might be Jython)
            names = [lang.getLanguageName() for lang in scriptService.getLanguages()]
            name_pref = next(n for n in names if "python" in n.toLowerCase())
            self._repl = jc.ScriptREPL(ctx, name_pref, REPLOutput())
            # NB: Adds bindings
            self._repl.initialize(True)
        return self._repl

    def add_repl_callback(self, repl_callback) -> None:
        self._repl_callbacks.append(repl_callback)
