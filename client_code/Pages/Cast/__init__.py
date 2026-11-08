import anvil.server
from anvil import *

from ._anvil_designer import CastTemplate
from ... import pc, router, state


class Cast(CastTemplate):
    """#cast/<key>: one collage, big. The stars with their "why", swoon, save as image, share, comments, report;
    edit / delete for its owner (and admins). More collages of the same character below."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.key = args[0] if args else ""
        d = anvil.server.call("get_cast", self.key)
        n = self.dom_nodes
        if not d.get("ok"):
            pc.show(n["main"], False)
            pc.show(n["missing"], True)
            n["missing_text"].textContent = d.get("error") or "That collage is gone."
            return
        self.d = d
        c, ch = d["cast"], d["cast"]["character"]
        user = c.get("user") or {}
        self.title = "%s's %s" % (user.get("name") or "A fan", ch["name"])
        self.collage.cast = c
        pc.show(n["hidden_note"], bool(c.get("hidden")))
        n["for_link"].textContent = "%s · %s" % (ch.get("role_label") or "", (c.get("book") or {}).get("title") or "")
        pc.link(n["for_link"], router.href("character", ch["key"]))
        n["name"].textContent = ch["name"]
        n["avatar"].textContent = state.initials(user.get("name"))
        n["user_link"].textContent = user.get("name") or "a fan"
        if user.get("id"):
            pc.link(n["user_link"], router.href("fan", user["id"]))
        else:
            n["user_link"].removeAttribute("href")
        n["ago"].textContent = state.ago(c.get("updated"))
        n["caption"].textContent = c.get("caption") or ""
        pc.show(n["caption"], bool(c.get("caption")))
        self.heart.cast = c
        pc.show(n["edit_link"], bool(c.get("mine")))
        pc.link(n["edit_link"], router.href("castedit", ch["key"]))
        self.delete_button.visible = bool(c.get("can_delete"))
        self.report_button.visible = not c.get("mine")
        picks = []
        for i, p in enumerate(c.get("picks") or []):
            p = dict(p)
            p["_lead"] = i == 0 and len(c["picks"]) > 1
            picks.append(p)
        self.stars_panel.items = picks
        self.comments_panel.add_event_handler("x-delete", self._delete_comment)
        self.comments_panel.add_event_handler("x-report", self._report_comment)
        self.add_part.visible = bool(state.me())
        pc.show(n["join"], not state.me())
        state.set_control_attr(self.comment_box, "maxlength", 500)
        state.set_control_attr(self.comment_box, "aria-label", "Your comment")
        self._draw_comments()
        pc.show(n["more"], bool(d.get("more")))
        n["more_title"].textContent = "More %s collages" % ch["name"]
        pc.link(n["more_link"], router.href("character", ch["key"]))
        more = []
        for x in d.get("more") or []:
            x = dict(x)
            x["_no_for"] = True
            more.append(x)
        self.more_panel.items = more

    def _draw_comments(self):
        cs = self.d["comments"]
        self.comments_panel.items = cs
        pc.show(self.dom_nodes["no_comments"], not cs)
        self.dom_nodes["ccount"].textContent = "(%d)" % len(cs) if cs else ""

    def _delete_comment(self, **event_args):
        x = event_args["comment"]
        if confirm("This can't be undone.", title="Delete this comment?", buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            if state.call("delete_comment", x["id"]) is not None:
                self.d["comments"] = [y for y in self.d["comments"] if y["id"] != x["id"]]
                self._draw_comments()

    def _report_comment(self, **event_args):
        if pc.need_sign_in("Sign in to report something to the admins."):
            from ...Dialogs.Report import Report
            alert(Report(kind="comment", target=event_args["comment"]["id"]), buttons=[], role="app-dialog")

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        self.save_button.enabled = False
        try:
            pc.export_image(self.d["cast"])
            state.toast("Saved! Share it anywhere.", "ok")
        except Exception as e:
            state.toast(str(getattr(e, "message", "") or e) or "The picture couldn't be made.", "error")
        finally:
            self.save_button.enabled = True

    @handle("share_button", "click")
    def share_button_click(self, **event_args):
        c = self.d["cast"]
        pc.share(router.href("cast", self.key), "%s's dream cast for %s" % ((c.get("user") or {}).get("name") or "A fan", c["character"]["name"]))

    @handle("report_button", "click")
    def report_button_click(self, **event_args):
        if pc.need_sign_in("Sign in to report something to the admins."):
            from ...Dialogs.Report import Report
            alert(Report(kind="casting", target=self.key), buttons=[], role="app-dialog")

    @handle("delete_button", "click")
    def delete_button_click(self, **event_args):
        if confirm("Its swoons and comments go too. Your photos stay in your drawer.", title="Delete this collage?",
                   buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            if state.call("delete_casting", self.key) is not None:
                state.toast("Collage deleted")
                router.go("character", self.d["cast"]["character"]["key"])

    @handle("post_button", "click")
    def post_button_click(self, **event_args):
        body = (self.comment_box.text or "").strip()
        if not body:
            state.toast("Write a comment first.", "error")
            return
        self.post_button.enabled = False
        try:
            r = state.call("add_comment", self.key, body)
        finally:
            self.post_button.enabled = True
        if r:
            self.d["comments"].append(r["comment"])
            self.comment_box.text = ""
            self._draw_comments()
