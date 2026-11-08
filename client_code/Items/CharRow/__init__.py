from anvil import *

from ._anvil_designer import CharRowTemplate
from ... import pc, state


class CharRow(CharRowTemplate):
    """A character in the book form. Edits go straight into item (the form's list); Remove raises x-remove."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c = self.item
        self.name_box.text = c.get("name") or ""
        self.role_box.items = [(label, k) for k, label in pc.ROLES.items()]
        self.role_box.selected_value = c.get("role") if c.get("role") in pc.ROLES else "side"
        self.blurb_box.text = c.get("blurb") or ""
        pc.show(self.dom_nodes["pending"], c.get("status") == "pending")
        state.set_control_attr(self.name_box, "maxlength", 60)
        state.set_control_attr(self.name_box, "aria-label", "Character name")
        state.set_control_attr(self.role_box, "aria-label", "Role")
        state.set_control_attr(self.blurb_box, "maxlength", 400)
        state.set_control_attr(self.blurb_box, "aria-label", "About the character")

    @handle("name_box", "change")
    def name_box_change(self, **event_args):
        self.item["name"] = self.name_box.text or ""

    @handle("role_box", "change")
    def role_box_change(self, **event_args):
        self.item["role"] = self.role_box.selected_value

    @handle("blurb_box", "change")
    def blurb_box_change(self, **event_args):
        self.item["blurb"] = self.blurb_box.text or ""

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self.parent.raise_event("x-remove", row=self.item)
