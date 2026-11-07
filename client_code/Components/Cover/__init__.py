from anvil import *

from ._anvil_designer import CoverTemplate
from ... import pc


class Cover(CoverTemplate):
    """A book cover: the picture (thumbnail unless full), else the title on the gradient; optional corner badge."""

    def __init__(self, **properties):
        self._book, self._badge, self._full, self._ready = None, "", False, False
        super().__init__(**properties)
        self._ready = True
        self._draw()

    def _draw(self):
        b = self._book
        if not self._ready or b is None:
            return
        n = self.dom_nodes
        n["badge"].textContent = self._badge or ""
        pc.show(n["badge"], bool(self._badge))
        key = b.get("cover")
        pc.show(n["img"], bool(key))
        pc.show(n["ph"], not key)
        if key:
            n["img"].setAttribute("src", pc.photo(key, not self._full))
            n["img"].setAttribute("alt", "Cover of " + (b.get("title") or "the book"))
        n["ph"].textContent = b.get("title") or ""

    @property
    def book(self):
        return self._book

    @book.setter
    def book(self, value):
        self._book = value
        self._draw()

    @property
    def badge(self):
        return self._badge

    @badge.setter
    def badge(self, value):
        self._badge = value or ""
        self._draw()

    @property
    def full(self):
        return self._full

    @full.setter
    def full(self, value):
        self._full = bool(value)
        self._draw()
