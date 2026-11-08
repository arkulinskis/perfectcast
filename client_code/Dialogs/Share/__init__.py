from anvil import *

from ._anvil_designer import ShareTemplate


class Share(ShareTemplate):
    """Shown only when the browser can neither share nor copy: the link to copy by hand."""

    def __init__(self, url="", **properties):
        super().__init__(**properties)
        self.url_box.text = url

    @handle("", "show")
    def form_show(self, **event_args):
        self.url_box.focus()
        self.url_box.select()

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
