from anvil import *

from ._anvil_designer import CharCardTemplate
from ... import pc, router, state


class CharCard(CharCardTemplate):
    """A character on a book page: the fans' pick photo, role, name, the runners-up, and Cast / Edit yours.
    item = a character from get_book + "_live" (the book is live) and "_mine" (my collage key, if any)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c, n = self.item, self.dom_nodes
        top = c["top"][0] if c.get("top") else None
        pc.link(n["pic"], router.href("character", c["key"]))
        if top and top.get("photo"):
            n["img"].setAttribute("src", pc.photo(top["photo"]))
            n["img"].setAttribute("alt", "%s as %s" % (top["name"], c["name"]))
            pc.show(n["img"], True)
            pc.show(n["mono"], False)
        n["mono"].textContent = state.initials(c["name"])
        n["role"].textContent = c.get("role_label") or ""
        n["role"].className = "role " + (c.get("role") or "")
        n["name"].textContent = c["name"]
        if top:
            n["pick_pre"].textContent = "Fans' pick: "
            n["pick_name"].textContent = top["name"]
            n["pick_pct"].textContent = " · %d%%" % top["pct"]
        else:
            n["pick_pre"].textContent = "Nobody has cast them yet"
        n["blurb"].textContent = c.get("blurb") or ""
        pc.show(n["blurb"], bool(c.get("blurb")))
        runners = [{"href": router.href("stars", s["star"]), "label": "%s · %d%%" % (s["name"], s["pct"]), "cls": ""}
                   for s in (c.get("top") or [])[1:]]
        self.runners.visible = bool(runners)
        self.runners_panel.items = runners
        mine = c.get("_mine")
        self.cast_button.visible = bool(c.get("_live"))
        self.cast_button.text = "Edit yours" if mine else "Cast"
        self.cast_button.role = ["btn", "btn-sm", "btn-soft" if mine else "btn-primary", "ic-edit" if mine else "ic-sparkle"]
        n["count_link"].textContent = state.plural(c.get("casts") or 0, "collage")
        pc.link(n["count_link"], router.href("character", c["key"]))

    @handle("cast_button", "click")
    def cast_button_click(self, **event_args):
        if pc.need_sign_in("Sign up to cast this character with your dream stars."):
            router.go("castedit", self.item["key"])
