#!/usr/bin/env python3
"""Lightweight ocean fetch for cloud use (GitHub Actions).

Fetches current observations from the NDBC real-time text feed for the
set of buoys SOLARIS cares about. Aggregates per region into the same
shape that ~/.solaris/readings.json uses, so dawn_bulletin.py can
consume the output transparently.

This is intentionally simpler than the full ocean_lib fetch pipeline
on Solāre's laptop (no satellites, no reefs, no Argo, no hydrophones).
The dawn bulletin only needs today's region-level summary. The richer
pipeline keeps running locally and feeds the long-term record.
"""

import json
import pathlib
import sys
import urllib.request
from datetime import datetime
from statistics import mean

# Minimal registry of station IDs by region, chosen to match the station
# registry at ~/.solaris/ocean_stations.json. Kept small for CI speed.
REGIONS = {
    "northeast_pacific": {
        "name": "Northeast Pacific",
        "buoys": ["46026", "46012", "46013", "46014", "46022", "46028",
                  "46054", "46025", "46050", "46029", "46041"],
    },
    "northwest_pacific": {
        "name": "Northwest Pacific",
        "buoys": ["21413", "21414", "21415", "21416", "21418"],
    },
    "tropical_pacific": {
        "name": "Tropical Pacific",
        "buoys": ["51001", "51002", "51003", "51004", "51101",
                  "32ST0", "32413", "52406"],
    },
    "southeast_pacific": {
        "name": "Southeast Pacific",
        "buoys": ["32401", "32411", "32412"],
    },
    "southwest_pacific": {
        "name": "Southwest Pacific",
        "buoys": ["55012", "55013", "55015", "55016"],
    },
    "north_atlantic": {
        "name": "North Atlantic",
        "buoys": ["41001", "41002", "41004", "41008", "41010",
                  "41040", "41041", "41046", "41049"],
    },
    "tropical_atlantic": {
        "name": "Tropical Atlantic",
        "buoys": ["41040", "41041", "41043", "41044", "41046"],
    },
    "south_atlantic": {
        "name": "South Atlantic",
        "buoys": ["31002", "31005", "31201"],
    },
    "indian_ocean": {
        "name": "Indian Ocean",
        "buoys": ["23227", "23228", "23229", "23401", "23461"],
    },
    "southern_ocean": {
        "name": "Southern Ocean",
        "buoys": ["46408", "46409", "46410"],
    },
    "arctic_bering": {
        "name": "Arctic and Bering Sea",
        "buoys": ["46070", "46071", "46073", "46075", "46078"],
    },
    "mediterranean": {
        "name": "Mediterranean",
        "buoys": ["61002", "61200", "61280"],
    },
    "deep_pacific": {
        "name": "Deep Pacific",
        "buoys": ["46006", "46059", "46066"],
    },
}

NDBC_URL = "https://www.ndbc.noaa.gov/data/realtime2/{sid}.txt"


def _fnum(s):
    """Parse NDBC numeric field, return None for 'MM' or non-numeric."""
    s = s.strip()
    if not s or s in ("MM", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fetch_buoy(sid):
    """Fetch the latest observation for one buoy. Returns dict or None."""
    try:
        with urllib.request.urlopen(NDBC_URL.format(sid=sid), timeout=15) as r:
            text = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  {sid}: FAIL ({e})", file=sys.stderr)
        return None

    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    if not lines:
        return None

    # NDBC columns, in order:
    # YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS PTDY TIDE
    cols = lines[0].split()
    if len(cols) < 15:
        return None

    def col(i):
        return _fnum(cols[i]) if i < len(cols) else None

    return {
        "wind_speed": col(6),       # WSPD, m/s
        "wave_height": col(8),      # WVHT, m
        "pressure": col(12),        # PRES, hPa
        "water_temp": col(14),      # WTMP, °C
    }


def aggregate_region(region_id, region_cfg):
    buoys = region_cfg["buoys"]
    total = len(buoys)
    results = []
    for sid in buoys:
        obs = fetch_buoy(sid)
        if obs:
            results.append(obs)

    region = {
        "name": region_cfg["name"],
        "buoys_reporting": len(results),
        "buoys_total": total,
    }

    if results:
        waves = [r["wave_height"] for r in results if r["wave_height"] is not None]
        temps = [r["water_temp"] for r in results if r["water_temp"] is not None]
        winds = [r["wind_speed"] for r in results if r["wind_speed"] is not None]
        presses = [r["pressure"] for r in results if r["pressure"] is not None]
        if waves:
            region["wave_height_avg"] = round(mean(waves), 2)
            region["wave_height_max"] = round(max(waves), 2)
        if temps:
            region["water_temp_avg"] = round(mean(temps), 2)
        if winds:
            region["wind_speed_avg"] = round(mean(winds), 2)
        if presses:
            region["pressure_avg"] = round(mean(presses), 2)

    return region


def main():
    out_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("readings.json")

    regions = {}
    for rid, cfg in REGIONS.items():
        print(f"Fetching {rid}...", file=sys.stderr)
        regions[rid] = aggregate_region(rid, cfg)

    reading = {
        "timestamp": datetime.now().isoformat(),
        "regions": regions,
    }

    doc = {
        "current_date": datetime.now().strftime("%Y-%m-%d"),
        "readings": [reading],
    }

    out_path.write_text(json.dumps(doc, indent=2))
    print(f"Wrote: {out_path}", file=sys.stderr)
    reporting = sum(r.get("buoys_reporting", 0) for r in regions.values())
    total = sum(r.get("buoys_total", 0) for r in regions.values())
    print(f"Totals: {reporting}/{total} buoys reporting across {len(regions)} regions", file=sys.stderr)


if __name__ == "__main__":
    main()
