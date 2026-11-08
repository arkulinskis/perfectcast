from anvil import *

from ._anvil_designer import VoteBarTemplate
from ... import pc, router


class VoteBar(VoteBarTemplate):
    """A star's share of the vote for a character. item = a consensus row {name, star, pct, votes}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        s, n = self.item, self.dom_nodes
        n["link"].textContent = s["name"]
        pc.link(n["link"], router.href("stars", s["star"]))
        n["pct"].textContent = "%d%%" % s["pct"]
        n["bar"].style.width = "%d%%" % max(4, s["pct"])
