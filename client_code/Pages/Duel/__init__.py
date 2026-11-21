import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import DuelTemplate
from ... import pc, router, state

_SEEN = []  # pair ids this tab has already shown, so the next pair is a fresh one
_GUEST = {"picks": 0}


class Duel(DuelTemplate):
    """#duel (any character) and #duel/<characterKey>: the swoon-off. Two collages of one character side by side;
    tap the one that wins your heart, see both collages' swoon-off scores, then the next pair. Open to everyone;
    a member's pick is saved (vote_duel), a visitor's isn't (a sign-up nudge after a few picks)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.title = "Swoon-off"
        self.key = args[0] if args else ""
        self.d, self.picked, self.busy = {}, None, False
        self._load()

    # ------------------------------------------------------------------------------------------- loading
    def _load(self):
        n = self.dom_nodes
        self.busy, self.picked = True, None
        n["status"].textContent = "Finding two collages..."
        pc.show(n["status"], True)
        pc.show(n["after"], False)
        pc.show(n["empty"], False)
        n["arena"].classList.add("busy")
        try:
            d = anvil.server.call("get_duel", self.key or None, _SEEN[-300:])
        except anvil.server.AppOfflineError:
            d = {"ok": False, "error": "You seem to be offline. Check your connection and try again."}
        self.busy = False
        n["arena"].classList.remove("busy")
        if not d.get("ok"):
            self._empty("This swoon-off didn't load", d.get("error") or "Something went wrong.", retry=True)
            return
        self.d = d
        self._draw_for(d.get("character"))
        self._draw_count()
        pair = d.get("pair")
        if not pair:
            ch = d.get("character")
            if d.get("reason") == "all":
                self._empty("You've judged every pair!", "Come back when fans post new collages, or try another character.",
                            link=("#duel", "Any character") if self.key else None)
            elif ch:
                self._empty("Not enough collages yet", "%s needs two collages from other fans for a swoon-off. Add yours!" % ch["name"],
                            link=(router.href("character", ch["key"]), "Cast " + ch["name"].split(" ")[0]))
            else:
                self._empty("Not enough collages yet", "Swoon-offs start once a character has two collages. Cast one!")
            return
        if d.get("pair_id") and d["pair_id"] not in _SEEN:
            _SEEN.append(d["pair_id"])
        pc.show(n["status"], False)
        pc.show(n["arena"], True)
        for i, side in enumerate(("a", "b")):
            c = pair[i]
            getattr(self, "coll_" + side).cast = c
            user = c.get("user") or {}
            n["by_" + side].textContent = user.get("name") or "A fan"
            if user.get("id"):
                pc.link(n["by_" + side], router.href("fan", user["id"]))
            n["cap_" + side].textContent = c.get("caption") or ""
            pc.show(n["cap_" + side], bool(c.get("caption")))
            pc.show(n["res_" + side], False)
            n["side_" + side].classList.remove("won", "lost")
            btn = getattr(self, "pick_" + side)
            btn.visible, btn.enabled = True, True
            state.set_control_attr(btn, "aria-label", "Pick the collage by %s" % (user.get("name") or "this fan"))

    def _draw_for(self, ch):
        n = self.dom_nodes
        pc.show(n["for_line"], bool(ch))
        if not ch:
            return
        n["char_link"].textContent = ch["name"]
        pc.link(n["char_link"], router.href("character", ch["key"]))
        n["book_title"].textContent = (ch.get("book") or {}).get("title") or ""
        pc.link(n["book_link"], router.href("book", (ch.get("book") or {}).get("key") or ""))
        if self.key:
            n["pin_link"].textContent = "Any character"
            pc.link(n["pin_link"], "#duel")
        else:
            n["pin_link"].textContent = "Only %s" % ch["name"].split(" ")[0]
            pc.link(n["pin_link"], router.href("duel", ch["key"]))

    def _draw_count(self):
        n = self.dom_nodes
        if state.me():
            judged = self.d.get("judged") or 0
            n["count"].textContent = ("You've judged %s." % state.plural(judged, "swoon-off")) if judged else ""
        else:
            n["count"].textContent = ("%s this visit (not counted)" % state.plural(_GUEST["picks"], "pick")) if _GUEST["picks"] else ""

    def _empty(self, title, text, retry=False, link=None):
        n = self.dom_nodes
        pc.show(n["status"], False)
        pc.show(n["arena"], False)
        pc.show(n["after"], False)
        pc.show(n["empty"], True)
        n["empty_title"].textContent = title
        n["empty_text"].textContent = text
        self.retry_button.visible = retry
        href, label = link or ("#books", "Browse the books")
        pc.link(n["empty_link"], href)
        n["empty_link"].lastChild.textContent = label

    # ------------------------------------------------------------------------------------------- picking
    def art_click(self, event):
        side = event.currentTarget.getAttribute("data-side")
        self._pick(int(side or 0))

    @handle("pick_a", "click")
    def pick_a_click(self, **event_args):
        self._pick(0)

    @handle("pick_b", "click")
    def pick_b_click(self, **event_args):
        self._pick(1)

    def _pick(self, idx):
        pair = self.d.get("pair") if self.d else None
        if self.busy or self.picked is not None or not pair:
            return
        self.picked = idx
        win, lose = pair[idx], pair[1 - idx]
        scores = {c["key"]: c.get("duel") or {} for c in pair}
        if state.me():
            self.busy = True
            for b in (self.pick_a, self.pick_b):
                b.enabled = False
            try:
                r = state.call("vote_duel", win["key"], lose["key"])
            finally:
                self.busy = False
            if r:
                scores.update(r.get("stats") or {})
                self.d["judged"] = r.get("judged") or 0
        else:
            _GUEST["picks"] += 1
        self._show_result(idx, scores)

    def _show_result(self, idx, scores):
        n, pair = self.dom_nodes, self.d["pair"]
        for i, side in enumerate(("a", "b")):
            c = pair[i]
            st = scores.get(c["key"]) or {}
            pct = st.get("pct")
            n["side_" + side].classList.add("won" if i == idx else "lost")
            n["bar_" + side].style.width = "%d%%" % (pct or 0)
            n["line_" + side].textContent = ("Its first swoon-off" if pct is None else
                                             "Wins %d%% of %s" % (pct, state.plural(st.get("duels") or 0, "swoon-off")))
            pc.show(n["res_" + side], True)
            getattr(self, "pick_" + side).visible = False
        pc.link(n["winner_link"], router.href("cast", pair[idx]["key"]))
        pc.show(n["after"], True)
        pc.show(n["nudge"], not state.me() and _GUEST["picks"] >= 3)
        self._draw_count()
        pc.hearts(14)
        state.focus(self.next_button)

    @handle("next_button", "click")
    def next_button_click(self, **event_args):
        self._load()
        window.scrollTo(0, 0)

    @handle("retry_button", "click")
    def retry_button_click(self, **event_args):
        self._load()

