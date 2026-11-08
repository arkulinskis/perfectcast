import anvil.server
from anvil import *

from ._anvil_designer import BookTemplate
from ... import pc, router, state


class Book(BookTemplate):
    """#book/<key>: one book. Cover, blurb, tropes, spice; the fans' dream cast (every character with the fans'
    favourite star); the latest collages; suggest a missing character. Open to everyone."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else ""
        d = anvil.server.call("get_book", self.key)
        n = self.dom_nodes
        if not d.get("ok"):
            pc.show(n["main"], False)
            pc.show(n["missing"], True)
            n["missing_text"].textContent = d.get("error") or "That book isn't here."
            return
        self.d = d
        b = d["book"]
        self.title = b["title"]
        if b.get("cover"):
            n["bg"].style.backgroundImage = "url('%s')" % pc.photo(b["cover"], True)
        self.cover.book = b
        n["title"].textContent = b["title"]
        n["by"].textContent = "by %s · %s" % (b.get("author") or "", pc.series_line(b))
        pc.set_when(n["when"], b.get("release"))
        self.spice.level = b.get("spice") or 0
        n["casts"].textContent = state.plural(b.get("casts") or 0, "collage")
        n["fans"].textContent = state.plural(d.get("fans") or 0, "fan")
        n["blurb"].textContent = b.get("blurb") or ""
        pc.show(n["blurb"], bool(b.get("blurb")))
        self.tropes_panel.items = [{"label": t} for t in b.get("tropes") or []]
        pc.show(n["edit_link"], bool(d.get("can_edit")))
        live = b.get("status") == "live"
        pc.show(n["pending"], not live)
        self.suggest_button.visible = live
        chars = []
        for c in d["characters"]:
            c = dict(c)
            c["_live"], c["_mine"] = live, (d.get("my") or {}).get(c["key"])
            chars.append(c)
        self.chars_panel.items = chars
        pc.show(n["recent"], bool(d.get("recent")))
        self.recent_panel.items = d.get("recent") or []

    @handle("jump_button", "click")
    def jump_button_click(self, **event_args):
        self.dom_nodes["cast_section"].scrollIntoView(pc.js({"behavior": "smooth"}))

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        pc.share(router.href("book", self.key), self.d["book"]["title"])

    @handle("suggest_button", "click")
    def suggest_button_click(self, **event_args):
        if not pc.need_sign_in("Sign up to add missing characters."):
            return
        from ...Dialogs.SuggestChar import SuggestChar
        msg = alert(SuggestChar(book_key=self.key, roles=self.d.get("roles")), buttons=[], role="app-dialog")
        if msg:
            state.toast(msg, "ok")
