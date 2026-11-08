from anvil import *

from ._anvil_designer import QueueCharTemplate
from ... import pc, router, state


class QueueChar(QueueCharTemplate):
    """Admin → Review: a character a member added to a live book. Approve / Turn down raise x-review."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c, n = self.item, self.dom_nodes
        n["name"].textContent = c["name"]
        n["role"].textContent = c.get("role_label") or ""
        n["book"].textContent = c["book"]["title"]
        pc.link(n["book"], router.href("book", c["book"]["key"]))
        n["meta"].textContent = "by %s · %s" % ((c.get("by") or {}).get("name") or "someone", state.ago(c.get("submitted_at")))
        n["blurb"].textContent = c.get("blurb") or ""
        pc.show(n["blurb"], bool(c.get("blurb")))

    @handle("approve_button", "click")
    def approve_button_click(self, **event_args):
        self.parent.raise_event("x-review", kind="character", key=self.item["key"], decision="approve")

    @handle("reject_button", "click")
    def reject_button_click(self, **event_args):
        self.parent.raise_event("x-review", kind="character", key=self.item["key"], decision="reject")
