from anvil import *

from ._anvil_designer import HeartTemplate
from ... import pc, state


class Heart(HeartTemplate):
    """Swoon over a collage: toggle_heart, then the count, the filled heart and a little pop."""

    def __init__(self, **properties):
        self._cast, self._big, self._ready = {}, False, False
        super().__init__(**properties)
        self.dom_nodes["btn"].addEventListener("click", self._click)
        self._ready = True
        self._draw()

    def _draw(self):
        c = self._cast
        if not self._ready or not c:
            return
        n = self.dom_nodes
        on = bool(c.get("hearted"))
        n["btn"].className = "pc-heart" + (" on" if on else "") + (" lg" if self._big else "")
        n["btn"].setAttribute("aria-pressed", "true" if on else "false")
        n["btn"].setAttribute("title", "Your collage" if c.get("mine") else "Swoon")
        n["btn"].setAttribute("aria-label", "Swoon (%d)" % int(c.get("hearts") or 0))
        n["icon"].className = "ic " + ("ic-heartfill" if on else "ic-heart")
        n["count"].textContent = str(int(c.get("hearts") or 0))

    def _click(self, event):
        event.preventDefault()
        btn = self.dom_nodes["btn"]
        if not pc.need_sign_in("Sign up to swoon over collages."):
            return
        r = state.call("toggle_heart", self._cast["key"])
        if not r:
            return
        self._cast["hearted"], self._cast["hearts"] = r["hearted"], r["hearts"]
        self._draw()
        if r["hearted"]:
            btn.classList.add("pop")
            pc.window.setTimeout(lambda: btn.classList.remove("pop"), 500)

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
