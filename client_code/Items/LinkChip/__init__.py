from anvil import *

from ._anvil_designer import LinkChipTemplate
from ... import pc, state


class LinkChip(LinkChipTemplate):
    """A link shaped as a chip. item = {href, label, cls?, icon?, face? (photo key or None), on?}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it, n = self.item, self.dom_nodes
        pc.link(n["link"], it["href"])
        n["link"].className = (it.get("cls") if it.get("cls") is not None else "pc-chip") + (" on" if it.get("on") else "")
        if it.get("on"):
            n["link"].setAttribute("aria-current", "page")
        n["label"].textContent = it["label"]
        if it.get("icon"):
            n["icon"].className = "ic ic-" + it["icon"]
            pc.show(n["icon"], True)
        if "face" in it:
            pc.show(n["face"], True)
            if it["face"]:
                n["img"].setAttribute("src", pc.photo(it["face"], True))
                pc.show(n["img"], True)
            else:
                n["ini"].textContent = state.initials(it["label"])
