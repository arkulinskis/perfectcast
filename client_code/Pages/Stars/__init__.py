import anvil.server
from anvil import *

from ._anvil_designer import StarsTemplate
from ... import pc, router, state


class Stars(StarsTemplate):
    """#stars: the leaderboard of the celebrities fans cast (podium + list, search). #stars/<slug>: one star, every
    role they were cast in (rank, share of the vote) and fans' photos of them. Open to everyone."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.title = "Stars"
        state.set_control_attr(self.search_box, "aria-label", "Find a star")
        state.set_control_attr(self.search_box, "type", "search")
        if args:
            self._star(args[0])
        else:
            self._board()

    # ---- the leaderboard
    def _board(self):
        d = anvil.server.call("list_stars")
        n = self.dom_nodes
        pc.show(n["board"], True)
        self.stars = d["stars"]
        for i, s in enumerate(self.stars):
            s["rank"] = i + 1
        n["board_line"].textContent = "Who fans see when they read. %s cast so far." % state.plural(d.get("total") or 0, "star")
        top = self.stars[:3]
        order = [1, 0, 2] if len(top) == 3 else list(range(len(top)))
        self.podium_panel.items = [{"href": router.href("stars", top[i]["star"]), "name": top[i]["name"], "photo": top[i].get("photo"),
                                    "thumb": i > 0, "rank": i + 1, "style": "st",
                                    "line": "%s · %s" % (state.plural(top[i]["casts"], "collage"), state.plural(top[i]["roles"], "role"))}
                                   for i in order]
        n["podium"].style.gridTemplateColumns = "1fr 1.2fr 1fr" if len(top) == 3 else "repeat(%d, minmax(0, 1fr))" % max(1, len(top))
        pc.show(n["no_stars"], not top)
        self._draw_list()

    def _draw_list(self):
        n = self.dom_nodes
        q = (self.search_box.text or "").strip().lower()
        rows = [s for s in self.stars if q in s["name"].lower()] if q else self.stars[3:]
        self.list_panel.items = rows
        pc.show(n["podium"], not q and bool(self.stars))
        pc.show(n["no_match"], bool(q) and not rows)

    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self._draw_list()

    # ---- one star
    def _star(self, slug):
        d = anvil.server.call("get_star", slug)
        n = self.dom_nodes
        if not d.get("ok"):
            pc.show(n["missing"], True)
            n["missing_text"].textContent = d.get("error") or "Nobody has cast that star yet."
            return
        pc.show(n["star"], True)
        s = d["star"]
        self.title = s["name"]
        if s.get("photo"):
            n["star_img"].setAttribute("src", pc.photo(s["photo"]))
            n["star_img"].setAttribute("alt", s["name"])
            pc.show(n["star_img"], True)
        else:
            n["star_ini"].textContent = state.initials(s["name"])
        n["star_name"].textContent = s["name"]
        roles = d.get("roles") or []
        n["s_casts"].textContent = str(s["casts"])
        n["s_casts_l"].textContent = "collage" if s["casts"] == 1 else "collages"
        n["s_roles"].textContent = str(len(roles))
        n["s_roles_l"].textContent = "role" if len(roles) == 1 else "roles"
        n["s_fans"].textContent = str(s["fans"])
        n["s_fans_l"].textContent = "fan" if s["fans"] == 1 else "fans"
        n["s_first"].textContent = str(len([r for r in roles if r["rank"] == 1]))
        self.roles_panel.items = roles
        pc.show(n["gallery"], bool(d.get("gallery")))
        self.gallery_panel.items = d.get("gallery") or []
