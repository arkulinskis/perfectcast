"""Casting: a fan's collage of celebrities for one character, plus swoons (hearts), comments and reports.

Each fan has at most one collage per character (saving again updates it). A collage holds 1 to 6 picks:
a celebrity's name, optionally one of the fan's own photos (Photos.py), and a short "why".
"""
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Photos, Shelf

MAX_PICKS = 6
LAYOUTS = ("hero", "grid", "polaroid", "strip")
TONES = ("rose", "violet", "crimson", "midnight")
REASONS = {"rude": "Rude or hateful", "spam": "Spam or ads", "explicit": "Explicit picture",
           "privacy": "Private person or stolen photo", "other": "Something else"}


def _casting(key):
    return app_tables.castings.get(key=key) if isinstance(key, str) and key else None


def _character(key):
    ch = app_tables.characters.get(key=key) if isinstance(key, str) and key else None
    if ch is None or (ch["status"] or "live") != "live" or ch["book"] is None or (ch["book"]["status"] or "live") != "live":
        return None
    return ch


def comment_dict(x, me, casting_owner=None):
    mine = me is not None and x["user"] == me
    return {"id": x.get_id(), "body": x["body"], "created": C.iso(x["created"]), "user": C.user_ref(x["user"]),
            "mine": mine, "can_delete": mine or C.is_admin(me) or (me is not None and casting_owner == me)}


def delete_casting_row(c):
    """A collage and everything hanging off it (picks, swoons, comments, reports). Photos stay in the drawer."""
    for x in app_tables.comments.search(casting=c):
        for r in app_tables.reports.search(comment=x):
            r.delete()
        x.delete()
    for t in (app_tables.picks, app_tables.hearts, app_tables.reports):
        for r in t.search(casting=c):
            r.delete()
    c.delete()


# ----------------------------------------------------------------------------------------------- reading
@anvil.server.callable
def get_cast(key):
    """One collage, its comments, and a few more collages of the same character."""
    me = C.me()
    c = _casting(key)
    if c is None or (c["hidden"] and not (C.is_admin(me) or (me is not None and c["user"] == me))):
        return C.fail("That collage is gone.")
    hearted = Shelf.hearted_ids(me)
    comments = sorted([x for x in app_tables.comments.search(casting=c) if not x["hidden"]], key=lambda x: x["created"])
    more = [o for o in Shelf.visible_castings(character=c["character"]) if o != c]
    more.sort(key=lambda o: int(o["hearts"] or 0), reverse=True)
    return C.ok(cast=Shelf.casting_card(c, me, hearted), comments=[comment_dict(x, me, c["user"]) for x in comments],
                more=[Shelf.casting_card(o, me, hearted) for o in more[:4]], reasons=REASONS)


@anvil.server.callable(require_user=True)
def get_editor(char_key):
    """Everything the collage editor needs: the character, my collage so far, my photos, the fans' favourites."""
    me = C.require_user()
    ch = _character(char_key)
    if ch is None:
        return C.fail("That character isn't open for casting.")
    c = app_tables.castings.get(user=me, character=ch)
    draft = None
    if c is not None:
        draft = {"key": c["key"], "caption": c["caption"] or "", "layout": c["layout"] or "hero", "tone": c["tone"] or "rose",
                 "picks": [Shelf.pick_dict(p) for p in Shelf.picks_of(c)]}
    photos = [Photos.photo_dict(p) for p in app_tables.photos.search(tables.order_by("created", ascending=False), owner=me)
              if (p["kind"] or "portrait") == "portrait" and not p["hidden"]]
    return C.ok(character=dict(Shelf.char_ref(ch), blurb=ch["blurb"] or ""), book=Shelf.book_card(ch["book"]),
                draft=draft, photos=photos, quota=Photos.quota(me), favourites=Shelf.consensus(ch)[:8],
                layouts=list(LAYOUTS), tones=list(TONES), max_picks=MAX_PICKS)


@anvil.server.callable(require_user=True)
def my_castings():
    """My casts page: my collages (hidden ones too), my numbers, and characters still waiting for me."""
    me = C.require_user()
    mine = sorted(app_tables.castings.search(user=me), key=lambda c: c["updated"] or c["created"], reverse=True)
    hearted = Shelf.hearted_ids(me)
    cast_chars = {c["character"].get_id() for c in mine if c["character"] is not None}
    waiting = []
    for b in {c["book"].get_id(): c["book"] for c in mine if c["book"] is not None}.values():
        if (b["status"] or "live") != "live":
            continue
        for ch in Shelf.live_characters(b):
            if ch.get_id() not in cast_chars:
                waiting.append(dict(Shelf.char_ref(ch), book={"key": b["key"], "title": b["title"], "cover": Shelf.photo_key(b["cover"])}))
    swooned = [h["casting"] for h in app_tables.hearts.search(tables.order_by("created", ascending=False), user=me)]
    swooned = [c for c in swooned if Shelf.visible(c)][:12]
    return {"castings": [Shelf.casting_card(c, me, hearted) for c in mine], "waiting": waiting[:12],
            "swooned": [Shelf.casting_card(c, me, hearted) for c in swooned],
            "stats": {"casts": len(mine), "hearts": int(sum(int(c["hearts"] or 0) for c in mine)),
                      "comments": int(sum(Shelf.comment_count(c) for c in mine)),
                      "books": len({c["book"].get_id() for c in mine if c["book"] is not None})},
            "quota": Photos.quota(me), "me": {"id": me.get_id(), "bio": me["bio"] or ""}}


# ----------------------------------------------------------------------------------------------- writing
@anvil.server.callable(require_user=True)
def save_casting(char_key, caption, layout, tone, picks):
    me = C.require_user()
    ch = _character(char_key)
    if ch is None:
        return C.fail("That character isn't open for casting.")
    if not isinstance(picks, list) or not picks:
        return C.fail("Add at least one star to your collage.")
    if len(picks) > MAX_PICKS:
        return C.fail("Up to %d stars per collage. Pick your favourites!" % MAX_PICKS)
    clean, seen = [], set()
    for i, p in enumerate(picks):
        if not isinstance(p, dict):
            return C.fail("Something in the collage didn't look right. Try again.")
        name = C.text(p.get("name"), 60)
        if len(name) < 2:
            return C.fail("Spot %d needs the star's name." % (i + 1))
        key = C.star_key(name)
        if not key:
            return C.fail("\"%s\" doesn't look like a name." % name)
        if key in seen:
            return C.fail("%s is in your collage twice." % name)
        seen.add(key)
        photo = None
        if p.get("photo"):
            photo = Photos.mine(me, p.get("photo"))
            if photo is None or photo["hidden"]:
                return C.fail("The photo for %s is gone. Choose another one." % name)
        clean.append((name, key, photo, C.text(p.get("note"), 140)))
    if C.rate_limited("save_casting", 40, 3600):
        return C.fail("That's a lot of casting for one hour. Take a breather and come back soon.")
    now = C.now()
    c = app_tables.castings.get(user=me, character=ch)
    created = c is None
    fields = dict(caption=C.text(caption, 280, multiline=True), layout=layout if layout in LAYOUTS else "hero",
                  tone=tone if tone in TONES else "rose", updated=now)
    if c is None:
        c = app_tables.castings.add_row(key=C.token(12), user=me, character=ch, book=ch["book"], hearts=0, hidden=False,
                                        created=now, is_demo=False, **fields)
    else:
        c.update(**fields)
        for old in app_tables.picks.search(casting=c):
            old.delete()
    for i, (name, key, photo, note) in enumerate(clean):
        app_tables.picks.add_row(casting=c, character=ch, user=me, star_name=name, star_key=key, photo=photo, note=note,
                                 position=i, is_demo=False)
    return C.ok(key=c["key"], created=created)


@anvil.server.callable(require_user=True)
def delete_casting(key):
    me = C.require_user()
    c = _casting(key)
    if c is None:
        return C.ok()
    if c["user"] != me and not C.is_admin(me):
        return C.fail("You can only delete your own collages.")
    delete_casting_row(c)
    return C.ok()


@anvil.server.callable(require_user=True)
def toggle_heart(key):
    """Swoon over someone's collage (or take the swoon back)."""
    me = C.require_user()
    c = _casting(key)
    if not Shelf.visible(c):
        return C.fail("That collage is gone.")
    if c["user"] == me:
        return C.fail("That's your own collage. Others will swoon over it!")
    h = app_tables.hearts.get(user=me, casting=c)
    if h is None:
        if C.rate_limited("heart", 300, 3600):
            return C.fail("Easy, heartthrob. Try again in a little while.")
        app_tables.hearts.add_row(user=me, casting=c, created=C.now(), is_demo=False)
    else:
        h.delete()
    c["hearts"] = len(app_tables.hearts.search(casting=c))
    return C.ok(hearts=int(c["hearts"]), hearted=h is None)


@anvil.server.callable(require_user=True)
def add_comment(key, body):
    me = C.require_user()
    c = _casting(key)
    if not Shelf.visible(c):
        return C.fail("That collage is gone.")
    body = C.text(body, 500, multiline=True)
    if len(body) < 2:
        return C.fail("Write a little more first.")
    if C.rate_limited("comment", 20, 3600):
        return C.fail("You're on fire! Please wait a bit before commenting again.")
    x = app_tables.comments.add_row(casting=c, user=me, body=body, created=C.now(), hidden=False, is_demo=False)
    return C.ok(comment=comment_dict(x, me, c["user"]))


@anvil.server.callable(require_user=True)
def delete_comment(comment_id):
    me = C.require_user()
    x = C.row_by_id(app_tables.comments, comment_id)
    if x is None:
        return C.ok()
    owner = x["casting"]["user"] if x["casting"] is not None else None
    if x["user"] != me and owner != me and not C.is_admin(me):
        return C.fail("You can only delete your own comments, or comments on your collage.")
    for r in app_tables.reports.search(comment=x):
        r.delete()
    x.delete()
    return C.ok()


@anvil.server.callable(require_user=True)
def report(kind, target, reason, note=""):
    """Flag a collage or a comment for the admins."""
    me = C.require_user()
    if reason not in REASONS:
        return C.fail("Please choose a reason.")
    if kind == "casting":
        c, x = _casting(target), None
        if c is None:
            return C.fail("That collage is gone.")
        if c["user"] == me:
            return C.fail("That's your own collage: you can edit or delete it instead.")
        dup = app_tables.reports.get(user=me, casting=c, comment=None, status="open")
    elif kind == "comment":
        x = C.row_by_id(app_tables.comments, target)
        if x is None:
            return C.fail("That comment is gone.")
        if x["user"] == me:
            return C.fail("That's your own comment: you can delete it instead.")
        c = x["casting"]
        dup = app_tables.reports.get(user=me, comment=x, status="open")
    else:
        return C.fail("Nothing to report.")
    if dup is not None:
        return C.ok(message="You already reported this. An admin will look at it.")
    if C.rate_limited("report", 10, 3600):
        return C.fail("Thanks for keeping an eye out! Please wait a bit before sending more reports.")
    app_tables.reports.add_row(user=me, casting=c, comment=x, reason=reason, note=C.text(note, 400, multiline=True),
                               status="open", created=C.now(), is_demo=False)
    return C.ok(message="Thank you. An admin will look at it soon.")
