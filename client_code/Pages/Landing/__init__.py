import anvil.server
from anvil import *

from ._anvil_designer import LandingTemplate
from ... import pc, state

# The app's video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json), shown in the Watch section.
YT_VIDEO = "_pmaxTfTg38"


class Landing(LandingTemplate):
    """#landing, the front page for visitors (and "About" for members): the promise, the Watch video, a live shelf
    row, how it works, features, FAQ. Static copy lives in the template; only the signed-in variations are set here."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.dom_nodes["yt_cover"].addEventListener("click", self._play)
        me = state.me()
        n = self.dom_nodes
        pc.show(n["guest_cta"], not me)
        pc.show(n["member_cta"], bool(me))
        if me:
            n["band_link"].setAttribute("href", "#books")
            n["band_link"].textContent = "Open the shelf"
        try:
            d = anvil.server.call_s("get_shelf")
        except Exception:
            d = None
        if d and d.get("books"):
            self.shelf_panel.items = d["books"][:10]
            pc.show(n["shelf"], True)

    def _play(self, event):
        """Swap the video's cover for YouTube's player (privacy-enhanced); nothing loads from YouTube before this click."""
        self.dom_nodes["yt_frame"].innerHTML = (
            '<iframe src="https://www.youtube-nocookie.com/embed/' + YT_VIDEO + '?autoplay=1&rel=0&playsinline=1" '
            'title="PerfectCast video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>')
