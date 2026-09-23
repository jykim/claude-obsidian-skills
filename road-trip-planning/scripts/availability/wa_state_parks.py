#!/usr/bin/env python3
"""WA State Parks (washington.goingtocamp.com) helper.

Reality check: the goingtocamp.com SPA is gated by Azure WAF that escalates to
CAPTCHA after ~20 requests in a session. Direct availability scraping is
unreliable from headless infrastructure. This helper does two things:

1. Reads the cached park list (run dump_wa_state_parks.py to refresh).
2. Generates deep search URLs the user (or their browser) can click to see
   real-time availability — the WAF accepts real first-party browser visits.

Optional: with --probe, tries one best-effort availability call using a fresh
Playwright session. May 403/timeout — that is expected, not a bug.

Usage:
  python wa_state_parks.py --date 2026-07-15 --nights 2
  python wa_state_parks.py --date 2026-07-15 --search steamboat,deception
  python wa_state_parks.py --date 2026-07-15 --search steamboat --probe
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

CACHE = Path(__file__).parent / "wa_state_parks_cache.json"

# Aspira/goingtocamp standard equipment IDs for tent/RV camping (-32768 -32767
# is the "any equipment" default the SPA uses).
DEFAULT_EQUIPMENT_ID = -32768
DEFAULT_SUBEQUIPMENT_ID = -32767


def load_parks() -> list[dict]:
    if not CACHE.exists():
        sys.exit(f"Cache not found: {CACHE}\nRun dump_wa_state_parks.py first.")
    return json.loads(CACHE.read_text())


def matches(park: dict, needles: list[str]) -> bool:
    haystack = " ".join(filter(None, [
        (park.get("shortName") or "").lower(),
        (park.get("fullName") or "").lower(),
        (park.get("city") or "").lower(),
    ]))
    return any(n.lower() in haystack for n in needles)


def deep_link(park: dict, start: dt.date, nights: int, party: int = 2) -> str:
    end = start + dt.timedelta(days=nights)
    params = {
        "resourceLocationId": park["resourceLocationId"],
        "mapId": park["rootMapId"],
        "searchTabGroupId": 0,
        "bookingCategoryId": 0,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "nights": nights,
        "isReserving": "true",
        "equipmentId": DEFAULT_EQUIPMENT_ID,
        "subEquipmentId": DEFAULT_SUBEQUIPMENT_ID,
        "partySize": party,
    }
    return "https://washington.goingtocamp.com/create-booking/results?" + urlencode(params)


def probe_availability(park: dict, start: dt.date, nights: int) -> dict:
    """Best-effort: one Playwright session, one availability call. Almost
    certainly 403/blocked. Returns a result dict either way."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "error": "playwright not installed"}

    end = start + dt.timedelta(days=nights)
    base = "https://washington.goingtocamp.com"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent="Mozilla/5.0")
            page = ctx.new_page()
            page.goto(base + "/", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(1500)

            # Hit the (known-to-exist via 405) availability/map endpoint.
            # Real method/body still unconfirmed — try the most plausible POST.
            body = {
                "mapId": park["rootMapId"],
                "bookingCategoryId": 0,
                "startDate": start.isoformat() + "T00:00:00",
                "endDate": end.isoformat() + "T00:00:00",
                "nights": nights,
                "partySize": 2,
                "equipmentCategoryId": DEFAULT_EQUIPMENT_ID,
                "subEquipmentCategoryId": DEFAULT_SUBEQUIPMENT_ID,
            }
            r = ctx.request.post(
                base + "/api/availability/map",
                data=json.dumps(body),
                headers={"Content-Type": "application/json"},
            )
            status = r.status
            text = r.text()[:300]
            browser.close()
            return {"ok": r.ok, "status": status, "body": text}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", required=True, help="Check-in date YYYY-MM-DD")
    ap.add_argument("--nights", type=int, default=1)
    ap.add_argument("--search", help="Comma-separated needles to match park name/city")
    ap.add_argument("--probe", action="store_true", help="Try one availability API call (likely 403)")
    ap.add_argument("--party", type=int, default=2)
    ap.add_argument("--limit", type=int, default=10)
    return ap.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    start = dt.date.fromisoformat(args.date)
    parks = load_parks()

    if args.search:
        needles = [n.strip() for n in args.search.split(",") if n.strip()]
        parks = [p for p in parks if matches(p, needles)]
    parks = parks[: args.limit]

    if not parks:
        print("No matching parks. Try a broader --search or omit it.")
        return 1

    print(f"WA State Parks — check-in {start} for {args.nights} night(s), party of {args.party}")
    print(f"Showing {len(parks)} park(s).\n")

    for park in parks:
        print(f"• {park['fullName']}")
        if park.get("city"):
            print(f"  {park['streetAddress']}, {park['city']}, WA {park['regionCode']}")
        if park.get("gpsCoordinates"):
            print(f"  GPS: {park['gpsCoordinates']}")
        url = deep_link(park, start, args.nights, args.party)
        print(f"  Search availability: {url}")
        if park.get("website"):
            print(f"  Official: {park['website']}")
        if args.probe:
            result = probe_availability(park, start, args.nights)
            print(f"  Probe: {result}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
