from anvil import *

from ._anvil_designer import SlotTemplate
from ... import pc, state


class Slot(SlotTemplate):
    """One star in the collage editor: photo (choose / upload), name, "why", and make lead / remove / move.
    item = the editor's pick dict {name, photo, note} + "_i" (position) and "_n" (how many). Typing updates the
    dict in place and raises x-typed (the preview redraws); the buttons raise x-slot with an action."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p, n = self.item, self.dom_nodes
        i, count = p["_i"], p["_n"]
        n["row"].className = "ce-slot" + (" lead" if i == 0 and count > 1 else "")
        if p.get("photo"):
            n["img"].setAttribute("src", pc.photo(p["photo"], True))
            pc.show(n["img"], True)
            pc.show(n["add"], False)
            n["photo_btn"].classList.add("has")
        n["photo_btn"].setAttribute("aria-label", "Change photo" if p.get("photo") else "Add a photo")
        n["photo_btn"].addEventListener("click", self._photo)
        self.name_box.text = p.get("name") or ""
        self.note_box.text = p.get("note") or ""
        state.set_control_attr(self.name_box, "maxlength", 60)
        state.set_control_attr(self.name_box, "list", "ce-names")
        state.set_control_attr(self.name_box, "aria-label", "Star's name")
        state.set_control_attr(self.note_box, "maxlength", 140)
        state.set_control_attr(self.note_box, "aria-label", "Why them")
        self.lead_button.role = ["btn", "btn-ghost", "btn-icon", "ic-crown"] + (["on"] if i == 0 else [])
        self.up_button.enabled = i > 0
        self.down_button.enabled = i < count - 1

    def _send(self, action, **kw):
        self.parent.raise_event("x-slot", action=action, index=self.item["_i"], **kw)

    def _photo(self, event):
        self._send("photo")

    @handle("name_box", "change")
    def name_box_change(self, **event_args):
        self.item["name"] = self.name_box.text or ""
        self.parent.raise_event("x-typed")

    @handle("name_box", "lost_focus")
    def name_box_lost_focus(self, **event_args):
        self.parent.raise_event("x-typed", done=True)

    @handle("note_box", "change")
    def note_box_change(self, **event_args):
        self.item["note"] = self.note_box.text or ""

    @handle("lead_button", "click")
    def lead_button_click(self, **event_args):
        self._send("lead")

    @handle("remove_button", "click")
    def remove_button_click(self, **event_args):
        self._send("remove")

    @handle("up_button", "click")
    def up_button_click(self, **event_args):
        self._send("move", step=-1)

    @handle("down_button", "click")
    def down_button_click(self, **event_args):
        self._send("move", step=1)
