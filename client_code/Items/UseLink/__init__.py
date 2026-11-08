from anvil import *

from ._anvil_designer import UseLinkTemplate
from ... import pc, router


class UseLink(UseLinkTemplate):
    """Where a photo is used (the photo dialog): a collage or a book cover. Click raises x-go (closes the dialog)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        u, n = self.item, self.dom_nodes
        n["link"].textContent = u.get("character") or ""
        pc.link(n["link"], router.href("cast", u["casting"]) if u.get("casting") else router.href("book", u.get("book")))
        n["link"].addEventListener("click", self._click)

    def _click(self, event):
        self.parent.raise_event("x-go")
