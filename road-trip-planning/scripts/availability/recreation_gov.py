#!/usr/bin/env python3
"""Recreation.gov campsite availability checker.

Hits the public web/booking endpoint used by recreation.gov itself:
  GET /api/camps/availability/campground/{facility_id}/month?start_date=YYYY-MM-01T00:00:00.000Z

Not the official RIDB API. May change, be rate-limited, or block aggressive polling.
Poll conservatively (>=1s between facilities) and cache locally.

Usage:
  python recreation_gov.py --date 2026-07-15
  python recreation_gov.py --date 2026-07-15 --nights 2
  python recreation_gov.py --date 2026-07-15 --facility 232450
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from collections import Counter
from urllib import parse, request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Curated WA campgrounds on recreation.gov.
# IDs from public recreation.gov URLs (/camping/campgrounds/{id}).
# Verify by running this script — stale IDs return empty data or wrong metadata.
WA_CAMPGROUNDS = [
    # North Cascades NP
    {"id": "255201",   "name": "Colonial Creek South", "park": "North Cascades NP", "region": "North Cascades"},
    {"id": "246855",   "name": "Colonial Creek North", "park": "North Cascades NP", "region": "North Cascades"},
    {"id": "234060",   "name": "Newhalem Creek",       "park": "North Cascades NP", "region": "North Cascades"},
    {"id": "246852",   "name": "Goodell Creek",        "park": "North Cascades NP", "region": "North Cascades"},
    # USFS Methow / Mazama (mostly first-come-first-served — API returns minimal data)
    {"id": "10314697", "name": "Klipchuck",      "park": "Okanogan-Wenatchee NF", "region": "Methow Valley"},
    {"id": "10314702", "name": "Lone Fir",       "park": "Okanogan-Wenatchee NF", "region": "Methow Valley"},
    {"id": "10314652", "name": "Early Winters",  "park": "Okanogan-Wenatchee NF", "region": "Methow Valley"},
    {"id": "10314602", "name": "Ballard",        "park": "Okanogan-Wenatchee NF", "region": "Methow Valley"},
    {"id": "10314682", "name": "Honeymoon",      "park": "Okanogan-Wenatchee NF", "region": "Methow Valley"},
    # Olympic NP / Mt Rainier NP — IDs need re-verification (some old ones returned stale data)
    {"id": "232464", "name": "Kalaloch",     "park": "Olympic NP",    "region": "Olympic Coast"},
    {"id": "232466", "name": "Cougar Rock",  "park": "Mt Rainier NP", "region": "Mt Rainier"},
    {"id": "232463", "name": "Mora",         "park": "Olympic NP",    "region": "Olympic Coast"},
]


def month_start(date: dt.date) -> str:
    return f"{date.year:04d}-{date.month:02d}-01T00:00:00.000Z"


def date_key(date: dt.date) -> str:
    return f"{date.year:04d}-{date.month:02d}-{date.day:02d}T00:00:00Z"


def fetch_month(facility_id: str, date: dt.date, timeout: float = 20.0) -> dict:
    url = (
        f"https://www.recreation.gov/api/camps/availability/campground/{facility_id}/month"
        f"?{parse.urlencode({'start_date': month_start(date)})}"
    )
    req = request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def check_facility(facility: dict, dates: list[dt.date]) -> dict:
    """Fetch one month per unique (year, month) the dates span, then filter."""
    months_needed = {(d.year, d.month) for d in dates}
    month_data: dict[tuple[int, int], dict] = {}
    for year, month in months_needed:
        anchor = dt.date(year, month, 1)
        try:
            month_data[(year, month)] = fetch_month(facility["id"], anchor)
        except Exception as exc:
            return {"facility": facility, "error": f"{type(exc).__name__}: {exc}", "sites": []}

    sites_status: list[dict] = []
    for target in dates:
        data = month_data[(target.year, target.month)]
        key = date_key(target)
        for site_id, site in (data.get("campsites") or {}).items():
            status = (site.get("availabilities") or {}).get(key)
            if not status:
                continue
            sites_status.append({
                "date": target.isoformat(),
                "site_id": site_id,
                "site": site.get("site"),
                "loop": site.get("loop"),
                "type": site.get("campsite_type"),
                "status": status,
            })

    return {"facility": facility, "sites": sites_status}


def summarize(result: dict, target_dates: list[dt.date]) -> str:
    f = result["facility"]
    head = f"{f['name']} ({f['park']}, {f['region']}) — id {f['id']}"
    if result.get("error"):
        return f"{head}\n  ERROR: {result['error']}"

    sites = result["sites"]
    lines = [head]
    for target in target_dates:
        day = [s for s in sites if s["date"] == target.isoformat()]
        if not day:
            lines.append(f"  {target}: no data (closed/out-of-season?)")
            continue
        counts = Counter(s["status"] for s in day)
        available = [s for s in day if s["status"] == "Available"]
        summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        lines.append(f"  {target}: total={len(day)}  {summary}")
        if available:
            sample = ", ".join(f"{s['loop'] or '?'}/{s['site'] or s['site_id']}" for s in available[:5])
            more = f" (+{len(available)-5} more)" if len(available) > 5 else ""
            lines.append(f"    Available sites: {sample}{more}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--date", required=True, help="Check-in date YYYY-MM-DD")
    p.add_argument("--nights", type=int, default=1, help="Number of consecutive nights to check (default 1)")
    p.add_argument("--facility", action="append", help="Only check this facility id (repeatable). Default: built-in WA list.")
    p.add_argument("--json", action="store_true", help="Emit raw JSON instead of human summary")
    p.add_argument("--delay", type=float, default=1.2, help="Seconds between facility requests (default 1.2)")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    start = dt.date.fromisoformat(args.date)
    dates = [start + dt.timedelta(days=i) for i in range(args.nights)]

    if args.facility:
        wanted_ids = set(args.facility)
        facilities = [f for f in WA_CAMPGROUNDS if f["id"] in wanted_ids]
        missing = wanted_ids - {f["id"] for f in facilities}
        for fid in missing:
            facilities.append({"id": fid, "name": f"<unknown {fid}>", "park": "?", "region": "?"})
    else:
        facilities = WA_CAMPGROUNDS

    results = []
    for i, facility in enumerate(facilities):
        if i:
            time.sleep(args.delay)
        results.append(check_facility(facility, dates))

    if args.json:
        print(json.dumps({"dates": [d.isoformat() for d in dates], "results": results}, indent=2))
    else:
        for r in results:
            print(summarize(r, dates))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
