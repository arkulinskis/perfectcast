from anvil import *

from ._anvil_designer import PhotoTileTemplate
from ... import pc


class PhotoTile(PhotoTileTemplate):
    """A photo in the drawer. item = a photo + "_on" (selected). Click raises x-tile on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, n = self.item, self.dom_nodes
        n["btn"].className = "ph-tile" + (" cover" if p.get("kind") == "cover" else "") + (" on" if p.get("_on") else "")
        n["btn"].setAttribute("data-key", p["key"])
        if p.get("_selecting"):
            n["btn"].setAttribute("aria-pressed", "true" if p.get("_on") else "false")
        n["img"].setAttribute("src", pc.photo(p["key"], True))
        n["img"].setAttribute("alt", p.get("label") or "Photo without a name")
        uses = len(p.get("uses") or [])
        n["use"].textContent = ("In %d" % uses) if uses else "Unused"
        n["use"].className = "use ui-badge" + (" brand" if uses else "")
        n["label"].textContent = p.get("label") or "No name"
        n["label"].classList.toggle("muted", not p.get("label"))
        n["meta"].textContent = "%s · %s" % (pc.kb(p.get("size")), pc.fmt_date(p.get("created"), "short"))
        n["btn"].addEventListener("click", self._click)

    def _click(self, event):
        self.parent.raise_event("x-tile", photo=self.item)
