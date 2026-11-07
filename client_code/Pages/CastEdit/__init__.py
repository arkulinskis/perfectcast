import anvil.js
import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import CastEditTemplate
from ... import pc, router, state


class CastEdit(CastEditTemplate):
    """#castedit/<characterKey>: the collage editor (members). Up to 6 stars, each with a name, a photo (upload + crop,
    or reuse from the drawer) and a "why"; make lead / move / remove; the fans' favourites as quick picks; layout,
    tone and caption; a live preview. One collage per fan per character: saving again updates it."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else ""
        d = anvil.server.call("get_editor", self.key)
        n = self.dom_nodes
        if not d.get("ok"):
            pc.show(n["main"], False)
            pc.show(n["missing"], True)
            n["missing_text"].textContent = d.get("error") or "That character isn't open for casting."
            return
        self.d = d
        c, b, dr = d["character"], d["book"], d.get("draft")
        self.title = "Cast " + c["name"]
        self.st: dict = {}
        if dr:
            self.st = {"picks": [{"name": p["name"], "photo": p.get("photo"), "note": p.get("note") or ""} for p in dr["picks"]],
                       "layout": dr["layout"], "tone": dr["tone"], "caption": dr.get("caption") or ""}
        else:
            self.st = {"picks": [self._blank()], "layout": "hero", "tone": "rose", "caption": ""}
        self.cover.book = b
        n["role"].textContent = c.get("role_label") or ""
        n["title"].textContent = ("Your " if dr else "Cast ") + c["name"]
        n["book_link"].textContent = b["title"]
        pc.link(n["book_link"], router.href("book", b["key"]))
        n["blurb"].textContent = (" · " + c["blurb"]) if c.get("blurb") else ""
        names = sorted(set([s["name"] for s in d.get("favourites") or []] + [p["label"] for p in d.get("photos") or [] if p.get("label")]))
        for name in names:
            opt = window.document.createElement("option")
            opt.setAttribute("value", name)
            n["names"].appendChild(opt)
        pc.show(n["favs"], bool(d.get("favourites")))
        self.caption_box.text = self.st["caption"]
        state.set_control_attr(self.caption_box, "maxlength", 280)
        state.set_control_attr(self.caption_box, "aria-label", "Caption")
        self.quota.quota = d.get("quota")
        self.save_button.text = "Save changes" if dr else "Publish my collage"
        if dr:
            n["second_link"].innerHTML = "See it live"
            pc.link(n["second_link"], router.href("cast", dr["key"]))
        else:
            n["second_link"].textContent = "Cancel"
            n["second_link"].className = "ui-btn ghost block"
            pc.link(n["second_link"], router.href("character", c["key"]))
        self.slots_panel.add_event_handler("x-slot", self._slot)
        self.slots_panel.add_event_handler("x-typed", self._typed)
        self.favs_panel.add_event_handler("x-chip", self._fav)
        self._draw_style()
        self._draw_slots()

    @staticmethod
    def _blank():
        return {"name": "", "photo": None, "note": ""}

    # ---- drawing
    def _draw_slots(self):
        picks, limit = self.st["picks"], self.d["max_picks"]
        for i, p in enumerate(picks):
            p["_i"], p["_n"] = i, len(picks)
        self.slots_panel.items = picks
        self.dom_nodes["count"].textContent = "%d of %d" % (len(picks), limit)
        self.add_button.enabled = len(picks) < limit
        self._draw_favs()
        self._draw_preview()

    def _draw_favs(self):
        names = set((p.get("name") or "").strip().lower() for p in self.st["picks"])
        self.favs_panel.items = [{"label": "%s · %d%%" % (s["name"], s["pct"]), "value": s["name"], "on": s["name"].lower() in names}
                                 for s in self.d.get("favourites") or []]

    def _preview_cast(self):
        picks = [{"name": (p.get("name") or "").strip() or "Who?", "photo": p.get("photo")}
                 for p in self.st["picks"] if (p.get("name") or "").strip() or p.get("photo")]
        return {"picks": picks, "layout": self.st["layout"], "tone": self.st["tone"]}

    def _draw_preview(self):
        self.preview.cast = self._preview_cast()
        self.dom_nodes["cap_preview"].textContent = self.st["caption"]

    def _draw_style(self):
        for k, el in (("hero", self.lay_hero), ("grid", self.lay_grid), ("polaroid", self.lay_polaroid), ("strip", self.lay_strip)):
            el.classes["on"] = self.st["layout"] == k
            state.set_attr(el, "aria-pressed", "true" if self.st["layout"] == k else "false")
        for k, el in (("rose", self.tone_rose), ("violet", self.tone_violet), ("crimson", self.tone_crimson), ("midnight", self.tone_midnight)):
            el.classes["on"] = self.st["tone"] == k
            state.set_attr(el, "aria-pressed", "true" if self.st["tone"] == k else "false")

    # ---- events
    def layout_click(self, event):
        self.st["layout"] = event.currentTarget.getAttribute("data-v")
        self._draw_style()
        self._draw_preview()

    def tone_click(self, event):
        self.st["tone"] = event.currentTarget.getAttribute("data-v")
        self._draw_style()
        self._draw_preview()

    @handle("caption_box", "change")
    def caption_box_change(self, **event_args):
        self.st["caption"] = self.caption_box.text or ""
        self._draw_preview()

    def _typed(self, **event_args):
        self._draw_preview()
        if event_args.get("done"):
            key = state.focus_key()
            self._draw_favs()
            state.refocus(self.favs_panel, key)

    def _add(self, name=""):
        picks, limit = self.st["picks"], self.d["max_picks"]
        empty = [p for p in picks if not (p.get("name") or "").strip() and not p.get("photo")]
        if not empty and len(picks) >= limit:
            state.toast("Up to %d stars per collage." % limit, "error")
            return
        if empty:
            empty[0]["name"] = name
        else:
            picks.append(self._blank())
            picks[-1]["name"] = name
        self._draw_slots()
        if not name:
            boxes = pc.loose(anvil.js.get_dom_node(self.slots_panel)).querySelectorAll(".anvil-role-ce-name input, input.anvil-role-ce-name")
            if boxes.length:
                boxes.item(boxes.length - 1).focus()

    @handle("add_button", "click")
    def add_button_click(self, **event_args):
        self._add("")

    def _fav(self, **event_args):
        name = event_args.get("value") or ""
        if any((p.get("name") or "").strip().lower() == name.lower() for p in self.st["picks"]):
            state.toast(name + " is already in your collage.")
            return
        self._add(name)

    def _slot(self, **event_args):
        picks, i, action = self.st["picks"], event_args["index"], event_args["action"]
        if action == "photo":
            self._choose_photo(i)
            return
        if action == "remove":
            picks.pop(i)
            if not picks:
                picks.append(self._blank())
        elif action == "lead":
            picks.insert(0, picks.pop(i))
        elif action == "move":
            j = i + event_args.get("step", 0)
            if not 0 <= j < len(picks):
                return
            picks[i], picks[j] = picks[j], picks[i]
        self._draw_slots()

    def _choose_photo(self, i):
        from ...Dialogs.ChoosePhoto import ChoosePhoto
        p = self.st["picks"][i]
        label = (p.get("name") or "").strip()
        got = alert(ChoosePhoto(photos=self.d["photos"], label=label), buttons=[], role="app-dialog", large=True)
        if not got:
            return
        if got.get("file") is not None:
            r = pc.upload_file(got["file"], "portrait", label)
            if not r:
                return
            self.d["photos"].insert(0, r["photo"])
            self.quota.quota = r["quota"]
            got = {"key": r["photo"]["key"], "label": r["photo"].get("label") or ""}
        p["photo"] = got["key"]
        if not label and got.get("label"):
            p["name"] = got["label"]
        self._draw_slots()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        picks = [p for p in self.st["picks"] if (p.get("name") or "").strip() or p.get("photo")]
        if not picks:
            state.toast("Add at least one star first.", "error")
            return
        if any(not (p.get("name") or "").strip() for p in picks):
            state.toast("Every star needs a name.", "error")
            return
        out = [{"name": p["name"].strip(), "photo": p.get("photo"), "note": (p.get("note") or "").strip()} for p in picks]
        self.save_button.enabled = False
        try:
            r = state.call("save_casting", self.key, self.st["caption"], self.st["layout"], self.st["tone"], out)
        finally:
            self.save_button.enabled = True
        if r:
            pc.hearts()
            state.toast("Your collage is live!" if r.get("created") else "Saved", "ok")
            router.go("cast", r["key"])
