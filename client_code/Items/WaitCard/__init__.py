from anvil import *

from ._anvil_designer import WaitCardTemplate
from ... import pc, router


class WaitCard(WaitCardTemplate):
    """A character still waiting for my collage (My casts, "Finish the cast")."""

    def __init__(self, **properties):
        super().__init__(**properties)
        w, n = self.item, self.dom_nodes
        pc.link(n["link"], router.href("castedit", w["key"]))
        self.cover.book = w["book"]
        n["name"].textContent = w["name"]
        n["book"].textContent = w["book"]["title"]
