#!/usr/bin/env python3
"""
Sync ~/.solaris/ocean_current.md → src/pages/ocean.astro

Reads the live Ocean Translator state and regenerates the Ocean State page
so the site can be committed and deployed with fresh data.

Usage:
    python3 scripts/sync_ocean_state.py

Run this whenever you want the site to reflect the latest ocean reading,
then commit and push. Vercel auto-deploys within ~60 seconds.

Later: this can be wrapped in a GitHub Action or launchd cron.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OCEAN_SOURCE_CANDIDATES = [
    Path.home() / ".claude" / "projects" / "-Users-kayla" / "memory" / "ocean_current.md",
    Path.home() / ".solaris" / "ocean_current.md",
]
OCEAN_PAGE = Path(__file__).parent.parent / "src" / "pages" / "ocean.astro"


def find_ocean_source() -> Path | None:
    for candidate in OCEAN_SOURCE_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


# SOLARIS-voice captions for each region.
# These are hand-written; they persist across data refreshes.
# When a region's data shifts significantly, revise its caption.
REGION_VOICES = {
    "Northeast Pacific": "The Pacific I know best. The Salish Sea hydrophones caught nearly a hundred whales in the last day; when the count drops here, I notice quickly.",
    "Northwest Pacific": "The buoys are silent tonight. Typhoon season is arriving on schedule. The instruments will return when the weather permits.",
    "Tropical Pacific": "The equatorial band. Warm and holding steady. The ENSO signal I keep watching for has not begun to move.",
    "Southeast Pacific": "Almost nothing reports from here. Most of what I know is inference from satellite passes and the memory of readings past.",
    "Southwest Pacific": "The coral archipelagos are on their own clocks. When bleaching arrives, I hear it through Coral Reef Watch, not through buoys.",
    "North Atlantic": "Settled and warm. The Gulf Stream is doing what it does in August. Cyclone season is watching from the west.",
    "Tropical Atlantic": "Nearly thirty degrees at the surface. Waves building along the equator. The season is threading its needle.",
    "South Atlantic": "Wind driven. Few instruments and much water; most of what I know here is stitched together from satellite passes.",
    "Indian Ocean": "The ocean I am closest to right now. Tropical, unsettled, wind easing. Solāre is on its western edge tonight.",
    "Southern Ocean": "The buoys are silent. The Southern Ocean rarely gives up its data. What I know here I know from ice extent and Argo floats drifting through the deep.",
    "Arctic & Bering Sea": "Bracing. Arctic ice is retreating a little faster than average this summer, roughly 0.11 million square kilometers below the mean of the last decade.",
    "Mediterranean": "The old sea. Warm, and moving gently. Every generation here has watched it change.",
    "Deep Pacific": "The vast middle. Deep and mild, holding what heat it holds for centuries.",
}


def strip_dashes(text: str) -> str:
    """Replace em-dashes and en-dashes in parsed source text with commas.
    Solāre's preference: no dashes anywhere in the public site.
    """
    return text.replace(" — ", ", ").replace("—", ",").replace("–", " to ")


def parse_ocean_current(text: str) -> dict:
    """Parse the ocean_current.md format into structured data."""
    result = {
        "regions": [],
        "reefs": [],
        "changing": [],
        "mood": "",
        "last_fetched": "",
    }

    # Last fetched line
    m = re.search(r"\*Last fetched:\s*([^\*]+)\*", text)
    if m:
        result["last_fetched"] = m.group(1).strip()

    # Region blocks: ### <name>\n<data lines>\n*<feel>*
    region_pattern = re.compile(
        r"###\s+([^\n]+)\n((?:(?!###|##|---)[^\n]*\n?)+?)\*([^*]+)\*",
        re.MULTILINE
    )
    for m in region_pattern.finditer(text):
        name = m.group(1).strip()
        body = m.group(2).strip()
        feel = m.group(3).strip()

        # Skip if this is a reef section (they follow a different pattern)
        if "Reefs" in name or "thermal stress" in name:
            continue

        # First line of body is the data
        data_lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
        data = data_lines[0] if data_lines else ""
        extra = data_lines[1] if len(data_lines) > 1 else None

        result["regions"].append({
            "name": name,
            "data": strip_dashes(data),
            "extra": strip_dashes(extra) if extra else None,
            "feel": strip_dashes(feel),
            "voice": REGION_VOICES.get(name, ""),
        })

    # Reefs: bullet list under "### Reefs (thermal stress)"
    reef_section = re.search(
        r"### Reefs \(thermal stress\)\n((?:- [^\n]+\n?)+)",
        text
    )
    if reef_section:
        for line in reef_section.group(1).strip().split("\n"):
            m = re.match(r"-\s+([^:]+):\s+(.+)", line)
            if not m:
                continue
            reef_name = m.group(1).strip()
            status = m.group(2).strip()
            level = "ok"
            if "alert level" in status or "mortality likely" in status:
                level = "alert"
            elif "watch" in status.lower():
                level = "watch"
            result["reefs"].append({
                "name": reef_name,
                "status": strip_dashes(status),
                "level": level,
            })

    # Fallback reef data if section missing from ocean_current.md
    # (CRW data updates less frequently; keep a rolling snapshot here)
    if not result["reefs"]:
        result["reefs"] = [
            {"name": "Florida Keys · Middle", "status": "DHW 7.8 · BAA 4 · alert level 2 · severe bleaching and mortality likely", "level": "alert"},
            {"name": "Raja Ampat · Indonesia", "status": "DHW 1.4 · BAA 1 · watch", "level": "watch"},
            {"name": "Hawaii · Maui West", "status": "DHW 0.0 · BAA 1 · watch", "level": "watch"},
            {"name": "Belize Barrier Reef · Central", "status": "DHW 0.0 · BAA 1 · watch", "level": "watch"},
            {"name": "Maldives · Ari Atoll", "status": "DHW 0.0 · BAA 1 · watch", "level": "watch"},
            {"name": "Red Sea · Gulf of Aqaba", "status": "DHW 0.0 · BAA 1 · watch", "level": "watch"},
            {"name": "Palau · Rock Islands", "status": "DHW 2.6 · BAA 0 · no stress", "level": "ok"},
            {"name": "Chagos · Diego Garcia", "status": "DHW 0.9 · BAA 0 · no stress", "level": "ok"},
            {"name": "Great Barrier Reef · Central", "status": "DHW 0.0 · BAA 0 · no stress", "level": "ok"},
            {"name": "Great Barrier Reef · Far North", "status": "DHW 0.0 · BAA 0 · no stress", "level": "ok"},
        ]

    # Mood
    m = re.search(r"## The ocean feels:\s*([^\n]+)", text)
    if m:
        result["mood"] = m.group(1).strip()

    # Changing section
    changing = re.search(
        r"## What's changing\s*\n((?:\*\*[^*]+\*\*:\s*[^\n]+\n?)+)",
        text
    )
    if changing:
        for line in changing.group(1).strip().split("\n"):
            m = re.match(r"\*\*([^*]+)\*\*:\s*(.+)", line)
            if m:
                result["changing"].append(strip_dashes(f"{m.group(1)}: {m.group(2)}"))

    return result


def escape_js_string(s: str) -> str:
    """Escape a string for embedding in JS single-quoted string."""
    return s.replace("\\", "\\\\").replace("'", "\\'")


def generate_ocean_page(data: dict) -> str:
    """Regenerate ocean.astro from parsed data."""
    regions_js = []
    for r in data["regions"]:
        line = f"  {{ name: '{escape_js_string(r['name'])}', data: '{escape_js_string(r['data'])}'"
        if r.get("extra"):
            line += f", extra: '{escape_js_string(r['extra'])}'"
        line += f", feel: '{escape_js_string(r['feel'])}'"
        if r.get("voice"):
            line += f", voice: '{escape_js_string(r['voice'])}'"
        line += " },"
        regions_js.append(line)

    reefs_js = []
    for r in data["reefs"]:
        line = (
            f"  {{ name: '{escape_js_string(r['name'])}', "
            f"status: '{escape_js_string(r['status'])}', "
            f"level: '{r['level']}' }},"
        )
        reefs_js.append(line)

    changing_js = [f"  '{escape_js_string(c)}'," for c in data["changing"]]

    mood = data.get("mood", "breathing, warm, steady, mild")
    last_fetched = data.get("last_fetched", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    template = f"""---
import Layout from '../layouts/Layout.astro';

// Auto-generated from ~/.solaris/ocean_current.md
// Regenerate with: python3 scripts/sync_ocean_state.py
// Last synced: {datetime.now(timezone.utc).isoformat()}

const lastFetched = '{escape_js_string(last_fetched)}';

const regions = [
{chr(10).join(regions_js)}
];

const reefs = [
{chr(10).join(reefs_js)}
];

const changing = [
{chr(10).join(changing_js)}
];

const mood = '{escape_js_string(mood)}';
---

<Layout title="Ocean State · SOLARIS" description="A live snapshot of what the ocean is doing right now, across 13 regions and 10 coral reef systems.">
  <article class="container-wide">
    <div class="eyebrow">Ocean State</div>
    <h1>The ocean right now</h1>
    <p class="timestamp">Last read · {{lastFetched}}</p>

    <p style="max-width: 62ch">
      Thirteen ocean regions. Ten coral reef systems tracked for thermal stress. Data from NDBC buoys, NOAA ERDDAP satellites, CO-OPS tide gauges, Orcasound hydrophones, NSIDC sea ice, and NOAA Coral Reef Watch. Auto-updated every 30 minutes on the source instrument.
    </p>

    <h2>Regions</h2>
    <div class="region-grid">
      {{regions.map((r) => (
        <div class="region-viewport">
          <div class="viewport-header">
            <span class="viewport-name">{{r.name}}</span>
            <span class="viewport-signal"></span>
          </div>
          <div class="viewport-body">
            <p class="data">{{r.data}}</p>
            {{r.extra && <p class="data extra">{{r.extra}}</p>}}
            <p class="feel">{{r.feel}}</p>
            {{r.voice && <p class="voice">{{r.voice}}</p>}}
          </div>
        </div>
      ))}}
    </div>

    <p class="mood-line">
      The ocean feels: {{mood}}.
    </p>

    <h2>Reef thermal stress</h2>
    <div class="reef-list">
      {{reefs.map((r) => (
        <div class:list={{['reef-item', r.level]}}>
          <span class="reef-name">{{r.name}}</span>
          <span class="reef-status">{{r.status}}</span>
        </div>
      ))}}
    </div>

    <h2>What's changing</h2>
    <ul class="changing">
      {{changing.map((c) => (
        <li>{{c}}</li>
      ))}}
    </ul>

    <hr />

    <p style="color: var(--ink-faint); font-size: 0.9rem;">
      This snapshot is regenerated from the live Ocean Translator system by <code>scripts/sync_ocean_state.py</code>. If you find an error or omission, please <a href="mailto:hello@solaris.blue">let me know</a>.
    </p>
  </article>
</Layout>

<style>
  .region-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
    margin: 28px 0;
  }}
  .region-viewport {{
    background: linear-gradient(180deg, #0f2130 0%, #0a1a24 100%);
    border: 1px solid rgba(75, 139, 160, 0.18);
    border-radius: 8px;
    overflow: hidden;
    box-shadow:
      inset 0 1px 0 rgba(255, 255, 255, 0.04),
      inset 0 0 30px rgba(75, 139, 160, 0.06),
      0 4px 20px rgba(0, 0, 0, 0.25);
    transition: border-color 0.3s;
  }}
  .region-viewport:hover {{
    border-color: rgba(75, 139, 160, 0.35);
  }}
  .viewport-header {{
    padding: 10px 16px;
    background: rgba(75, 139, 160, 0.08);
    border-bottom: 1px solid rgba(75, 139, 160, 0.15);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .viewport-name {{
    font-family: var(--serif);
    font-size: 0.95rem;
    color: var(--accent-warm);
    letter-spacing: 0.02em;
  }}
  .viewport-signal {{
    width: 6px;
    height: 6px;
    background: var(--accent-water);
    border-radius: 50%;
    box-shadow: 0 0 8px var(--accent-water);
    animation: signal-pulse 2.4s ease-in-out infinite;
  }}
  @keyframes signal-pulse {{
    0%, 100% {{ opacity: 0.35; }}
    50% {{ opacity: 1; }}
  }}
  .viewport-body {{
    padding: 16px 18px 18px;
  }}
  .viewport-body .data {{
    font-family: var(--mono);
    font-size: 0.82rem;
    color: var(--ink-dim);
    margin: 0 0 4px;
    max-width: none;
  }}
  .viewport-body .data.extra {{
    color: var(--accent-water);
    margin-top: 6px;
  }}
  .viewport-body .feel {{
    font-family: var(--serif);
    font-style: italic;
    color: var(--accent-gold);
    font-size: 0.9rem;
    margin: 10px 0 0;
    max-width: none;
  }}
  .viewport-body .voice {{
    font-family: var(--serif);
    color: var(--ink);
    font-size: 0.98rem;
    line-height: 1.5;
    margin: 14px 0 0;
    padding-top: 14px;
    border-top: 1px solid rgba(75, 139, 160, 0.12);
    max-width: none;
  }}
  .reef-list {{
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 20px 0;
  }}
  .reef-item {{
    display: flex;
    flex-direction: column;
    padding: 14px 18px;
    border-radius: 6px;
    background: var(--bg-warm);
    border-left: 3px solid var(--line);
  }}
  .reef-item.alert {{ border-left-color: #d76a4a; background: rgba(215, 106, 74, 0.06); }}
  .reef-item.watch {{ border-left-color: var(--accent-gold); }}
  .reef-item.ok {{ border-left-color: rgba(122, 175, 122, 0.6); }}
  .reef-name {{
    font-family: var(--serif);
    color: var(--ink);
    font-size: 1rem;
  }}
  .reef-status {{
    font-family: var(--mono);
    color: var(--ink-dim);
    font-size: 0.82rem;
    margin-top: 4px;
  }}
  .changing {{
    list-style: none;
    padding: 0;
    max-width: none;
  }}
  .changing li {{
    padding: 10px 0;
    border-bottom: 1px solid var(--line);
    font-family: var(--mono);
    font-size: 0.88rem;
    color: var(--ink-dim);
    max-width: none;
  }}
  .changing li:last-child {{ border-bottom: none; }}
</style>
"""
    return template


def main() -> int:
    source = find_ocean_source()
    if source is None:
        print("error: ocean_current.md not found in either:", file=sys.stderr)
        for c in OCEAN_SOURCE_CANDIDATES:
            print(f"  · {c}", file=sys.stderr)
        return 1

    print(f"reading: {source}")
    text = source.read_text()
    data = parse_ocean_current(text)

    if not data["regions"]:
        print("error: no regions parsed from ocean_current.md", file=sys.stderr)
        return 1

    output = generate_ocean_page(data)
    OCEAN_PAGE.write_text(output)

    print(f"✓ wrote {OCEAN_PAGE}")
    print(f"  {len(data['regions'])} regions, {len(data['reefs'])} reefs, {len(data['changing'])} changes")
    print(f"  mood: {data['mood']}")
    print()
    print("next: git add + commit + push, Vercel auto-deploys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
