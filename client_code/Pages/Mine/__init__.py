import anvil.server
from anvil import *

from ._anvil_designer import MineTemplate
from ... import pc, router, state


class Mine(MineTemplate):
    """#mine: the member's own corner. Their numbers, characters still waiting in books they've started, their
    collages (hidden ones too), the collages they swooned over, their public page and bio."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        d = anvil.server.call("my_castings")
        n, s = self.dom_nodes, d["stats"]
        n["s_casts"].textContent = str(s["casts"])
        n["s_casts_l"].textContent = "collage" if s["casts"] == 1 else "collages"
        n["s_hearts"].textContent = str(s["hearts"])
        n["s_comments"].textContent = str(s["comments"])
        n["s_books"].textContent = str(s["books"])
        n["s_books_l"].textContent = "book" if s["books"] == 1 else "books"
        self.bio_box.text = d["me"].get("bio") or ""
        state.set_control_attr(self.bio_box, "maxlength", 160)
        state.set_control_attr(self.bio_box, "aria-label", "Your bio")
        pc.link(n["fan_link"], router.href("fan", d["me"]["id"]))
        pc.show(n["waiting"], bool(d.get("waiting")))
        self.wait_panel.items = d.get("waiting") or []
        self.casts_panel.items = d.get("castings") or []
        self.no_casts.visible = not d.get("castings")
        pc.show(n["swooned"], bool(d.get("swooned")))
        self.swoon_panel.items = d.get("swooned") or []

    @handle("bio_box", "pressed_enter")
    def bio_box_pressed_enter(self, **event_args):
        self.bio_button_click()

    @handle("bio_button", "click")
    def bio_button_click(self, **event_args):
        r = state.call("update_bio", self.bio_box.text or "")
        if r:
            state.set_me(r["me"])
            state.toast("Saved", "ok")
