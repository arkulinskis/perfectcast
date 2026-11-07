from anvil import *

from ._anvil_designer import ChipTemplate


class Chip(ChipTemplate):
    """A toggle chip (tropes, fans' favourites). item = {label, value, on}. Click raises x-chip on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        btn = self.dom_nodes["btn"]
        btn.textContent = self.item["label"]
        btn.setAttribute("data-key", str(self.item.get("value", "")))
        on = bool(self.item.get("on"))
        btn.classList.toggle("on", on)
        btn.setAttribute("aria-pressed", "true" if on else "false")
        btn.addEventListener("click", self._click)

    def _click(self, event):
        self.parent.raise_event("x-chip", value=self.item.get("value"), item=self.item)
