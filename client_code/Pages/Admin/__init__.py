from anvil import *

from ._anvil_designer import AdminTemplate
from ... import state

TABS = ["overview", "books", "queue", "reports", "feedback", "users", "demo"]


class Admin(AdminTemplate):
    """#admin/<tab> (admins only): overview counts; books (add / edit with characters / delete); the review queue
    (members' suggested books and characters); reports (dismiss / hide / delete); the old feedback inbox; users
    (admin / active switches); demo data. Each tab is its own address, so the browser's back button works."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.tab = args[0] if args and args[0] in TABS else "overview"
        self._filter, self._rep_filter, self._tropes = "new", "open", []
        parts = {"overview": self.overview_part, "books": self.books_part, "queue": self.queue_part,
                 "reports": self.reports_part, "feedback": self.feedback_part, "users": self.users_part, "demo": self.demo_part}
        tabs = {"overview": self.tab_overview, "books": self.tab_books, "queue": self.tab_queue, "reports": self.tab_reports,
                "feedback": self.tab_feedback, "users": self.tab_users, "demo": self.tab_demo}
        for name in TABS:
            parts[name].visible = name == self.tab
            tabs[name].classes["on"] = name == self.tab
            state.set_attr(tabs[name], "aria-current", "page" if name == self.tab else None)
        self.feedback_panel.add_event_handler("x-changed", self._feedback_changed)
        self.books_panel.add_event_handler("x-edit", self._edit_book)
        self.books_panel.add_event_handler("x-delete", self._delete_book)
        for panel in (self.q_books_panel, self.q_chars_panel):
            panel.add_event_handler("x-review", self._review)
        self.q_books_panel.add_event_handler("x-edit", self._queue_edit)
        self.reports_panel.add_event_handler("x-resolve", self._resolve)
        self.reports_panel.add_event_handler("x-unhide", self._unhide)
        getattr(self, "_" + self.tab)()

    # ---- overview
    def _overview(self):
        d = state.call("admin_overview")
        n = self.dom_nodes
        for key in ("users", "books", "castings", "queue", "reports", "admins"):
            n["s_" + key].textContent = str(d[key])
        n["s_feedback"].textContent = str(d["feedback_new"])
        n["s_photos"].textContent = str(d["photos"])
        n["s_photos_l"].textContent = "photos · %s MB" % d["photo_mb"]
        n["s_admins_l"].textContent = "admin" if d["admins"] == 1 else "admins"
        c = d["demo"]["counts"]
        n["demo_line"].textContent = "Demo data is %s (%d demo fans, %d demo books). Manage it in the Demo data tab." % (
            d["demo"]["state"], c.get("users", 0), c.get("books", 0))

    # ---- books
    def _books(self):
        d = state.call("admin_books")
        self._tropes = d.get("tropes") or []
        self._book_list = d["books"]
        self.books_panel.items = d["books"]
        self.dom_nodes["books_count"].textContent = state.plural(len(d["books"]), "book")

    def _open_editor(self, book):
        from ...Dialogs.BookEdit import BookEdit
        return alert(BookEdit(book=book, tropes=self._tropes), buttons=[], role="app-dialog", large=True)

    @handle("new_book_button", "click")
    def new_book_button_click(self, **event_args):
        if self._open_editor(None):
            self._books()

    def _edit_book(self, **event_args):
        if self._open_editor(event_args["book"]):
            self._books()

    def _delete_book(self, **event_args):
        b = event_args["book"]
        if confirm("Its characters and every collage of them are deleted. This can't be undone.", title="Delete %s?" % b["title"],
                   buttons=[("Cancel", False), ("Delete", True)], role="app-dialog"):
            if state.call("admin_delete_book", b["key"]) is not None:
                state.toast("Book deleted")
                self._books()

    # ---- review queue
    def _queue(self):
        d = state.call("admin_queue")
        n = self.dom_nodes
        self.q_books_panel.items = d["books"]
        self.q_chars_panel.items = d["characters"]
        n["q_books_n"].textContent = "(%d)" % len(d["books"])
        n["q_chars_n"].textContent = "(%d)" % len(d["characters"])
        n["q_books_none"].hidden = bool(d["books"])
        n["q_chars_none"].hidden = bool(d["characters"])

    def _review(self, **event_args):
        if state.call("admin_review", event_args["kind"], event_args["key"], event_args["decision"]) is not None:
            state.toast("Approved" if event_args["decision"] == "approve" else "Turned down", "ok")
            self._queue()

    def _queue_edit(self, **event_args):
        d = state.call("admin_books")
        self._tropes = d.get("tropes") or []
        book = [b for b in d["books"] if b["key"] == event_args["key"]]
        if book and self._open_editor(book[0]):
            self._queue()

    # ---- reports
    def _reports(self):
        d = state.call("admin_reports", self._rep_filter)
        self.reports_panel.items = d["reports"]
        self.dom_nodes["no_reports"].hidden = bool(d["reports"])
        self.dom_nodes["r_open_n"].textContent = "(%d)" % d.get("open", 0)
        self.r_open.classes["on"] = self._rep_filter == "open"
        self.r_all.classes["on"] = self._rep_filter == "all"

    def rep_filter_click(self, event):
        self._rep_filter = event.currentTarget.getAttribute("data-f")
        self._reports()

    def _resolve(self, **event_args):
        if state.call("admin_resolve", event_args["report"]["id"], event_args["action"]) is not None:
            state.toast("Done", "ok")
            self._reports()

    def _unhide(self, **event_args):
        if state.call("admin_unhide", "casting", event_args["key"]) is not None:
            state.toast("Visible again", "ok")
            self._reports()

    # ---- feedback
    def _feedback(self):
        d = state.call("list_feedback", None)
        items = [i for i in d["items"] if self._filter == "all" or i["status"] == self._filter]
        self.feedback_panel.items = items
        self.no_feedback.visible = not items
        labels = {"new": "New", "read": "Read", "done": "Done", "all": "All"}
        for key, el in (("new", self.f_new), ("read", self.f_read), ("done", self.f_done), ("all", self.f_all)):
            k = len(d["items"]) if key == "all" else d["counts"].get(key, 0)
            el.text = "%s (%d)" % (labels[key], k)
            el.role = ["seg", "on"] if key == self._filter else ["seg"]

    def _set_filter(self, value):
        self._filter = value
        self._feedback()

    @handle("f_new", "click")
    def f_new_click(self, **event_args):
        self._set_filter("new")

    @handle("f_read", "click")
    def f_read_click(self, **event_args):
        self._set_filter("read")

    @handle("f_done", "click")
    def f_done_click(self, **event_args):
        self._set_filter("done")

    @handle("f_all", "click")
    def f_all_click(self, **event_args):
        self._set_filter("all")

    def _feedback_changed(self, **event_args):
        self._feedback()

    # ---- users
    def _users(self, query=None):
        d = state.call("list_users", query or None)
        self.users_panel.items = d["users"]
        self.users_count.text = state.plural(d["total"], "person", "people")

    @handle("search_box", "pressed_enter")
    def search_box_pressed_enter(self, **event_args):
        self._users(self.search_box.text)

    @handle("search_button", "click")
    def search_button_click(self, **event_args):
        self._users(self.search_box.text)

    # ---- demo data
    def _demo(self):
        d = state.call("admin_overview")["demo"]
        counts = ", ".join("%s %s" % (v, k) for k, v in d["counts"].items())
        self.demo_status.text = "Status: %s · %s" % (d["state"], counts)
        self.demo_load_button.text = "Reload demo data" if d["state"] == "loaded" else "Load demo data"

    @handle("demo_load_button", "click")
    def demo_load_button_click(self, **event_args):
        if confirm("Demo fans, books and collages are added (any old demo rows are replaced).", title="Load the demo data?",
                   buttons=[("Cancel", False), ("Load", True)], role="app-dialog"):
            if state.call("demo_load") is not None:
                state.toast("Done", "ok")
                self._demo()

    @handle("demo_remove_button", "click")
    def demo_remove_button_click(self, **event_args):
        if confirm("Every demo row is deleted. Real data stays.", title="Remove the demo data?",
                   buttons=[("Cancel", False), ("Remove", True)], role="app-dialog"):
            if state.call("demo_remove") is not None:
                state.toast("Done", "ok")
                self._demo()
