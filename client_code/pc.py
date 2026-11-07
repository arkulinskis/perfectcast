"""PerfectCast helpers every page uses, and the Python side of the JavaScript engine (theme/assets/pc.js).

    pc.photo(key, thumb)        URL of a stored picture (the /photo endpoint); "" for none
    pc.days(iso) / pc.when(iso) days until a release date; the release line ("Out in 3 days", css class)
    pc.series_line(book)        "The Ember Courts · Book 2" or "Standalone"
    pc.need_sign_in(why)        the "Join the casting couch" dialog for visitors; returns False so callers can `return`
    pc.share(hash, title)       the phone's share sheet, else copy the link
    pc.hearts(n)                floating hearts (PC.hearts)
    pc.export_image(cast)       the 1080x1350 PNG of a collage (PC.exportImage)
    pc.upload_file(file, kind)  crop dialog + upload_photo; the server's {photo, quota} or None
    pc.js(value)                a Python dict/list as a real JS object (for the engine)
    pc.show(node, flag)         show/hide a dom node (the `hidden` attribute)
"""
import datetime
import json

import anvil
import anvil.server
from anvil.js import window

from . import router, state

LAYOUTS = {"hero": "Leading star", "grid": "Gallery grid", "polaroid": "Polaroid wall", "strip": "Film strip"}
TONES = {"rose": "Rose", "violet": "Violet", "crimson": "Crimson", "midnight": "Midnight"}
ROLES = {"heroine": "Heroine", "hero": "Hero", "love": "Love interest", "villain": "Villain", "royal": "Royalty",
         "ally": "Ally", "side": "Supporting"}


def js(value):
    return window.JSON.parse(json.dumps(value))


def show(node, flag):
    if flag:
        node.removeAttribute("hidden")
    else:
        node.setAttribute("hidden", "")


def link(node, href):
    node.setAttribute("href", href)


def photo(key, thumb=False):
    return window.PC.photo(key, bool(thumb)) if key else ""


def initials(name):
    return state.initials(name)


def days(iso):
    """Whole days from today to an ISO date (negative = already out), or None."""
    if not iso:
        return None
    y, m, d = iso[:10].split("-")
    return (datetime.date(int(y), int(m), int(d)) - datetime.date.today()).days


def fmt_date(iso, style="long"):
    """'14 Mar 2026' (long), '14 Mar' (short), 'Mar 2026' (month)."""
    if not iso:
        return ""
    y, m, d = iso[:10].split("-")
    mon = state.MONTHS[int(m) - 1]
    if style == "short":
        return "%d %s" % (int(d), mon)
    if style == "month":
        return "%s %s" % (mon, y)
    return "%d %s %s" % (int(d), mon, y)


def when(iso):
    """(text, css class) for a release date."""
    n = days(iso)
    if n is None:
        return "Release date to come", ""
    if n > 1:
        return "Out in %d days" % n, "soon"
    if n == 1:
        return "Out tomorrow", "soon"
    if n == 0:
        return "Out today!", "new"
    if n > -31:
        return "New · " + fmt_date(iso, "short"), "new"
    return fmt_date(iso, "month"), ""


def set_when(node, iso):
    text, cls = when(iso)
    node.textContent = text
    node.className = "pc-when" + (" " + cls if cls else "")


def badge_for(iso):
    n = days(iso)
    return "Soon" if n is not None and n > 0 else "New" if n is not None and n > -15 else ""


def series_line(b):
    if not b.get("series"):
        return "Standalone"
    return b["series"] + (" · Book %s" % b["series_no"] if b.get("series_no") else "")


def kb(n):
    if not n:
        return "0 KB"
    return ("%.1f MB" % (n / 1048576.0)) if n >= 1048576 else "%d KB" % max(1, int(round(n / 1024.0)))


def need_sign_in(why=None):
    """Visitors: the "Join the casting couch" dialog (remembers where they were). Members: True."""
    if state.me():
        return True
    from .Dialogs.SignIn import SignIn
    router.remember_after(window.location.hash)
    alert(SignIn(why=why or ""), buttons=[], role="app-dialog")
    return False


def alert(content, **kw):
    return anvil.alert(content, **kw)


def share(hash_part, title):
    url = str(window.location.href).split("#")[0] + hash_part
    nav = window.navigator
    if getattr(nav, "share", None):
        try:
            nav.share(js({"title": title, "text": title + " on PerfectCast", "url": url}))
        except Exception:
            pass  # the person closed the share sheet
        return
    try:
        nav.clipboard.writeText(url)
        state.toast("Link copied. Paste it anywhere!", "ok")
    except Exception:
        from .Dialogs.Share import Share
        alert(Share(url=url), buttons=[], role="app-dialog")


def hearts(n=26):
    window.PC.hearts(n)


def export_image(cast):
    window.PC.exportImage(js(cast))  # resolves once the PNG has been handed to the browser


def upload_file(file, kind="portrait", label=""):
    """Frame + shrink one picture (dialog), then store it. Returns {photo, quota} or None."""
    problem = window.PC.fileProblem(file)
    if problem:
        state.toast(problem, "error")
        return None
    from .Dialogs.Crop import Crop
    c = alert(Crop(file=file, kind=kind, label=label), buttons=[], role="app-dialog")
    if not c:
        return None
    r = state.call("upload_photo", c["full"], c["thumb"], c.get("label") or label or "", kind)
    if r:
        state.toast("Saved (%s)" % kb(c["bytes"]), "ok")
    return r


def loose(x):
    """Hand a value through untyped (the validator's stubs miss a few DOM methods, e.g. FileList.item)."""
    return x
