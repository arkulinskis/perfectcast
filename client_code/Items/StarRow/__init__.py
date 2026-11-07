from anvil import *

from ._anvil_designer import StarRowTemplate
from ... import pc, router, state


class StarRow(StarRowTemplate):
    """A row of the Stars leaderboard: rank, photo, name, their top role, collage count."""

    def __init__(self, **properties):
        super().__init__(**properties)
        s, n = self.item, self.dom_nodes
        pc.link(n["link"], router.href("stars", s["star"]))
        n["rank"].textContent = str(s.get("rank") or "")
        if s.get("photo"):
            n["img"].setAttribute("src", pc.photo(s["photo"], True))
            pc.show(n["img"], True)
        else:
            n["ini"].textContent = state.initials(s["name"])
        n["name"].textContent = s["name"]
        t = s.get("top_role")
        n["sub"].textContent = ("Top as %s · %s" % (t["name"], t["book"])) if t else ""
        n["casts"].textContent = str(s["casts"])
        n["unit"].textContent = "collage" if s["casts"] == 1 else "collages"
