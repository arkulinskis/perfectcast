from anvil import *

from ._anvil_designer import CropTemplate
from ... import pc, state


class Crop(CropTemplate):
    """Frame a picked picture (PC.mountCrop: drag, pinch, wheel, zoom slider, arrow keys), then shrink it on the device.
    Closes with {full, thumb, bytes, label} (JPEG data URLs) or None."""

    def __init__(self, file=None, kind="portrait", label="", **properties):
        super().__init__(**properties)
        self._file, self._kind, self._ctl = file, kind, pc.loose(None)
        shape = "600×900" if kind == "cover" else "600×750"
        self.dom_nodes["title"].textContent = "Frame the cover" if kind == "cover" else "Frame the photo"
        self.dom_nodes["hint"].textContent = ("Drag to move, zoom with the slider. We save a small %s picture, so your "
                                              "drawer stays light." % shape)
        if kind == "cover":
            self.dom_nodes["frame"].classList.add("cover")
        self.name_field.visible = kind != "cover"
        self.name_box.text = label or ""
        state.set_control_attr(self.name_box, "maxlength", 60)

    @handle("", "show")
    def form_show(self, **event_args):
        if self._ctl is not None:
            return
        try:
            self._ctl = pc.window.PC.mountCrop(self.dom_nodes["frame"], self.dom_nodes["zoom"], self._file, self._kind)
        except Exception as e:
            self.message.text, self.message.visible = str(getattr(e, "message", "") or e), True
            return
        self.use_button.enabled = True

    def _done(self, value):
        if self._ctl is not None:
            self._ctl.destroy()
        self.raise_event("x-close-alert", value=value)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self._done(None)

    @handle("use_button", "click")
    def use_button_click(self, **event_args):
        r = self._ctl.result()
        self._done({"full": r.full, "thumb": r.thumb, "bytes": r.bytes, "label": (self.name_box.text or "").strip()})
