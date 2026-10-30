"""Photos: celebrity pictures for collages and book covers.

The browser does the heavy lifting: the member crops each picture to a fixed shape and the page shrinks it
(portrait 600x750, cover 600x900, JPEG) plus a small thumbnail, before anything is uploaded. Here we only
accept real JPEG / PNG / WebP pictures under tight byte limits, and each member has a photo quota, so the
app's storage stays small. Re-encoding in the browser also drops EXIF data (camera, location).

Photos are served by the /photo endpoint under a random 20-character key: <api>/photo?k=KEY[&s=t]
(s=t: the thumbnail). Hidden photos (moderation) aren't served.
"""
import base64

import anvil
import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C

MAX_FULL = {"portrait": 220 * 1024, "cover": 320 * 1024}
MAX_THUMB = 48 * 1024
QUOTA = 60          # photos per member (admins: no limit)
KINDS = ("portrait", "cover")


@anvil.server.http_endpoint("/photo")
def photo(k=None, s=None, **kw):
    p = app_tables.photos.get(key=k) if isinstance(k, str) and 10 <= len(k) <= 40 else None
    if p is None or p["hidden"]:
        return anvil.server.HttpResponse(404, "Not found")
    media = p["thumb"] if s == "t" and p["thumb"] is not None else p["image"]
    return anvil.server.HttpResponse(200, media, headers={"Cache-Control": "public, max-age=31536000, immutable",
                                                         "Content-Type": media.content_type})


def _image(data_url, limit):
    """data:image/...;base64,... -> BlobMedia, only real JPEG / PNG / WebP pictures under `limit` bytes."""
    if not isinstance(data_url, str) or not data_url.startswith("data:image/") or ";base64," not in data_url:
        return None
    if len(data_url) > limit * 4 // 3 + 200:
        return None
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=False)
    except Exception:
        return None
    if raw[:3] == b"\xff\xd8\xff":
        kind = "image/jpeg"
    elif raw[:8] == b"\x89PNG\r\n\x1a\n":
        kind = "image/png"
    elif raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        kind = "image/webp"
    else:
        return None
    if len(raw) > limit:
        return None
    return anvil.BlobMedia(kind, raw, name="photo." + kind.split("/")[1])


def used_count(user):
    return len(app_tables.photos.search(owner=user))


def quota(user):
    used = app_tables.photos.search(owner=user)
    return {"used": len(used), "max": None if C.is_admin(user) else QUOTA,
            "bytes": int(sum((p["size"] or 0) for p in used))}


def photo_dict(p, uses=None):
    return {"key": p["key"], "label": p["label"] or "", "kind": p["kind"] or "portrait", "size": int(p["size"] or 0),
            "created": C.iso(p["created"]), "hidden": bool(p["hidden"]), "uses": uses or []}


def mine(user, key):
    """The member's own photo with this key, or None."""
    p = app_tables.photos.get(key=key) if isinstance(key, str) and key else None
    return p if p is not None and p["owner"] == user else None


@anvil.server.callable(require_user=True)
def upload_photo(full, thumb, label="", kind="portrait"):
    """One cropped, shrunk picture. Returns its key (collages and covers refer to it)."""
    me = C.require_user()
    kind = kind if kind in KINDS else "portrait"
    if C.rate_limited("photo", 40, 3600):
        return C.fail("That's a lot of photos in one hour. Please take a short break.")
    if not C.is_admin(me) and used_count(me) >= QUOTA:
        return C.fail("Your photo drawer is full (%d photos). Delete a few you no longer use, then try again." % QUOTA)
    img, th = _image(full, MAX_FULL[kind]), _image(thumb, MAX_THUMB)
    if img is None or th is None:
        return C.fail("That picture is too big or isn't a JPEG, PNG or WebP. Try another one.")
    p = app_tables.photos.add_row(owner=me, key=C.token(20), image=img, thumb=th, label=C.text(label, 60), kind=kind,
                                  size=img.length + th.length, created=C.now(), hidden=False, is_demo=False)
    return C.ok(photo=photo_dict(p), quota=quota(me))


@anvil.server.callable(require_user=True)
def list_photos():
    """The photo drawer: every picture of mine, newest first, with where each one is used."""
    me = C.require_user()
    uses = {}
    for pk in app_tables.picks.search(user=me):
        if pk["photo"] is not None and pk["casting"] is not None and pk["character"] is not None:
            uses.setdefault(pk["photo"]["key"], []).append({"casting": pk["casting"]["key"], "character": pk["character"]["name"]})
    for b in app_tables.books.search(submitted_by=me):
        if b["cover"] is not None:
            uses.setdefault(b["cover"]["key"], []).append({"book": b["key"], "character": "Cover of " + b["title"]})
    rows = app_tables.photos.search(tables.order_by("created", ascending=False), owner=me)
    return {"photos": [photo_dict(p, uses.get(p["key"])) for p in rows], "quota": quota(me)}


@anvil.server.callable(require_user=True)
def rename_photo(key, label):
    me = C.require_user()
    p = mine(me, key)
    if p is None:
        return C.fail("That photo is gone.")
    p["label"] = C.text(label, 60)
    return C.ok(photo=photo_dict(p))


@anvil.server.callable(require_user=True)
def delete_photo(key):
    """Delete one of my photos. Collage spots using it keep the name and show a monogram instead."""
    me = C.require_user()
    p = mine(me, key)
    if p is None:
        return C.ok(quota=quota(me))
    if app_tables.books.search(cover=p):
        return C.fail("This picture is a book's cover. Ask an admin to change the cover first.")
    for pk in app_tables.picks.search(photo=p):
        pk["photo"] = None
    p.delete()
    return C.ok(quota=quota(me))
