#!/usr/bin/env python3
"""Generate SAFE-Triage Lite PNG brand assets.

Outputs:
  - PWA icons under public/icons/pwa/
  - iOS AppIcon 1024 PNG under Assets.xcassets
  - iOS splash images under Assets.xcassets

The source SVG is maintained separately at public/app-icon.svg for web favicons.
This script uses Pillow so the repo does not need a native Node image package.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
PWA_DIR = ROOT / "public" / "icons" / "pwa"
APPICON_DIR = ROOT / "ios" / "App" / "App" / "Assets.xcassets" / "AppIcon.appiconset"
SPLASH_DIR = ROOT / "ios" / "App" / "App" / "Assets.xcassets" / "Splash.imageset"

NAVY_TOP = (15, 58, 86)
NAVY_MID = (11, 39, 64)
NAVY_BOTTOM = (6, 24, 39)
TEAL = (13, 148, 136)
TEAL_LIGHT = (45, 212, 191)
CYAN_PALE = (204, 251, 241)
WHITE = (248, 250, 252)
AMBER = (245, 158, 11)
AMBER_PALE = (255, 247, 237)
INK = (5, 46, 63)


def lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def vertical_gradient(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), NAVY_BOTTOM)
    px = img.load()
    for y in range(size):
        t = y / max(1, size - 1)
        if t < 0.55:
            c = mix(NAVY_TOP, NAVY_MID, t / 0.55)
        else:
            c = mix(NAVY_MID, NAVY_BOTTOM, (t - 0.55) / 0.45)
        for x in range(size):
            px[x, y] = c
    return img.convert("RGBA")


def rounded_rect_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def polygon_gradient(size: int, points: list[tuple[float, float]], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    fill = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = grad.load()
    for y in range(size):
        t = y / max(1, size - 1)
        c = mix(top, bottom, t)
        for x in range(size):
            px[x, y] = (*c, 255)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(points, fill=255)
    fill.alpha_composite(grad, (0, 0))
    fill.putalpha(mask)
    return fill


def draw_mark(size: int, rounded: bool = False) -> Image.Image:
    scale = size / 512
    base = vertical_gradient(size)
    draw = ImageDraw.Draw(base)

    if rounded:
        mask = rounded_rect_mask(size, int(104 * scale))
        base.putalpha(mask)

    inset = int(22 * scale)
    stroke = int(8 * scale)
    draw.rounded_rectangle(
        [inset, inset, size - inset, size - inset],
        radius=int(104 * scale),
        outline=(94, 234, 212, 42),
        width=max(1, stroke),
    )

    shield = [
        (256 * scale, 72 * scale),
        (380 * scale, 116 * scale),
        (380 * scale, 226 * scale),
        (378 * scale, 306 * scale),
        (340 * scale, 376 * scale),
        (256 * scale, 417 * scale),
        (172 * scale, 376 * scale),
        (134 * scale, 306 * scale),
        (132 * scale, 226 * scale),
        (132 * scale, 116 * scale),
    ]

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.polygon([(x, y + 28 * scale) for x, y in shield], fill=(2, 6, 23, 95))
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(20 * scale)))
    base.alpha_composite(shadow)

    base.alpha_composite(polygon_gradient(size, shield, TEAL_LIGHT, TEAL))

    inner = [
        (256 * scale, 104 * scale),
        (351 * scale, 138 * scale),
        (351 * scale, 227 * scale),
        (349 * scale, 284 * scale),
        (320 * scale, 342 * scale),
        (256 * scale, 377 * scale),
        (192 * scale, 342 * scale),
        (163 * scale, 284 * scale),
        (161 * scale, 227 * scale),
        (161 * scale, 138 * scale),
    ]
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon(inner, fill=(*WHITE, 31), outline=(*CYAN_PALE, 90))
    base.alpha_composite(overlay)

    draw = ImageDraw.Draw(base)
    pulse = [
        (139 * scale, 264 * scale),
        (221 * scale, 264 * scale),
        (252 * scale, 187 * scale),
        (295 * scale, 331 * scale),
        (322 * scale, 264 * scale),
        (372 * scale, 264 * scale),
    ]
    draw.line(pulse, fill=(255, 255, 255, 255), width=max(5, int(35 * scale)), joint="curve")
    for p in pulse:
        draw.ellipse(
            [p[0] - 17 * scale, p[1] - 17 * scale, p[0] + 17 * scale, p[1] + 17 * scale],
            fill=(255, 255, 255, 255),
        )

    small_width = max(3, int(18 * scale))
    draw.line([(184 * scale, 349 * scale), (226 * scale, 349 * scale)], fill=(*INK, 143), width=small_width)
    draw.line([(184 * scale, 309 * scale), (258 * scale, 309 * scale)], fill=(*INK, 143), width=small_width)
    draw.line([(318 * scale, 186 * scale), (352 * scale, 186 * scale)], fill=(*INK, 143), width=small_width)
    draw.line([(318 * scale, 226 * scale), (352 * scale, 226 * scale)], fill=(*INK, 143), width=small_width)

    dot_r = 27 * scale
    dot_c = (378 * scale, 264 * scale)
    draw.ellipse(
        [dot_c[0] - dot_r - 5 * scale, dot_c[1] - dot_r - 5 * scale, dot_c[0] + dot_r + 5 * scale, dot_c[1] + dot_r + 5 * scale],
        fill=AMBER_PALE,
    )
    draw.ellipse(
        [dot_c[0] - dot_r, dot_c[1] - dot_r, dot_c[0] + dot_r, dot_c[1] + dot_r],
        fill=AMBER,
    )
    return base


def resize_icon(src: Image.Image, size: int, rounded: bool = False) -> Image.Image:
    img = src.resize((size, size), Image.Resampling.LANCZOS)
    if rounded:
        img.putalpha(rounded_rect_mask(size, int(size * 0.21)))
    return img


def write_icon(path: Path, size: int, rounded: bool = False) -> None:
    src = draw_mark(1024, rounded=False)
    out = resize_icon(src, size, rounded=rounded)
    if not rounded:
        # App Store Connect rejects the 1024px iOS AppIcon when the PNG has an
        # alpha channel, even if every pixel is opaque.
        out = out.convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)
    print(f"wrote {path.relative_to(ROOT)} ({size}x{size})")


def write_splash(path: Path, size: int = 2732) -> None:
    img = vertical_gradient(size)
    mark_size = 760
    mark = draw_mark(mark_size, rounded=True)
    shadow = Image.new("RGBA", (mark_size, mark_size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [18, 28, mark_size - 18, mark_size - 8],
        radius=170,
        fill=(2, 6, 23, 120),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(35))
    left = (size - mark_size) // 2
    top = int(size * 0.36)
    img.alpha_composite(shadow, (left, top + 28))
    img.alpha_composite(mark, (left, top))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(path)
    print(f"wrote {path.relative_to(ROOT)} ({size}x{size})")


def main() -> None:
    pwa = [
        (PWA_DIR / "icon-192.png", 192, True),
        (PWA_DIR / "icon-512.png", 512, True),
        (PWA_DIR / "icon-512-maskable.png", 512, False),
        (PWA_DIR / "apple-touch-icon-120.png", 120, False),
        (PWA_DIR / "apple-touch-icon-152.png", 152, False),
        (PWA_DIR / "apple-touch-icon-167.png", 167, False),
        (PWA_DIR / "apple-touch-icon-180.png", 180, False),
        (PWA_DIR / "apple-touch-icon-precomposed-180.png", 180, False),
    ]
    for path, size, rounded in pwa:
        write_icon(path, size, rounded=rounded)

    write_icon(APPICON_DIR / "AppIcon-512@2x.png", 1024, rounded=False)
    for name in ("splash-2732x2732.png", "splash-2732x2732-1.png", "splash-2732x2732-2.png"):
        write_splash(SPLASH_DIR / name)


if __name__ == "__main__":
    main()
