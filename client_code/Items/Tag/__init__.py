from anvil import *

from ._anvil_designer import TagTemplate
from ... import pc, router


class Tag(TagTemplate):
    """A trope chip that links to the shelf filtered by that trope (#books/<trope>). item = {label}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        n = self.dom_nodes
        n["tag"].textContent = self.item["label"]
        pc.link(n["tag"], router.href("books", self.item["label"]))
        n["tag"].setAttribute("aria-label", "More %s books" % self.item["label"])
