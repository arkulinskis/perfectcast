from anvil import *

from ._anvil_designer import QueueBookTemplate
from ... import pc, state


class QueueBook(QueueBookTemplate):
    """Admin → Review: a book a member suggested. Approve / Turn down raise x-review; Edit first raises x-edit."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b, n = self.item, self.dom_nodes
        self.cover.book = b
        n["title"].textContent = b["title"]
        n["author"].textContent = "by " + (b.get("author") or "")
        by = (b.get("submitted_by") or {}).get("name") or "someone"
        n["meta"].textContent = "Suggested by %s · %s · %s" % (by, state.ago(b.get("submitted_at")),
                                                               ("out " + pc.fmt_date(b["release"])) if b.get("release") else "no date")
        n["blurb"].textContent = b.get("blurb") or ""
        pc.show(n["blurb"], bool(b.get("blurb")))
        n["chars"].textContent = ", ".join("%s (%s)" % (c["name"], c.get("role_label") or "") for c in b.get("characters") or [])

    @handle("approve_button", "click")
    def approve_button_click(self, **event_args):
        self.parent.raise_event("x-review", kind="book", key=self.item["key"], decision="approve")

    @handle("reject_button", "click")
    def reject_button_click(self, **event_args):
        self.parent.raise_event("x-review", kind="book", key=self.item["key"], decision="reject")

    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        self.parent.raise_event("x-edit", key=self.item["key"])
