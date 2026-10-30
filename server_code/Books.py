"""Books and characters: members suggest them, admins publish, edit and moderate.

A suggested book (status "pending") is visible only to the member who sent it and to admins until an admin
approves it ("live") or turns it down ("rejected"). A character suggested for a live book waits the same way.
Reports (Casting.report) land in the admin's Reports tab.
"""
import datetime as dt

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Casting, Photos, Shelf

STATUSES = ("live", "pending", "rejected")
MAX_CHARACTERS = 14


def _book(key):
    return app_tables.books.get(key=key) if isinstance(key, str) and key else None


def _date(v):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return False


def _book_fields(data):
    """Clean book fields from a form, or (None, problem)."""
    if not isinstance(data, dict):
        return None, C.fail("Something in the form didn't look right.")
    title, author = C.text(data.get("title"), 120), C.text(data.get("author"), 80)
    if len(title) < 2:
        return None, C.fail("The book needs a title.")
    if len(author) < 2:
        return None, C.fail("Who wrote it? Add the author.")
    release = _date(data.get("release"))
    if release is False:
        return None, C.fail("The release date doesn't look right.")
    try:
        spice = max(0, min(5, int(data.get("spice") or 0)))
    except (TypeError, ValueError):
        spice = 0
    try:
        series_no = int(data.get("series_no")) if data.get("series_no") not in (None, "") else None
        if series_no is not None and not 0 < series_no < 100:
            series_no = None
    except (TypeError, ValueError):
        series_no = None
    tropes = [t for t in (data.get("tropes") or []) if t in Shelf.TROPES][:6] if isinstance(data.get("tropes"), list) else []
    return {"title": title, "author": author, "series": C.text(data.get("series"), 80), "series_no": series_no,
            "release": release, "blurb": C.text(data.get("blurb"), 1500, multiline=True), "tropes": tropes,
            "spice": spice}, None


def _char_fields(c):
    if not isinstance(c, dict):
        return None
    name = C.text(c.get("name"), 60)
    if len(name) < 2:
        return None
    role = c.get("role") if c.get("role") in Shelf.ROLES else "side"
    return {"name": name, "role": role, "blurb": C.text(c.get("blurb"), 400, multiline=True)}


def delete_character_row(ch):
    for c in app_tables.castings.search(character=ch):
        Casting.delete_casting_row(c)
    for pk in app_tables.picks.search(character=ch):
        pk.delete()
    ch.delete()


# ----------------------------------------------------------------------------------------------- members suggest
@anvil.server.callable(require_user=True)
def suggest_book(data):
    """A member suggests a new book with its characters. An admin reviews it before it goes live."""
    me = C.require_user()
    fields, problem = _book_fields(data)
    if problem:
        return problem
    chars = [x for x in (_char_fields(c) for c in (data.get("characters") or [])[:MAX_CHARACTERS]) if x]
    if not chars:
        return C.fail("Add at least one character, so fans have someone to cast.")
    same = [b for b in app_tables.books.search() if b["title"].lower() == fields["title"].lower() and (b["status"] or "live") != "rejected"]
    if same:
        return C.fail("\"%s\" is already on PerfectCast or waiting for review." % fields["title"])
    cover = None
    if data.get("cover"):
        cover = Photos.mine(me, data.get("cover"))
        if cover is None:
            return C.fail("The cover picture is gone. Add it again.")
    if C.rate_limited("suggest_book", 6, 86400):
        return C.fail("Thanks for all the suggestions! Please wait until tomorrow for more.")
    b = app_tables.books.add_row(key=C.token(10), status="pending", submitted_by=me, cover=cover, created=C.now(),
                                 is_demo=False, **fields)
    for i, c in enumerate(chars):
        app_tables.characters.add_row(key=C.token(10), book=b, position=i, status="live", submitted_by=me, created=C.now(),
                                      is_demo=False, **c)
    return C.ok(key=b["key"], message="Thank you! An admin will review \"%s\" soon." % fields["title"])


@anvil.server.callable(require_user=True)
def suggest_character(book_key, name, role, blurb=""):
    """A member adds a missing character to a live book (an admin reviews it)."""
    me = C.require_user()
    b = _book(book_key)
    if b is None or (b["status"] or "live") != "live":
        return C.fail("That book isn't on PerfectCast.")
    c = _char_fields({"name": name, "role": role, "blurb": blurb})
    if c is None:
        return C.fail("The character needs a name.")
    if any(ch["name"].lower() == c["name"].lower() for ch in app_tables.characters.search(book=b)):
        return C.fail("%s is already in this book (or waiting for review)." % c["name"])
    if C.rate_limited("suggest_character", 10, 3600):
        return C.fail("That's plenty of characters for one hour. Thank you!")
    n = len(app_tables.characters.search(book=b))
    app_tables.characters.add_row(key=C.token(10), book=b, position=n, status="pending", submitted_by=me, created=C.now(),
                                  is_demo=False, **c)
    return C.ok(message="Thanks! %s will appear once an admin approves it." % c["name"])


# ----------------------------------------------------------------------------------------------- admin: books
def _admin_book(b):
    chars = sorted(app_tables.characters.search(book=b), key=lambda ch: (ch["position"] or 0, ch["name"]))
    return dict(Shelf.book_full(b, len(app_tables.castings.search(book=b))), created=C.iso(b["created"]),
                characters=[dict(Shelf.char_ref(ch), blurb=ch["blurb"] or "", status=ch["status"] or "live",
                                 casts=len(app_tables.castings.search(character=ch))) for ch in chars])


@anvil.server.callable(require_user=True)
def admin_books():
    C.require_admin()
    order = {"pending": 0, "live": 1, "rejected": 2}
    rows = sorted(app_tables.books.search(), key=lambda b: (order.get(b["status"] or "live", 1), -(b["release"] or dt.date(1900, 1, 1)).toordinal()))
    return {"books": [_admin_book(b) for b in rows], "tropes": Shelf.TROPES, "roles": Shelf.ROLES}


@anvil.server.callable(require_user=True)
def admin_save_book(key, data):
    """Create (key None) or update a book and its whole character list. Characters left out are deleted,
    with their collages."""
    me = C.require_admin()
    fields, problem = _book_fields(data)
    if problem:
        return problem
    status = data.get("status") if data.get("status") in STATUSES else "live"
    b = _book(key) if key else None
    if key and b is None:
        return C.fail("That book no longer exists.")
    cover = b["cover"] if b is not None else None
    if data.get("cover") and (cover is None or data.get("cover") != cover["key"]):
        cover = app_tables.photos.get(key=data.get("cover")) if isinstance(data.get("cover"), str) else None
        if cover is None:
            return C.fail("The cover picture is gone. Add it again.")
    elif not data.get("cover"):
        cover = None
    incoming = data.get("characters") or []
    if not isinstance(incoming, list) or len(incoming) > MAX_CHARACTERS * 2:
        return C.fail("Too many characters.")
    if b is None:
        b = app_tables.books.add_row(key=C.token(10), submitted_by=me, created=C.now(), is_demo=False, status=status,
                                     cover=cover, **fields)
    else:
        b.update(status=status, cover=cover, **fields)
    keep = set()
    for i, raw in enumerate(incoming):
        c = _char_fields(raw)
        if c is None:
            continue
        ch = app_tables.characters.get(key=raw.get("key")) if raw.get("key") else None
        if ch is not None and ch["book"] == b:
            ch.update(position=i, status=raw.get("status") if raw.get("status") in ("live", "pending") else "live", **c)
        else:
            ch = app_tables.characters.add_row(key=C.token(10), book=b, position=i, status="live", submitted_by=me,
                                               created=C.now(), is_demo=False, **c)
        keep.add(ch.get_id())
    for ch in app_tables.characters.search(book=b):
        if ch.get_id() not in keep:
            delete_character_row(ch)
    return C.ok(book=_admin_book(b))


@anvil.server.callable(require_user=True)
def admin_delete_book(key):
    C.require_admin()
    b = _book(key)
    if b is None:
        return C.ok()
    for ch in app_tables.characters.search(book=b):
        delete_character_row(ch)
    for c in app_tables.castings.search(book=b):
        Casting.delete_casting_row(c)
    b.delete()
    return C.ok()


# ----------------------------------------------------------------------------------------------- admin: review queue
@anvil.server.callable(require_user=True)
def admin_queue():
    C.require_admin()
    books = [dict(_admin_book(b), submitted_at=C.iso(b["created"])) for b in app_tables.books.search(status="pending")]
    chars = []
    for ch in app_tables.characters.search(tables.order_by("created", ascending=False), status="pending"):
        b = ch["book"]
        if b is None or (b["status"] or "live") != "live":
            continue
        chars.append(dict(Shelf.char_ref(ch), blurb=ch["blurb"] or "", book={"key": b["key"], "title": b["title"]},
                          by=C.user_ref(ch["submitted_by"]), submitted_at=C.iso(ch["created"])))
    return {"books": books, "characters": chars}


@anvil.server.callable(require_user=True)
def admin_review(kind, key, decision):
    C.require_admin()
    if decision not in ("approve", "reject"):
        return C.fail("Approve or reject?")
    if kind == "book":
        b = _book(key)
        if b is None:
            return C.fail("That book no longer exists.")
        b["status"] = "live" if decision == "approve" else "rejected"
        return C.ok()
    if kind == "character":
        ch = app_tables.characters.get(key=key) if isinstance(key, str) and key else None
        if ch is None:
            return C.fail("That character no longer exists.")
        if decision == "approve":
            ch["status"] = "live"
        else:
            delete_character_row(ch)
        return C.ok()
    return C.fail("Nothing to review.")


def queue_count():
    pending_chars = [ch for ch in app_tables.characters.search(status="pending")
                     if ch["book"] is not None and (ch["book"]["status"] or "live") == "live"]
    return len(app_tables.books.search(status="pending")) + len(pending_chars)


# ----------------------------------------------------------------------------------------------- admin: reports
def _report(r, me):
    x, c = r["comment"], r["casting"]
    target = {"kind": "comment" if x is not None else "casting"}
    if x is not None:
        target.update(body=x["body"], hidden=bool(x["hidden"]), by=C.user_ref(x["user"]), id=x.get_id())
    if c is not None:
        target["cast"] = Shelf.casting_card(c, me, set())
    return {"id": r.get_id(), "reason": Casting.REASONS.get(r["reason"], r["reason"]), "note": r["note"] or "",
            "status": r["status"], "created": C.iso(r["created"]), "by": C.user_ref(r["user"]), "target": target}


@anvil.server.callable(require_user=True)
def admin_reports(status="open"):
    me = C.require_admin()
    rows = app_tables.reports.search(tables.order_by("created", ascending=False))
    rows = [r for r in rows if status == "all" or r["status"] == status]
    return {"reports": [_report(r, me) for r in rows[:100]], "open": len(app_tables.reports.search(status="open"))}


@anvil.server.callable(require_user=True)
def admin_resolve(report_id, action):
    """dismiss: nothing wrong. hide: hide the collage or comment (its owner still sees it). delete: remove it.
    Every open report about the same thing is closed with it."""
    C.require_admin()
    r = C.row_by_id(app_tables.reports, report_id)
    if r is None:
        return C.fail("That report is gone.")
    if action not in ("dismiss", "hide", "delete"):
        return C.fail("Dismiss, hide or delete?")
    x, c = r["comment"], r["casting"]
    same = [o for o in app_tables.reports.search(status="open") if (o["comment"] == x if x is not None else (o["comment"] is None and o["casting"] == c))]
    for o in same + [r]:
        o["status"] = "done"
    if action == "hide":
        if x is not None:
            x["hidden"] = True
        elif c is not None:
            c["hidden"] = True
    elif action == "delete":
        if x is not None:
            for o in app_tables.reports.search(comment=x):
                o.delete()
            x.delete()
        elif c is not None:
            Casting.delete_casting_row(c)
    return C.ok()


@anvil.server.callable(require_user=True)
def admin_unhide(kind, key):
    C.require_admin()
    if kind == "casting":
        c = app_tables.castings.get(key=key) if isinstance(key, str) and key else None
        if c is not None:
            c["hidden"] = False
    return C.ok()
