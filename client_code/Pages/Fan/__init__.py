import anvil.server
from anvil import *

from ._anvil_designer import FanTemplate
from ... import pc, router, state


class Fan(FanTemplate):
    """#fan/<userId>: a fan-caster's public page. Name, bio, numbers, favourite stars and collages. Never their email."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        d = anvil.server.call("get_fan", args[0] if args else "")
        n = self.dom_nodes
        if not d.get("ok"):
            pc.show(n["main"], False)
            pc.show(n["missing"], True)
            n["missing_text"].textContent = d.get("error") or "That fan isn't here any more."
            return
        f = d["fan"]
        self.title = f["name"]
        n["avatar"].textContent = state.initials(f["name"])
        n["name"].textContent = f["name"]
        n["bio"].textContent = f.get("bio") or ""
        pc.show(n["bio"], bool(f.get("bio")))
        pc.show(n["add_bio"], not f.get("bio") and bool(f.get("me")))
        k = len(d.get("castings") or [])
        n["n_casts"].textContent = state.plural(k, "collage")
        n["n_hearts"].textContent = state.plural(d.get("hearts") or 0, "swoon")
        n["n_books"].textContent = state.plural(d.get("books") or 0, "book")
        n["since"].textContent = ("Since " + state.month_year(f["joined"])) if f.get("joined") else ""
        self.stars_panel.items = [{"href": router.href("stars", s["star"]), "label": s["name"], "icon": "star"} for s in d.get("stars") or []]
        self.casts_panel.items = d.get("castings") or []
        self.no_casts.visible = not k
        n["empty_line"].textContent = "Cast your first character!" if f.get("me") else "Nothing to see here yet."
