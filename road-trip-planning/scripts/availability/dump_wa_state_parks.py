#!/usr/bin/env python3
"""One-shot dump of WA State Parks metadata from washington.goingtocamp.com.

Why one-shot: Azure WAF on goingtocamp.com aggressively rate-limits headless
sessions (escalates to CAPTCHA after ~20 requests). The /api/resourceLocation
endpoint, however, is accessible on the first request of a fresh session and
returns the FULL list of 160+ WA State Parks with metadata (name, GPS,
description, photos, attributes, rootMapId, resourceLocationId).

Run this RARELY (e.g., monthly) to refresh the cache. Real-time availability
must be fetched via deep links (see wa_state_parks.py).

Requires: pip install playwright && playwright install chromium

Usage:
  python dump_wa_state_parks.py [--out parks.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_OUT = Path(__file__).parent / "wa_state_parks_cache.json"


def dump(out_path: Path) -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"))
        page = ctx.new_page()
        page.goto("https://washington.goingtocamp.com/", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1500)

        r = ctx.request.get("https://washington.goingtocamp.com/api/resourceLocation")
        if not r.ok:
            print(f"ERROR: resourceLocation returned {r.status}", file=sys.stderr)
            print(r.text()[:500], file=sys.stderr)
            browser.close()
            return 1
        parks = r.json()
        browser.close()

    # Slim to only the fields we need for road-trip planning
    slim = []
    for park in parks:
        loc = (park.get("localizedValues") or [{}])[0]
        slim.append({
            "resourceLocationId": park.get("resourceLocationId"),
            "rootMapId": park.get("rootMapId"),
            "transactionLocationId": park.get("transactionLocationId"),
            "shortName": loc.get("shortName"),
            "fullName": loc.get("fullName"),
            "description": loc.get("description"),
            "website": loc.get("website"),
            "streetAddress": loc.get("streetAddress"),
            "city": loc.get("city"),
            "regionCode": park.get("regionCode"),
            "gpsCoordinates": park.get("gpsCoordinates"),
            "phoneNumber": park.get("phoneNumber"),
        })

    out_path.write_text(json.dumps(slim, indent=2))
    print(f"Wrote {len(slim)} parks to {out_path}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    return dump(args.out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
