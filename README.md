# PerfectCast

A fan-casting site for romantasy readers. Every new romantasy book is listed with its cover, blurb, tropes and spice level, and every character in it; fans make photo collages of the celebrities they'd cast in a film, swoon over (heart) and comment on each other's collages, and every character shows "the fans' pick". A calmer, prettier home for fan-casts than Reddit threads, with real photo management. Built on [Anvil](https://anvil.works).

- **App repo:** github.com/arkulinskis/perfectcast (branch `master`). Anvil pulls `master`.
- **Live:** https://perfectcast.anvil.app

## What it does

**For everyone (no account needed):**
- **Landing** (`#landing`): the promise, a live "Fresh on the shelf" row, how it works, features, FAQ.
- **Books** (`#books`, the home page): the newest release featured, "Coming soon" countdowns, the most-swooned collages, and every
  book with search, spice filter (sweet / warm / scorching), trope chips and sort (newest / coming soon / most cast).
- **A book** (`#book/<key>`): cover, blurb, tropes, spice, release; **the fans' dream cast** (each character with the most-picked
  star's photo, share of the vote and runners-up); latest collages; share; "a character is missing".
- **A character** (`#character/<key>`): the fans' pick podium (top 3) and every vote as bars, all collages (most swooned / newest),
  quick hops to the book's other characters.
- **A collage** (`#cast/<key>`): big collage, each star's "why", swoon, **save as image** (1080×1350 PNG for socials), share,
  comments, report.
- **Stars** (`#stars`, `#stars/<slug>`): leaderboard of the most-cast celebrities (podium + list + search); a star's page with every
  role they were cast in (rank, % of collages) and fans' photos of them.
- **Fan pages** (`#fan/<id>`): a member's name, bio, numbers, favourite stars and collages (never their email).
- Sign-up with email and password, a feedback form, and the Privacy & Terms page (footer link, `#legal`).

**For members:**
- **Collage editor** (`#castedit/<characterKey>`): up to 6 stars, each with a name (autocomplete), a photo and a "why"; make lead,
  move, remove; fans' favourites as quick picks; 4 layouts (leading star, gallery grid, polaroid wall, film strip) × 4 tones (rose,
  violet, crimson, midnight); caption; live preview. One collage per fan per character (saving again updates it).
- **Photos, kept small:** every picture is framed in a cropper (drag, zoom slider, pinch, wheel) and shrunk on the device before upload:
  portraits 600×750 (≤ 210 KB), covers 600×900 (≤ 300 KB), thumbnails 320×400 (≤ 44 KB), JPEG re-encoded (drops EXIF/location).
  The server rejects anything else (JPEG/PNG/WebP only, byte caps) and each member has **60 photos** max (admins: no limit).
- **Photo drawer** (`#photos`): quota meter, multi-upload, filters (all / in use / unused / covers), search, rename, "used in" links,
  delete one, or select many ("select all unused") and delete. Deleting a photo in use leaves the star's name with a monogram.
- **My casts** (`#mine`): numbers, "finish the cast" (characters still waiting in books you started), your collages, collages you
  swooned over, bio + link to your public page.
- **Swoons, comments, reports:** heart others' collages (not your own), comment (the collage owner can delete comments on it), report a
  collage or comment (reason + note).
- **Suggest a book** (`#suggest`): title, author, series, release date, spice, tropes, blurb, cover (cropped 2:3) and characters;
  waits for an admin. Suggest a missing character from a book page.

**For admins** (`#admin`; arkulinskis@gmail.com becomes an admin on first sign-in):
- **Books:** add / edit (all fields, cover, the character list, status live / pending / turned down) / delete. Removing a character
  deletes its collages (the editor warns first).
- **Review:** suggested books (approve, edit first, turn down) and suggested characters (approve, turn down).
- **Reports:** open / all; nothing wrong, hide (the owner still sees it), delete; unhide a hidden collage.
- **Overview:** members, live books, collages, photos + storage, review queue, open reports.
- **Feedback inbox:** New / Read / Done, private notes.
- **Users:** search, make admin, disable an account.
- **Demo data:** 8 fictional books with drawn covers, 18 fictional stars with drawn portraits, 6 demo fans, ~90 collages, swoons,
  comments, a suggested book and character and a report; remove or reload it.

## Setting it up in Anvil (once)

1. In the Anvil editor: **Create app → Clone from GitHub**, and paste `https://github.com/arkulinskis/perfectcast`.
2. **Users** service: email + password, sign-up allowed (already set in `anvil.yaml`; check it).
3. Open the app in the editor. If it shows a **Schema Mismatch** alert, choose **"The schema of the source code is correct"** so Anvil creates the tables.
4. **Run** it and sign up with **arkulinskis@gmail.com** straight away (that account becomes the admin).
5. **Publish** (Publish → public URL, or your own domain).

<!-- libraries:start -->
## Libraries and outside services

What this project uses besides its own code. Generated by `APP_MAKER/tools/libraries.py`; to change it, edit `APP_MAKER/libraries/catalog.py` and re-run the script.

| Name | How it gets in | Used here for |
|---|---|---|
| [Google Fonts](https://fonts.google.com) | Loaded from a CDN | Cormorant Garamond, Manrope |

**Built into the browser:** Canvas 2D, Web Share, localStorage, Clipboard, File downloads (Blob).

**Anvil platform:** Anvil, Anvil Data Tables, Anvil JS bridge (anvil.js), Anvil Users.

**Build and test tools (not shipped):** Node.js, Headless Chrome (DevTools Protocol), PyYAML.

<!-- libraries:end -->

## Working on it

See `.claude/skills/perfectcast/SKILL.md`. In short:

```
python -I tools/check.py --ui                    # syntax, server tests, headless UI tests → ALL CHECKS PASSED
python -I tools/preview/devserver.py 8765        # the app on in-memory data: http://localhost:8765/  (?as=ana#books, ?as=admin#admin)
python tools/deploy.py                           # dry run (needs PyYAML, so no -I)
python tools/deploy.py --push "Message"          # deploy: commit + push to GitHub, Anvil pulls it
```

## Project layout

```
web/            the interface: core.js/core.css (shared engine + design tokens), app.js (header, footer), pages/*.html
                (pages/_pc.html = window.PC: collages, cropper, photo picker, export, hearts)
client_code/    Main.py (the only Anvil form: bridge to the server, sign-in), legal.py
server_code/    common.py, Accounts.py, Feedback.py, Admin.py, DemoData.py (+ DemoArt.py), legal_server.py,
                Shelf.py (reading), Casting.py (collages, swoons, comments, reports), Photos.py, Books.py (suggestions + admin)
assets/         icon.svg + generated PNG icons, pictures (served at _/theme/<name>)
tools/          sync_to_anvil.py (settings + table schema), deploy.py, check.py, preview/ (dev server, UI tests, screenshots), testing/
```
