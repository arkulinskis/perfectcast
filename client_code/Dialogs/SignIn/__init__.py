from anvil import *

from ._anvil_designer import SignInTemplate
from ... import router


class SignIn(SignInTemplate):
    """For visitors who try to swoon, cast, comment or report: sign in or sign up (they come back here after)."""

    def __init__(self, why="", **properties):
        super().__init__(**properties)
        self.dom_nodes["why"].textContent = (why or "Sign up to cast characters, swoon over collages and join the conversation.") + " It's free."

    def _close(self, page=None):
        self.raise_event("x-close-alert", value=None)
        if page:
            router.go("auth", *page)

    @handle("not_now_button", "click")
    def not_now_button_click(self, **event_args):
        self._close()

    @handle("sign_in_button", "click")
    def sign_in_button_click(self, **event_args):
        self._close([])

    @handle("sign_up_button", "click")
    def sign_up_button_click(self, **event_args):
        self._close(["signup"])
