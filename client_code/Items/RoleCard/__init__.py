from anvil import *

from ._anvil_designer import RoleCardTemplate
from ... import pc, router, state


class RoleCard(RoleCardTemplate):
    """A role a star was cast in (their star page): the book, rank in the vote, share of collages."""

    def __init__(self, **properties):
        super().__init__(**properties)
        r, n = self.item, self.dom_nodes
        pc.link(n["link"], router.href("character", r["key"]))
        self.cover.book = r["book"]
        first = r["rank"] == 1
        n["rank"].textContent = "Fans' pick" if first else "#%d" % r["rank"]
        n["rank"].className = "ui-badge" + (" brand" if first else "")
        n["role"].textContent = r.get("role_label") or ""
        n["name"].textContent = r["name"]
        n["book"].textContent = r["book"]["title"]
        n["bar"].style.width = "%d%%" % max(4, r["pct"])
        n["pct"].textContent = "%d%% of collages · %s" % (r["pct"], state.plural(r["votes"], "vote"))
