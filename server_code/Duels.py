"""Swoon-off: two collages of the same character side by side; tap the one that wins your heart.

Anyone can play. A signed-in fan's pick is saved in `duels` (one vote per fan per pair: picking again changes it);
visitors see the scores without adding to them. A collage's swoon-off score = wins / swoon-offs it was in.
Your own collages never appear in your swoon-offs. The table may not exist until the user accepts the schema:
C.opt_table("duels") keeps everything working (scores show as "new") until then.
"""
import random

import anvil.server
from anvil.tables import app_tables

from . import common as C
from . import DemoData, Shelf


def _pair_id(a, b):
    return "|".join(sorted([a["key"], b["key"]]))


def stats(c, duels=None):
    """{wins, duels, pct} for one collage (pct None before its first swoon-off)."""
    duels = duels if duels is not None else C.opt_table("duels")
    if duels is None or c is None:
        return {"wins": 0, "duels": 0, "pct": None}
    w, lost = len(duels.search(winner=c)), len(duels.search(loser=c))
    n = w + lost
    return {"wins": w, "duels": n, "pct": int(round(100.0 * w / n)) if n else None}


def _live(ch):
    return ch is not None and (ch["status"] or "live") == "live" and ch["book"] is not None and \
        (ch["book"]["status"] or "live") == "live"


def _casting(key):
    return app_tables.castings.get(key=key) if isinstance(key, str) and key else None


def _judged(me, duels):
    return len(duels.search(user=me)) if me is not None and duels is not None else 0


@anvil.server.callable
def get_duel(char_key=None, seen=None):
    """The next pair: two visible collages of one live character (a random one, or char_key's), not a pair this
    browser has already seen (`seen`: pair ids) nor one the signed-in fan already judged."""
    DemoData.ensure_loaded()
    me = C.me()
    duels = C.opt_table("duels")
    pinned = None
    if char_key:
        pinned = app_tables.characters.get(key=char_key) if isinstance(char_key, str) else None
        if not _live(pinned):
            return C.fail("That character isn't on PerfectCast.")
    done = {x for x in (seen if isinstance(seen, list) else [])[:400] if isinstance(x, str)}
    if me is not None and duels is not None:
        for d in duels.search(user=me):
            if d["winner"] is not None and d["loser"] is not None:
                done.add(_pair_id(d["winner"], d["loser"]))
    groups, chars = {}, {}
    for c in Shelf.visible_castings(**({"character": pinned} if pinned is not None else {})):
        ch = c["character"]
        if ch is None or (me is not None and c["user"] == me):
            continue
        cid = ch.get_id()
        if cid not in chars:
            chars[cid] = ch if _live(ch) else None
        if chars[cid] is not None:
            groups.setdefault(cid, []).append(c)
    pools = [g for g in groups.values() if len(g) >= 2]
    head = None
    if pinned is not None:
        head = dict(Shelf.char_ref(pinned), book={"key": pinned["book"]["key"], "title": pinned["book"]["title"]})
    if not pools:
        return C.ok(pair=None, reason="few", character=head, judged=_judged(me, duels))
    rnd = random.Random()
    pair = None
    weights = [len(g) for g in pools]
    for _ in range(40):
        g = rnd.choices(pools, weights=weights)[0]
        a, b = rnd.sample(g, 2)
        if _pair_id(a, b) not in done:
            pair = (a, b)
            break
    if pair is None:  # few fresh pairs left: look through them all (capped per character)
        fresh = [(a, b) for g in pools for i, a in enumerate(g[:60]) for b in g[i + 1:60] if _pair_id(a, b) not in done]
        pair = rnd.choice(fresh) if fresh else None
    if pair is None:
        return C.ok(pair=None, reason="all", character=head, judged=_judged(me, duels))
    hearted = Shelf.hearted_ids(me)
    ch = pair[0]["character"]
    return C.ok(pair=[dict(Shelf.casting_card(c, me, hearted), duel=stats(c, duels)) for c in pair],
                character=dict(Shelf.char_ref(ch), book={"key": ch["book"]["key"], "title": ch["book"]["title"]}),
                pair_id=_pair_id(*pair), judged=_judged(me, duels), counts=duels is not None)


@anvil.server.callable(require_user=True)
def vote_duel(winner_key, loser_key):
    """Save my pick for one pair (picking the same pair again changes the vote). Returns both collages' scores."""
    me = C.require_user()
    duels = C.opt_table("duels")
    if duels is None:
        return C.fail("Swoon-offs are still being set up. Your pick wasn't saved this time.")
    w, lost = _casting(winner_key), _casting(loser_key)
    if not (Shelf.visible(w) and Shelf.visible(lost)) or w == lost:
        return C.fail("That collage is gone. Here's another pair!")
    ch = w["character"]
    if ch is None or ch != lost["character"] or not _live(ch):
        return C.fail("Those two collages aren't for the same character.")
    if w["user"] == me or lost["user"] == me:
        return C.fail("You can't judge your own collage.")
    if C.rate_limited("duel", 300, 3600):
        return C.fail("So many swoons! Take a little break and come back.")
    pid = _pair_id(w, lost)
    row = None
    for d in duels.search(user=me, character=ch):
        if d["winner"] is not None and d["loser"] is not None and _pair_id(d["winner"], d["loser"]) == pid:
            row = d
            break
    if row is not None:
        row.update(winner=w, loser=lost, created=C.now())
    else:
        duels.add_row(user=me, character=ch, winner=w, loser=lost, created=C.now(), is_demo=False)
    return C.ok(stats={w["key"]: stats(w, duels), lost["key"]: stats(lost, duels)}, judged=_judged(me, duels))
