"""Drawn pictures for the demo: romantasy book covers (600x900) and painted-style portraits of fictional
stars (400x500, the same 4:5 shape as members' photos). Only demo content is SVG; members' uploads are
always JPEG / PNG / WebP (Photos._image).
"""
import math
import random

GOLD = "#f3c98b"

# ----------------------------------------------------------------------------------------------- covers
MOTIFS = {
    "crown": (
        '<circle r="150" fill="{glow}" opacity=".35"/>'
        '<path d="M-120 50 -135 -60 -62 -5 0 -105 62 -5 135 -60 120 50z" fill="{gold}"/>'
        '<rect x="-124" y="50" width="248" height="34" rx="6" fill="{gold}"/>'
        '<circle cx="0" cy="-105" r="13" fill="{jewel}"/><circle cx="-135" cy="-60" r="10" fill="{jewel}"/>'
        '<circle cx="135" cy="-60" r="10" fill="{jewel}"/><circle cx="0" cy="67" r="9" fill="{jewel}"/>'
        '<circle cx="-62" cy="67" r="7" fill="{jewel}"/><circle cx="62" cy="67" r="7" fill="{jewel}"/>'
        '<path d="M-60 100c10 30 0 55-15 80M0 100c8 40 0 70-6 95M60 100c-6 30 4 55 18 78" stroke="{gold}" stroke-width="5" '
        'fill="none" stroke-linecap="round" opacity=".7"/>'),
    "wings": (
        '<circle r="160" fill="{glow}" opacity=".3"/>'
        '<g id="w"><path d="M-14 0C-60-95-170-130-245-95c42 18 60 38 70 60-34-4-58 8-72 30 40-4 62 2 84 14-26 14-40 36-42 62 '
        '40-26 90-40 191-41z" fill="{gold}"/>'
        '<path d="M-40-20c-50-30-110-40-160-30M-50 0c-45-8-90-2-130 18M-48 20c-40 4-80 18-104 40" stroke="{bg}" stroke-width="4" fill="none" opacity=".5"/></g>'
        '<use href="#w" transform="scale(-1 1)"/>'
        '<ellipse rx="28" ry="44" fill="{jewel}"/><ellipse rx="7" ry="36" fill="#1a0610"/>'),
    "rose": (
        '<circle r="150" fill="{glow}" opacity=".3"/>'
        '<path d="M0 60C-8 120 8 170 0 230" stroke="{gold}" stroke-width="8" fill="none"/>'
        '<path d="M2 120l-24-10M-2 165l26-12M1 200l-20-6" stroke="{gold}" stroke-width="5" stroke-linecap="round"/>'
        '<path d="M0 140c-50-30-90-10-100 20 40 10 70 5 100-20zM0 175c45-25 85-10 95 18-38 8-65 2-95-18z" fill="{gold}" opacity=".85"/>'
        '{petals}'),
    "moon": (
        '<circle r="165" fill="{glow}" opacity=".35"/>'
        '<path d="M50-130A140 140 0 1 0 50 130 112 112 0 1 1 50-130z" fill="{gold}"/>'
        '<path d="M-30 150c20-30 60-40 90-30-10-40 10-70 40-80" stroke="{gold}" stroke-width="3" fill="none" opacity=".6"/>'
        '<g fill="{gold}"><path d="M110-60l6 16 16 6-16 6-6 16-6-16-16-6 16-6z"/><path d="M140 40l4 10 10 4-10 4-4 10-4-10-10-4 10-4z"/>'
        '<path d="M-150-110l4 10 10 4-10 4-4 10-4-10-10-4 10-4z"/></g>'),
    "key": (
        '<circle r="150" fill="{glow}" opacity=".3"/>'
        '<g fill="{gold}"><circle cy="-110" r="62"/><rect x="-11" y="-55" width="22" height="250" rx="6"/>'
        '<rect x="11" y="130" width="46" height="18" rx="4"/><rect x="11" y="166" width="34" height="18" rx="4"/></g>'
        '<circle cy="-110" r="34" fill="{bg}"/><path d="M0-138v56M-28-110h56M-20-130l40 40M20-130l-40 40" stroke="{gold}" stroke-width="5"/>'
        '<g stroke="{gold}" stroke-width="3" opacity=".7" stroke-linecap="round">'
        '<path d="M-150-40v40M-170-20h40M-164-34l28 28M-136-34l-28 28"/><path d="M150 60v34M133 77h34M138 65l24 24M162 65l-24 24"/></g>'),
    "dagger": (
        '<circle r="150" fill="{glow}" opacity=".3"/>'
        '<path d="M0 205-24-25H24z" fill="{gold}"/><path d="M0 205V-25" stroke="{bg}" stroke-width="3" opacity=".5"/>'
        '<rect x="-80" y="-42" width="160" height="22" rx="11" fill="{gold}"/>'
        '<rect x="-13" y="-140" width="26" height="100" rx="8" fill="{gold}"/><circle cy="-152" r="20" fill="{jewel}"/>'
        '<circle cy="-31" r="8" fill="{jewel}"/>'
        '<path d="M0 205c-5 12-5 22 0 30 5-8 5-18 0-30z" fill="{jewel}"/>'
        '<path d="M-120-80c40 20 60 60 70 110M120-80c-40 20-60 60-70 110" stroke="{gold}" stroke-width="3" fill="none" opacity=".45"/>'),
    "star": (
        '<circle r="165" fill="{glow}" opacity=".35"/>'
        '<ellipse rx="190" ry="60" fill="none" stroke="{gold}" stroke-width="3" transform="rotate(-18)" opacity=".7"/>'
        '<ellipse rx="160" ry="44" fill="none" stroke="{gold}" stroke-width="2" transform="rotate(24)" opacity=".5"/>'
        '<path d="M0-140 22-22 140 0 22 22 0 140-22 22-140 0-22-22z" fill="{gold}"/>'
        '<path d="M0-80 12-12 80 0 12 12 0 80-12 12-80 0-12-12z" fill="{jewel}" transform="rotate(45)"/>'
        '<circle r="16" fill="#fff8ec"/>'),
    "tide": (
        '<circle r="160" fill="{glow}" opacity=".35"/>'
        '<path d="M0 150C-110 80-150 20-150-40c0-50 38-85 82-85 34 0 58 18 68 42 10-24 34-42 68-42 44 0 82 35 82 85 0 60-40 120-150 190z" '
        'fill="none" stroke="{gold}" stroke-width="10"/>'
        '<path d="M-120-10c30-25 55 25 85 0s55 25 85 0 55 25 85 0M-100 40c30-25 55 25 85 0s55 25 85 0 45 20 55 8M-60 90c25-20 45 20 70 0s45 20 60 2" '
        'stroke="{gold}" stroke-width="7" fill="none" stroke-linecap="round"/>'
        '<circle cy="-60" r="10" fill="{jewel}"/>'),
}


def _petals(rnd, jewel, gold):
    out = []
    for i in range(9):
        rx, ry, rot = 92 - i * 9, 52 - i * 4.5, i * 41
        fill = jewel if i % 2 == 0 else "#ffffff"
        op = 0.95 if i % 2 == 0 else 0.18
        out.append('<ellipse rx="%d" ry="%d" transform="rotate(%d)" fill="%s" opacity="%.2f"/>' % (rx, ry, rot, fill, op))
    out.append('<circle r="12" fill="%s"/>' % gold)
    return "".join(out)


def cover_svg(title_lines, author, series, motif, palette, seed=1):
    """A gilded romantasy cover. palette = (top, bottom, glow, jewel)."""
    rnd = random.Random(seed)
    top, bottom, glow, jewel = palette
    specks = "".join('<circle cx="%d" cy="%d" r="%.1f" fill="#fff" opacity="%.2f"/>'
                     % (rnd.randint(40, 560), rnd.randint(40, 620), rnd.uniform(0.6, 2.2), rnd.uniform(0.2, 0.7)) for _ in range(46))
    art = MOTIFS[motif].format(gold=GOLD, glow=glow, jewel=jewel, bg=bottom,
                               petals=_petals(rnd, jewel, GOLD) if motif == "rose" else "")
    size = 64 if max(len(l) for l in title_lines) <= 11 else 54 if max(len(l) for l in title_lines) <= 14 else 46
    y0 = 650 - (len(title_lines) - 1) * size * 0.5
    title = "".join('<text x="300" y="%d" text-anchor="middle" font-family="Georgia, \'Times New Roman\', serif" font-style="italic" '
                    'font-size="%d" fill="#fff6ea" letter-spacing="1">%s</text>' % (y0 + i * size * 1.05, size, _x(l))
                    for i, l in enumerate(title_lines))
    corners = "".join('<path d="M%d %dl10 10-10 10-10-10z" fill="%s"/>' % (x, y, GOLD) for x, y in ((40, 30), (560, 30), (40, 850), (560, 850)))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 900" width="600" height="900">'
            '<defs><linearGradient id="bg" x1="0" y1="0" x2=".3" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
            '<radialGradient id="gl" cx=".5" cy=".42" r=".55"><stop offset="0" stop-color="%s" stop-opacity=".55"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".45"/></linearGradient></defs>'
            '<rect width="600" height="900" fill="url(#bg)"/><rect width="600" height="900" fill="url(#gl)"/>%s'
            '<g transform="translate(300 360)">%s</g><rect width="600" height="900" fill="url(#fade)"/>'
            '<rect x="26" y="26" width="548" height="848" rx="4" fill="none" stroke="%s" stroke-width="2" opacity=".75"/>'
            '<rect x="38" y="38" width="524" height="824" rx="2" fill="none" stroke="%s" stroke-width="1" opacity=".4"/>%s'
            '<text x="300" y="92" text-anchor="middle" font-family="Georgia, serif" font-size="17" letter-spacing="5" fill="%s">%s</text>'
            '%s<text x="300" y="815" text-anchor="middle" font-family="Georgia, serif" font-size="22" letter-spacing="7" fill="%s">%s</text>'
            '</svg>') % (top, bottom, glow, glow, specks, art, GOLD, GOLD, corners, GOLD, _x(series.upper()), title, GOLD, _x(author.upper()))


def _x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------------------------------------- portraits
SKINS = ["#f7d7c4", "#efc3a4", "#dca47f", "#bf8158", "#935c3b", "#64402a"]
HAIRS = ["#2a1912", "#4a2c1d", "#7b4a2a", "#c38b4b", "#e8c67e", "#9b2f2a", "#17142a", "#e2dcd6"]
BGS = [("#4c1d95", "#be185d"), ("#831843", "#e11d48"), ("#312e81", "#a21caf"), ("#7f1d1d", "#db2777"),
       ("#581c87", "#f472b6"), ("#1e1b4b", "#9d174d"), ("#6b21a8", "#fb7185"), ("#3b0a2a", "#c026d3")]
CLOTHES = ["#1f0a1e", "#5b1235", "#3b0764", "#7f1d1d", "#f3e3ea", "#111827", "#9d174d", "#e8d5b5"]


def _shade(hex_color, k):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    f = (lambda v: max(0, min(255, int(v * k))))
    return "#%02x%02x%02x" % (f(r), f(g), f(b))


HAIR_BACK = {
    "long": '<path d="M108 230C96 120 150 112 200 112s108 12 94 118l14 220c-50 22-166 22-216 0z" fill="{h}"/>',
    "waves": '<path d="M106 230C94 118 150 110 200 110s110 12 96 120c10 40-8 60 6 90s-6 60 6 100c-60 26-160 26-218 0 12-40-8-70 6-100s-4-50 4-90z" fill="{h}"/>',
    "bob": '<path d="M104 230C94 120 150 112 200 112s110 10 96 118l4 90c-30 22-170 22-200 0z" fill="{h}"/>',
    "braid": '<path d="M110 230C98 120 150 112 200 112s106 12 92 118l-6 60H116z" fill="{h}"/>'
             '<g fill="{h}"><ellipse cx="282" cy="330" rx="22" ry="28"/><ellipse cx="288" cy="380" rx="20" ry="26"/>'
             '<ellipse cx="292" cy="426" rx="18" ry="24"/><ellipse cx="294" cy="468" rx="15" ry="20"/></g>',
    "curly": '{curls}',
    "bun": '<circle cx="200" cy="112" r="44" fill="{h}"/>',
    "short": "", "slick": "", "tousled": "",
}
HAIR_FRONT = {
    "long": '<path d="M120 214c8-74 58-92 86-90 48 2 80 34 78 92-20-44-60-56-92-50-30 6-54 22-72 48z" fill="{h}"/>',
    "waves": '<path d="M118 220c6-80 60-98 90-96 50 4 80 40 76 98-14-30-34-46-60-52 10 20 4 30 4 30-20-24-60-30-110 20z" fill="{h}"/>',
    "bob": '<path d="M116 226c4-76 54-104 92-100 48 4 80 40 76 100-30-40-60-56-94-58-32 0-56 20-74 58z" fill="{h}"/>',
    "braid": '<path d="M120 212c10-70 58-90 88-88 48 4 76 34 74 90-26-40-58-52-90-48s-54 18-72 46z" fill="{h}"/>',
    "curly": '<path d="M122 206c10-70 56-86 86-84 48 4 76 32 72 86-20-34-56-44-86-42s-52 16-72 40z" fill="{h}"/>',
    "bun": '<path d="M122 212c6-70 56-92 86-90 46 2 76 34 72 90-24-40-56-56-88-54-30 2-54 20-70 54z" fill="{h}"/>',
    "short": '<path d="M122 204c-4-72 46-90 82-90 44 0 82 22 76 92-10-34-34-50-76-50-42 0-66 18-82 48z" fill="{h}"/>',
    "slick": '<path d="M122 208c-2-76 52-94 90-92 40 2 74 24 70 94-14-40-44-58-96-56-30 2-50 22-64 54z" fill="{h}"/>'
             '<path d="M170 128c20 4 50 10 74 34" stroke="{hl}" stroke-width="4" fill="none" opacity=".5"/>',
    "tousled": '<path d="M118 214c-10-60 20-100 70-104 20-14 60-6 74 10 30 10 30 50 22 90-8-20-20-34-34-40 4 16 0 24 0 24-14-22-40-34-62-30 6 10 6 18 6 18-26-12-56 0-76 32z" fill="{h}"/>',
}
STYLES_F = ["long", "waves", "bob", "braid", "curly", "bun"]
STYLES_M = ["short", "slick", "tousled", "curly"]


def portrait_svg(seed, femme=True):
    rnd = random.Random(seed * 7919 + (1 if femme else 2))
    skin = SKINS[rnd.randrange(len(SKINS))]
    hair = HAIRS[rnd.randrange(len(HAIRS))]
    bg1, bg2 = BGS[rnd.randrange(len(BGS))]
    cloth = CLOTHES[rnd.randrange(len(CLOTHES))]
    style = rnd.choice(STYLES_F if femme else STYLES_M)
    shade, hl = _shade(skin, 0.86), _shade(hair, 1.6)
    curls = "".join('<circle cx="%d" cy="%d" r="%d" fill="{h}"/>' % (200 + int(110 * math.cos(a / 10.0)),
                                                                        215 + int(-110 * math.sin(a / 10.0)), rnd.randint(26, 36))
                    for a in range(-6, 38, 4))
    back = HAIR_BACK[style].replace("{curls}", curls).replace("{h}", hair)
    front = HAIR_FRONT[style].replace("{h}", hair).replace("{hl}", hl)
    lips = "#b23a5b" if femme else _shade(skin, 0.72)
    lash = "#2a1215"
    eyes = ('<path d="M158 240q14 10 28 0M214 240q14 10 28 0" stroke="%s" stroke-width="4" fill="none" stroke-linecap="round"/>' % lash
            if rnd.random() < 0.5 else
            '<g fill="%s"><ellipse cx="172" cy="238" rx="9" ry="6"/><ellipse cx="228" cy="238" rx="9" ry="6"/></g>'
            '<g fill="#fff" opacity=".8"><circle cx="175" cy="236" r="2"/><circle cx="231" cy="236" r="2"/></g>' % lash)
    brows = ('<path d="M154 220q18-10 36-2M210 218q18-8 36 2" stroke="%s" stroke-width="%d" fill="none" stroke-linecap="round"/>'
             % (_shade(hair, 0.8) if hair != "#e2dcd6" else "#6b5a52", 4 if femme else 6))
    blush = '<g fill="#e05a7a" opacity=".22"><ellipse cx="160" cy="268" rx="18" ry="10"/><ellipse cx="240" cy="268" rx="18" ry="10"/></g>' if femme else ""
    stubble = '' if femme or rnd.random() < 0.5 else '<path d="M140 270c10 50 40 64 60 64s50-14 60-64c-10 30-30 44-60 44s-50-14-60-44z" fill="%s" opacity=".18"/>' % hair
    earrings = '<g fill="#f3c98b"><circle cx="124" cy="270" r="6"/><circle cx="276" cy="270" r="6"/></g>' if femme and rnd.random() < 0.6 else ""
    neckline = ('<path d="M150 400q50 40 100 0" stroke="#f3c98b" stroke-width="3" fill="none" opacity=".8"/>' if femme and rnd.random() < 0.5 else
                '<path d="M170 380l30 50 30-50" fill="%s" opacity=".9"/>' % _shade(cloth, 1.5))
    sparkles = "".join('<path d="M%d %dl3 8 8 3-8 3-3 8-3-8-8-3 8-3z" fill="#fff" opacity=".55"/>' % (rnd.randint(20, 380), rnd.randint(20, 200)) for _ in range(5))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="50 70 300 375" width="400" height="500">'
            '<defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
            '<radialGradient id="l" cx=".5" cy=".42" r=".5"><stop offset="0" stop-color="#ffd9ec" stop-opacity=".55"/><stop offset="1" stop-color="#ffd9ec" stop-opacity="0"/></radialGradient></defs>'
            '<rect width="400" height="500" fill="url(#b)"/><rect width="400" height="500" fill="url(#l)"/>%s'
            '%s<path d="M30 500c16-92 92-128 170-128s154 36 170 128z" fill="%s"/>%s'
            '<rect x="172" y="290" width="56" height="96" rx="24" fill="%s"/>'
            '<ellipse cx="200" cy="232" rx="80" ry="98" fill="%s"/>'
            '<ellipse cx="122" cy="246" rx="12" ry="20" fill="%s"/><ellipse cx="278" cy="246" rx="12" ry="20" fill="%s"/>'
            '%s%s%s%s<path d="M196 250q-6 22 4 26" stroke="%s" stroke-width="3" fill="none" stroke-linecap="round"/>'
            '<path d="M182 296q18 12 36 0q-18 6-36 0z" fill="%s" stroke="%s" stroke-width="5" stroke-linejoin="round"/>%s%s'
            '</svg>') % (bg1, bg2, sparkles, back, cloth, neckline, shade, skin, shade, shade, blush, stubble, brows, eyes, shade,
                         lips, lips, front, earrings)
