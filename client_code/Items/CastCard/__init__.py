from anvil import *

from ._anvil_designer import CastCardTemplate
from ... import pc, router, state


class CastCard(CastCardTemplate):
    """A collage card: the collage, who made it and when, the caption, "as X in Book", swoons and comments.
    item = a casting card from the server; item["_no_for"] hides the "as X in Book" line (character pages)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c, n = self.item, self.dom_nodes
        pc.link(n["open"], router.href("cast", c["key"]))
        self.collage.cast = c
        user = c.get("user") or {}
        n["avatar"].textContent = state.initials(user.get("name"))
        n["user_link"].textContent = user.get("name") or "A fan"
        if user.get("id"):
            pc.link(n["user_link"], router.href("fan", user["id"]))
        else:
            n["user_link"].removeAttribute("href")
        n["ago"].textContent = "· " + state.ago(c.get("updated"))
        n["caption"].textContent = c.get("caption") or ""
        pc.show(n["caption"], bool(c.get("caption")))
        ch = c.get("character")
        pc.show(n["for_line"], bool(ch) and not c.get("_no_for"))
        if ch:
            n["char_link"].textContent = ch["name"]
            pc.link(n["char_link"], router.href("character", ch["key"]))
        pc.show(n["book_part"], bool(c.get("book")))
        if c.get("book"):
            n["book_title"].textContent = c["book"]["title"]
        self.heart.cast = c
        n["comments"].textContent = str(c.get("comments") or 0)
        n["comments_box"].setAttribute("aria-label", state.plural(c.get("comments") or 0, "comment"))
        pc.show(n["hidden_badge"], bool(c.get("hidden")))
