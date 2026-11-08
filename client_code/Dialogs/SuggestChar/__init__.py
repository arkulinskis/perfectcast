import anvil.server
from anvil import *

from ._anvil_designer import SuggestCharTemplate
from ... import pc, state


class SuggestChar(SuggestCharTemplate):
    """A member adds a missing character to a live book (suggest_character). Closes with the server's message."""

    def __init__(self, book_key="", roles=None, **properties):
        super().__init__(**properties)
        self._key = book_key
        roles = roles or pc.ROLES
        self.role_box.items = [(label, k) for k, label in roles.items()]
        self.role_box.selected_value = "side"
        state.set_control_attr(self.name_box, "maxlength", 60)
        state.set_control_attr(self.blurb_box, "maxlength", 400)

    @handle("", "show")
    def form_show(self, **event_args):
        self.name_box.focus()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if len(name) < 2:
            self.message.text, self.message.visible = "What's the character called?", True
            return
        self.send_button.enabled = False
        try:
            r = anvil.server.call("suggest_character", self._key, name, self.role_box.selected_value, self.blurb_box.text or "")
        finally:
            self.send_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=r.get("message") or "Thanks!")
