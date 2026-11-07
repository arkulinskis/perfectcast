from anvil import *

from ._anvil_designer import TagTemplate


class Tag(TagTemplate):
    """A trope shown as a chip (not clickable). item = {label}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self.dom_nodes["tag"].textContent = self.item["label"]
