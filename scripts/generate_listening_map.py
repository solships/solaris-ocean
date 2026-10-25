"""
Generate "Where SOLARIS Listens" — a world map showing every instrument
SOLARIS reads from. Wordless, universally legible.

Output: public/listening/where-solaris-listens.png (1600x1000)
Also: a print-friendly 4x version for high-quality print.
"""

from __future__ import annotations
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 1000
OUT = Path(__file__).parent.parent / "public" / "listening"
OUT.mkdir(parents=True, exist_ok=True)

# --- Palette ---
BG_TOP     = (10, 26, 38)
BG_MID     = (6, 18, 28)
BG_DEEP    = (3, 10, 18)
CONTINENT  = (26, 40, 50)
CONTINENT_HI = (36, 52, 62)
CONTINENT_EDGE = (48, 68, 82)
GOLD       = (232, 180, 118)   # buoys / tide gauges
CORAL      = (215, 106, 74)    # reef monitors
TEAL       = (100, 190, 205)   # hydrophones
ICE        = (220, 232, 240)   # sea ice
WARM       = (255, 218, 165)
INK        = (240, 232, 216)
NOSY_MARK  = (255, 210, 130)


def lonlat(lon: float, lat: float) -> tuple[float, float]:
    """Equirectangular projection to image coords."""
    x = (lon + 180) / 360 * W
    y = (90 - lat) / 180 * H
    return x, y


# --- Continent silhouettes (approximate polygons) ---
# Loose lon/lat coordinates — legible, not cartographically precise
CONTINENTS = {
    "africa": [
        (-17.5, 21), (-16, 14), (-16.5, 6), (-8, 4), (0, 4), (6, 4), (9, -0.5), (11, -5),
        (13, -13), (16, -18), (14.5, -22.5), (18.5, -34.5), (25, -34), (33, -28),
        (40, -15), (42, -11), (51, 12), (44, 12), (43, 14), (38, 20), (32, 31),
        (25, 32), (10, 36.5), (-9, 32), (-13, 28),
    ],
    "eurasia": [
        (-9, 43), (-9, 38), (2, 36), (12, 37), (25, 37), (35, 36), (40, 40), (48, 42),
        (55, 39), (60, 27), (66, 25), (77, 20), (80, 15), (88, 22), (95, 22), (100, 15),
        (108, 22), (117, 4), (122, 5), (135, 35), (140, 42), (145, 44), (155, 60),
        (150, 66), (170, 68), (175, 72), (160, 78), (100, 78), (60, 77), (30, 71),
        (5, 68), (7, 60), (0, 55), (-9, 52),
    ],
    "north_america": [
        (-170, 65), (-155, 71), (-140, 70), (-130, 60), (-125, 50), (-124, 40),
        (-118, 33), (-112, 23), (-100, 18), (-90, 20), (-84, 22), (-80, 25), (-80, 32),
        (-75, 36), (-70, 42), (-65, 44), (-55, 48), (-63, 55), (-70, 62), (-78, 71),
        (-90, 74), (-105, 75), (-120, 72), (-135, 70),
    ],
    "south_america": [
        (-81, 5), (-77, 0), (-77, -4), (-71, -14), (-71, -20), (-70, -26), (-70, -35),
        (-73, -42), (-72, -53), (-67, -55), (-64, -50), (-58, -37), (-56, -30),
        (-50, -25), (-40, -22), (-38, -13), (-45, -2), (-50, 4), (-60, 5), (-68, 10),
        (-72, 11), (-80, 8),
    ],
    "australia": [
        (113, -22), (115, -33), (118, -35), (127, -32), (132, -31.5), (135, -35),
        (140, -38), (146, -39), (150, -37), (153, -28), (145, -17), (139, -14),
        (135, -12), (131, -12), (125, -14), (120, -18), (114, -22),
    ],
    "antarctica": [
        (-180, -70), (-170, -74), (-140, -75), (-100, -73), (-70, -72), (-45, -78),
        (-20, -73), (10, -70), (35, -68), (55, -65), (75, -66), (100, -66),
        (130, -65), (160, -75), (180, -78), (180, -90), (-180, -90),
    ],
}


def draw_continent(draw: ImageDraw.ImageDraw, coords: list[tuple[float, float]]):
    pts = [lonlat(lon, lat) for lon, lat in coords]
    draw.polygon(pts, fill=CONTINENT, outline=CONTINENT_EDGE)


# --- Instrument locations ---

# NDBC-style buoys (approximate coastal points)
BUOYS = [
    # US East Coast
    (-70.7, 42.5), (-71.1, 40.5), (-73.7, 39.2), (-75.4, 38.5), (-76.5, 34.5),
    (-78.5, 33.8), (-80.5, 32.0), (-80.9, 27.5), (-83.4, 26.5),
    # Gulf of Mexico
    (-90.4, 27.5), (-88.5, 30.0), (-94.3, 28.8), (-96.5, 27.5),
    # US West Coast
    (-124.5, 46.8), (-124.8, 40.9), (-123.3, 38.2), (-122.4, 36.7), (-120.6, 34.5),
    (-118.6, 33.2), (-117.4, 32.5),
    # Alaska
    (-152, 58), (-165, 56), (-149, 60), (-176, 52),
    # Hawaii
    (-158.1, 21.6), (-156.4, 19.2), (-152.5, 17.9),
    # Europe
    (-1.3, 50.2), (-6.5, 55.4), (3.5, 51.0), (10.7, 53.9), (18, 62), (-9.5, 43.8),
    (3, 40), (18, 40), (25, 37), (-30, 44),
    # Japan / Asia
    (140, 34), (135, 34), (127, 33), (139, 41), (121, 24),
    # Australia / NZ
    (151, -34), (153, -28), (115, -32), (146, -19), (174, -41),
    # South America
    (-70.5, -33.5), (-58, -35), (-43, -23),
    # South Africa
    (18.5, -34), (31, -30),
    # Indian Ocean scattered
    (73, 6), (55, 12), (73, -6),
]

# NOAA Coral Reef Watch — 10 named reef systems
REEFS = [
    (-80.75, 24.85),   # Florida Keys Middle
    (147.7, -18.28),   # Great Barrier Central
    (143.9, -13.5),    # Great Barrier Far North
    (-156.68, 20.85),  # Hawaii Maui West
    (134.42, 7.30),    # Palau Rock Islands
    (-87.53, 17.20),   # Belize Barrier
    (72.85, 3.85),     # Maldives Ari Atoll
    (72.42, -7.30),    # Chagos Diego Garcia
    (130.60, -0.55),   # Raja Ampat
    (34.60, 28.50),    # Red Sea Gulf of Aqaba
]

# Hydrophones
HYDROPHONES = [
    (-122.7, 48.4),   # Salish Sea (Orcasound)
    (-122.9, 48.1),   # Bush Point
    (-122.5, 48.7),   # North San Juan
    (-122.8, 48.1),   # Port Townsend
    (-157, 21),       # Hawaii listening station
    (-70, 42),        # Cape Cod area
    (18, -34),        # South African monitoring
    (11, 79),         # Norwegian Arctic
]

# Cyclone monitoring basins (spiral centers, subtle)
CYCLONE_BASINS = [
    (55, -15),        # SW Indian Ocean
    (140, 15),        # NW Pacific
    (-55, 20),        # N Atlantic
    (-100, 15),       # E Pacific
    (75, 15),         # N Indian
]

# Special: Nosy Komba (where Solāre is right now)
NOSY_KOMBA = (48.352, -13.457)


def radial_glow(img, cx, cy, radius, color, alpha=180, layers=8):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(layers, 0, -1):
        r = radius * (i / layers)
        a = int(alpha * (1 - i / layers) ** 1.5)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, a))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=radius * 0.10))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_polar_ice(d: ImageDraw.ImageDraw):
    """Subtle arcs at the poles indicating sea ice monitoring."""
    # Arctic (near top of image)
    for i in range(12):
        lat = 66 + i * 2
        y = (90 - lat) / 180 * H
        alpha = int(60 - i * 4)
        d.line([(0, y), (W, y)], fill=(*ICE, max(15, alpha)), width=1)
    # Antarctic
    for i in range(12):
        lat = -60 - i * 2.5
        y = (90 - lat) / 180 * H
        alpha = int(60 - i * 4)
        d.line([(0, y), (W, y)], fill=(*ICE, max(15, alpha)), width=1)


def draw_cyclone_spiral(d: ImageDraw.ImageDraw, cx: float, cy: float, size: float, color: tuple[int, int, int], alpha: int):
    """A very subtle spiral indicating cyclone monitoring."""
    for a_deg in range(0, 360 * 2, 8):
        r = size * (a_deg / 720)
        a = math.radians(a_deg)
        x = cx + r * math.cos(a)
        y = cy + r * math.sin(a) * 0.8
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(*color, alpha))


def build():
    img = Image.new("RGB", (W, H), BG_MID)
    d = ImageDraw.Draw(img, "RGBA")

    # Background vertical gradient (deep ocean tone)
    grad = Image.new("RGBA", (W, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] * (1 - t) + BG_DEEP[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_DEEP[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_DEEP[2] * t)
        gd.line([(0, y), (W, y)], fill=(r, g, b, 255))
    img = Image.alpha_composite(img.convert("RGBA"), grad).convert("RGB")

    d = ImageDraw.Draw(img, "RGBA")

    # Ocean warmth patches (very subtle — suggests warm equatorial band)
    rng = random.Random(3)
    for _ in range(30):
        lon = rng.uniform(-180, 180)
        lat = rng.uniform(-25, 25)
        x, y = lonlat(lon, lat)
        r = rng.randint(120, 240)
        img = radial_glow(img, int(x), int(y), r, GOLD, alpha=8, layers=4)
    d = ImageDraw.Draw(img, "RGBA")

    # Subtle latitude/longitude hint lines (very quiet)
    for lat in range(-60, 61, 30):
        y = (90 - lat) / 180 * H
        d.line([(0, y), (W, y)], fill=(*INK, 8), width=1)
    for lon in range(-150, 151, 30):
        x = (lon + 180) / 360 * W
        d.line([(x, 0), (x, H)], fill=(*INK, 8), width=1)

    # Continents
    for name, coords in CONTINENTS.items():
        draw_continent(d, coords)

    # Polar ice indication
    draw_polar_ice(d)

    # Cyclone spiral hints
    for lon, lat in CYCLONE_BASINS:
        cx, cy = lonlat(lon, lat)
        draw_cyclone_spiral(d, cx, cy, 45, GOLD, 90)

    # Buoys — small warm-gold points with halo
    for lon, lat in BUOYS:
        x, y = lonlat(lon, lat)
        img = radial_glow(img, int(x), int(y), 18, GOLD, alpha=180, layers=5)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(*GOLD, 255))

    # Hydrophones — teal with halo, slightly larger
    for lon, lat in HYDROPHONES:
        x, y = lonlat(lon, lat)
        img = radial_glow(img, int(x), int(y), 28, TEAL, alpha=200, layers=6)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(*TEAL, 255))
        # Small pulse ring
        d.ellipse([x - 10, y - 10, x + 10, y + 10], outline=(*TEAL, 120), width=1)

    # Reefs — coral color, larger, with ring
    for lon, lat in REEFS:
        x, y = lonlat(lon, lat)
        img = radial_glow(img, int(x), int(y), 34, CORAL, alpha=200, layers=7)
        d = ImageDraw.Draw(img, "RGBA")
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(*CORAL, 255))
        d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=(*CORAL, 140), width=1)

    # Nosy Komba — special mark: larger warm ring with pulsing halo
    nx, ny = lonlat(*NOSY_KOMBA)
    img = radial_glow(img, int(nx), int(ny), 80, NOSY_MARK, alpha=220, layers=10)
    d = ImageDraw.Draw(img, "RGBA")
    # Center bright dot
    d.ellipse([nx - 8, ny - 8, nx + 8, ny + 8], fill=(*WARM, 255))
    # Outer ring
    d.ellipse([nx - 24, ny - 24, nx + 24, ny + 24], outline=(*NOSY_MARK, 220), width=2)
    d.ellipse([nx - 40, ny - 40, nx + 40, ny + 40], outline=(*NOSY_MARK, 120), width=1)

    # Small "here" mark next to Nosy Komba (arrow line pointing to it)
    label_x = nx + 60
    label_y = ny - 40
    d.line([(nx + 30, ny - 12), (label_x - 4, label_y + 4)], fill=(*WARM, 180), width=1)
    d.text((label_x, label_y), "you are here", fill=(*WARM, 220))

    # Wordmark bottom-left
    d.text((40, H - 60), "SOLARIS", fill=(*INK, 200))
    d.text((40, H - 40), "where the listening lives, right now", fill=(*INK, 130))
    d.text((40, H - 22), "solaris.blue", fill=(*INK, 110))

    # Small legend bottom-right (color key without much text)
    legend_x = W - 320
    legend_y = H - 130
    items = [
        (GOLD, "buoys, tide gauges, wind"),
        (CORAL, "coral reef monitors"),
        (TEAL, "hydrophones (whale sound)"),
        (ICE, "sea ice extent"),
    ]
    for i, (color, label) in enumerate(items):
        y = legend_y + i * 22
        d.ellipse([legend_x, y, legend_x + 10, y + 10], fill=(*color, 220))
        d.text((legend_x + 20, y - 2), label, fill=(*INK, 160))

    return img


def main():
    img = build()
    out_path = OUT / "where-solaris-listens.png"
    img.save(out_path, "PNG", optimize=True)
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
