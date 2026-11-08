from anvil import *

from ._anvil_designer import BookCardTemplate
from ... import pc, router


class BookCard(BookCardTemplate):
    """A book on the shelf: cover (New / Soon badge), title, author, release line, collage count."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b, n = self.item, self.dom_nodes
        pc.link(n["link"], router.href("book", b["key"]))
        self.cover.badge = pc.badge_for(b.get("release"))
        self.cover.book = b
        n["title"].textContent = b["title"]
        n["author"].textContent = b.get("author") or ""
        pc.set_when(n["when"], b.get("release"))
        n["casts_n"].textContent = str(b.get("casts") or 0)
        n["casts"].setAttribute("aria-label", "%d collages" % (b.get("casts") or 0))
        pc.show(n["casts"], bool(b.get("casts")))
