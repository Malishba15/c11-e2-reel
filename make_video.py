"""C11 ya E-2? — 9:16 motion-graphics reel (navy + gold).
Usage: python3 make_video.py OUT.mp4 [--no-captions]
"""
import math, random, subprocess, sys, os, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
W, H, FPS, DUR = 1080, 1920, 30, 60.0
OUT = sys.argv[1]
CAPTIONS = "--no-captions" not in sys.argv

NAVY0 = (6, 12, 28); NAVY1 = (12, 24, 52); NAVY2 = (22, 40, 80)
GOLD = (214, 172, 72); GOLD_L = (245, 214, 140); GOLD_D = (130, 95, 35)
WHITE = (255, 255, 255); RED = (214, 40, 46); GREEN = (40, 190, 110)
PK_GREEN = (0, 82, 50)

def font(name, size, var="Bold"):
    f = ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), size)
    f.set_variation_by_name(var)
    return f

ease = lambda x: 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, x)))
clamp = lambda x, a=0.0, b=1.0: max(a, min(b, x))

def vgrad(w, h, stops):
    """stops: list of (pos, rgb)."""
    ys = np.linspace(0, 1, h)
    arr = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        col = np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops])
        arr[:, :, c] = col[:, None]
    return Image.fromarray(arr.astype(np.uint8), "RGB")

def glow(size, center, radius, color, strength=1.0, blur=None):
    """Additive RGB glow layer."""
    lay = Image.new("RGB", size, 0)
    d = ImageDraw.Draw(lay)
    cx, cy = center
    rx, ry = radius if isinstance(radius, tuple) else (radius, radius)
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=tuple(int(c * strength) for c in color))
    return lay.filter(ImageFilter.GaussianBlur(blur or max(rx, ry) * 0.6))

def add(base, layer, k=1.0):
    if k <= 0: return base
    if k < 1: layer = layer.point(lambda v: int(v * k))
    return ImageChops.add(base, layer)

def scale_alpha(im, k):
    if k >= 1: return im
    im = im.copy()
    a = im.getchannel("A").point(lambda v: int(v * k))
    im.putalpha(a)
    return im

def paste(base, layer, xy, k=1.0):
    if k <= 0.01: return
    layer = scale_alpha(layer, k)
    base.paste(layer, (int(xy[0]), int(xy[1])), layer)

def zoom(img, s, cx, cy):
    if abs(s - 1) < 1e-3: return img
    w, h = W / s, H / s
    x0 = clamp(cx - w / 2, 0, W - w); y0 = clamp(cy - h / 2, 0, H - h)
    return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))

# ---------------------------------------------------------------- icons
def maple_leaf(d, cx, cy, s, fill):
    pts = [(0, -1), (.12, -.72), (.3, -.8), (.24, -.42), (.55, -.6), (.48, -.42), (.78, -.3),
           (.62, -.2), (.72, .02), (.44, -.02), (.5, .18), (.12, .1), (.06, .1), (.06, .5),
           (-.06, .5), (-.06, .1), (-.12, .1), (-.5, .18), (-.44, -.02), (-.72, .02), (-.62, -.2),
           (-.78, -.3), (-.48, -.42), (-.55, -.6), (-.24, -.42), (-.3, -.8), (-.12, -.72)]
    d.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=fill)

def flag_ca(w):
    h = w // 2
    im = Image.new("RGBA", (w, h), WHITE + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w // 4, h), fill=RED); d.rectangle((w - w // 4, 0, w, h), fill=RED)
    maple_leaf(d, w / 2, h / 2 + h * .04, h * .42, RED)
    return im

def flag_us(w):
    h = int(w * 0.53)
    im = Image.new("RGBA", (w, h), WHITE + (255,))
    d = ImageDraw.Draw(im)
    sh = h / 13
    for i in range(0, 13, 2):
        d.rectangle((0, i * sh, w, (i + 1) * sh), fill=(178, 34, 52))
    cw, ch = w * .4, sh * 7
    d.rectangle((0, 0, cw, ch), fill=(60, 59, 110))
    for r in range(5):
        for c in range(6):
            x = cw * (c + .5 + (r % 2) * .25) / 6.3; y = ch * (r + .6) / 5.4
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=WHITE)
    return im

def round_flag(im, r=8):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r, fill=255)
    im.putalpha(m)
    return im

def icon(kind, s):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if kind == "check":
        d.ellipse((0, 0, s - 1, s - 1), fill=GREEN)
        d.line([(s * .27, s * .52), (s * .44, s * .68), (s * .74, s * .34)], fill=WHITE, width=max(3, s // 9), joint="curve")
    elif kind == "x":
        d.ellipse((0, 0, s - 1, s - 1), fill=RED)
        w = max(3, s // 9)
        d.line([(s * .32, s * .32), (s * .68, s * .68)], fill=WHITE, width=w)
        d.line([(s * .68, s * .32), (s * .32, s * .68)], fill=WHITE, width=w)
    elif kind == "warn":
        d.polygon([(s / 2, s * .05), (s * .97, s * .92), (s * .03, s * .92)], fill=(245, 180, 40))
        d.rectangle((s * .46, s * .35, s * .54, s * .65), fill=NAVY0)
        d.ellipse((s * .45, s * .72, s * .55, s * .82), fill=NAVY0)
    elif kind == "dot":
        d.ellipse((s * .3, s * .3, s * .7, s * .7), fill=GOLD)
    elif kind in ("us", "ca"):
        f = round_flag(flag_us(s) if kind == "us" else flag_ca(s), 6)
        im.paste(f, (0, (s - f.size[1]) // 2), f)
    elif kind == "phone":
        d.rounded_rectangle((s * .28, s * .08, s * .72, s * .92), s * .1, outline=GOLD, width=max(3, s // 12))
        d.ellipse((s * .45, s * .74, s * .55, s * .84), fill=GOLD)
    elif kind == "globe":
        w = max(3, s // 14)
        d.ellipse((s * .08, s * .08, s * .92, s * .92), outline=GOLD, width=w)
        d.ellipse((s * .3, s * .08, s * .7, s * .92), outline=GOLD, width=w)
        d.line([(s * .08, s / 2), (s * .92, s / 2)], fill=GOLD, width=w)
    return im

# ---------------------------------------------------------------- text
def rich_line(parts, size, fname="Montserrat", var="Bold", shadow=True, track=0):
    """parts: list of (text, color) or ('@icon', kind). Returns RGBA image."""
    f = font(fname, size, var)
    asc, desc = f.getmetrics()
    lh = asc + desc
    widths = []
    for t, c in parts:
        if t == "@icon": widths.append(int(size * 1.05) + int(size * .3))
        else: widths.append(int(f.getlength(t)) + track * len(t))
    pad = 30
    im = Image.new("RGBA", (sum(widths) + pad * 2, lh + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = pad
    for (t, c), w in zip(parts, widths):
        if t == "@icon":
            ic = icon(c, int(size * 1.05))
            im.paste(ic, (x, pad + (lh - ic.size[1]) // 2 + int(size * .05)), ic)
        elif track:
            xx = x
            for ch in t:
                d.text((xx, pad), ch, font=f, fill=c)
                xx += f.getlength(ch) + track
        else:
            d.text((x, pad), t, font=f, fill=c)
        x += w
    if shadow:
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: min(255, v * 2)))
        sh = scale_alpha(sh, 0.8)
        out = Image.new("RGBA", im.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 4)); out.alpha_composite(im)
        im = out
    return im

def parse_marked(text, base=WHITE, hi=GOLD_L):
    """'*word*' -> gold."""
    out = []
    for i, seg in enumerate(text.split("*")):
        if seg: out.append((seg, hi if i % 2 else base))
    return out

def wrap_words(parts, f, maxw):
    """Split rich parts into lines (word level)."""
    words = []
    for t, c in parts:
        for i, w in enumerate(t.split(" ")):
            if w: words.append((w, c))
    lines, cur, curw = [], [], 0
    sp = f.getlength(" ")
    for w, c in words:
        ww = f.getlength(w)
        if cur and curw + sp + ww > maxw:
            lines.append(cur); cur, curw = [], 0
        cur.append((w, c)); curw += (sp if len(cur) > 1 else 0) + ww
    if cur: lines.append(cur)
    res = []
    for ln in lines:
        p = []
        for i, (w, c) in enumerate(ln):
            p.append(((" " if i else "") + w, c))
        res.append(p)
    return res

def caption_img(text):
    size = 48
    f = font("Montserrat", size, "ExtraBold")
    lines = wrap_words(parse_marked(text), f, 900)
    imgs = [rich_line(l, size, "Montserrat", "ExtraBold", shadow=False) for l in lines]
    lh = int(size * 1.32)
    bw = max(i.size[0] for i in imgs) - 60 + 64
    bh = lh * len(imgs) + 40
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, bw - 1, bh - 1), 26, fill=(5, 10, 24, 175))
    for i, li in enumerate(imgs):
        im.alpha_composite(li, ((bw - li.size[0]) // 2, 20 + i * lh - 30 + 4))
    return im

# ---------------------------------------------------------------- figures
def man_back(scale=1.0, rim=GOLD):
    """Back view, head+shoulders silhouette in suit, rim-lit. Returns RGBA 700x900*scale."""
    w, h = int(700 * scale), int(900 * scale)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    s = scale
    cx = w / 2
    d.ellipse((cx - 72 * s, 40 * s, cx + 72 * s, 230 * s), fill=255)           # head
    d.rectangle((cx - 48 * s, 180 * s, cx + 48 * s, 290 * s), fill=255)        # neck
    d.rounded_rectangle((cx - 300 * s, 270 * s, cx + 300 * s, h + 200), int(150 * s), fill=255)  # shoulders
    d.polygon([(cx - 300 * s, 400 * s), (cx - 340 * s, h), (cx + 340 * s, h), (cx + 300 * s, 400 * s)], fill=255)
    return rimlit(m, (14, 18, 30), rim)

def man_front(scale=1.0, rim=GOLD, passport=False):
    w, h = int(700 * scale), int(900 * scale)
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    s = scale; cx = w / 2
    d.ellipse((cx - 70 * s, 40 * s, cx + 70 * s, 235 * s), fill=255)
    d.rectangle((cx - 46 * s, 190 * s, cx + 46 * s, 290 * s), fill=255)
    d.rounded_rectangle((cx - 290 * s, 270 * s, cx + 290 * s, h + 200), int(150 * s), fill=255)
    d.polygon([(cx - 290 * s, 400 * s), (cx - 330 * s, h), (cx + 330 * s, h), (cx + 290 * s, 400 * s)], fill=255)
    im = rimlit(m, (16, 20, 34), rim)
    dd = ImageDraw.Draw(im)
    # shirt V + tie hint
    dd.polygon([(cx - 70 * s, 280 * s), (cx, 470 * s), (cx + 70 * s, 280 * s)], fill=(200, 200, 210, 255))
    dd.polygon([(cx - 16 * s, 300 * s), (cx + 16 * s, 300 * s), (cx + 22 * s, 440 * s), (cx, 470 * s), (cx - 22 * s, 440 * s)], fill=GOLD_D + (255,))
    dd.line([(cx - 70 * s, 280 * s), (cx - 10 * s, 600 * s)], fill=(40, 50, 80, 255), width=int(6 * s))
    dd.line([(cx + 70 * s, 280 * s), (cx + 10 * s, 600 * s)], fill=(40, 50, 80, 255), width=int(6 * s))
    if passport:
        pw, ph = 150 * s, 205 * s
        px, py = cx + 60 * s, 400 * s
        dd.rounded_rectangle((px, py, px + pw, py + ph), int(10 * s), fill=PK_GREEN + (255,), outline=GOLD + (255,), width=int(3 * s))
        crescent(dd, px + pw / 2, py + ph * .45, 30 * s, GOLD, PK_GREEN)
        # hand
        dd.rounded_rectangle((px - 20 * s, py + ph * .55, px + 70 * s, py + ph * .55 + 70 * s), int(30 * s), fill=(70, 50, 40, 255))
    return im

def rimlit(mask, body, rim):
    w, h = mask.size
    blur = mask.filter(ImageFilter.GaussianBlur(10))
    edge = ImageChops.subtract(blur.filter(ImageFilter.MaxFilter(9)), ImageChops.offset(mask, 0, 10))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    halo = Image.new("RGBA", (w, h), rim + (0,))
    halo.putalpha(mask.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .55)))
    out.alpha_composite(halo)
    b = Image.new("RGBA", (w, h), body + (255,)); b.putalpha(mask)
    out.alpha_composite(b)
    r = Image.new("RGBA", (w, h), rim + (0,)); r.putalpha(edge.point(lambda v: min(255, v * 3)))
    out.alpha_composite(r)
    return out

def crescent(d, cx, cy, r, col, bg):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    d.ellipse((cx - r * .55, cy - r * 1.0, cx + r * 1.25, cy + r * .8), fill=bg)
    sx, sy, sr = cx + r * .55, cy - r * .35, r * .32
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = sr if i % 2 == 0 else sr * .42
        pts.append((sx + rr * math.cos(a), sy + rr * math.sin(a)))
    d.polygon(pts, fill=col)

# ---------------------------------------------------------------- hallway
DL = (110, 600, 490, 1400); DR = (590, 600, 970, 1400)
DW, DH = DL[2] - DL[0], DL[3] - DL[1]

def door_panel(kind):
    im = vgrad(DW, DH, [(0, (196, 156, 70)), (.5, (150, 112, 44)), (1, (92, 66, 24))]).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, DW - 1, DH - 1), outline=GOLD_L, width=6)
    for (y0, y1) in ((60, 360), (430, 760)):
        d.rectangle((40, y0, DW - 40, y1), outline=(110, 80, 28), width=5)
        d.rectangle((46, y0 + 6, DW - 34, y1 + 6), outline=(235, 200, 120), width=2)
    hx = DW - 50 if kind == "ca" else 50
    d.rounded_rectangle((hx - 10, 400, hx + 10, 520), 8, fill=GOLD_L)
    # emblem disc
    cy = 210
    d.ellipse((DW / 2 - 105, cy - 105, DW / 2 + 105, cy + 105), fill=(18, 26, 50), outline=GOLD_L, width=6)
    if kind == "ca":
        maple_leaf(d, DW / 2, cy + 8, 80, (240, 40, 40))
    else:
        f = round_flag(flag_us(150), 4)
        im.paste(f, (int(DW / 2 - 75), int(cy - f.size[1] / 2)), f)
    return im

def emblem_glow(size):
    lay = Image.new("RGB", size, 0)
    for (box, col) in ((DL, (255, 40, 40)), (DR, (120, 150, 255))):
        lay = ImageChops.add(lay, glow(size, ((box[0] + box[2]) / 2, box[1] + 210), 170, col, .9, 60))
    return lay

def hall_base():
    im = vgrad(W, H, [(0, NAVY0), (.35, NAVY1), (.72, (16, 30, 62)), (.73, (8, 14, 30)), (1, (4, 8, 18))])
    d = ImageDraw.Draw(im)
    # wall pilasters & mouldings
    for x in (40, 1040):
        d.rectangle((x - 14, 0, x + 14, 1400), fill=(18, 32, 66)); d.line([(x - 14, 0), (x - 14, 1400)], fill=GOLD_D, width=2)
    d.rectangle((520, 520, 560, 1400), fill=(18, 32, 66)); d.line([(540, 520), (540, 1400)], fill=GOLD_D, width=2)
    d.line([(0, 1400), (W, 1400)], fill=GOLD, width=4)
    d.line([(0, 470), (W, 470)], fill=GOLD_D, width=3)
    # door frames
    for b in (DL, DR):
        d.rectangle((b[0] - 22, b[1] - 22, b[2] + 22, b[3]), outline=GOLD, width=8)
        d.rectangle((b[0] - 6, b[1] - 6, b[2] + 6, b[3]), fill=(4, 6, 12))
    # marble floor perspective
    vp = (540, 700)
    for i in range(-14, 15):
        xb = 540 + i * 170
        t = (1400 - vp[1]) / (H - vp[1])
        xs = vp[0] + (xb - vp[0]) * t
        d.line([(xs, 1400), (xb, H)], fill=(30, 46, 84), width=2)
    y = 1400; step = 18
    while y < H:
        d.line([(0, y), (W, y)], fill=(26, 40, 76), width=2); step *= 1.35; y += step
    # marble veins
    rng = random.Random(3)
    for _ in range(40):
        x = rng.randint(0, W); yy = rng.randint(1410, H)
        pts = [(x, yy)]
        for k in range(6):
            x += rng.randint(-60, 60); yy += rng.randint(-10, 20); pts.append((x, yy))
        d.line(pts, fill=(36, 54, 96), width=1)
    im = add(im, glow((W, H), (540, 120), (520, 180), GOLD, .45, 120))
    im = add(im, glow((W, H), (540, 1500), (600, 120), GOLD, .18, 90))
    return im

PANEL = {"ca": door_panel("ca"), "us": door_panel("us")}

def reflection(panel):
    r = panel.transpose(Image.FLIP_TOP_BOTTOM).crop((0, 0, DW, 420))
    a = Image.linear_gradient("L").resize((DW, 420)).point(lambda v: int((255 - v) * .22))
    r.putalpha(a)
    return r

def street_ny():
    im = vgrad(DW, DH, [(0, (255, 236, 190)), (.5, (250, 200, 130)), (1, (210, 150, 90))])
    d = ImageDraw.Draw(im)
    rng = random.Random(7)
    for side in (0, 1):
        x = 0 if side == 0 else DW
        for k in range(6):
            bw = rng.randint(60, 110); top = rng.randint(30, 300) + k * 40
            col = (150 - k * 8, 100 - k * 6, 70 - k * 4)
            x0 = x if side == 0 else x - bw
            d.rectangle((x0, top, x0 + bw, DH), fill=col)
            for wy in range(top + 20, DH - 200, 36):
                for wx in range(x0 + 10, x0 + bw - 14, 22):
                    d.rectangle((wx, wy, wx + 10, wy + 18), fill=(255, 225, 160) if rng.random() < .5 else (120, 80, 55))
            x = int(x0 + bw * .7) if side == 0 else int(x0 + bw * .3)
    d.rectangle((0, 640, DW, DH), fill=(120, 90, 70))
    # storefront
    d.rectangle((70, 450, DW - 70, 660), fill=(28, 40, 74))
    d.rectangle((90, 520, DW - 90, 650), fill=(255, 214, 140))
    for i in range(8):
        d.polygon([(70 + i * 30, 450), (100 + i * 30, 450), (110 + i * 30, 500), (80 + i * 30, 500)],
                  fill=GOLD if i % 2 else (28, 40, 74))
    d.rectangle((70, 450, DW - 70, 500), outline=GOLD, width=3)
    d.rounded_rectangle((DW / 2 - 50, 540, DW / 2 + 50, 576), 6, fill=RED)
    d.text((DW / 2, 558), "OPEN", font=font("Montserrat", 24, "Black"), fill=WHITE, anchor="mm")
    im = add(im, glow((DW, DH), (DW / 2, 120), 220, (255, 240, 200), 1.0, 120))
    return im

def street_to():
    im = vgrad(DW, DH, [(0, (60, 80, 130)), (.55, (120, 140, 180)), (.75, (190, 200, 225)), (1, (235, 240, 250))])
    d = ImageDraw.Draw(im)
    # CN tower
    tx = DW * .7
    d.polygon([(tx - 6, 40), (tx + 6, 40), (tx + 14, 540), (tx - 14, 540)], fill=(40, 52, 86))
    d.ellipse((tx - 26, 200, tx + 26, 236), fill=(40, 52, 86))
    rng = random.Random(11)
    for k in range(9):
        bw = rng.randint(40, 90); x0 = rng.randint(-20, DW - 40); top = rng.randint(330, 470)
        d.rectangle((x0, top, x0 + bw, 560), fill=(46, 58, 96))
        for wy in range(top + 10, 550, 22):
            for wx in range(x0 + 6, x0 + bw - 8, 14):
                if rng.random() < .35: d.rectangle((wx, wy, wx + 6, wy + 9), fill=(255, 210, 140))
    d.rectangle((0, 560, DW, DH), fill=(228, 234, 246))
    # cafe
    d.rectangle((50, 380, DW - 50, 640), fill=(52, 38, 34))
    d.rectangle((50, 380, DW - 50, 650), outline=GOLD, width=3)
    d.rectangle((70, 450, DW / 2 - 15, 630), fill=(255, 196, 110))
    d.rectangle((DW / 2 + 15, 450, DW - 70, 630), fill=(255, 196, 110))
    d.rectangle((50, 380, DW - 50, 430), fill=(20, 30, 60))
    d.text((DW / 2, 405), "CAFÉ", font=font("PlayfairDisplay", 30, "Bold"), fill=GOLD_L, anchor="mm")
    d.rectangle((50, 372, DW - 50, 386), fill=WHITE)
    im = add(im, glow((DW, DH), (DW / 2, 560), (200, 90), (255, 170, 80), .8, 60))
    return im

INSIDE = {"us": street_ny(), "ca": street_to()}

def spill(box, col):
    lay = Image.new("RGB", (W, H), 0)
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = box
    d.polygon([(x0, y1), (x1, y1), (x1 + 260, H), (x0 - 260, H)], fill=tuple(int(c * .55) for c in col))
    lay = lay.filter(ImageFilter.GaussianBlur(40))
    lay = add(lay, glow((W, H), ((x0 + x1) / 2, (y0 + y1) / 2), ((x1 - x0) * .75, (y1 - y0) * .6), col, .45, 90))
    return lay

SPILL = {"us": spill(DR, (255, 205, 130)), "ca": spill(DL, (255, 215, 170))}
HALL = hall_base()
EMB = emblem_glow((W, H))
MAN_B = man_back(1.0)
SNOW = [(random.uniform(0, DW), random.uniform(0, DH), random.uniform(1.5, 4), random.uniform(40, 90)) for _ in range(90)]

def hall_frame(t, open_us=0.0, open_ca=0.0, man=True, emb_pulse=1.0):
    im = HALL.copy()
    for kind, box, p in (("ca", DL, open_ca), ("us", DR, open_us)):
        p = ease(p)
        if p > 0:
            inside = INSIDE[kind].copy()
            if kind == "ca":
                dd = ImageDraw.Draw(inside)
                for (x, y, r, v) in SNOW:
                    yy = (y + t * v) % DH; xx = (x + 14 * math.sin(t + y)) % DW
                    dd.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(250, 252, 255))
            im.paste(inside, box[:2])
        panel = PANEL[kind]
        pw = int(DW * math.cos(p * math.pi * .46))
        if pw > 4:
            pnl = panel.resize((pw, DH)) if pw != DW else panel
            if p > 0:
                dark = Image.new("RGBA", pnl.size, (0, 0, 0, int(150 * p)))
                pnl = Image.alpha_composite(pnl, dark)
            x = box[0] if kind == "ca" else box[2] - pw
            im.paste(pnl, (x, box[1]), pnl)
            ref = reflection(pnl)
            im.paste(ref, (x, 1404), ref)
        if p > 0:
            im = add(im, SPILL[kind], p)
    im = add(im, EMB, .55 * emb_pulse * (1 - .5 * max(open_us, open_ca)))
    if man:
        im.paste(MAN_B, (540 - MAN_B.size[0] // 2, 1180), MAN_B)
    return im

# ---------------------------------------------------------------- other scenes
def office_base():
    im = vgrad(W, H, [(0, (4, 8, 22)), (.5, (14, 24, 54)), (.62, (30, 40, 80)), (1, NAVY0)])
    d = ImageDraw.Draw(im)
    rng = random.Random(5)
    for k in range(40):
        bw = rng.randint(50, 140); x0 = rng.randint(-40, W); top = rng.randint(600, 1050)
        c = rng.randint(14, 26)
        d.rectangle((x0, top, x0 + bw, 1240), fill=(c, c + 8, c + 26))
        for wy in range(top + 12, 1230, 26):
            for wx in range(x0 + 8, x0 + bw - 10, 18):
                if rng.random() < .3:
                    d.rectangle((wx, wy, wx + 8, wy + 12), fill=rng.choice([(255, 210, 130), (250, 240, 220), (200, 170, 100)]))
    for x in (0, 360, 720, 1080):
        d.rectangle((x - 16, 0, x + 16, 1250), fill=(6, 10, 22))
    d.rectangle((0, 0, W, 60), fill=(6, 10, 22))
    im = add(im, glow((W, H), (540, 1200), (700, 160), (90, 110, 170), .5, 120))
    man = man_front(1.0)
    im.paste(man, (540 - 350, 760), man)
    d = ImageDraw.Draw(im)
    im2 = vgrad(W, 680, [(0, (40, 30, 26)), (1, (12, 10, 12))])
    im.paste(im2, (0, 1240))
    d.line([(0, 1240), (W, 1240)], fill=GOLD_D, width=4)
    # lamp
    d.polygon([(70, 980), (250, 980), (210, 860), (110, 860)], fill=GOLD)
    d.rectangle((152, 980, 168, 1240), fill=GOLD_D)
    d.ellipse((100, 1225, 220, 1255), fill=GOLD_D)
    im = add(im, glow((W, H), (160, 1120), (300, 260), (255, 190, 90), .8, 110))
    d = ImageDraw.Draw(im)
    # papers
    for i in range(7):
        d.rectangle((700 + i * 3, 1290 - i * 14, 980 + i * 2, 1310 - i * 14), fill=(230 - i * 6, 222 - i * 6, 205 - i * 6), outline=(150, 140, 120))
    for i in range(5):
        d.rectangle((760, 1330 - i * 12, 1010, 1345 - i * 12), fill=(215, 208, 190), outline=(140, 130, 110))
    # calculator
    d.rounded_rectangle((330, 1300, 560, 1600), 18, fill=(20, 22, 30), outline=GOLD_D, width=3)
    d.rectangle((355, 1325, 535, 1385), fill=(150, 175, 140))
    d.text((525, 1356), "Rs 0.00", font=font("Montserrat", 26, "Bold"), fill=(30, 40, 30), anchor="rm")
    for r in range(4):
        for c in range(4):
            x = 360 + c * 45; y = 1405 + r * 46
            d.rounded_rectangle((x, y, x + 35, y + 34), 6, fill=GOLD if c == 3 else (60, 64, 80))
    im = add(im, glow((W, H), (420, 1350), (240, 120), (255, 190, 90), .35, 80))
    return im

def passport_img():
    pw, ph = 560, 780
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, pw - 1, ph - 1), 28, fill=PK_GREEN)
    d.rounded_rectangle((18, 18, pw - 19, ph - 19), 20, outline=(0, 60, 36), width=3)
    f1 = font("PlayfairDisplay", 30, "Bold"); f2 = font("PlayfairDisplay", 54, "Bold")
    d.text((pw / 2, 110), "ISLAMIC REPUBLIC", font=f1, fill=GOLD, anchor="mm")
    d.text((pw / 2, 155), "OF PAKISTAN", font=f1, fill=GOLD, anchor="mm")
    crescent(d, pw / 2 - 10, 380, 120, GOLD, PK_GREEN)
    d.text((pw / 2, 620), "PASSPORT", font=f2, fill=GOLD, anchor="mm")
    d.rounded_rectangle((pw / 2 - 40, 680, pw / 2 + 40, 730), 6, outline=GOLD, width=3)
    d.ellipse((pw / 2 - 12, 693, pw / 2 + 12, 717), outline=GOLD, width=3)
    # leather noise
    n = (np.random.default_rng(1).normal(0, 6, (ph, pw))).astype(np.int16)
    a = np.array(im).astype(np.int16)
    a[:, :, :3] = np.clip(a[:, :, :3] + n[:, :, None], 0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")

def leather():
    rng = np.random.default_rng(2)
    base = np.array(vgrad(W, H, [(0, (10, 20, 44)), (.5, (20, 36, 72)), (1, (8, 14, 32))])).astype(np.int16)
    n = rng.normal(0, 7, (H // 4, W // 4))
    n = np.array(Image.fromarray(((n + 30) * 4).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)).astype(np.int16) - 120
    base += (n // 10)[:, :, None]
    im = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle((60, 300, W - 60, H - 300), outline=GOLD_D, width=3)
    d.rectangle((76, 316, W - 76, H - 316), outline=(40, 56, 96), width=2)
    return im

def dubai_base():
    im = vgrad(W, H, [(0, (20, 22, 60)), (.3, (80, 50, 100)), (.5, (200, 100, 90)), (.6, (250, 170, 90)), (.62, (40, 30, 50)), (1, (8, 10, 20))])
    im = add(im, glow((W, H), (760, 1170), (420, 140), (255, 170, 80), .9, 110))
    d = ImageDraw.Draw(im)
    rng = random.Random(9)
    for k in range(26):
        bw = rng.randint(40, 110); x0 = rng.randint(-40, W); top = rng.randint(820, 1100)
        d.rectangle((x0, top, x0 + bw, 1200), fill=(30, 26, 48))
        for wy in range(top + 10, 1190, 22):
            for wx in range(x0 + 6, x0 + bw - 8, 14):
                if rng.random() < .25: d.rectangle((wx, wy, wx + 5, wy + 8), fill=(255, 200, 120))
    # Burj Khalifa
    bx = 700
    tiers = [(0, 70), (120, 58), (260, 46), (420, 34), (580, 24), (720, 14), (840, 6)]
    for i, (dy, hw) in enumerate(tiers):
        y0 = 1200 - dy - 160
        d.rectangle((bx - hw, y0, bx + hw, 1200 - dy), fill=(26, 22, 44))
    d.polygon([(bx - 6, 200), (bx + 6, 200), (bx + 8, 360), (bx - 8, 360)], fill=(26, 22, 44))
    d.line([(bx, 120), (bx, 220)], fill=(26, 22, 44), width=4)
    for y in range(300, 1200, 14):
        d.point((bx + 2, y), fill=(255, 200, 140))
    # window frame
    for x in (0, 380, 760, 1080):
        d.rectangle((x - 18, 0, x + 18, 1200), fill=(4, 6, 14))
    d.rectangle((0, 1180, W, 1220), fill=(4, 6, 14))
    d.line([(0, 1220), (W, 1220)], fill=GOLD_D, width=3)
    man = man_front(1.0, rim=(255, 170, 90), passport=True)
    im.paste(man, (300 - 350, 800), man)
    return im

def endcard_base():
    im = vgrad(W, H, [(0, (6, 12, 30)), (.5, (14, 26, 58)), (1, (4, 8, 20))])
    im = add(im, glow((W, H), (540, 560), 360, GOLD, .35, 160))
    d = ImageDraw.Draw(im)
    d.rectangle((50, 50, W - 50, H - 50), outline=GOLD_D, width=2)
    return im

def logo_img():
    s = 260
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(s * .5, s * .02), (s * .95, s * .2), (s * .88, s * .65), (s * .5, s * .98), (s * .12, s * .65), (s * .05, s * .2)], fill=GOLD)
    d.polygon([(s * .5, s * .1), (s * .86, s * .25), (s * .8, s * .62), (s * .5, s * .88), (s * .2, s * .62), (s * .14, s * .25)], fill=NAVY1)
    d.polygon([(s * .25, s * .3), (s * .38, s * .3), (s * .5, s * .62), (s * .62, s * .3), (s * .75, s * .3), (s * .5, s * .8)], fill=GOLD_L)
    return im

# ---------------------------------------------------------------- text assets
def H1(parts, size=88):
    return rich_line(parts, size, "PlayfairDisplay", "Bold")

def bullet(kind, parts, size=43):
    return rich_line([("@icon", kind), ("", WHITE)] + parts, size, "Montserrat", "Bold")

T = {}
T["hook1"] = rich_line([("C11 ", WHITE), ("@icon", "ca"), (" ya ", GOLD_L), ("E-2 ", WHITE), ("@icon", "us"), ("?", WHITE)], 110, "PlayfairDisplay", "Black")
T["wrong"] = rich_line([("@icon", "x"), (" “Kaunsa sasta hai?”", WHITE)], 72, "PlayfairDisplay", "Bold")
T["wrong2"] = rich_line([("Cost is ", GOLD_L), ("not", WHITE), (" the first question", GOLD_L)], 42, "Montserrat", "SemiBold")
T["pp1"] = rich_line([("Pehla sawal:", WHITE)], 64, "PlayfairDisplay", "Bold")
T["pp2"] = rich_line([("Aapka ", WHITE), ("PASSPORT", GOLD_L)], 96, "PlayfairDisplay", "Black")
T["e2t"] = rich_line([("@icon", "us"), (" E-2 Treaty Investor", WHITE)], 64, "PlayfairDisplay", "Bold")
T["e2a"] = bullet("dot", [(" Treaty countries ", WHITE), ("only", GOLD_L)])
T["e2b"] = bullet("check", [(" Pakistan on the list since ", WHITE), ("1961", GOLD_L)])
T["e2c"] = bullet("dot", [(" Investment must be ", WHITE), ("substantial", GOLD_L)])
T["dx1"] = rich_line([("Dubai ya Riyadh mein ho?", WHITE)], 64, "PlayfairDisplay", "Bold")
T["dx2"] = rich_line([("Pakistani ", WHITE), ("passport", GOLD_L), (" still counts ", WHITE), ("@icon", "check")], 50, "Montserrat", "Bold")
T["c11t"] = rich_line([("@icon", "ca"), (" C11 Entrepreneur", WHITE)], 64, "PlayfairDisplay", "Bold")
T["c11a"] = bullet("check", [(" No country list", WHITE)])
T["c11b"] = bullet("dot", [(" Own ", GOLD_L), ("& ", WHITE), ("control", GOLD_L), (" the business", WHITE)])
T["c11c"] = bullet("warn", [(" Time doesn’t count for ", WHITE), ("CEC", GOLD_L)], 44)
T["tr1"] = rich_line([("Both are ", WHITE), ("temporary.", GOLD_L)], 84, "PlayfairDisplay", "Bold")
T["tr2"] = rich_line([("Different doors.", WHITE)], 84, "PlayfairDisplay", "Bold")
T["ec_name"] = rich_line([("VANGUARD", GOLD_L)], 108, "PlayfairDisplay", "Black", track=10)
T["ec_sub"] = rich_line([("GLOBAL MIGRATION", WHITE)], 38, "Montserrat", "SemiBold", track=12)
T["ec_line"] = rich_line([("Passport", GOLD_L), (" first. Then the ", WHITE), ("plan.", GOLD_L)], 66, "PlayfairDisplay", "Bold")
T["ec_cta1"] = rich_line([("Book your C11 / E-2", NAVY0)], 46, "Montserrat", "ExtraBold", shadow=False)
T["ec_cta2"] = rich_line([("Strategy Session", NAVY0)], 46, "Montserrat", "ExtraBold", shadow=False)
T["ec_ph"] = rich_line([("@icon", "phone"), (" +92 321 401 3525", WHITE)], 46, "Montserrat", "Bold")
T["ec_web"] = rich_line([("@icon", "globe"), (" vanguardglobalmigration.com", WHITE)], 40, "Montserrat", "SemiBold")
T["ec_disc"] = rich_line([("General information, not legal advice.", (150, 160, 185))], 28, "Montserrat", "Medium", shadow=False)
LOGO = logo_img()

CAPS = [
    (0.25, 2.2, "Canada *C11* ya America *E-2*?"),
    (2.2, 4.0, "Zyada log pehla sawal hi galat poochte hain."),
    (4.2, 6.9, "Sab poochte hain, kaunsa sasta hai?"),
    (6.9, 9.9, "But cost is not the first question."),
    (10.2, 13.0, "The first question is your *passport*."),
    (13.0, 15.9, "Kya aapki nationality allowed hai?"),
    (16.2, 19.0, "*E-2* sirf treaty countries ke liye hai."),
    (19.0, 22.3, "Good news: Pakistan *1961* se is list par hai."),
    (22.3, 25.9, "Koi fixed amount nahi, lekin investment substantial honi chahiye."),
    (26.2, 30.0, "Aur agar aap Dubai ya Saudi Arabia mein kaam kar rahe hain,"),
    (30.0, 33.9, "aapka Pakistani *passport* phir bhi qualify karta hai."),
    (34.2, 37.0, "Canada *C11* mein koi country list nahi."),
    (37.0, 40.5, "Lekin business aapka hona chahiye, aur aap control karein."),
    (40.5, 43.9, "Aur yaad rakhein: *C11* ka time Express Entry *CEC* mein count nahi hota."),
    (44.2, 47.2, "Dono temporary hain. Dono alag darwaze hain."),
    (47.2, 51.9, "Sahi darwaza aapke *passport* aur aapke long-term plan par depend karta hai."),
    (52.2, 55.4, "*Passport* first, then the plan."),
    (55.4, 59.9, "Comment *‘BUSINESS’* and Vanguard ki team aapka route map karegi."),
]
CAP_IMG = [caption_img(c[2]) for c in CAPS]

def appear(im, t, t0, x=None, y=0, dur=.6, slide=40, t1=None):
    """Fade+slide in text at t0, optional fade out at t1."""
    k = clamp((t - t0) / dur)
    if t1 is not None: k = min(k, clamp((t1 - t) / .4))
    return k, (x, y + slide * (1 - ease(k)))

def put(base, key, t, t0, y, t1=None, x=None, dur=.6):
    im = T[key] if isinstance(key, str) else key
    k, (_, yy) = appear(im, t, t0, y=y, dur=dur, t1=t1)
    xx = (W - im.size[0]) // 2 if x is None else x
    paste(base, im, (xx, yy), ease(k))

def top_scrim(im, h=700, k=.85):
    a = Image.linear_gradient("L").resize((W, h)).point(lambda v: int((255 - v) * k))
    blk = Image.new("RGB", (W, h), NAVY0)
    im.paste(blk, (0, 0), a)

def card(base, box, k=1.0):
    lay = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle((0, 0, lay.size[0] - 1, lay.size[1] - 1), 30, fill=(6, 12, 30, 200), outline=GOLD + (255,), width=3)
    paste(base, lay, box[:2], k)

# ---------------------------------------------------------------- scenes
OFFICE = office_base(); LEATHER = leather(); PASS = passport_img()
DUBAI = dubai_base(); ENDB = endcard_base()
DUST = [(random.uniform(0, W), random.uniform(0, H), random.uniform(1, 3.5), random.uniform(-12, 12), random.uniform(-20, -5)) for _ in range(110)]

def dust(im, t, n=110, box=None):
    d = ImageDraw.Draw(im)
    for i, (x, y, r, vx, vy) in enumerate(DUST[:n]):
        xx = (x + vx * t) % W; yy = (y + vy * t) % H
        b = .5 + .5 * math.sin(t * 1.3 + i)
        c = tuple(int(v * (.35 + .65 * b)) for v in GOLD_L)
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=c)

def s1(t):  # 0-4 hook
    im = hall_frame(t, emb_pulse=.8 + .2 * math.sin(t * 3))
    dust(im, t, 50)
    im = zoom(im, 1.0 + .1 * ease(t / 4), 540, 1000)
    top_scrim(im)
    put(im, "hook1", t, .15, 220)
    return im

def s2(t):  # 4-10
    lt = t - 4
    im = zoom(OFFICE, 1.1, 540 - 40 + 80 * ease(lt / 6), 1000)
    top_scrim(im, 600, .7)
    put(im, "wrong", t, 4.3, 210)
    put(im, "wrong2", t, 7.0, 340)
    return im

def s3(t):  # 10-16
    lt = t - 10
    im = LEATHER.copy()
    drop = 1 - ease(lt / 1.4)
    s = 1 + .08 * drop
    p = PASS.rotate(-5 + 3 * drop, expand=True, resample=Image.BICUBIC)
    if s != 1: p = p.resize((int(p.size[0] * s), int(p.size[1] * s)), Image.BILINEAR)
    # shadow
    sh = Image.new("RGBA", p.size, (0, 0, 0, 0)); sh.putalpha(p.getchannel("A").point(lambda v: int(v * .6)))
    sh = sh.filter(ImageFilter.GaussianBlur(20 + 30 * drop))
    cx, cy = 540, 1060 - 40 * drop
    im.paste(sh, (int(cx - p.size[0] / 2 + 20 + 40 * drop), int(cy - p.size[1] / 2 + 30 + 60 * drop)), sh)
    im.paste(p, (int(cx - p.size[0] / 2), int(cy - p.size[1] / 2)), p)
    # gold light sweep
    sw = clamp((lt - 1.4) / 2.6)
    if 0 < sw < 1:
        lay = Image.new("RGB", (W, H), 0)
        x = -300 + sw * 1700
        ImageDraw.Draw(lay).polygon([(x - 120, 500), (x + 60, 500), (x - 240, 1700), (x - 420, 1700)], fill=(150, 115, 50))
        lay = lay.filter(ImageFilter.GaussianBlur(50))
        im = add(im, lay, math.sin(math.pi * sw))
    im = add(im, glow((W, H), (540, 1000), (500, 600), GOLD, .12, 160))
    dust(im, t)
    im = zoom(im, 1.0 + .05 * ease(lt / 6), 540, 1000)
    top_scrim(im, 620, .8)
    put(im, "pp1", t, 10.5, 200)
    put(im, "pp2", t, 11.0, 300)
    return im

def s4(t):  # 16-26 E-2 door
    lt = t - 16
    im = hall_frame(t, open_us=clamp(lt / 2.2))
    dust(im, t, 40)
    im = zoom(im, 1.0 + .28 * ease(lt / 10), 780, 1000)
    top_scrim(im, 800, .9)
    card(im, (70, 150, 1010, 690), ease(clamp((lt - .8) / .6)))
    put(im, "e2t", t, 16.8, 180)
    put(im, "e2a", t, 17.2, 320, x=110)
    put(im, "e2b", t, 19.2, 420, x=110)
    put(im, "e2c", t, 22.4, 520, x=110)
    return im

def s5(t):  # 26-34 Dubai
    lt = t - 26
    im = zoom(DUBAI, 1.12 - .08 * ease(lt / 8), 560, 1000)
    dust(im, t, 30)
    top_scrim(im, 500, .6)
    card(im, (90, 150, 990, 470), ease(clamp((lt - .2) / .6)))
    put(im, "dx1", t, 26.3, 180)
    put(im, "dx2", t, 27.6, 320)
    return im

def s6(t):  # 34-44 C11 door
    lt = t - 34
    im = hall_frame(t, open_us=0, open_ca=clamp(lt / 2.2))
    dust(im, t, 40)
    im = zoom(im, 1.0 + .28 * ease(lt / 10), 300, 1000)
    top_scrim(im, 800, .9)
    card(im, (70, 150, 1010, 690), ease(clamp((lt - .8) / .6)))
    put(im, "c11t", t, 34.8, 180)
    put(im, "c11a", t, 35.2, 320, x=110)
    put(im, "c11b", t, 37.2, 420, x=110)
    put(im, "c11c", t, 40.6, 520, x=110)
    return im

def s7(t):  # 44-52
    lt = t - 44
    im = hall_frame(t, open_us=1, open_ca=1)
    im = add(im, glow((W, H), (540, 1820), (380, 90), (255, 220, 160), .8, 50), .5 + .5 * ease(lt / 3))
    dust(im, t, 70)
    im = zoom(im, 1.14 - .14 * ease(lt / 8), 540, 1000)
    top_scrim(im, 600, .85)
    put(im, "tr1", t, 44.4, 190)
    put(im, "tr2", t, 46.0, 310)
    return im

def s8(t):  # 52-60 end card
    lt = t - 52
    im = ENDB.copy()
    dust(im, t, 60)
    k = ease(clamp(lt / .9))
    sz = int(LOGO.size[0] * (.6 + .4 * k))
    lg = LOGO.resize((sz, sz), Image.BICUBIC)
    paste(im, lg, (540 - sz // 2, 470 - sz // 2), k)
    # shimmer across logo
    sh = clamp((lt - .9) / 1.2)
    if 0 < sh < 1:
        lay = Image.new("RGB", (W, H), 0)
        x = 300 + sh * 480
        ImageDraw.Draw(lay).polygon([(x, 320), (x + 50, 320), (x - 40, 620), (x - 90, 620)], fill=(255, 240, 200))
        lay = lay.filter(ImageFilter.GaussianBlur(14))
        m = Image.new("L", (W, H), 0); m.paste(LOGO.getchannel("A"), (540 - 130, 470 - 130))
        im = Image.composite(add(im, lay, math.sin(math.pi * sh)), im, m)
    put(im, "ec_name", t, 52.6, 640)
    put(im, "ec_sub", t, 53.0, 780)
    d = ImageDraw.Draw(im)
    lk = ease(clamp((lt - 1.2) / .8))
    if lk > 0: d.line([(540 - 200 * lk, 880), (540 + 200 * lk, 880)], fill=GOLD, width=3)
    put(im, "ec_line", t, 53.6, 920)
    bk = ease(clamp((lt - 2.4) / .6))
    if bk > 0:
        btn = Image.new("RGBA", (820, 190), (0, 0, 0, 0))
        bd = ImageDraw.Draw(btn)
        bd.rounded_rectangle((0, 0, 819, 189), 40, fill=GOLD)
        bd.rounded_rectangle((6, 6, 813, 90), 36, fill=GOLD_L)
        bd.rounded_rectangle((6, 6, 813, 183), 36, outline=(255, 235, 180), width=2)
        for i, key in enumerate(("ec_cta1", "ec_cta2")):
            ti = T[key]; btn.alpha_composite(ti, ((820 - ti.size[0]) // 2, 12 + i * 72 - 10))
        # pulse
        ps = 1 + .03 * math.sin(max(0, lt - 3) * 4) * (lt > 3)
        b2 = btn.resize((int(820 * ps), int(190 * ps)), Image.BICUBIC)
        paste(im, b2, (540 - b2.size[0] // 2, 1080 + 30 * (1 - bk) - (b2.size[1] - 190) // 2), bk)
    put(im, "ec_ph", t, 55.0, 1300)
    put(im, "ec_web", t, 55.4, 1380)
    put(im, "ec_disc", t, 55.8, 1450)
    return im

SCENES = [(0, 4, s1), (4, 10, s2), (10, 16, s3), (16, 26, s4), (26, 34, s5), (34, 44, s6), (44, 52, s7), (52, 60, s8)]
XF = .45

def frame(t):
    for i, (a, b, fn) in enumerate(SCENES):
        if a <= t < b or (i == len(SCENES) - 1 and t >= a):
            im = fn(t)
            if i > 0 and t - a < XF:
                prev = SCENES[i - 1][2](t)
                im = Image.blend(prev, im, ease((t - a) / XF))
            break
    if CAPTIONS:
        for (a, b, _), ci in zip(CAPS, CAP_IMG):
            if a <= t < b:
                k = min(clamp((t - a) / .18), clamp((b - t) / .18))
                cy = 1650 if t >= 52 else 1470
                paste(im, ci, ((W - ci.size[0]) // 2, cy - ci.size[1] // 2 + 10 * (1 - k)), k)
    if t < .4:
        im = Image.blend(Image.new("RGB", (W, H), 0), im, t / .4)
    return im

# ---------------------------------------------------------------- audio
def audio(path, sr=44100):
    n = int(DUR * sr); tt = np.arange(n) / sr
    out = np.zeros(n)
    # chord pad: Dm  Bb  F  C (4 bars of 3.75s, looped)
    chords = [[146.83, 174.61, 220.0, 293.66], [116.54, 174.61, 233.08, 293.66],
              [87.31, 174.61, 220.0, 261.63], [130.81, 196.0, 261.63, 329.63]]
    bar = 3.75
    for j in range(int(DUR / bar) + 1):
        ch = chords[j % 4]
        s0 = int(j * bar * sr); s1_ = min(n, int((j + 1) * bar * sr + .8 * sr))
        if s0 >= n: break
        seg = tt[s0:s1_] - j * bar
        env = np.minimum(1, seg / .9) * np.minimum(1, np.maximum(0, (bar + .8 - seg) / 1.2))
        v = np.zeros_like(seg)
        for f in ch:
            for det in (-.6, .6):
                v += np.sin(2 * np.pi * (f + det) * seg) + .25 * np.sin(2 * np.pi * 2 * (f + det) * seg)
        v += .6 * np.sin(2 * np.pi * ch[0] / 2 * seg)
        out[s0:s1_] += v * env * .028
    # soft pulse on each beat (~80 bpm)
    beat = 60 / 64
    for k in range(int(DUR / beat)):
        s0 = int(k * beat * sr); L = int(.5 * sr)
        if s0 + L > n: break
        seg = np.arange(L) / sr
        f = 55 * np.exp(-seg * 6) + 45
        out[s0:s0 + L] += .16 * np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-seg * 7) * (k % 2 == 0 or .5)
    # high shimmer bed
    out += .006 * np.sin(2 * np.pi * 880 * tt) * (0.5 + .5 * np.sin(2 * np.pi * .13 * tt))
    rng = np.random.default_rng(0)

    def whoosh(t0, dur, gain, up=True):
        L = int(dur * sr); s0 = int(t0 * sr)
        if s0 + L > n: L = n - s0
        nz = rng.normal(0, 1, L)
        spec = np.fft.rfft(nz); fr = np.fft.rfftfreq(L, 1 / sr)
        spec *= np.exp(-((np.log(fr + 1) - np.log(1200)) ** 2) / 1.2)
        w = np.fft.irfft(spec, L); w /= np.abs(w).max() + 1e-9
        x = np.linspace(0, 1, L)
        env = (x ** 2 if up else 1) * np.exp(-((x - .6) ** 2) / .06)
        out[s0:s0 + L] += w * env * gain

    for t0 in (15.3, 33.3):          # door opens
        whoosh(t0, 2.4, .45)
    for t0 in (3.75, 9.75, 25.75, 43.75, 51.6):  # transitions
        whoosh(t0, .9, .22)
    # impact on hook and passport drop
    for t0, g in ((0.05, .5), (11.2, .35), (16.2, .3), (34.2, .3)):
        s0 = int(t0 * sr); L = int(1.2 * sr); seg = np.arange(L) / sr
        out[s0:s0 + L] += g * np.sin(2 * np.pi * (40 + 40 * np.exp(-seg * 10)) * seg) * np.exp(-seg * 4)
    # end-card chime
    for i, f in enumerate((587.33, 739.99, 880.0, 1174.66)):
        s0 = int((52.9 + i * .12) * sr); L = int(2.5 * sr); seg = np.arange(L) / sr
        out[s0:s0 + L] += .07 * np.sin(2 * np.pi * f * seg) * np.exp(-seg * 2.2)
    fade = np.ones(n); fo = int(1.5 * sr); fade[-fo:] = np.linspace(1, 0, fo); fade[:int(.3 * sr)] = np.linspace(0, 1, int(.3 * sr))
    out *= fade
    out = np.tanh(out * 1.2) / np.tanh(1.2)
    out /= np.abs(out).max(); out *= .8
    st = np.stack([out, np.roll(out, 90)], 1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes((st * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    wav = OUT + ".wav"
    audio(wav)
    if os.environ.get("PREVIEW"):
        for ts in map(float, os.environ["PREVIEW"].split(",")):
            frame(ts).save(f"{OUT}_{ts:05.1f}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                         stdin=subprocess.PIPE)
    N = int(DUR * FPS)
    for i in range(N):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 150 == 0: print(f"{i}/{N}", flush=True)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("done", OUT)
