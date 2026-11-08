from anvil import *

from ._anvil_designer import CommentTemplate
from ... import pc, router, state


class Comment(CommentTemplate):
    """A comment under a collage. Delete / Report raise x-delete / x-report on the panel."""

    def __init__(self, **properties):
        super().__init__(**properties)
        x, n = self.item, self.dom_nodes
        user = x.get("user") or {}
        n["avatar"].textContent = state.initials(user.get("name"))
        n["who"].textContent = user.get("name") or "A fan"
        if user.get("id"):
            pc.link(n["who"], router.href("fan", user["id"]))
        else:
            n["who"].removeAttribute("href")
        n["ago"].textContent = state.ago(x.get("created"))
        n["body"].textContent = x.get("body") or ""
        self.delete_button.visible = bool(x.get("can_delete"))
        self.report_button.visible = not x.get("mine") and bool(state.me())

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self.parent.raise_event("x-delete", comment=self.item)

    @handle("report_button", "click")
    def report_button_click(self, **event_args):
        self.parent.raise_event("x-report", comment=self.item)
