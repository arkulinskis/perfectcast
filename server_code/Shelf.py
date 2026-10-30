"""The reading side, open to everyone: the shelf of books, one book, one character, the stars, a fan's page.

The "fans' pick" for a character (consensus) counts, for each celebrity, how many collages include them
(one vote per collage, hidden collages don't count); ties go to the star whose collages got more hearts.
"""
import datetime as dt

import anvil.server
from anvil.tables import app_tables

from . import common as C
from . import DemoData

ROLES = {"heroine": "Heroine", "hero": "Hero", "love": "Love interest", "villain": "Villain",
         "royal": "Royalty", "ally": "Ally", "side": "Supporting"}
TROPES = ["Enemies to lovers", "Fae", "Dragons", "Morally grey", "Forced proximity", "Slow burn", "Found family",
          "Fated mates", "Court intrigue", "Arranged marriage", "Chosen one", "Who did this to you", "Vampires",
          "Witches", "Only one bed", "Rivals", "Dark academia", "Gods & curses", "Shapeshifters", "Touch her and die"]


# ----------------------------------------------------------------------------------------------- shapes sent to pages
def photo_key(p):
    return p["key"] if p is not None and not p["hidden"] else None


def book_card(b, casts=0):
    return {"key": b["key"], "title": b["title"], "author": b["author"] or "", "series": b["series"] or "",
            "series_no": b["series_no"], "release": C.iso(b["release"]), "tropes": list(b["tropes"] or []),
            "spice": int(b["spice"] or 0), "cover": photo_key(b["cover"]), "casts": casts, "status": b["status"] or "live",
            "blurb": b["blurb"] or ""}


def book_full(b, casts=0):
    out = book_card(b, casts)
    out["submitted_by"] = C.user_ref(b["submitted_by"]) if b["submitted_by"] is not None else None
    return out


def role_label(role):
    return ROLES.get(role or "", "Supporting")


def char_ref(ch):
    return {"key": ch["key"], "name": ch["name"], "role": ch["role"] or "side", "role_label": role_label(ch["role"])}


def picks_of(c):
    return sorted(app_tables.picks.search(casting=c), key=lambda p: p["position"] or 0)


def pick_dict(pk):
    return {"name": pk["star_name"], "star": pk["star_key"], "photo": photo_key(pk["photo"]), "note": pk["note"] or ""}


def visible(c):
    return c is not None and not c["hidden"]


def visible_castings(**kw):
    return [c for c in app_tables.castings.search(**kw) if not c["hidden"]]


def hearted_ids(me):
    if me is None:
        return set()
    return {h["casting"].get_id() for h in app_tables.hearts.search(user=me) if h["casting"] is not None}


def comment_count(c):
    return len([x for x in app_tables.comments.search(casting=c) if not x["hidden"]])


def casting_card(c, me, hearted=None):
    if hearted is None:
        hearted = hearted_ids(me)
    ch, b = c["character"], c["book"]
    mine = me is not None and c["user"] == me
    return {"key": c["key"], "caption": c["caption"] or "", "layout": c["layout"] or "hero", "tone": c["tone"] or "rose",
            "hearts": int(c["hearts"] or 0), "hearted": c.get_id() in hearted, "comments": comment_count(c),
            "created": C.iso(c["created"]), "updated": C.iso(c["updated"] or c["created"]),
            "user": C.user_ref(c["user"]), "character": char_ref(ch) if ch is not None else None,
            "book": {"key": b["key"], "title": b["title"], "cover": photo_key(b["cover"])} if b is not None else None,
            "picks": [pick_dict(p) for p in picks_of(c)], "mine": mine, "hidden": bool(c["hidden"]),
            "can_delete": mine or C.is_admin(me)}


def consensus(ch, castings=None):
    """[{name, star, votes, pct, photo, hearts}] for one character, best first."""
    castings = castings if castings is not None else visible_castings(character=ch)
    ids = {c.get_id(): c for c in castings}
    tally = {}
    for pk in app_tables.picks.search(character=ch):
        c = pk["casting"]
        if c is None or c.get_id() not in ids:
            continue
        t = tally.setdefault(pk["star_key"], {"names": {}, "casts": set(), "hearts": 0, "photo": None, "best": -1, "lead": 0})
        t["names"][pk["star_name"]] = t["names"].get(pk["star_name"], 0) + 1
        if c.get_id() not in t["casts"]:
            t["casts"].add(c.get_id())
            t["hearts"] += int(c["hearts"] or 0)
        if (pk["position"] or 0) == 0:
            t["lead"] += 1
        key = photo_key(pk["photo"])
        if key and int(c["hearts"] or 0) > t["best"]:
            t["best"], t["photo"] = int(c["hearts"] or 0), key
    n = max(1, len(castings))
    out = [{"name": max(t["names"].items(), key=lambda kv: kv[1])[0], "star": k, "votes": len(t["casts"]),
            "lead": t["lead"], "pct": int(round(100.0 * len(t["casts"]) / n)), "photo": t["photo"], "hearts": t["hearts"]}
           for k, t in tally.items()]
    out.sort(key=lambda s: (-s["votes"], -s["lead"], -s["hearts"], s["name"]))
    return out


def can_see_book(b, me):
    if b is None:
        return False
    return (b["status"] or "live") == "live" or C.is_admin(me) or (me is not None and b["submitted_by"] == me)


def live_characters(b):
    return sorted([ch for ch in app_tables.characters.search(book=b) if (ch["status"] or "live") == "live"],
                  key=lambda ch: (ch["position"] or 0, ch["name"]))


# ----------------------------------------------------------------------------------------------- callables
@anvil.server.callable
def get_shelf():
    """The books page (and the landing page's shelf): every live book, the trending collages, the trope list."""
    DemoData.ensure_loaded()
    me = C.me()
    castings = visible_castings()
    per_book = {}
    for c in castings:
        if c["book"] is not None:
            per_book[c["book"].get_id()] = per_book.get(c["book"].get_id(), 0) + 1
    books = [book_card(b, per_book.get(b.get_id(), 0)) for b in app_tables.books.search(status="live")]
    books.sort(key=lambda b: b["release"] or "", reverse=True)
    recent = C.now() - dt.timedelta(days=45)
    hot = sorted(castings, key=lambda c: (int(c["hearts"] or 0) + (3 if (c["updated"] or c["created"]) > recent else 0),
                                           c["updated"] or c["created"]), reverse=True)[:8]
    hearted = hearted_ids(me)
    stats = None
    if me is not None:
        mine = [c for c in app_tables.castings.search(user=me)]
        stats = {"casts": len(mine), "hearts": int(sum(int(c["hearts"] or 0) for c in mine))}
    return {"books": books, "trending": [casting_card(c, me, hearted) for c in hot], "tropes": TROPES,
            "fans": len([u for u in app_tables.users.search() if u["enabled"] is not False or u["is_demo"]]),
            "total_casts": len(castings), "me": stats}


@anvil.server.callable
def get_book(key):
    me = C.me()
    b = app_tables.books.get(key=key) if isinstance(key, str) and key else None
    if not can_see_book(b, me):
        return C.fail("That book isn't on PerfectCast (yet).")
    castings = visible_castings(book=b)
    hearted = hearted_ids(me)
    my = {}
    if me is not None:
        for c in app_tables.castings.search(user=me, book=b):
            if c["character"] is not None:
                my[c["character"]["key"]] = c["key"]
    chars = []
    for ch in live_characters(b):
        mine = [c for c in castings if c["character"] == ch]
        top = consensus(ch, mine)[:3]
        chars.append(dict(char_ref(ch), blurb=ch["blurb"] or "", casts=len(mine), top=top))
    recent = sorted(castings, key=lambda c: c["updated"] or c["created"], reverse=True)[:6]
    return C.ok(book=book_full(b, len(castings)), characters=chars, recent=[casting_card(c, me, hearted) for c in recent],
                my=my, fans=len({c["user"].get_id() for c in castings if c["user"] is not None}),
                can_edit=C.is_admin(me), roles=ROLES)


@anvil.server.callable
def get_character(key, sort="loved"):
    me = C.me()
    ch = app_tables.characters.get(key=key) if isinstance(key, str) and key else None
    if ch is None or not can_see_book(ch["book"], me) or ((ch["status"] or "live") != "live" and not C.is_admin(me)):
        return C.fail("That character isn't on PerfectCast.")
    castings = visible_castings(character=ch)
    if sort == "new":
        castings.sort(key=lambda c: c["updated"] or c["created"], reverse=True)
    else:
        castings.sort(key=lambda c: (int(c["hearts"] or 0), c["updated"] or c["created"]), reverse=True)
    hearted = hearted_ids(me)
    mine = app_tables.castings.get(user=me, character=ch) if me is not None else None
    siblings = []
    for other in live_characters(ch["book"]):
        top = consensus(other)[:1]
        siblings.append(dict(char_ref(other), photo=top[0]["photo"] if top else None, star=top[0]["name"] if top else None,
                             current=other == ch))
    return C.ok(character=dict(char_ref(ch), blurb=ch["blurb"] or ""), book=book_card(ch["book"], 0),
                consensus=consensus(ch, castings)[:8], castings=[casting_card(c, me, hearted) for c in castings[:60]],
                total=len(castings), mine=mine["key"] if mine is not None else None, siblings=siblings)


def _star_tally():
    """star_key -> {names, picks, castings, characters, fans, photo, best}"""
    ok_castings = {c.get_id(): c for c in visible_castings()}
    out = {}
    for pk in app_tables.picks.search():
        c = pk["casting"]
        if c is None or c.get_id() not in ok_castings or not pk["star_key"]:
            continue
        t = out.setdefault(pk["star_key"], {"names": {}, "castings": set(), "characters": {}, "votes": {}, "fans": set(),
                                            "photo": None, "best": -1})
        t["names"][pk["star_name"]] = t["names"].get(pk["star_name"], 0) + 1
        t["castings"].add(c.get_id())
        if c["user"] is not None:
            t["fans"].add(c["user"].get_id())
        if pk["character"] is not None:
            cid = pk["character"].get_id()
            t["characters"][cid] = pk["character"]
            t["votes"][cid] = t["votes"].get(cid, 0) + 1
        key, hearts = photo_key(pk["photo"]), int(c["hearts"] or 0)
        if key and hearts > t["best"]:
            t["best"], t["photo"] = hearts, key
    return out


def _star_name(t):
    return max(t["names"].items(), key=lambda kv: kv[1])[0]


@anvil.server.callable
def list_stars():
    """The Stars page: every celebrity the fans have cast, most-cast first."""
    DemoData.ensure_loaded()
    tally = _star_tally()
    stars = []
    for k, t in tally.items():
        chars = list(t["characters"].values())
        top_role = None
        if chars:
            ch = t["characters"][max(t["votes"].items(), key=lambda kv: kv[1])[0]]
            top_role = {"key": ch["key"], "name": ch["name"], "book": ch["book"]["title"] if ch["book"] is not None else ""}
        stars.append({"star": k, "name": _star_name(t), "casts": len(t["castings"]), "roles": len(chars),
                      "fans": len(t["fans"]), "photo": t["photo"], "top_role": top_role})
    stars.sort(key=lambda s: (-s["casts"], -s["roles"], s["name"]))
    return {"stars": stars[:80], "total": len(stars)}


@anvil.server.callable
def get_star(slug):
    slug = C.star_key(slug)
    tally = _star_tally()
    t = tally.get(slug)
    if not slug or t is None:
        return C.fail("Nobody has cast that star yet.")
    roles = []
    for ch in t["characters"].values():
        cons = consensus(ch)
        mine = [s for s in cons if s["star"] == slug]
        if not mine:
            continue
        rank = [s["star"] for s in cons].index(slug) + 1
        roles.append(dict(char_ref(ch), book=book_card(ch["book"], 0), votes=mine[0]["votes"], pct=mine[0]["pct"],
                          rank=rank, photo=mine[0]["photo"]))
    roles.sort(key=lambda r: (r["rank"], -r["votes"]))
    gallery = []
    seen = set()
    for pk in app_tables.picks.search(star_key=slug):
        c, key = pk["casting"], photo_key(pk["photo"])
        if key and key not in seen and visible(c):
            seen.add(key)
            gallery.append({"photo": key, "casting": c["key"], "by": C.user_ref(c["user"])["name"], "hearts": int(c["hearts"] or 0)})
    gallery.sort(key=lambda g: -g["hearts"])
    return C.ok(star={"star": slug, "name": _star_name(t), "casts": len(t["castings"]), "fans": len(t["fans"]),
                      "photo": t["photo"]}, roles=roles, gallery=gallery[:12])


@anvil.server.callable
def get_fan(user_id):
    """A fan's public page: their name, bio and collages. Never their email."""
    me = C.me()
    u = C.row_by_id(app_tables.users, user_id)
    if u is None or (u["enabled"] is False and not u["is_demo"]):
        return C.fail("That fan isn't here any more.")
    castings = sorted(visible_castings(user=u), key=lambda c: c["updated"] or c["created"], reverse=True)
    hearted = hearted_ids(me)
    stars = {}
    for c in castings:
        for pk in app_tables.picks.search(casting=c):
            stars[pk["star_name"]] = stars.get(pk["star_name"], 0) + 1
    fav = sorted(stars.items(), key=lambda kv: -kv[1])[:5]
    return C.ok(fan={"id": u.get_id(), "name": C.name_of(u), "bio": u["bio"] or "", "joined": C.iso(u["signed_up"]),
                     "me": me is not None and me == u}, castings=[casting_card(c, me, hearted) for c in castings],
                hearts=int(sum(int(c["hearts"] or 0) for c in castings)),
                books=len({c["book"].get_id() for c in castings if c["book"] is not None}),
                stars=[{"name": n, "star": C.star_key(n), "count": k} for n, k in fav])
