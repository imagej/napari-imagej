from typing import Dict

from napari.utils import progress

from napari_imagej.java import jc


class ModuleProgressManager:
    def __init__(self):
        self.prog_bars: Dict[jc.Module, progress] = {}

    def init_progress(self, module: "jc.Module"):
        prog = progress(
            desc=str(module.getInfo().getTitle()),
            total=3,
        )
        self.prog_bars[module] = prog

    def update_progress(self, module: "jc.Module"):
        if pbr := self.prog_bars.get(module):
            pbr.update()
            if pbr.total == pbr.n:
                self.prog_bars.pop(module)
                pbr.close()


pm = ModuleProgressManager()
