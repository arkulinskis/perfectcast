from anvil import *

from ._anvil_designer import AdminBookTemplate
from ... import pc, router, state


class AdminBook(AdminBookTemplate):
    """Admin → Books: one book with View, Edit (x-edit) and Delete (x-delete)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b, n = self.item, self.dom_nodes
        self.cover.book = b
        n["title"].textContent = b["title"]
        n["meta"].textContent = " · ".join([b.get("author") or "", pc.fmt_date(b.get("release")) or "no date",
                                            state.plural(len(b.get("characters") or []), "character"),
                                            state.plural(b.get("casts") or 0, "collage")])
        st = b.get("status") or "live"
        n["status"].textContent = st
        n["status"].className = "ui-badge " + ("good" if st == "live" else "warn" if st == "pending" else "bad")
        pc.link(n["view"], router.href("book", b["key"]))

    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        self.parent.raise_event("x-edit", book=self.item)

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self.parent.raise_event("x-delete", book=self.item)
