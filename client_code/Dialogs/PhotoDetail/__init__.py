from anvil import *

from ._anvil_designer import PhotoDetailTemplate
from ... import pc, state


class PhotoDetail(PhotoDetailTemplate):
    """One photo of the drawer: rename it, see where it's used, delete it.
    Closes with {"renamed": True} / {"deleted": True, "quota"} / None (the photo dict is updated in place on rename)."""

    def __init__(self, photo=None, **properties):
        super().__init__(**properties)
        p = self.photo = photo or {}
        n = self.dom_nodes
        n["title"].textContent = p.get("label") or "Photo"
        n["img"].setAttribute("src", pc.photo(p.get("key")))
        n["img"].setAttribute("alt", p.get("label") or "Photo")
        self.label_box.text = p.get("label") or ""
        state.set_control_attr(self.label_box, "maxlength", 60)
        n["meta"].textContent = "%s · uploaded %s" % (pc.kb(p.get("size")), pc.fmt_date(p.get("created")))
        uses = p.get("uses") or []
        self.uses_part.visible = bool(uses)
        pc.show(n["unused"], not uses)
        self.uses_panel.items = uses
        self.uses_panel.add_event_handler("x-go", self._go)
        self._changed = False

    def _go(self, **event_args):
        self.raise_event("x-close-alert", value={"renamed": self._changed})

    @handle("label_box", "pressed_enter")
    def label_box_pressed_enter(self, **event_args):
        self.rename_button_click()

    @handle("rename_button", "click")
    def rename_button_click(self, **event_args):
        r = state.call("rename_photo", self.photo["key"], self.label_box.text or "")
        if r:
            self.photo["label"] = r["photo"]["label"]
            state.toast("Saved", "ok")
            self.raise_event("x-close-alert", value={"renamed": True})

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        uses = len(self.photo.get("uses") or [])
        text = ("It's in %s. Those spots keep the name and show a monogram instead." % state.plural(uses, "collage")) if uses else "This can't be undone."
        if not confirm(text, title="Delete this photo?", buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            return
        r = state.call("delete_photo", self.photo["key"])
        if r:
            self.raise_event("x-close-alert", value={"deleted": True, "quota": r["quota"]})

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value={"renamed": self._changed})
