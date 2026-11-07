from anvil import *

from ._anvil_designer import CollageTemplate
from ... import pc


class Collage(CollageTemplate):
    """A collage drawn by the JavaScript engine (PC.collage: 4 layouts x 4 tones, CSS .pc-col in app.css)."""

    def __init__(self, **properties):
        self._cast, self._big, self._ready = {}, False, False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        if self._ready and self._cast:
            self.dom_nodes["box"].innerHTML = pc.window.PC.collage(pc.js(self._cast), pc.js({"big": self._big}))

    @property
    def cast(self):
        return self._cast

    @cast.setter
    def cast(self, value):
        self._cast = value
        self._draw()

    @property
    def big(self):
        return self._big

    @big.setter
    def big(self, value):
        self._big = bool(value)
        self._draw()
