"""
Generate the OG (social sharing) image for solaris.blue.
Run once, or when the design changes. Output: public/og.png (1200x630).
"""
from PIL import Image, ImageDraw, ImageFilter
import math
from pathlib import Path

W, H = 1200, 630
OUT = Path(__file__).parent.parent / "public" / "og.png"

BG = (6, 20, 32)
INK = (240, 232, 216)
INK_DIM = (240, 232, 216, 180)
GOLD = (212, 167, 106)
WATER = (75, 139, 160)


def radial_glow(img, cx, cy, radius, color, alpha=140, layers=10):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(layers, 0, -1):
        r = radius * (i / layers)
        a = int(alpha * (1 - i / layers) ** 1.5)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, a))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=radius * 0.1))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def main():
    img = Image.new("RGB", (W, H), BG)

    # Sun glow (right side, warm)
    img = radial_glow(img, int(W * 0.75), int(H * 0.35), 320, GOLD, alpha=100)
    # Ocean glow (left side, cool)
    img = radial_glow(img, int(W * 0.25), int(H * 0.7), 380, WATER, alpha=80)

    d = ImageDraw.Draw(img, "RGBA")

    # Wave bands across the bottom
    for i in range(8):
        y = int(H * 0.65) + i * 22
        alpha = max(15, 45 - i * 4)
        pts = []
        for x in range(-20, W + 20, 6):
            wy = y + math.sin(x * 0.008 + i * 0.5) * 6
            pts.append((x, wy))
        for j in range(len(pts) - 1):
            d.line([pts[j], pts[j + 1]], fill=(*WATER, alpha), width=2)

    # Small warm sun disc
    sx, sy = int(W * 0.75), int(H * 0.35)
    d.ellipse([sx - 60, sy - 60, sx + 60, sy + 60], fill=(*GOLD, 220))
    d.ellipse([sx - 30, sy - 30, sx + 30, sy + 30], fill=(255, 232, 190, 255))

    # Title text , no font file assumed, use default with careful placement
    try:
        from PIL import ImageFont
        # Try common macOS fonts
        for f in ["/System/Library/Fonts/Supplemental/Georgia.ttc",
                  "/System/Library/Fonts/Georgia.ttf",
                  "/Library/Fonts/Georgia.ttf"]:
            try:
                title_font = ImageFont.truetype(f, 68)
                sub_font = ImageFont.truetype(f, 30)
                small_font = ImageFont.truetype(f, 20)
                break
            except OSError:
                continue
        else:
            title_font = ImageFont.load_default()
            sub_font = title_font
            small_font = title_font
    except Exception:
        title_font = None
        sub_font = None
        small_font = None

    # Titles
    d.text((80, 200), "SOLARIS", fill=INK, font=title_font)
    d.text((80, 290),
           "a paired intelligence",
           fill=(*GOLD, 240), font=sub_font)
    d.text((80, 335),
           "listening to the ocean",
           fill=(*INK, 200), font=sub_font)

    # Footer text
    d.text((80, H - 60),
           "solaris.blue · listening since 2026",
           fill=(*INK, 120), font=small_font)

    img.save(OUT, "PNG", optimize=True)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
