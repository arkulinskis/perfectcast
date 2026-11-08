import anvil.server
from anvil import *

from ._anvil_designer import SuggestTemplate
from ... import pc, router, state


class Suggest(SuggestTemplate):
    """#suggest: a member suggests a new book with its characters (an admin reviews it)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        d = anvil.server.call("get_shelf")
        self.form.setup(None, d.get("tropes") or [])
        self.dom_nodes["count_line"].textContent = "Already %s on PerfectCast. Search the shelf first!" % state.plural(len(d.get("books") or []), "book")

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        v = self.form.values()
        if not v:
            return
        self.send_button.enabled = False
        try:
            r = state.call("suggest_book", v)
        finally:
            self.send_button.enabled = True
        if r:
            state.toast(r.get("message") or "Thanks!", "ok")
            pc.hearts(14)
            router.go("book", r["key"])
