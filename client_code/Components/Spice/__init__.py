from anvil import *

from ._anvil_designer import SpiceTemplate


class Spice(SpiceTemplate):
    """Spice 0-5 as flames (the unlit ones are faint)."""

    def __init__(self, **properties):
        self._level, self._ready = 0, False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        if not self._ready:
            return
        n = self.dom_nodes
        label = "Spice %d of 5" % self._level
        n["box"].setAttribute("aria-label", label)
        n["box"].setAttribute("title", label)
        for i, f in enumerate([n["f1"], n["f2"], n["f3"], n["f4"], n["f5"]]):
            f.classList.toggle("off", i >= self._level)

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        try:
            self._level = max(0, min(5, int(value or 0)))
        except (TypeError, ValueError):
            self._level = 0
        self._draw()
