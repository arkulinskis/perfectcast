"""Server tests against the strict mock of Anvil (tools/testing/mock).

    python tools/testing/test_server.py          -> prints ALL OK, or the first failure

call(name, ...) runs a server function the way the browser does: by name, with require_user enforced,
and the reply must be JSON (a datetime or a row in a reply fails here, like it would break the page).
Add tests for every new server function: the happy path, bad input, and someone who isn't allowed.
"""
import datetime as dt
import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
_tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copytree(PROJECT / "server_code", _tmp / "app")
(_tmp / "app" / "__init__.py").write_text("")
os.environ["ANVIL_APP_YAML"] = str(PROJECT / "anvil.yaml")  # the mock's tables follow the app's own schema
sys.path[:0] = [str(HERE / "mock"), str(_tmp)]
import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
from anvil.tables import app_tables as T  # noqa: E402

M = {p.stem: importlib.import_module("app." + p.stem) for p in sorted((PROJECT / "server_code").glob("*.py"))}
now = dt.datetime.now(dt.timezone.utc)


def call(name, *args):
    r = anvil.server.call(name, *args)
    json.dumps(r)  # strict: must be JSON-able
    return r


def as_user(row):
    anvil.users.CURRENT[0] = row
    anvil.server.session.use(row.get_id() if row is not None else None)


def denied(name, *args):
    try:
        call(name, *args)
    except anvil.server.PermissionDenied:
        return True
    return False


def ok(r, msg=""):
    assert isinstance(r, dict) and r.get("ok"), (msg, r)
    return r


def bad(r, msg=""):
    assert isinstance(r, dict) and r.get("ok") is False and r.get("error"), (msg, r)
    return r


def person(email, name=None, **kw):
    return T.users.add_row(email=email, enabled=True, signed_up=now, display_name=name, **kw)


# ---------------------------------------------------------------------------------- accounts
admin = person("arkulinskis@gmail.com", "The Admin")
ana = person("ana@example.com", "Ana")
bob = person("bob@example.com")

as_user(None)
assert call("get_me") is None
assert denied("update_profile", "X")
as_user(admin)
assert call("get_me")["is_admin"] is True, "ADMIN_EMAILS become admins on first sign-in"
as_user(ana)
me = call("get_me")
assert me["name"] == "Ana" and me["is_admin"] is False
assert ana["last_seen"] is not None
as_user(bob)
assert call("get_me")["name"] == "Bob", "a name comes from the email when none is set"
bad(call("update_profile", " x "))
assert ok(call("update_profile", "  Bob   Stone "))["me"]["name"] == "Bob Stone"

# ---------------------------------------------------------------------------------- feedback
as_user(None)
bad(call("submit_feedback", "bug", "hi"))
ok(call("submit_feedback", "bug", "The button is broken", "guest@example.com", {"page": "#home", "evil": "x" * 9999}))
fb = T.feedback.search()[0]
assert fb["name"] == "Guest" and fb["email"] == "guest@example.com" and "evil" not in fb["context"] and fb["status"] == "new"
for i in range(4):
    ok(call("submit_feedback", "idea", "Idea number %d" % i))
bad(call("submit_feedback", "idea", "One too many this hour"), "rate limit")
as_user(ana)
ok(call("submit_feedback", "nonsense-kind", "Signed-in feedback"))
assert T.feedback.get(message="Signed-in feedback")["kind"] == "other"
assert denied("list_feedback")
as_user(admin)
lst = call("list_feedback")
assert lst["counts"]["new"] == 6 and len(lst["items"]) == 6
fid = lst["items"][0]["id"]
ok(call("set_feedback_status", fid, "done", "Fixed it"))
assert call("list_feedback", "done")["items"][0]["note"] == "Fixed it"
bad(call("set_feedback_status", fid, "weird"))
bad(call("set_feedback_status", "nope", "done"))
ok(call("delete_feedback", fid))
assert len(call("list_feedback")["items"]) == 5

# ---------------------------------------------------------------------------------- admin
as_user(ana)
for fn, args in [("admin_overview", ()), ("list_users", ()), ("set_admin", (bob.get_id(), True)), ("demo_load", ()), ("demo_remove", ())]:
    assert denied(fn, *args), fn
as_user(admin)
ov = call("admin_overview")
assert ov["users"] == 3 and ov["admins"] == 1 and ov["feedback_new"] == 5 and "books" in ov
assert len(call("list_users")["users"]) == 3 and len(call("list_users", "bob")["users"]) == 1
ok(call("set_admin", bob.get_id(), True))
assert bob["is_admin"] is True
bad(call("set_admin", admin.get_id(), False), "can't remove your own admin")
ok(call("set_enabled", bob.get_id(), False))
assert bob["enabled"] is False
bad(call("set_enabled", admin.get_id(), False))
ok(call("set_enabled", bob.get_id(), True))
ok(call("set_admin", bob.get_id(), False))
assert bob["is_admin"] is False

# ---------------------------------------------------------------------------------- demo data
as_user(None)
shelf = call("get_shelf")
DD = M["DemoData"]
assert DD.state() == "loaded" and len(shelf["books"]) == len(DD.BOOKS), "demo loads on first visit"
assert shelf["trending"] and shelf["tropes"] and shelf["me"] is None
assert shelf["books"][0]["release"] >= shelf["books"][-1]["release"], "newest first"
assert all(b["cover"] for b in shelf["books"])
first = [b for b in shelf["books"] if b["title"] == "A Crown of Ash & Honey"][0]
assert "@" not in json.dumps(shelf), "no emails leak"

# ---------------------------------------------------------------------------------- photo endpoint
from anvil.server import ENDPOINTS  # noqa: E402
r = ENDPOINTS["/photo"](k=first["cover"])
assert r.status == 200 and r.body.content_type == "image/svg+xml"
assert ENDPOINTS["/photo"](k="nope").status == 404 and ENDPOINTS["/photo"](k=None).status == 404

# ---------------------------------------------------------------------------------- reading pages
bk = ok(call("get_book", first["key"]))
assert len(bk["characters"]) == 4, "the pending character isn't listed"
assert bk["characters"][0]["top"], "consensus for a demo character"
bad(call("get_book", "missing"))
isolde = bk["characters"][0]
chp = ok(call("get_character", isolde["key"]))
assert chp["consensus"][0]["votes"] >= chp["consensus"][-1]["votes"] and chp["total"] == len(chp["castings"])
assert chp["mine"] is None and len(chp["siblings"]) == 4
assert ok(call("get_character", isolde["key"], "new"))["castings"]
bad(call("get_character", "missing"))
stars = call("list_stars")
assert stars["stars"] and stars["stars"][0]["casts"] >= stars["stars"][-1]["casts"]
st = ok(call("get_star", stars["stars"][0]["star"]))
assert st["roles"] and st["gallery"] and st["star"]["name"]
assert ok(call("get_star", stars["stars"][0]["name"].upper()))["star"]["star"] == stars["stars"][0]["star"], "names normalise"
bad(call("get_star", "nobody-at-all"))
demo_fan = T.users.get(email="wren.demo@example.com")
fan = ok(call("get_fan", demo_fan.get_id()))
assert fan["fan"]["name"] == "Wren Talbot" and "email" not in fan["fan"]
bad(call("get_fan", "nope"))
pending_book = T.books.get(status="pending")
bad(call("get_book", pending_book["key"]), "pending books are hidden from visitors")
cast_key = chp["castings"][0]["key"]
cp = ok(call("get_cast", cast_key))
assert cp["cast"]["picks"] and "reasons" in cp
bad(call("get_cast", "missing"))

# guests can't write
for fn, args in [("upload_photo", ("x", "y")), ("list_photos", ()), ("get_editor", (isolde["key"],)),
                 ("save_casting", (isolde["key"], "", "hero", "rose", [])), ("toggle_heart", (cast_key,)),
                 ("add_comment", (cast_key, "hi")), ("report", ("casting", cast_key, "spam")), ("my_castings", ()),
                 ("suggest_book", ({},)), ("suggest_character", (first["key"], "X", "side")), ("update_bio", ("x",)),
                 ("rename_photo", ("x", "y")), ("delete_photo", ("x",)), ("delete_casting", ("x",)), ("delete_comment", ("x",))]:
    assert denied(fn, *args), fn

# ---------------------------------------------------------------------------------- photos
import base64  # noqa: E402
JPG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 2000).decode()
THUMB = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 300).decode()
HUGE = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * (M["Photos"].MAX_FULL["portrait"] + 10)).decode()
GIF = "data:image/gif;base64," + base64.b64encode(b"GIF89a" + b"0" * 50).decode()
as_user(ana)
bad(call("upload_photo", HUGE, THUMB, "Too big"), "size limit")
bad(call("upload_photo", GIF, THUMB, "Gif"), "only jpeg/png/webp")
bad(call("upload_photo", "nonsense", THUMB))
up = ok(call("upload_photo", JPG, THUMB, "  Saoirse   Vale "))
pk1 = up["photo"]["key"]
assert up["photo"]["label"] == "Saoirse Vale" and up["quota"]["used"] == 1 and up["quota"]["max"] == M["Photos"].QUOTA
pk2 = ok(call("upload_photo", JPG, THUMB, "Dmitri Ashcombe"))["photo"]["key"]
assert ENDPOINTS["/photo"](k=pk1, s="t").body.length < ENDPOINTS["/photo"](k=pk1).body.length, "thumbnail is served with s=t"
lst = call("list_photos")
assert {p["key"] for p in lst["photos"]} == {pk1, pk2} and lst["quota"]["used"] == 2
ok(call("rename_photo", pk1, "Saoirse V."))
as_user(bob)
bad(call("rename_photo", pk1, "mine now"), "can't rename someone else's photo")
ok(call("delete_photo", pk1))  # not his: nothing happens
assert T.photos.get(key=pk1) is not None
assert call("list_photos")["photos"] == []

# ---------------------------------------------------------------------------------- casting
as_user(ana)
ed = ok(call("get_editor", isolde["key"]))
assert ed["draft"] is None and len(ed["photos"]) == 2 and ed["favourites"] and ed["max_picks"] == 6
bad(call("get_editor", "missing"))
bad(call("save_casting", isolde["key"], "", "hero", "rose", []), "needs a pick")
bad(call("save_casting", isolde["key"], "", "hero", "rose", [{"name": "x"}]), "name too short")
bad(call("save_casting", isolde["key"], "", "hero", "rose", [{"name": "Ana Star"}, {"name": "ana  star"}]), "duplicate star")
bad(call("save_casting", isolde["key"], "", "hero", "rose", [{"name": "Star number %d" % i} for i in range(7)]), "max 6")
as_user(bob)
bob_photo = ok(call("upload_photo", JPG, THUMB, "Bob's pic"))["photo"]["key"]
as_user(ana)
bad(call("save_casting", isolde["key"], "", "hero", "rose", [{"name": "Someone", "photo": bob_photo}]), "only my photos")
sv = ok(call("save_casting", isolde["key"], "My Isolde", "weird-layout", "rose",
             [{"name": "Saoirse Vale", "photo": pk1, "note": "Perfect"}, {"name": "Brand New Star", "photo": pk2},
              {"name": "No Photo Person"}]))
assert sv["created"] is True
mine = ok(call("get_cast", sv["key"]))["cast"]
assert mine["layout"] == "hero" and mine["mine"] and len(mine["picks"]) == 3 and mine["picks"][2]["photo"] is None
sv2 = ok(call("save_casting", isolde["key"], "Changed my mind", "polaroid", "violet", [{"name": "Brand New Star", "photo": pk2}]))
assert sv2["key"] == sv["key"] and sv2["created"] is False, "one collage per fan per character"
assert len(T.picks.search(casting=T.castings.get(key=sv["key"]))) == 1
assert ok(call("get_editor", isolde["key"]))["draft"]["caption"] == "Changed my mind"
assert ok(call("get_character", isolde["key"]))["mine"] == sv["key"]
assert ok(call("get_book", first["key"]))["my"][isolde["key"]] == sv["key"]
lst = call("list_photos")
assert [u for p in lst["photos"] if p["key"] == pk2 for u in p["uses"]], "the drawer shows where a photo is used"
assert ok(call("get_star", "brand-new-star"))["star"]["casts"] == 1
bad(call("toggle_heart", sv["key"]), "no swooning over your own collage")
mc = call("my_castings")
assert mc["stats"]["casts"] == 1 and mc["waiting"], "other characters of the same book are waiting"

as_user(bob)
h = ok(call("toggle_heart", sv["key"]))
assert h["hearted"] and h["hearts"] == 1
assert ok(call("toggle_heart", sv["key"]))["hearts"] == 0
ok(call("toggle_heart", sv["key"]))
assert call("my_castings")["swooned"][0]["key"] == sv["key"]
bad(call("toggle_heart", "missing"))
bad(call("add_comment", sv["key"], " "))
cm = ok(call("add_comment", sv["key"], "Gorgeous pick!"))["comment"]
assert cm["mine"] and cm["can_delete"]
assert ok(call("get_cast", sv["key"]))["comments"][0]["body"] == "Gorgeous pick!"
bad(call("report", "casting", sv["key"], "nonsense"))
ok(call("report", "casting", sv["key"], "spam", "testing"))
assert "already" in ok(call("report", "casting", sv["key"], "spam"))["message"]
bad(call("report", "comment", cm["id"], "rude"), "can't report your own comment")
bad(call("delete_casting", sv["key"]), "can't delete someone else's collage")
as_user(ana)
ok(call("report", "comment", cm["id"], "rude"))
bad(call("report", "casting", sv["key"], "spam"), "can't report your own collage")
assert ok(call("get_cast", sv["key"]))["comments"][0]["can_delete"], "the collage owner can delete comments on it"
bio = ok(call("update_bio", "  Hello  there "))
assert bio["me"]["bio"] == "Hello there" and ok(call("get_fan", ana.get_id()))["fan"]["bio"] == "Hello there"

# deleting a photo in use keeps the pick, without the picture
ok(call("delete_photo", pk2))
assert ok(call("get_cast", sv["key"]))["cast"]["picks"][0]["photo"] is None
assert ENDPOINTS["/photo"](k=pk2).status == 404

# quota
QUOTA = M["Photos"].QUOTA
M["Photos"].QUOTA = 1
as_user(bob)
bad(call("upload_photo", JPG, THUMB, "over"), "quota")
M["Photos"].QUOTA = QUOTA

# ---------------------------------------------------------------------------------- suggestions
as_user(bob)
bad(call("suggest_book", {"title": "x", "author": "Someone"}))
bad(call("suggest_book", {"title": "Good Title", "author": "Someone", "characters": []}), "needs a character")
bad(call("suggest_book", {"title": "A Crown of Ash & Honey", "author": "X", "characters": [{"name": "Hero"}]}), "duplicate title")
bad(call("suggest_book", {"title": "Good Title", "author": "Someone", "release": "not a date", "characters": [{"name": "Hero"}]}))
sb = ok(call("suggest_book", {"title": "The Bob Book", "author": "Bob Stone", "release": "2026-12-01", "spice": 9,
                               "tropes": ["Fae", "Not a trope"], "cover": bob_photo,
                               "characters": [{"name": "Lead Lady", "role": "heroine"}, {"name": "Brooding Man", "role": "weird"}]}))
bbook = T.books.get(key=sb["key"])
assert bbook["status"] == "pending" and bbook["spice"] == 5 and bbook["tropes"] == ["Fae"] and bbook["cover"]["key"] == bob_photo
assert ok(call("get_book", sb["key"]))["book"]["status"] == "pending", "the suggester sees their pending book"
bad(call("delete_photo", bob_photo), "a cover can't be deleted")
as_user(ana)
bad(call("get_book", sb["key"]))
bad(call("get_editor", T.characters.get(book=bbook, name="Lead Lady")["key"]), "pending books can't be cast yet")
bad(call("suggest_character", first["key"], "x", "side"))
bad(call("suggest_character", first["key"], "isolde varre", "heroine"), "duplicate character")
ok(call("suggest_character", first["key"], "New Side Character", "side", "Blurb"))
bad(call("suggest_character", sb["key"], "Someone", "side"), "only live books")

# ---------------------------------------------------------------------------------- admin: books, queue, reports
for fn, args in [("admin_books", ()), ("admin_save_book", (None, {})), ("admin_delete_book", (first["key"],)), ("admin_queue", ()),
                 ("admin_review", ("book", sb["key"], "approve")), ("admin_reports", ()), ("admin_resolve", ("x", "hide")),
                 ("admin_unhide", ("casting", sv["key"]))]:
    assert denied(fn, *args), fn
as_user(admin)
ov = call("admin_overview")
assert ov["queue"] >= 3 and ov["reports"] >= 2 and ov["books"] == len(DD.BOOKS) and ov["photos"] > 0
ab = call("admin_books")
assert ab["books"][0]["status"] == "pending", "pending books first"
q = call("admin_queue")
assert any(b["key"] == sb["key"] for b in q["books"]) and any(c["name"] == "New Side Character" for c in q["characters"])
bad(call("admin_review", "book", sb["key"], "maybe"))
ok(call("admin_review", "book", sb["key"], "approve"))
assert T.books.get(key=sb["key"])["status"] == "live"
newc = [c for c in q["characters"] if c["name"] == "New Side Character"][0]
ok(call("admin_review", "character", newc["key"], "approve"))
assert len(ok(call("get_book", first["key"]))["characters"]) == 5
rej = [c for c in q["characters"] if c["name"] == "Lady Briar"][0]
ok(call("admin_review", "character", rej["key"], "reject"))
assert T.characters.get(key=rej["key"]) is None
# create, edit, delete a book
up = ok(call("upload_photo", JPG, THUMB, "Cover", "cover"))
assert up["quota"]["max"] is None, "admins have no photo limit"
nb = ok(call("admin_save_book", None, {"title": "Admin Book", "author": "A. Writer", "status": "live", "cover": up["photo"]["key"],
                                       "characters": [{"name": "One", "role": "hero"}, {"name": "Two", "role": "heroine"}]}))["book"]
assert len(nb["characters"]) == 2 and nb["cover"] == up["photo"]["key"]
one = nb["characters"][0]
as_user(ana)
ok(call("save_casting", one["key"], "", "grid", "midnight", [{"name": "Some Star"}]))
as_user(admin)
nb2 = ok(call("admin_save_book", nb["key"], {"title": "Admin Book 2", "author": "A. Writer", "status": "live", "cover": nb["cover"],
                                             "characters": [{"key": nb["characters"][1]["key"], "name": "Two renamed", "role": "heroine"},
                                                            {"name": "Three"}]}))["book"]
assert [c["name"] for c in nb2["characters"]] == ["Two renamed", "Three"]
assert not T.characters.search(name="One") and not T.picks.search(star_name="Some Star"), "a removed character takes its collages along"
bad(call("admin_save_book", "missing", {"title": "X Y", "author": "Z Z"}))
ok(call("admin_delete_book", nb["key"]))
assert T.books.get(key=nb["key"]) is None and not T.characters.search(name="Three")
# reports
reps = call("admin_reports")
assert reps["open"] >= 2
rc = [r for r in reps["reports"] if r["target"]["kind"] == "casting" and r["target"]["cast"]["key"] == sv["key"]][0]
bad(call("admin_resolve", rc["id"], "explode"))
ok(call("admin_resolve", rc["id"], "hide"))
assert T.castings.get(key=sv["key"])["hidden"] is True
as_user(bob)
bad(call("get_cast", sv["key"]), "hidden collages are gone for others")
assert all(c["key"] != sv["key"] for c in ok(call("get_character", isolde["key"]))["castings"])
as_user(ana)
assert ok(call("get_cast", sv["key"]))["cast"]["hidden"], "the owner still sees it"
as_user(admin)
ok(call("admin_unhide", "casting", sv["key"]))
assert T.castings.get(key=sv["key"])["hidden"] is False
rm = [r for r in call("admin_reports")["reports"] if r["target"]["kind"] == "comment" and r["target"].get("body") == "Gorgeous pick!"][0]
ok(call("admin_resolve", rm["id"], "delete"))
assert not T.comments.search(body="Gorgeous pick!")
assert call("admin_reports", "all")["reports"]

# comments: the admin can delete any
as_user(bob)
cm2 = ok(call("add_comment", sv["key"], "Another one"))["comment"]
as_user(admin)
ok(call("delete_comment", cm2["id"]))
ok(call("delete_comment", "missing"))
assert not T.comments.search(body="Another one")

# ---------------------------------------------------------------------------------- demo removal keeps real data
ok(call("demo_remove"))
assert DD.state() == "removed" and not T.users.search(is_demo=True) and not T.books.search(is_demo=True)
assert T.castings.get(key=sv["key"]) is None, "members' collages of demo characters go with them"
assert [b["title"] for b in call("get_shelf")["books"]] == ["The Bob Book"], "real books stay"
assert T.photos.get(key=bob_photo) is not None, "members' photos stay"
as_user(None)
call("get_shelf")
assert DD.state() == "removed", "removed demo data doesn't come back by itself"
as_user(admin)
ok(call("demo_load"))
ok(call("demo_load"))
assert len(call("get_shelf")["books"]) == len(DD.BOOKS) + 1, "reloading replaces the demo instead of doubling it"
lead = T.characters.get(name="Lead Lady")
as_user(ana)
k = ok(call("save_casting", lead["key"], "", "hero", "rose", [{"name": "A Star"}]))["key"]
ok(call("delete_casting", k))
assert T.castings.get(key=k) is None

# ---------------------------------------------------------------------------------- Privacy & Terms
if "legal_server" in M:
    as_user(ana)
    st = call("legal_state")
    assert st["signedIn"] and st["accepted_version"] is None
    ok(call("legal_accept", st["version"], "signup"))
    assert ana["legal_source"] == "signup" and call("legal_state")["accepted_version"] == st["version"]

# ---------------------------------------------------------------------------------- every callable is covered by a permission check
# A callable that changes data without require_user / a C.require_* check is a security hole. List the public ones here.
PUBLIC = {"get_me", "submit_feedback", "legal_state", "legal_accept", "get_shelf", "get_book", "get_character",
          "list_stars", "get_star", "get_fan", "get_cast"}
for name, (f, need) in sorted(anvil.server.CALLABLES.items()):
    if name in PUBLIC:
        continue
    assert need, "%s is callable by anyone: add require_user=True (or list it in PUBLIC in test_server.py)" % name

print("ALL OK (%d server functions)" % len(anvil.server.CALLABLES))
