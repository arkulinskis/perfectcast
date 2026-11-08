from anvil import *

from ._anvil_designer import GalleryTileTemplate
from ... import pc, router


class GalleryTile(GalleryTileTemplate):
    """A fan's photo of a star; opens the collage it is in."""

    def __init__(self, **properties):
        super().__init__(**properties)
        g, n = self.item, self.dom_nodes
        pc.link(n["link"], router.href("cast", g["casting"]))
        n["img"].setAttribute("src", pc.photo(g["photo"], True))
        n["img"].setAttribute("alt", "Photo in %s's collage" % g["by"])
        n["by"].textContent = "by " + g["by"]
