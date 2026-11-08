from anvil import *

from ._anvil_designer import StarLineTemplate
from ... import pc, router, state


class StarLine(StarLineTemplate):
    """A star in a collage (the collage page): photo, name, Lead badge, the fan's "why"."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, n = self.item, self.dom_nodes
        if p.get("photo"):
            n["img"].setAttribute("src", pc.photo(p["photo"], True))
            pc.show(n["img"], True)
        else:
            n["ini"].textContent = state.initials(p["name"])
        n["link"].textContent = p["name"]
        if p.get("star"):
            pc.link(n["link"], router.href("stars", p["star"]))
        pc.show(n["lead"], bool(p.get("_lead")))
        n["note"].textContent = ("“%s”" % p["note"]) if p.get("note") else ""
        pc.show(n["note"], bool(p.get("note")))
