from anvil import *

from ._anvil_designer import ReportRowTemplate
from ... import pc, router, state


class ReportRow(ReportRowTemplate):
    """Admin → Reports: one report with the comment or collage it is about. The buttons raise x-resolve / x-unhide."""

    def __init__(self, **properties):
        super().__init__(**properties)
        r, n = self.item, self.dom_nodes
        t = r.get("target") or {}
        c = t.get("cast")
        n["reason"].textContent = r.get("reason") or ""
        n["by"].textContent = (r.get("by") or {}).get("name") or ""
        n["when"].textContent = pc.fmt_date(r.get("created")) + " · " + state.ago(r.get("created"))
        pc.show(n["done"], r.get("status") != "open")
        n["note"].textContent = r.get("note") or ""
        pc.show(n["note"], bool(r.get("note")))
        is_comment = t.get("kind") == "comment"
        pc.show(n["quote"], is_comment)
        if is_comment:
            n["quote_by"].textContent = (t.get("by") or {}).get("name") or ""
            n["quote_head"].textContent = "commented" + (" (hidden)" if t.get("hidden") else "") + ":"
            n["quote_body"].textContent = t.get("body") or ""
        self.prev.visible = bool(c)
        pc.show(n["gone"], not c)
        if c:
            pc.link(n["cast_link"], router.href("cast", c["key"]))
            self.collage.cast = c
            n["cast_by"].textContent = (c.get("user") or {}).get("name") or ""
            n["cast_for"].textContent = "'s " + ((c.get("character") or {}).get("name") or "")
            pc.show(n["cast_hidden"], bool(c.get("hidden")))
            n["cast_cap"].textContent = c.get("caption") or ""
            self.unhide_button.visible = bool(c.get("hidden"))
        self.actions.visible = r.get("status") == "open"
        self.hide_button.text = "Hide the " + ("comment" if is_comment else "collage")

    def _resolve(self, action):
        self.parent.raise_event("x-resolve", report=self.item, action=action)

    @handle("dismiss_button", "click")
    def dismiss_button_click(self, **event_args):
        self._resolve("dismiss")

    @handle("hide_button", "click")
    def hide_button_click(self, **event_args):
        self._resolve("hide")

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        self._resolve("delete")

    @handle("unhide_button", "click")
    def unhide_button_click(self, **event_args):
        self.parent.raise_event("x-unhide", key=self.item["target"]["cast"]["key"])
