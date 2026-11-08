import anvil.server
from anvil import *

from ._anvil_designer import CharacterTemplate
from ... import pc, router, state


class Character(CharacterTemplate):
    """#character/<key>: one character. The fans' pick (podium of the three most-cast stars + vote bars), every
    collage (most swooned / newest), the other characters of the book. Open to everyone."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else ""
        self.sort = "loved"
        self._load()

    def _load(self):
        d = anvil.server.call("get_character", self.key, self.sort)
        n = self.dom_nodes
        if not d.get("ok"):
            pc.show(n["main"], False)
            pc.show(n["missing"], True)
            n["missing_text"].textContent = d.get("error") or "That character isn't here."
            return
        c, b = d["character"], d["book"]
        self.title = c["name"]
        pc.link(n["cover_link"], router.href("book", b["key"]))
        self.cover.book = b
        n["role"].textContent = c.get("role_label") or ""
        n["name"].textContent = c["name"]
        n["book_link"].textContent = b["title"]
        pc.link(n["book_link"], router.href("book", b["key"]))
        n["author"].textContent = "by " + (b.get("author") or "")
        n["blurb"].textContent = c.get("blurb") or ""
        pc.show(n["blurb"], bool(c.get("blurb")))
        live = b.get("status") == "live"
        label = "Edit your collage" if d.get("mine") else "Cast " + c["name"].split(" ")[0]
        for btn in (self.cast_button, self.cast_button_2):
            btn.visible = live
            btn.text = label
            btn.role = ["btn", "btn-primary"] + (["btn-lg"] if btn is self.cast_button else []) + ["ic-edit" if d.get("mine") else "ic-sparkle"]
        self.sibs_panel.items = [{"href": router.href("character", s["key"]), "label": s["name"], "face": s.get("photo"),
                                  "on": bool(s.get("current")), "cls": ""} for s in d.get("siblings") or []]
        cons = d.get("consensus") or []
        top = cons[:3]
        order = [1, 0, 2] if len(top) >= 3 else ([1, 0] if len(top) == 2 else [0] if top else [])
        self.podium_panel.items = [{"href": router.href("stars", top[i]["star"]), "name": top[i]["name"], "photo": top[i].get("photo"),
                                    "thumb": i > 0, "rank": i + 1, "style": "cp",
                                    "line": "%d%% · %s" % (top[i]["pct"], state.plural(top[i]["votes"], "vote"))} for i in order]
        n["podium"].style.gridTemplateColumns = "1fr 1.25fr 1fr" if len(top) >= 3 else "repeat(%d, minmax(0, 1fr))" % max(1, len(top))
        pc.show(n["podium"], bool(top))
        pc.show(n["no_pick"], not top)
        self.bars_panel.items = cons
        pc.show(n["no_votes"], not cons)
        n["total"].textContent = state.plural(d.get("total") or 0, "collage")
        self.sort_loved.classes["on"] = self.sort == "loved"
        self.sort_new.classes["on"] = self.sort == "new"
        casts = []
        for x in d.get("castings") or []:
            x = dict(x)
            x["_no_for"] = True
            casts.append(x)
        self.casts_panel.items = casts
        self.no_casts.visible = not casts
        n["empty_line"].textContent = "Who do you see when you read %s?" % c["name"]

    def sort_click(self, event):
        self.sort = event.currentTarget.getAttribute("data-sort")
        self._load()

    def _cast(self):
        if pc.need_sign_in("Sign up to cast this character with your dream stars."):
            router.go("castedit", self.key)

    @handle("cast_button", "click")
    def cast_button_click(self, **event_args):
        self._cast()

    @handle("cast_button_2", "click")
    def cast_button_2_click(self, **event_args):
        self._cast()
