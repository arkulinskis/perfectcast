from anvil import *

from ._anvil_designer import BookEditTemplate
from ... import state


class BookEdit(BookEditTemplate):
    """Admin: add or edit a book with its whole character list (admin_save_book). Closes with True when saved."""

    def __init__(self, book=None, tropes=(), **properties):
        super().__init__(**properties)
        self.book = book
        self.dom_nodes["title"].textContent = ("Edit " + book["title"]) if book else "Add a book"
        self.form.setup(book, tropes, admin=True)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        v = self.form.values()
        if not v:
            return
        b = self.book
        kept = set(c.get("key") for c in v["characters"] if c.get("key"))
        lost = [c for c in (b or {}).get("characters", []) if c["key"] not in kept and c.get("casts")]
        if lost and not confirm("Their collages (%d) are deleted too." % sum(c["casts"] for c in lost),
                                title="Remove %s?" % ", ".join(c["name"] for c in lost),
                                buttons=[("Cancel", False), ("Save anyway", True)], role="app-dialog"):
            return
        self.save_button.enabled = False
        try:
            r = state.call("admin_save_book", b["key"] if b else None, v)
        finally:
            self.save_button.enabled = True
        if r:
            state.toast("Saved", "ok")
            self.raise_event("x-close-alert", value=True)
