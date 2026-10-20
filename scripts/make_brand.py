"""Channel avatar (800x800) and banner (2560x1440) from the channel's own character art."""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
random.seed(7)

SKY_TOP, SKY_BOTTOM = (120, 200, 255), (205, 238, 255)
HILL_BACK, HILL_FRONT = (150, 215, 120), (110, 190, 95)
LETTER_COLORS = [(255, 107, 107), (255, 170, 50), (255, 210, 60), (107, 203, 119),
                 (77, 150, 255), (185, 103, 255)]


def cutout(path: Path) -> Image.Image:
    """Remove the plain studio background connected to the image border."""
    img = Image.open(path).convert("RGB")
    a = np.asarray(img).astype(np.int16)
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((a - bg) ** 2).sum(axis=2))
    # studio background and its soft floor shadow: same tint as the background, darker
    norm = np.linalg.norm(a, axis=2) + 1e-6
    cos = (a * bg).sum(axis=2) / (norm * np.linalg.norm(bg))
    ratio = a.mean(axis=2) / bg.mean()
    shadow = (cos > 0.9985) & (ratio > 0.55) & (ratio < 1.05)
    similar = (dist < 34) | shadow
    labels, _ = ndimage.label(similar)
    edge_labels = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    edge_labels.discard(0)
    background = np.isin(labels, list(edge_labels))
    fg = ~background
    # keep the biggest object (the character), fill holes, soften the edge
    lab, n = ndimage.label(fg)
    if n > 1:
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        fg = lab == (int(np.argmax(sizes)) + 1)
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_erosion(fg, iterations=2)
    alpha = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))
    rgba = img.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba.crop(rgba.getbbox())


def vertical_gradient(size, top, bottom):
    w, h = size
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return grad.resize((w, h))


def cloud(draw, cx, cy, s):
    for dx, dy, r in [(-1.1, 0.2, 0.75), (0, 0, 1), (1.1, 0.25, 0.7), (0.5, -0.45, 0.65), (-0.5, -0.35, 0.6)]:
        draw.ellipse([cx + dx * s - r * s, cy + dy * s - r * s, cx + dx * s + r * s, cy + dy * s + r * s],
                     fill=(255, 255, 255, 235))


def note(draw, x, y, s, color):
    draw.ellipse([x, y + s * 1.6, x + s, y + s * 2.3], fill=color)
    draw.rectangle([x + s * 0.82, y, x + s * 0.98, y + s * 2.0], fill=color)
    draw.polygon([(x + s * 0.9, y), (x + s * 1.6, y + s * 0.35), (x + s * 1.6, y + s * 0.7),
                  (x + s * 0.9, y + s * 0.4)], fill=color)


def flower(draw, x, y, s, color):
    for k in range(5):
        ang = k * 2 * math.pi / 5
        px, py = x + math.cos(ang) * s, y + math.sin(ang) * s
        draw.ellipse([px - s * 0.7, py - s * 0.7, px + s * 0.7, py + s * 0.7], fill=color)
    draw.ellipse([x - s * 0.55, y - s * 0.55, x + s * 0.55, y + s * 0.55], fill=(255, 220, 80))


def meadow(size, hill_top_ratio=0.62, seed=1):
    random.seed(seed)
    w, h = size
    base = vertical_gradient(size, SKY_TOP, SKY_BOTTOM).convert("RGBA")
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # sun
    sx, sy, sr = int(w * 0.88), int(h * 0.16), int(h * 0.09)
    d.ellipse([sx - sr * 1.5, sy - sr * 1.5, sx + sr * 1.5, sy + sr * 1.5], fill=(255, 255, 235, 150))
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 214, 70, 255))
    # clouds
    for cx, cy, s in [(0.12, 0.17, 0.05), (0.40, 0.10, 0.04), (0.66, 0.20, 0.045)]:
        cloud(d, int(w * cx), int(h * cy), int(h * s))
    base.alpha_composite(layer)
    # hills
    hills = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(hills)
    top = int(h * hill_top_ratio)
    d.ellipse([-w * 0.2, top - h * 0.05, w * 0.65, top + h * 0.9], fill=HILL_BACK)
    d.ellipse([w * 0.35, top - h * 0.09, w * 1.25, top + h * 0.9], fill=HILL_BACK)
    d.ellipse([-w * 0.3, top + h * 0.10, w * 1.3, top + h * 1.4], fill=HILL_FRONT)
    for _ in range(int(w / 40)):
        x = random.randint(0, w)
        y = random.randint(int(top + h * 0.16), h)
        flower(d, x, y, max(4, h * 0.008), random.choice(
            [(255, 255, 255), (255, 150, 190), (255, 120, 120), (190, 160, 255)]))
    base.alpha_composite(hills)
    return base


def shadow_under(canvas, x, y_bottom, width):
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([x - width * 0.38, y_bottom - width * 0.06, x + width * 0.38,
                                y_bottom + width * 0.06], fill=(0, 60, 0, 70))
    canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(width * 0.03)))


def place(canvas, char, cx, bottom, height, angle=0):
    k = height / char.height
    c = char.resize((int(char.width * k), int(height)), Image.LANCZOS)
    if angle:
        c = c.rotate(angle, resample=Image.BICUBIC, expand=True)
    shadow_under(canvas, cx, bottom, c.width)
    canvas.alpha_composite(c, (int(cx - c.width / 2), int(bottom - c.height)))


def bouncy_title(canvas, text, cx, cy, size, outline=None):
    font = ImageFont.truetype(FONT, size)
    outline = outline or max(6, size // 9)
    widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] if ch != " " else size * 0.28 for ch in text]
    spacing = size * 0.02
    total = sum(widths) + spacing * (len(text) - 1)
    x = cx - total / 2
    ci = 0
    for ch, cw in zip(text, widths):
        if ch == " ":
            x += cw + spacing
            continue
        tile = Image.new("RGBA", (int(size * 1.6), int(size * 1.8)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        bb = font.getbbox(ch)
        ox, oy = (tile.width - (bb[2] - bb[0])) / 2 - bb[0], (tile.height - (bb[3] - bb[1])) / 2 - bb[1]
        td.text((ox + size * 0.03, oy + size * 0.06), ch, font=font, fill=(40, 60, 120, 110),
                stroke_width=outline, stroke_fill=(40, 60, 120, 110))
        td.text((ox, oy), ch, font=font, fill=LETTER_COLORS[ci % len(LETTER_COLORS)],
                stroke_width=outline, stroke_fill=(255, 255, 255))
        angle = [-6, 4, -3, 5, -4, 3][ci % 6]
        dy = [0, -0.06, 0.02, -0.04, 0.03, -0.05][ci % 6] * size
        tile = tile.rotate(angle, resample=Image.BICUBIC)
        canvas.alpha_composite(tile, (int(x + cw / 2 - tile.width / 2), int(cy + dy - tile.height / 2)))
        x += cw + spacing
        ci += 1


def pill(canvas, text, cx, cy, size):
    font = ImageFont.truetype(FONT, size)
    bb = font.getbbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad_x, pad_y = size * 0.8, size * 0.45
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([cx - tw / 2 - pad_x, cy - th / 2 - pad_y, cx + tw / 2 + pad_x, cy + th / 2 + pad_y],
                        radius=th, fill=(255, 255, 255, 235))
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1]), text, font=font, fill=(60, 90, 160))
    canvas.alpha_composite(layer)


chars = {n: cutout(REPO / f"assets/characters/{n}.png") for n in ["pip", "lulu", "bo"]}
for n, c in chars.items():
    c.save(OUT / f"_cutout_{n}.png")

# ── Banner 2560x1440, safe area 1546x423 in the centre ──
W, H = 2560, 1440
banner = meadow((W, H), hill_top_ratio=0.60, seed=3)
note_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
nd = ImageDraw.Draw(note_layer)
for x, y, s, col in [(560, 470, 34, (255, 107, 107)), (1960, 450, 38, (77, 150, 255)),
                     (700, 820, 26, (185, 103, 255)), (1860, 860, 28, (255, 170, 50))]:
    note(nd, x, y, s, col + (230,))
banner.alpha_composite(note_layer)
safe_top, safe_bottom = (H - 423) // 2, (H + 423) // 2
bouncy_title(banner, "Bouncy", W // 2, safe_top + 80, 140)
bouncy_title(banner, "Meadow", W // 2, safe_top + 225, 140)
pill(banner, "Kids Songs with Pip, Lulu & Bo", W // 2, safe_top + 365, 40)
ground = safe_bottom + 25
left = (W - 1546) // 2
place(banner, chars["pip"], left + 230, ground, 420, angle=4)
place(banner, chars["lulu"], W - left - 330, ground, 430, angle=-4)
place(banner, chars["bo"], W - left - 90, ground + 15, 300, angle=-6)
banner.convert("RGB").save(OUT / "banner_2560x1440.png", optimize=True)

# preview with safe-area guides (not for upload)
prev = banner.copy()
pd = ImageDraw.Draw(prev)
pd.rectangle([(W - 1546) // 2, safe_top, (W + 1546) // 2, safe_bottom], outline=(255, 0, 0), width=6)
prev.convert("RGB").resize((1280, 720)).save(OUT / "_banner_preview_safe_area.png")

# ── Avatar 800x800 (shown as a circle) ──
A = 800
av = vertical_gradient((A, A), (255, 214, 90), (255, 160, 70)).convert("RGBA")
rays = Image.new("RGBA", (A, A), (0, 0, 0, 0))
rd = ImageDraw.Draw(rays)
for k in range(16):
    a0, a1 = k * 2 * math.pi / 16, (k + 0.5) * 2 * math.pi / 16
    rd.polygon([(A / 2, A / 2), (A / 2 + math.cos(a0) * A, A / 2 + math.sin(a0) * A),
                (A / 2 + math.cos(a1) * A, A / 2 + math.sin(a1) * A)], fill=(255, 255, 255, 45))
av.alpha_composite(rays)
pip = chars["pip"]
# head and shoulders of Pip, large and centred
crop = pip.crop((0, 0, pip.width, int(pip.height * 0.72)))
k = A * 0.86 / crop.width
crop = crop.resize((int(crop.width * k), int(crop.height * k)), Image.LANCZOS)
av.alpha_composite(crop, (int((A - crop.width) / 2), int(A - crop.height + A * 0.04)))
ring = Image.new("RGBA", (A, A), (0, 0, 0, 0))
ImageDraw.Draw(ring).ellipse([14, 14, A - 14, A - 14], outline=(255, 255, 255, 255), width=22)
av.alpha_composite(ring)
av.convert("RGB").save(OUT / "avatar_800x800.png", optimize=True)

# circular preview (how YouTube shows it)
mask = Image.new("L", (A, A), 0)
ImageDraw.Draw(mask).ellipse([0, 0, A, A], fill=255)
circle = Image.new("RGBA", (A, A), (24, 24, 24, 255))
circle.paste(av, (0, 0), mask)
circle.convert("RGB").resize((300, 300)).save(OUT / "_avatar_preview_circle.png")
print("done")
