"""Page addresses: #name/arg1/arg2 -> a page Form (open_form), with sign-in rules.

Links in templates are plain <a href="#books">; code calls router.go("item", id).

    PAGES[name] = (who may open it, browser-tab title)   who: None = anyone, "guest" = signed out only, "user", "admin"
    NAV = the main menu (header + phone tab bar, signed-in people): (page, label, icon). At most 4.
New page: add it to PAGES, to _form() and (if it belongs in the menu) to NAV.
"""
import anvil
import anvil.js
from anvil.js import window

from . import state

PAGES = {
    "landing": (None, "Welcome"),
    "auth": ("guest", "Sign in"),
    "books": (None, "New romantasy releases"),
    "book": (None, "Book"),
    "character": (None, "Character"),
    "cast": (None, "Collage"),
    "castedit": ("user", "Cast a character"),
    "stars": (None, "Stars"),
    "mine": ("user", "My casts"),
    "photos": ("user", "Your photo drawer"),
    "fan": (None, "Fan"),
    "suggest": ("user", "Suggest a book"),
    "profile": ("user", "Your profile"),
    "admin": ("admin", "Admin"),
}
# The main menu: (page, label, icon). Books and Stars are open to everyone, so visitors see them in the header too;
# the phone tab bar is for members (all four + You).
NAV = [("books", "Books", "book"), ("stars", "Stars", "star"), ("mine", "My casts", "heart"), ("photos", "Photos", "image")]
APP_NAME = "PerfectCast"
_r: dict = {"after": "", "listening": False}


def nav_for(me):
    """The menu entries this person may open."""
    return [n for n in NAV if PAGES[n[0]][0] is None or me]


def _form(name):
    """The page's Form class (imported when first needed, so start-up stays quick)."""
    if name == "landing":
        from .Pages.Landing import Landing
        return Landing
    if name == "auth":
        from .Pages.Auth import Auth
        return Auth
    if name == "books":
        from .Pages.Books import Books
        return Books
    if name == "book":
        from .Pages.Book import Book
        return Book
    if name == "character":
        from .Pages.Character import Character
        return Character
    if name == "cast":
        from .Pages.Cast import Cast
        return Cast
    if name == "castedit":
        from .Pages.CastEdit import CastEdit
        return CastEdit
    if name == "stars":
        from .Pages.Stars import Stars
        return Stars
    if name == "mine":
        from .Pages.Mine import Mine
        return Mine
    if name == "photos":
        from .Pages.Photos import Photos
        return Photos
    if name == "fan":
        from .Pages.Fan import Fan
        return Fan
    if name == "suggest":
        from .Pages.Suggest import Suggest
        return Suggest
    if name == "profile":
        from .Pages.Profile import Profile
        return Profile
    from .Pages.Admin import Admin
    return Admin


def parse(hash_text):
    h = (hash_text or "").lstrip("#").lstrip("!").lstrip("/").split("?")[0]
    parts = [window.decodeURIComponent(p) for p in h.split("/") if p]
    return (parts[0] if parts else ""), parts[1:]


def href(name, *args):
    """'#name/arg1/arg2' with every part URL-encoded (row ids contain brackets and commas)."""
    return "#" + "/".join([name] + [window.encodeURIComponent(str(a)) for a in args if a not in (None, "")])


def home_page():
    return "books" if state.me() else "landing"


def show():
    """Open the page for the current address."""
    name, args = parse(window.location.hash)
    if name not in PAGES:
        name, args = home_page(), []
    who = PAGES[name][0]
    if who == "guest" and state.me():
        name, args = "books", []
    elif who in ("user", "admin") and not state.me():
        _r["after"] = window.location.hash
        name, args = "auth", []
    elif who == "admin" and not state.is_admin():
        state.toast("That page is for admins only.", "error")
        name, args = "books", []
    if name != parse(window.location.hash)[0] and window.location.hash not in ("", "#"):
        replace(name, *args)  # a redirect: keep the address in step with the page
    window.document.title = PAGES[name][1] + " · " + APP_NAME
    window.UI_READY = False
    page = _form(name)(args=args)
    anvil.open_form(page)
    shell = getattr(page, "layout", None)
    if shell is not None and hasattr(shell, "refresh"):
        shell.refresh(name)  # Anvil reuses the layout between pages: tell it who is signed in and which page is open
    title = getattr(page, "title", None)
    if title:
        window.document.title = title + " · " + APP_NAME
    window.scrollTo(0, 0)
    window.UI_READY = True  # tests and screenshots wait for this


def go(name, *args):
    """Go to a page. Same address again = reload the page."""
    target = href(name, *args)
    if window.location.hash == target:
        show()
    else:
        window.location.hash = target


def replace(name, *args):
    """Change the address without opening anything (a page that switches its own view)."""
    window.history.replaceState(None, "", href(name, *args))


def after_sign_in():
    """Where to go once someone signs in: the page they were heading for, or home."""
    target = _r["after"]
    _r["after"] = ""
    if target and target != window.location.hash:
        window.location.hash = target
    else:
        go("books")


def remember_after(target):
    _r["after"] = target


def _on_hash(event):
    show()


def start():
    if not _r["listening"]:
        window.addEventListener("hashchange", anvil.js.report_exceptions(_on_hash))
        _r["listening"] = True
    show()
