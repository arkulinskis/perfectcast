"""Demo content, so the app never looks empty: eight fictional romantasy books with drawn covers, their
characters, eighteen fictional "stars" with drawn portraits, six demo fans and their collages, swoons and
comments, plus one suggested book, one suggested character and one report for the admin to try.

Loaded automatically the first time anyone opens the app (ensure_loaded), removed or reloaded from
Admin -> Demo data. Removing it is remembered: it doesn't come back by itself.
Every name here is made up. Demo users have @example.com emails and can't sign in (no password).
Every demo row has is_demo=True; removing the demo also removes members' collages of demo characters
(those characters are gone).
"""
import datetime as dt
import random

import anvil
from anvil.tables import app_tables

from . import common as C
from . import DemoArt

DEMO_USERS = [
    ("Wren Talbot", "wren.demo@example.com", "Professional fan-caster, amateur dragon. I cast villains first."),
    ("Marisol Kaye", "marisol.demo@example.com", "Enemies-to-lovers or nothing. Book 3 ruined me (affectionately)."),
    ("Bea Hartley", "bea.demo@example.com", "Annotating every page in five colours. Polaroid layout supremacy."),
    ("Juniper Ash", "juniper.demo@example.com", "Here for the found family and the yearning."),
    ("Odile Moreau", "odile.demo@example.com", "Lectrice de romantasy, Montréal. I cast with my heart, not my head."),
    ("Tamsin Ray", "tamsin.demo@example.com", "If he isn't tall and tormented, I don't want him."),
]

# Fictional stars: name, drawn as femme?
STARS = [
    ("Saoirse Vale", True), ("Dmitri Ashcombe", False), ("Imani Rowe", True), ("Theo Castellane", False),
    ("Lena Marchetti", True), ("Rafe Okonkwo", False), ("Hana Mizuki", True), ("Callum Breck", False),
    ("Priya Devaraj", True), ("Jonah Whitlock", False), ("Esme Laurent", True), ("Mateo Ruiz-Vance", False),
    ("Aurelia Stone", True), ("Kit Harrowgate", False), ("Noor Haddad", True), ("Silas Crane", False),
    ("Freya Lindqvist", True), ("Ezra Bellamy", False),
]
F = [i for i, s in enumerate(STARS) if s[1]]
M = [i for i, s in enumerate(STARS) if not s[1]]

# title lines (cover), author, series, number, days from today, spice, motif, palette, tropes, blurb,
# characters: (name, role, blurb, f/m, favourite stars - the first is the fans' usual pick)
BOOKS = [
    (["A Crown of", "Ash & Honey"], "Mirelle Thorne", "The Ember Courts", 1, -20, 3, "crown",
     ("#3b0764", "#9d174d", "#f472b6", "#e11d48"), ["Enemies to lovers", "Fae", "Court intrigue", "Morally grey"],
     "Isolde Varre steals for a living, until she steals from the wrong prince. Now she owes the Ember Court a year of service, "
     "the queen wants her dead, and the prince who caught her keeps finding reasons to stand far too close.",
     [("Isolde Varre", "heroine", "A mortal thief with a debt to the Ember Court and a knife she never puts down.", "f", [0, 2, 8]),
      ("Prince Caelan", "love", "Heir to a burning throne. Charming in public, cruel in private... or so everyone says.", "m", [1, 5, 15]),
      ("Queen Morwenna", "villain", "Caelan's stepmother. Beautiful, ancient, and patient as poison.", "f", [10, 12, 16]),
      ("Fennick", "ally", "Isolde's sharp-tongued best friend, a half-pixie forger with a heart of gold leaf.", "m", [13, 9, 7])]),
    (["The Dragon's", "Second Wife"], "Odessa Quill", "", None, -45, 2, "wings",
     ("#1e1b4b", "#7f1d1d", "#fb7185", "#c026d3"), ["Dragons", "Arranged marriage", "Slow burn", "Who did this to you"],
     "Wren Albrecht marries the dragon lord to save her village. His first wife died in the mountains, the castle whispers, "
     "and his dragon has decided Wren is hers.",
     [("Lady Wren Albrecht", "heroine", "Practical, stubborn, terrified of heights. Married to a dragon rider.", "f", [4, 6, 14]),
      ("Lord Tarrik Vael", "hero", "Scarred dragon lord of the Ashen Peaks. Says nine words a day, means all of them.", "m", [3, 11, 1]),
      ("Seraphine", "villain", "The first wife. Very much not as dead as everyone thinks.", "f", [16, 10, 0]),
      ("Captain Ivo Brand", "ally", "Captain of the keep's guard and Wren's only friend at court.", "m", [7, 17, 9])]),
    (["Thorns for the", "Night Queen"], "Celeste Marlowe", "The Thornbound Saga", 2, -8, 4, "rose",
     ("#4c0519", "#1e1b4b", "#f9a8d4", "#be123c"), ["Vampires", "Forced proximity", "Only one bed", "Morally grey"],
     "The vampire queen needs a hunter to find her brother's killer. The hunter needs her dead. Snowed into the same castle "
     "for a winter, they will have to settle for wanting each other instead.",
     [("Queen Nyx Ardent", "heroine", "Four hundred years old, bored of everything except the one man sworn to kill her.", "f", [12, 2, 10]),
      ("Ronan Hale", "love", "The best vampire hunter alive, and the most stubborn.", "m", [5, 15, 3]),
      ("Lucian Ardent", "villain", "The queen's brother. Charming, missing, and maybe not the victim.", "m", [17, 13, 1]),
      ("Pell", "ally", "A very opinionated raven who reports to the queen.", "m", [9, 7, 11])]),
    (["Moonbound"], "Sable Ashgrove", "Silver Wolves", 1, -70, 3, "moon",
     ("#2e1065", "#581c87", "#c4b5fd", "#e879f9"), ["Shapeshifters", "Fated mates", "Rivals", "Found family"],
     "Kira has spent her life hiding what she is. Then the moon names her the mate of the rival pack's heir, and hiding "
     "stops being an option.",
     [("Kira Solenne", "heroine", "A wolf who has never shifted, with a temper that could crack the moon.", "f", [6, 14, 4]),
      ("Alder Grey", "hero", "Heir of the Silver pack. Raised to hate her family. Doing badly at it.", "m", [11, 3, 7]),
      ("Alpha Matthias", "villain", "Alder's father, who will not lose his son to a Solenne.", "m", [15, 1, 17]),
      ("Juniper", "ally", "Kira's cousin, a healer with a crossbow and no patience.", "f", [8, 0, 16])]),
    (["The Witch Who", "Stole Winter"], "Hollis Penrose", "", None, -3, 1, "key",
     ("#172554", "#701a75", "#a5b4fc", "#f0abfc"), ["Witches", "Slow burn", "Found family", "Gods & curses"],
     "Elowen stole winter to save her village and accidentally doomed the kingdom. Now she has one season, one locked "
     "door and one very patient blacksmith to put it back.",
     [("Elowen Frost", "heroine", "A hedge witch with cold fingers and a warm, guilty heart.", "f", [16, 8, 2]),
      ("Bram Halloway", "love", "The village blacksmith. Big, gentle, and alarmingly good at waiting.", "m", [7, 9, 5]),
      ("The Winter King", "royal", "A god who wants his season back, and the girl who took it.", "m", [1, 17, 13]),
      ("Mags", "ally", "Her grandmother's cat. Older than the kingdom. Unimpressed.", "f", [10, 14, 6])]),
    (["Daggers in the", "Velvet Court"], "Rhiannon Vey", "The Velvet Court", 3, -30, 4, "dagger",
     ("#450a0a", "#701a75", "#fda4af", "#e11d48"), ["Court intrigue", "Enemies to lovers", "Touch her and die", "Chosen one"],
     "The empress has named Ophelia her heir, which makes her the most hunted woman in the Velvet Court. Her new bodyguard "
     "is the assassin who almost killed her last spring.",
     [("Ophelia Darrow", "heroine", "Heir to an empire that wants her dead. Smiles while she plans.", "f", [2, 12, 0]),
      ("Lord Sorin Blackwood", "love", "Assassin turned bodyguard. Will not explain the scar.", "m", [15, 5, 11]),
      ("Empress Valka", "villain", "Ophelia's patron, or her executioner. It changes daily.", "f", [10, 16, 4]),
      ("Thessaly", "ally", "Lady's maid, spymaster, and the most dangerous person in the room.", "f", [14, 6, 8])]),
    (["Academy of", "Starfall"], "Juno Calloway", "Starfall", 1, 12, 2, "star",
     ("#1e1b4b", "#6b21a8", "#c4b5fd", "#f472b6"), ["Dark academia", "Rivals", "Chosen one", "Forced proximity"],
     "Only one student a year survives the Starfall trials. Mira plans to be that student, even if it means sharing a "
     "tower room with the boy who wants the title just as badly.",
     [("Mira Ellison", "heroine", "Scholarship student. Has read every book in the library. Twice.", "f", [6, 4, 8]),
      ("Dorian Ashe", "hero", "Old money, sharp tongue, top of the class until she arrived.", "m", [13, 3, 17]),
      ("Headmistress Corvina", "villain", "She chooses who lives. She enjoys it.", "f", [12, 16, 10]),
      ("Pip Thackeray", "ally", "Mira's roommate. Chaotic, loyal, mostly on fire.", "m", [9, 7, 5])]),
    (["Heart of the", "Tidecaller"], "Marisol Bright", "", None, 26, 3, "tide",
     ("#0c0a3e", "#831843", "#f9a8d4", "#a855f7"), ["Gods & curses", "Fated mates", "Slow burn"],
     "Every hundred years the sea takes a bride. This time the bride takes a knife, and the sea's prince falls in love.",
     [("Nerys", "heroine", "Fisherman's daughter, chosen by the tide, unwilling to drown quietly.", "f", [0, 14, 2]),
      ("Kael of the Deep", "love", "The sea's youngest prince. Has never wanted anything until now.", "m", [3, 11, 15]),
      ("The Drowned God", "villain", "Ancient, hungry, and owed a bride.", "m", [17, 1, 13])]),
]

CAPTIONS = [
    "I have thought about this way too much and I regret nothing.",
    "Hear me out before you scroll.",
    "This is the only correct answer, respectfully.",
    "Cast this way or I riot.",
    "Every time I reread, I see this face.",
    "Producers, my inbox is open.",
    "The vibes are immaculate and I will not be taking questions.",
    "Lead pick is non-negotiable. The rest are negotiable (they are not).",
    "Made this at 2am after the chapter 31 reveal.",
    "Swoon-worthy. Fight me in the comments.",
]
NOTES = [
    "The jawline alone was made for brooding on balconies.", "Villain-era energy, and she knows it.",
    "Knife-in-the-boot eyes.", "Watch any of the period dramas and tell me I'm wrong.", "Can do soft AND terrifying.",
    "Delivers a threat with a smile.", "Already proved they can wear a crown.", "The height difference with the lead!",
    "That laugh is exactly how I hear the dialogue.", "Has played a monster before and made me cry.",
    "Pure chaos, which is the point.", "The yearning is built in.", "", "", "",
]
COMMENTS = [
    "OK but the second pick is PERFECT.", "I didn't know I needed this until now.",
    "Respectfully disagree with the lead, but the collage is gorgeous.", "The polaroid layout!!",
    "Adding this to my vision board.", "I'd watch this movie tomorrow.", "Someone send this to the producers.",
    "You saw into my soul with this one.", "Close, but I see them as younger.", "The note about the eyes is so true.",
]
LAYOUTS = ["hero", "polaroid", "grid", "hero", "strip", "polaroid"]
TONES = ["rose", "violet", "crimson", "midnight"]

# Tables that hold demo rows (each has an is_demo column). Children before parents.
DEMO_TABLES = ["reports", "comments", "hearts", "picks", "castings", "characters", "books", "photos"]


def state():
    return C.get_setting("demo", "never")  # "never" | "loaded" | "removed"


def ensure_loaded():
    """Call from the app's main data callables: loads the demo once, unless an admin removed it."""
    if state() == "never":
        load()


def _svg(owner, svg, label, kind, created):
    data = svg.encode("utf-8")
    media = anvil.BlobMedia("image/svg+xml", data, name="demo.svg")
    return app_tables.photos.add_row(owner=owner, key=C.token(20), image=media, thumb=media, label=label, kind=kind,
                                     size=len(data), created=created, hidden=False, is_demo=True)


def load():
    remove(remember=False)
    rnd = random.Random(20261029)
    now = C.now()
    today = now.date()
    fans = []
    for name, email, bio in DEMO_USERS:
        u = app_tables.users.get(email=email) or app_tables.users.add_row(email=email, enabled=False)
        u.update(display_name=name, bio=bio, is_demo=True, signed_up=now - dt.timedelta(days=rnd.randint(30, 120)))
        fans.append(u)
    star_photos = [_svg(fans[i % len(fans)], DemoArt.portrait_svg(i, femme), name, "portrait", now - dt.timedelta(days=40))
                   for i, (name, femme) in enumerate(STARS)]

    all_castings = []
    for bi, (lines, author, series, no, days, spice, motif, pal, tropes, blurb, chars) in enumerate(BOOKS):
        series_line = (series + " · Book " + ["One", "Two", "Three"][no - 1]) if no else "A standalone novel"
        cover = _svg(fans[0], DemoArt.cover_svg(lines, author, series_line, motif, pal, bi), " ".join(lines), "cover",
                     now - dt.timedelta(days=60))
        b = app_tables.books.add_row(key=C.token(10), title=" ".join(lines), author=author, series=series, series_no=no,
                                     release=today + dt.timedelta(days=days), blurb=blurb, tropes=tropes, spice=spice,
                                     cover=cover, status="live", submitted_by=None,
                                     created=now - dt.timedelta(days=60 - bi), is_demo=True)
        for ci, (cname, role, cblurb, kind, favs) in enumerate(chars):
            ch = app_tables.characters.add_row(key=C.token(10), book=b, name=cname, role=role, blurb=cblurb, position=ci,
                                               status="live", submitted_by=None, created=b["created"], is_demo=True)
            pool = F if kind == "f" else M
            n_cast = rnd.randint(1, 2) if days > 0 else rnd.randint(2, 5)  # unreleased books have fewer collages
            for fan in rnd.sample(fans, n_cast):
                lead = favs[0] if rnd.random() < 0.6 else rnd.choice(favs[1:])
                other_favs = [s for s in favs if s != lead]
                extra = [s for s in rnd.sample(pool, 5) if s not in favs]
                chosen = [lead] + rnd.sample(other_favs, rnd.randint(0, 1)) + extra[:rnd.randint(1, 3)]
                when = now - dt.timedelta(hours=rnd.randint(2, 24 * 30))
                c = app_tables.castings.add_row(key=C.token(12), user=fan, character=ch, book=b, caption=rnd.choice(CAPTIONS),
                                                layout=rnd.choice(LAYOUTS), tone=rnd.choice(TONES), hearts=0, hidden=False,
                                                created=when, updated=when, is_demo=True)
                for pi, si in enumerate(chosen):
                    app_tables.picks.add_row(casting=c, character=ch, user=fan, star_name=STARS[si][0],
                                             star_key=C.star_key(STARS[si][0]), photo=star_photos[si],
                                             note=rnd.choice(NOTES) if pi < 2 else "", position=pi, is_demo=True)
                all_castings.append(c)

    for c in all_castings:
        others = [f for f in fans if f != c["user"]]
        for f in rnd.sample(others, rnd.randint(0, len(others))):
            app_tables.hearts.add_row(user=f, casting=c, created=c["created"] + dt.timedelta(hours=1), is_demo=True)
        c["hearts"] = len(app_tables.hearts.search(casting=c))
        for _ in range(rnd.choice([0, 0, 1, 1, 2, 3])):
            app_tables.comments.add_row(casting=c, user=rnd.choice(others), body=rnd.choice(COMMENTS),
                                        created=c["created"] + dt.timedelta(hours=rnd.randint(1, 40)), hidden=False, is_demo=True)

    # Something for the admin to review: a suggested book, a suggested character and a report.
    pending = app_tables.books.add_row(key=C.token(10), title="Court of Sapphire Smoke", author="Lyra Fenwick", series="",
                                       series_no=None, release=today + dt.timedelta(days=40), spice=3,
                                       blurb="A smoke-mage, a sapphire crown, and a heist inside the fae king's dreams.",
                                       tropes=["Fae", "Enemies to lovers", "Court intrigue"], cover=None, status="pending",
                                       submitted_by=fans[2], created=now - dt.timedelta(hours=5), is_demo=True)
    for i, (n, r) in enumerate([("Liora Ash", "heroine"), ("King Aurelian", "love")]):
        app_tables.characters.add_row(key=C.token(10), book=pending, name=n, role=r, blurb="", position=i, status="live",
                                      submitted_by=fans[2], created=pending["created"], is_demo=True)
    first = app_tables.books.get(title="A Crown of Ash & Honey")
    app_tables.characters.add_row(key=C.token(10), book=first, name="Lady Briar", role="side",
                                  blurb="Morwenna's lady-in-waiting, who sees everything.", position=9, status="pending",
                                  submitted_by=fans[4], created=now - dt.timedelta(hours=9), is_demo=True)
    some = app_tables.comments.search(is_demo=True)
    if len(some):
        x = some[0]
        app_tables.reports.add_row(user=fans[5], casting=x["casting"], comment=x, reason="rude",
                                   note="Feels a bit mean? (demo report)", status="open", created=now - dt.timedelta(hours=2),
                                   is_demo=True)
    C.set_setting("demo", "loaded")
    return counts()


def remove(remember=True):
    from . import Casting  # imported here: Casting -> Shelf -> DemoData would be circular at load time
    for ch in app_tables.characters.search(is_demo=True):
        for c in app_tables.castings.search(character=ch):
            Casting.delete_casting_row(c)  # members' collages of demo characters go with them
    for name in DEMO_TABLES:
        for r in getattr(app_tables, name).search(is_demo=True):
            r.delete()
    for u in app_tables.users.search(is_demo=True):
        u.delete()
    if remember:
        C.set_setting("demo", "removed")
    return counts()


def counts():
    out = {"users": len(app_tables.users.search(is_demo=True))}
    for name in ["books", "characters", "castings", "photos"]:
        out[name] = len(getattr(app_tables, name).search(is_demo=True))
    return out
