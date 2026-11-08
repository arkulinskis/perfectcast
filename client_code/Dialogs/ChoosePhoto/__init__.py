from anvil import *

from ._anvil_designer import ChoosePhotoTemplate
from ... import pc


class ChoosePhoto(ChoosePhotoTemplate):
    """A photo for a collage spot: upload a new one (crop dialog next) or reuse one from the drawer.
    Closes with {"key", "label"} for a drawer photo, {"file": File} for a new upload, or None."""

    def __init__(self, photos=(), label="", **properties):
        super().__init__(**properties)
        q = (label or "").lower()
        items = sorted(photos, key=lambda p: 0 if (p.get("label") or "").lower() == q and q else 1)
        self.dom_nodes["title"].textContent = "Choose a photo" + (" of " + label if label else "")
        self.dom_nodes["count"].textContent = "(%d)" % len(items)
        self.drawer_part.visible = bool(items)
        self.photos_panel.items = items
        self.photos_panel.add_event_handler("x-pick", self._pick)
        self.dom_nodes["file"].addEventListener("change", self._file)

    def _pick(self, **event_args):
        photo = event_args["photo"]
        self.raise_event("x-close-alert", value={"key": photo["key"], "label": photo.get("label") or ""})

    def _file(self, event):
        files = self.dom_nodes["file"].files
        if files and files.length:
            self.raise_event("x-close-alert", value={"file": pc.loose(files).item(0)})

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
