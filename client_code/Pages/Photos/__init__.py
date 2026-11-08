import anvil.server
from anvil import *

from ._anvil_designer import PhotosTemplate
from ... import pc, router, state


class Photos(PhotosTemplate):
    """#photos: the member's photo drawer. Quota meter, upload several at once (each one cropped and shrunk),
    filter (all / in use / unused / covers), search by name, rename, see where a photo is used, delete one or many
    (select mode, "select all unused")."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.filter, self.selecting, self.picked = "all", False, set()
        state.set_control_attr(self.search_box, "aria-label", "Find a photo by name")
        state.set_control_attr(self.search_box, "type", "search")
        self.grid_panel.add_event_handler("x-tile", self._tile)
        self.dom_nodes["file"].addEventListener("change", self._files)
        self.d = anvil.server.call("list_photos")
        limit = self.d["quota"].get("max")
        self.dom_nodes["limit_line"].textContent = ("You can keep up to %s photos. Deleting one that's in a collage leaves the "
                                                    "star's name with a monogram." % (limit or "unlimited"))
        self._draw()

    def _visible(self):
        q = (self.search_box.text or "").strip().lower()
        out = []
        for p in self.d["photos"]:
            if self.filter == "used" and not p.get("uses"):
                continue
            if self.filter == "unused" and p.get("uses"):
                continue
            if self.filter == "cover" and p.get("kind") != "cover":
                continue
            if q and q not in (p.get("label") or "").lower():
                continue
            out.append(p)
        return out

    def _draw(self):
        n = self.dom_nodes
        rows = self._visible()
        for p in rows:
            p["_on"], p["_selecting"] = p["key"] in self.picked, self.selecting
        self.grid_panel.items = rows
        has = bool(self.d["photos"])
        pc.show(n["empty"], not rows)
        n["empty_h"].textContent = "Nothing here" if has else "Your drawer is empty"
        n["empty_p"].textContent = ("Try another filter." if has else
                                    "Upload photos of the stars you'd cast. You can reuse each one in as many collages as you like.")
        self.quota.quota = self.d["quota"]
        for key, el in (("all", self.f_all), ("used", self.f_used), ("unused", self.f_unused), ("cover", self.f_cover)):
            el.classes["on"] = self.filter == key
        self.bulk.visible = self.selecting
        n["bulk_n"].textContent = state.plural(len(self.picked), "photo") + " selected"
        self.bulk_delete_button.enabled = bool(self.picked)
        self.select_button.text = "Done" if self.selecting else "Select"
        n["grid"].classList.toggle("ph-select", self.selecting)

    def filter_click(self, event):
        self.filter = event.currentTarget.getAttribute("data-f")
        self._draw()

    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self._draw()

    @handle("select_button", "click")
    def select_button_click(self, **event_args):
        self.selecting, self.picked = not self.selecting, set()
        self._draw()

    @handle("unused_button", "click")
    def unused_button_click(self, **event_args):
        for p in self._visible():
            if not p.get("uses") and p.get("kind") != "cover":
                self.picked.add(p["key"])
        self._draw()

    def _tile(self, **event_args):
        p = event_args["photo"]
        if self.selecting:
            key = state.focus_key()
            if p["key"] in self.picked:
                self.picked.discard(p["key"])
            else:
                self.picked.add(p["key"])
            self._draw()
            state.refocus(self.grid_panel, key)
            return
        from ...Dialogs.PhotoDetail import PhotoDetail
        r = alert(PhotoDetail(photo=p), buttons=[], role="app-dialog", large=True)
        if not r:
            return
        if r.get("deleted"):
            self.d["photos"] = [x for x in self.d["photos"] if x["key"] != p["key"]]
            self.d["quota"] = r["quota"]
            state.toast("Photo deleted")
        self._draw()

    def _files(self, event):
        inp = self.dom_nodes["file"]
        files = pc.loose(inp.files)
        picked = [files.item(i) for i in range(files.length)]
        inp.value = ""
        for f in picked:
            r = pc.upload_file(f, "portrait")
            if r:
                self.d["photos"].insert(0, r["photo"])
                self.d["quota"] = r["quota"]
                self._draw()

    @handle("bulk_delete_button", "click")
    def bulk_delete_button_click(self, **event_args):
        keys = list(self.picked)
        if not confirm("Collage spots using them keep the star's name with a monogram.", title="Delete %s?" % state.plural(len(keys), "photo"),
                       buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            return
        gone = 0
        for k in keys:
            r = state.call("delete_photo", k)
            if r:
                gone += 1
                self.d["quota"] = r["quota"]
                self.d["photos"] = [x for x in self.d["photos"] if x["key"] != k]
        self.picked, self.selecting = set(), False
        self._draw()
        state.toast(state.plural(gone, "photo") + " deleted", "ok")
