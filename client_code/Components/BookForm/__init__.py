import datetime

from anvil import *

from ._anvil_designer import BookFormTemplate
from ... import pc, state

STATUSES = [("Live: everyone sees it", "live"), ("Pending review", "pending"), ("Turned down (hidden)", "rejected")]


class BookForm(BookFormTemplate):
    """The book + characters form (members' Suggest a book, and the admin's Books tab). setup() fills it,
    values() returns the data for suggest_book / admin_save_book, or None after showing what's missing."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.tropes, self.chosen, self.chars, self.spice, self.cover_key = [], [], [], 2, pc.loose(None)
        self.status_box.items = STATUSES
        self.status_field.visible = False
        for box, limit in ((self.title_box, 120), (self.author_box, 80), (self.series_box, 80), (self.blurb_box, 1500)):
            state.set_control_attr(box, "maxlength", limit)
        state.set_control_attr(self.series_no_box, "min", 1)
        state.set_control_attr(self.series_no_box, "max", 99)
        self.tropes_panel.add_event_handler("x-chip", self._trope)
        self.chars_panel.add_event_handler("x-remove", self._remove_char)
        self.dom_nodes["file"].addEventListener("change", self._file)
        self.setup(None, [])

    def setup(self, book, tropes, admin=False):
        b: dict = book or {"title": "", "author": "", "series": "", "series_no": None, "release": "", "blurb": "", "tropes": [],
                     "spice": 2, "cover": None, "status": "live", "characters": []}
        self.tropes = list(tropes or [])
        self.chosen = list(b.get("tropes") or [])
        self.cover_key = b.get("cover")
        self.chars = [{"key": c.get("key"), "name": c["name"], "role": c.get("role"), "blurb": c.get("blurb") or "",
                       "status": c.get("status")} for c in b.get("characters") or []]
        if not self.chars:
            self.chars = [{"name": "", "role": "heroine", "blurb": ""}, {"name": "", "role": "love", "blurb": ""}]
        self.title_box.text = b.get("title") or ""
        self.author_box.text = b.get("author") or ""
        self.series_box.text = b.get("series") or ""
        self.series_no_box.text = "" if b.get("series_no") is None else str(b["series_no"])
        rel = b.get("release")
        self.release_box.date = datetime.date(int(rel[:4]), int(rel[5:7]), int(rel[8:10])) if rel else None
        self.blurb_box.text = b.get("blurb") or ""
        self.status_field.visible = bool(admin)
        self.status_box.selected_value = b.get("status") or "live"
        self.spice = int(b.get("spice") or 0)
        self._draw_cover()
        self._draw_spice()
        self._draw_tropes()
        self.chars_panel.items = self.chars

    def _draw_cover(self):
        self.cover.book = {"title": (self.title_box.text or "Cover"), "cover": self.cover_key}
        self.cover_remove_button.visible = bool(self.cover_key)

    def _draw_spice(self):
        for i, el in enumerate([self.sp0, self.sp1, self.sp2, self.sp3, self.sp4, self.sp5]):
            el.classes["on"] = (0 < i <= self.spice) or (i == 0 and self.spice == 0)
            state.set_attr(el, "aria-pressed", "true" if i == self.spice else "false")

    def _draw_tropes(self):
        self.tropes_panel.items = [{"label": t, "value": t, "on": t in self.chosen} for t in self.tropes]

    def spice_click(self, event):
        self.spice = int(event.currentTarget.getAttribute("data-v"))
        self._draw_spice()

    def _trope(self, **event_args):
        t = event_args.get("value")
        if t in self.chosen:
            self.chosen.remove(t)
        elif len(self.chosen) < 6:
            self.chosen.append(t)
        else:
            state.toast("Up to 6 tropes.")
            return
        key = state.focus_key()
        self._draw_tropes()
        state.refocus(self.tropes_panel, key)

    def _remove_char(self, **event_args):
        row = event_args["row"]
        self.chars = [c for c in self.chars if c is not row]
        self.chars_panel.items = self.chars

    @handle("add_char_button", "click")
    def add_char_button_click(self, **event_args):
        self.chars.append({"name": "", "role": "side", "blurb": ""})
        self.chars_panel.items = self.chars

    @handle("cover_remove_button", "click")
    def cover_remove_button_click(self, **event_args):
        self.cover_key = None
        self._draw_cover()

    def _file(self, event):
        inp = self.dom_nodes["file"]
        files = pc.loose(inp.files)
        f = files.item(0) if files.length else None
        inp.value = ""
        if f is None:
            return
        r = pc.upload_file(f, "cover")
        if r:
            self.cover_key = r["photo"]["key"]
            self._draw_cover()

    def values(self):
        title, author = (self.title_box.text or "").strip(), (self.author_box.text or "").strip()
        chars = [c for c in self.chars if (c.get("name") or "").strip()]
        if len(title) < 2:
            state.toast("The book needs a title.", "error")
            return None
        if len(author) < 2:
            state.toast("Who wrote it? Add the author.", "error")
            return None
        if not chars:
            state.toast("Add at least one character.", "error")
            return None
        rel = self.release_box.date
        return {"title": title, "author": author, "series": (self.series_box.text or "").strip(),
                "series_no": (self.series_no_box.text or "").strip(), "release": rel.isoformat() if rel else "",
                "blurb": self.blurb_box.text or "", "spice": self.spice, "tropes": list(self.chosen), "cover": self.cover_key,
                "status": self.status_box.selected_value, "characters": [dict(c, name=c["name"].strip()) for c in chars]}
