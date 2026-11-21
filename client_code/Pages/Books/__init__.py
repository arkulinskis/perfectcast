import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import BooksTemplate
from ... import pc, router, state

SPICE = [("Any spice", ""), ("Sweet (0-1)", "mild"), ("Warm (2-3)", "warm"), ("Scorching (4-5)", "hot")]
SPICE_WORDS = {"mild": "sweet", "warm": "warm", "hot": "scorching"}


class Books(BooksTemplate):
    """#books, the home page and the shelf (open to everyone): the newest release up top, coming-soon countdowns,
    trending collages, then every book with search, trope, spice and sort filters (all in the browser: get_shelf
    sends everything in one call)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.title = "New romantasy releases"
        self.f = {"q": "", "trope": "", "spice": "", "sort": "new"}
        self.spice_box.items = SPICE
        state.set_control_attr(self.spice_box, "aria-label", "Spice")
        state.set_control_attr(self.search_box, "aria-label", "Search books")
        state.set_control_attr(self.search_box, "type", "search")
        self.trope_panel.add_event_handler("x-chip", self._trope)
        self.d = anvil.server.call("get_shelf")
        self._from_address(args)
        self._draw()
        if args:  # opened from a trope link or a shared list: go straight to the shelf
            window.setTimeout(lambda: self.dom_nodes["shelf"].scrollIntoView(pc.js({"block": "start"})), 80)

    def _from_address(self, args):
        """#books/<trope>/<spice>: a shareable filtered shelf ("all" = any trope)."""
        tropes = {t.lower(): t for t in self.d.get("tropes") or []}
        trope = tropes.get((args[0] if args else "").strip().lower(), "")
        spice = args[1] if len(args) > 1 and args[1] in SPICE_WORDS else ""
        self.f.update(trope=trope, spice=spice)
        self.spice_box.selected_value = spice
        if trope or spice:
            self.title = self._list_name()

    def _list_name(self):
        parts = [SPICE_WORDS[self.f["spice"]]] if self.f["spice"] else []
        name = " ".join(parts + ["romantasy"]).capitalize()
        return "%s: %s" % (name, self.f["trope"].lower()) if self.f["trope"] else name + " books"

    def _sync_address(self):
        f = self.f
        if f["trope"] or f["spice"]:
            router.replace("books", f["trope"] or "all", f["spice"])
            window.document.title = self._list_name() + " · PerfectCast"
        else:
            router.replace("books")
            window.document.title = "New romantasy releases · PerfectCast"
        self.share_list_button.visible = bool(f["trope"] or f["spice"])

    def _draw(self):
        d, n, me = self.d, self.dom_nodes, state.me()
        books = d["books"]
        released = [b for b in books if pc.days(b.get("release")) is not None and pc.days(b["release"]) <= 0]
        soon = sorted([b for b in books if (pc.days(b.get("release")) or 0) > 0], key=lambda b: b["release"])
        top = released[0] if released else (books[0] if books else None)
        pc.show(n["feature"], bool(top))
        if top:
            self.top = top
            if top.get("cover"):
                n["feature_bg"].style.backgroundImage = "url('%s')" % pc.photo(top["cover"], True)
            pc.link(n["feature_cover_link"], router.href("book", top["key"]))
            pc.link(n["feature_cast"], router.href("book", top["key"]))
            self.feature_cover.book = top
            n["feature_title"].textContent = top["title"]
            soon_word = "Coming soon" if (pc.days(top.get("release")) or 0) > 0 else "Fresh from the forge"
            n["feature_by"].textContent = "by %s · %s · %s" % (top.get("author") or "", pc.series_line(top), soon_word)
            pc.set_when(n["feature_when"], top.get("release"))
            self.feature_spice.level = top.get("spice") or 0
            n["feature_casts"].textContent = state.plural(top.get("casts") or 0, "collage")
            n["feature_blurb"].textContent = top.get("blurb") or ""
            pc.show(n["feature_blurb"], bool(top.get("blurb")))
            self.feature_tropes.items = [{"label": t} for t in top.get("tropes") or []]
        pc.show(n["hello"], bool(me))
        if me:
            n["hello_name"].textContent = "Welcome back, %s." % (me.get("name") or "there").split(" ")[0]
            st = d.get("me") or {}
            n["hello_line"].textContent = ("You've made %s and earned %s." % (state.plural(st["casts"], "collage"), state.plural(st["hearts"], "swoon"))
                                           if st.get("casts") else "Pick a book and cast your first character!")
        pc.show(n["soon"], bool(soon))
        self.soon_panel.items = soon
        pc.show(n["trend"], bool(d.get("trending")))
        self.trend_panel.items = d.get("trending", [])[:4]
        self._draw_shelf()

    def _filtered(self):
        f, q = self.f, self.f["q"].strip().lower()
        out = []
        for b in self.d["books"]:
            if q and q not in ("%s %s %s" % (b["title"], b.get("author") or "", b.get("series") or "")).lower():
                continue
            if f["trope"] and f["trope"] not in (b.get("tropes") or []):
                continue
            sp = b.get("spice") or 0
            if (f["spice"] == "mild" and sp > 1) or (f["spice"] == "warm" and not 2 <= sp <= 3) or (f["spice"] == "hot" and sp < 4):
                continue
            out.append(b)
        if f["sort"] == "cast":
            out.sort(key=lambda b: -(b.get("casts") or 0))
        elif f["sort"] == "soon":
            out = sorted([b for b in out if (pc.days(b.get("release")) or 0) > 0], key=lambda b: b["release"])
        return out

    def _draw_shelf(self):
        books = self._filtered()
        self.shelf_panel.items = books
        self.no_books.visible = not books
        self.dom_nodes["count"].textContent = state.plural(len(books), "book")
        self.trope_panel.items = [{"label": "All tropes", "value": "", "on": not self.f["trope"]}] + \
            [{"label": t, "value": t, "on": t == self.f["trope"]} for t in self.d.get("tropes") or []]
        for key, el in (("new", self.sort_new), ("soon", self.sort_soon), ("cast", self.sort_cast)):
            el.classes["on"] = self.f["sort"] == key
        self.share_list_button.visible = bool(self.f["trope"] or self.f["spice"])

    def _trope(self, **event_args):
        key = state.focus_key()
        self.f["trope"] = event_args.get("value") or ""
        self._draw_shelf()
        self._sync_address()
        state.refocus(self.trope_panel, key)

    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self.f["q"] = self.search_box.text or ""
        self._draw_shelf()

    @handle("spice_box", "change")
    def spice_box_change(self, **event_args):
        self.f["spice"] = self.spice_box.selected_value or ""
        self._draw_shelf()
        self._sync_address()

    def sort_click(self, event):
        self.f["sort"] = event.currentTarget.getAttribute("data-sort")
        self._draw_shelf()

    @handle("feature_share", "click")
    def feature_share_click(self, **event_args):
        pc.share(router.href("book", self.top["key"]), "A new romantasy to fan-cast")

    @handle("share_list_button", "click")
    def share_list_button_click(self, **event_args):
        pc.share(router.href("books", self.f["trope"] or "all", self.f["spice"]), self._list_name())

    def _suggest(self):
        if pc.need_sign_in("Sign up to suggest books for the shelf."):
            router.go("suggest")

    @handle("suggest_button", "click")
    def suggest_button_click(self, **event_args):
        self._suggest()

    @handle("suggest_button_2", "click")
    def suggest_button_2_click(self, **event_args):
        self._suggest()
