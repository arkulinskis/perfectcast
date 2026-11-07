from anvil import *

from ._anvil_designer import ReportTemplate
from ... import state


class Report(ReportTemplate):
    """Flag a collage or a comment for the admins (report). Closes with True when sent."""

    def __init__(self, kind="casting", target="", **properties):
        super().__init__(**properties)
        self._kind, self._target = kind, target
        self.dom_nodes["title"].textContent = "Report this " + ("comment" if kind == "comment" else "collage")
        state.set_control_attr(self.note_box, "maxlength", 400)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        reason = "rude"
        for rb in (self.r_rude, self.r_spam, self.r_explicit, self.r_privacy, self.r_other):
            if rb.selected:
                reason = rb.value
        self.send_button.enabled = False
        try:
            r = state.call("report", self._kind, self._target, reason, self.note_box.text or "")
        finally:
            self.send_button.enabled = True
        if r:
            state.toast(r.get("message") or "Thank you.", "ok")
            self.raise_event("x-close-alert", value=True)
