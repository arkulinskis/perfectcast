from anvil import *

from ._anvil_designer import DrawerPickTemplate
from ... import pc


class DrawerPick(DrawerPickTemplate):
    """A photo in the "choose a photo" dialog's drawer grid. Click raises x-pick on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, n = self.item, self.dom_nodes
        n["img"].setAttribute("src", pc.photo(p["key"], True))
        n["img"].setAttribute("alt", p.get("label") or "A photo from your drawer")
        n["label"].textContent = p.get("label") or ""
        pc.show(n["label"], bool(p.get("label")))
        n["btn"].setAttribute("title", p.get("label") or "")
        n["btn"].addEventListener("click", self._click)

    def _click(self, event):
        self.parent.raise_event("x-pick", photo=self.item)
