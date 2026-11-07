from anvil import *

from ._anvil_designer import PodiumStepTemplate
from ... import pc, state


class PodiumStep(PodiumStepTemplate):
    """One step of a podium (the fans' pick on a character page, the Stars leaderboard).
    item = {href, name, photo, rank (1-3), line, thumb, style ("cp" medal / "st" rank)}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        s, n = self.item, self.dom_nodes
        pc.link(n["link"], s["href"])
        n["link"].className = "first" if s["rank"] == 1 else ""
        n["medal"].className = "medal" if s.get("style") == "cp" else "rank"
        n["medal"].textContent = str(s["rank"]) if s.get("style") == "cp" else "#%d" % s["rank"]
        if s.get("photo"):
            n["img"].setAttribute("src", pc.photo(s["photo"], s.get("thumb")))
            n["img"].setAttribute("alt", s["name"])
            pc.show(n["img"], True)
            pc.show(n["mono"], False)
        n["mono"].textContent = state.initials(s["name"])
        n["name"].textContent = s["name"]
        n["line"].textContent = s.get("line") or ""
