from anvil import *

from ._anvil_designer import SoonCardTemplate
from ... import pc, router


class SoonCard(SoonCardTemplate):
    """A coming-soon book with its countdown in days."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b, n = self.item, self.dom_nodes
        pc.link(n["link"], router.href("book", b["key"]))
        self.cover.book = b
        n["title"].textContent = b["title"]
        n["author"].textContent = b.get("author") or ""
        self.spice.level = b.get("spice") or 0
        d = pc.days(b.get("release")) or 0
        n["days"].textContent = str(d)
        n["unit"].textContent = "day" if d == 1 else "days"
