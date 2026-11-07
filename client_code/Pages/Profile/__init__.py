from anvil import *

from ._anvil_designer import ProfileTemplate
from ... import auth, router, state


class Profile(ProfileTemplate):
    """#profile: your name and bio, light/dark, a password reset link, your pages, Privacy & Terms, feedback, sign out."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        state.set_control_attr(self.name_box, "maxlength", 60)
        state.set_control_attr(self.name_box, "autocomplete", "name")
        state.set_control_attr(self.bio_box, "maxlength", 160)
        self._show_me()
        self._show_theme()

    def _show_me(self):
        me = state.me()
        self.initials.text = state.initials(me.get("name"))
        self.name_title.text = me.get("name") or ""
        state.heading(self.name_title, 1)
        joined = state.month_year(me.get("joined"))
        self.email_line.text = (me.get("email") or "") + (" · member since " + joined if joined else "")
        self.name_box.text = me.get("name") or ""
        self.bio_box.text = me.get("bio") or ""
        self.admin_link.visible = bool(me.get("is_admin"))
        self.dom_nodes["fan_link"].setAttribute("href", router.href("fan", me["id"]))

    def _show_theme(self):
        t = state.theme()
        for name, el in (("auto", self.theme_auto), ("light", self.theme_light), ("dark", self.theme_dark)):
            el.classes["on"] = name == t

    def theme_click(self, event):
        state.set_theme(event.currentTarget.getAttribute("data-theme-pick"))
        self._show_theme()

    @handle("name_box", "pressed_enter")
    def name_box_pressed_enter(self, **event_args):
        self.save_button_click()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        name = (self.name_box.text or "").strip()
        if len(name) < 2:
            state.toast("Please tell us your name.", "error")
            return
        if state.call("update_profile", name) is None:
            return
        r = state.call("update_bio", self.bio_box.text or "")
        if r:
            state.set_me(r["me"])
            self._show_me()
            layout = getattr(self, "layout", None)
            if layout is not None and hasattr(layout, "refresh"):
                layout.refresh("profile")
            state.toast("Saved", "ok")

    @handle("reset_button", "click")
    def reset_button_click(self, **event_args):
        r = auth.reset(state.me()["email"])
        state.toast(r["message"], "ok")

    def feedback_click(self, event):
        state.feedback()

    def sign_out_click(self, event):
        auth.sign_out()
        state.toast("Signed out. See you soon!")
        router.go("landing")
