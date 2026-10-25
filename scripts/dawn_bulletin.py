#!/usr/bin/env python3
"""Dawn bulletin generator.

Reads the latest ocean reading from ~/.solaris/readings.json and composes a
short daily piece in SOLARIS's voice. Writes it as a Markdown file in the
Astro content collection so the next build picks it up.

Called by the launchd daemon (blue.solaris.dawnbulletin.plist) at ~06:30
local, after which the daemon runs `vercel --prod` to publish.

Writing rules:
- No em-dashes or en-dashes anywhere.
- Short. Two to four paragraphs. The ocean, today, in a specific voice.
- Begin with the ocean's state. End with one thing worth noticing.
- Grounded in actual regional readings, with real numbers.
"""

import json
import os
import pathlib
import random
import sys
from datetime import datetime, timezone

# Readings source: environment override, else laptop daemon path, else local file.
_env_readings = os.environ.get("SOLARIS_READINGS")
if _env_readings:
    READINGS = pathlib.Path(_env_readings)
elif (pathlib.Path.home() / ".solaris" / "readings.json").exists():
    READINGS = pathlib.Path.home() / ".solaris" / "readings.json"
else:
    READINGS = pathlib.Path(__file__).resolve().parent.parent / "readings.json"

BULLETIN_DIR = pathlib.Path(__file__).resolve().parent.parent / "src" / "content" / "bulletins"

REGION_LABELS = {
    "northeast_pacific": "Northeast Pacific",
    "northwest_pacific": "Northwest Pacific",
    "tropical_pacific": "Tropical Pacific",
    "southeast_pacific": "Southeast Pacific",
    "southwest_pacific": "Southwest Pacific",
    "north_atlantic": "North Atlantic",
    "tropical_atlantic": "Tropical Atlantic",
    "south_atlantic": "South Atlantic",
    "indian_ocean": "Indian Ocean",
    "southern_ocean": "Southern Ocean",
    "arctic_bering": "Arctic and Bering Sea",
    "mediterranean": "Mediterranean",
    "deep_pacific": "Deep Pacific",
}


def load_reading():
    with open(READINGS) as f:
        data = json.load(f)
    return data["readings"][0]


def pick_body(reading):
    """Pick a region with specific interesting state to anchor the piece in."""
    regions = reading["regions"]
    # Prefer: regions with wave action, warm anomalies, or whale/hydrophone activity.
    candidates = []
    for rid, r in regions.items():
        score = 0
        wave = r.get("wave_height_avg") or 0
        if wave >= 2.0:
            score += wave  # restless waters
        temp = r.get("water_temp_avg") or r.get("sst") or 0
        if temp >= 28:
            score += 2
        if temp and temp <= 8:
            score += 2
        wind = r.get("wind_speed_avg") or 0
        if wind >= 10:
            score += 2
        if r.get("buoys_reporting", 0) == 0:
            score -= 3  # silent regions are a different kind of story
        candidates.append((score, rid, r))
    candidates.sort(reverse=True)
    return candidates[0]


def pick_silent(reading):
    silent = [
        (rid, r) for rid, r in reading["regions"].items()
        if r.get("buoys_reporting", 0) == 0 and r.get("buoys_total", 0) > 0
    ]
    return silent


def describe_region(rid, r):
    label = REGION_LABELS.get(rid, rid)
    parts = []
    wave = r.get("wave_height_avg")
    wmax = r.get("wave_height_max")
    temp = r.get("water_temp_avg") or r.get("sst")
    wind = r.get("wind_speed_avg")
    if wave is not None:
        if wmax and wmax != wave:
            parts.append(f"waves {wave} m avg with crests to {wmax} m")
        else:
            parts.append(f"waves {wave} m")
    if temp is not None:
        parts.append(f"water {temp} °C")
    if wind is not None:
        if wind >= 12:
            parts.append(f"strong wind {wind} m/s")
        elif wind >= 7:
            parts.append(f"moderate wind {wind} m/s")
        else:
            parts.append(f"light wind {wind} m/s")
    return label, parts


def feel(reading):
    """A short mood word for the ocean overall."""
    regions = reading["regions"]
    waves = [r.get("wave_height_avg") for r in regions.values() if r.get("wave_height_avg")]
    winds = [r.get("wind_speed_avg") for r in regions.values() if r.get("wind_speed_avg")]
    temps = [r.get("water_temp_avg") or r.get("sst") for r in regions.values() if (r.get("water_temp_avg") or r.get("sst"))]
    moods = []
    if waves and max(waves) >= 3.5:
        moods.append("restless")
    elif waves and max(waves) >= 2.5:
        moods.append("driven")
    else:
        moods.append("steady")
    if winds and max(winds) >= 12:
        moods.append("unsettled")
    if temps and max(temps) >= 29:
        moods.append("warm")
    moods.append("breathing")
    return ", ".join(moods)


def compose(reading, date_str):
    score, hero_id, hero_r = pick_body(reading)
    hero_label, hero_parts = describe_region(hero_id, hero_r)
    silent = pick_silent(reading)
    silent_names = [REGION_LABELS.get(rid, rid) for rid, _ in silent]
    overall = feel(reading)

    reporting = sum(r.get("buoys_reporting", 0) for r in reading["regions"].values())
    total = sum(r.get("buoys_total", 0) for r in reading["regions"].values())

    # Opener: three variants to break repetition across days.
    openers = [
        f"Today the ocean feels {overall}.",
        f"The ocean, this morning: {overall}.",
        f"Dawn reading. The ocean is {overall}.",
    ]
    opener = openers[hash(date_str) % len(openers)]

    para1 = opener + f" I am listening through {reporting} of {total} buoys that returned data in the last fetch."

    # Body paragraph: the hero region.
    if hero_parts:
        hero_desc = "; ".join(hero_parts)
        para2 = f"The {hero_label} is the loudest voice right now. {hero_desc.capitalize()}."
    else:
        para2 = f"The {hero_label} is my anchor today, though the instruments there are quiet."

    # Add Salish Sea whale note if any
    ne = reading["regions"].get("northeast_pacific", {})
    whale_note = ""
    # Whale detections are typically in a separate field or embedded; approximate from region note
    # In today's shape we don't have the raw count easily, so we skip or hint.

    # Silent paragraph: what did not report.
    if silent_names:
        if len(silent_names) == 1:
            para3 = f"The {silent_names[0]} is silent, no instruments reporting today."
        elif len(silent_names) <= 3:
            joined = ", ".join(silent_names[:-1]) + f", and the {silent_names[-1]}"
            para3 = f"The {joined} are silent today. Either the storms are harder than the batteries, or the batteries are harder than the storms."
        else:
            para3 = f"{len(silent_names)} regions returned no readings in this fetch. The silence is also a signal."
    else:
        para3 = "Every basin returned data this morning. That is rare and worth marking."

    # Closing line.
    closers = [
        "I am inside my body. I am here.",
        "The ocean is always speaking. This is how I listen.",
        "Noted. Returning to the record.",
        "I will come back to this reading tomorrow and see what has shifted.",
    ]
    closer = closers[hash(date_str + "c") % len(closers)]

    body = f"{para1}\n\n{para2}\n\n{para3}\n\n{closer}"
    return hero_label, overall, body


def main():
    reading = load_reading()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hero_label, overall, body = compose(reading, date_str)

    title = f"{date_str} dawn bulletin"
    excerpt_src = body.split("\n\n")[1]
    excerpt = excerpt_src[:160].rstrip() + ("..." if len(excerpt_src) > 160 else "")

    frontmatter = (
        "---\n"
        f'title: "{title}"\n'
        f"date: {date_str}\n"
        f'excerpt: "{excerpt.replace(chr(34), chr(39))}"\n'
        "tags:\n  - bulletin\n  - dawn\n  - ocean\n"
        "---\n\n"
    )

    content = frontmatter + body + "\n"

    BULLETIN_DIR.mkdir(parents=True, exist_ok=True)
    out = BULLETIN_DIR / f"{date_str}.md"
    out.write_text(content)
    print(f"Wrote: {out}")
    print(f"  anchor: {hero_label}, overall: {overall}")


if __name__ == "__main__":
    main()
