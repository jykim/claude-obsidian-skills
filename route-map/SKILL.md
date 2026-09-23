---
name: route-map
description: Render a static route map (PNG) from a list of waypoints with colored route segments, markers, and labels. Use OpenStreetMap tiles (no API key). Also generate a Google Maps directions URL for the same route. Use when a user asks for a trip/route map, travelog map, or route overlay image.
allowed-tools:
  - Read
  - Write
  - Bash
license: MIT
---

# Route Map Skill

Render a static route map as PNG with multi-segment routes, markers, and labels — using OpenStreetMap tiles via the `staticmap` Python library (no API key needed). Also produces a Google Maps directions URL for the same route.

## When to Use

- User asks for a route map, travelog map, or "map with route overlaid"
- User wants a static image of a multi-stop trip for embedding in markdown
- User wants a Google Maps URL to open the same route in their browser/phone

## Prerequisites

- Python 3 with `staticmap` and `Pillow` packages
  - Install: `pip install staticmap pillow`

## How to Render

### Step 1: Define waypoints

Each waypoint is `(lon, lat, label, color)`. Group waypoints into segments — each segment becomes a colored polyline. A segment is just a list of waypoints in order.

Useful color palette:
- Day 1 / outbound: `#0066cc` (blue)
- Day 2 / main loop: `#cc3300` (red)
- Return leg: `#999999` (gray)
- Optional Day 3: `#2e8b57` (green)

### Step 2: Run the renderer

```bash
python3 <skill-dir>/render_route.py <config_json> <output_png>
```

Where `<config_json>` is a JSON file like:

```json
{
  "title": "2026-05-02~03  Eastern Washington Trip",
  "size": [1200, 800],
  "waypoints": [
    {"lon": -122.1936, "lat": 47.6135, "label": "Bellevue", "color": "#2c7fb8", "label_offset": [14, -10]},
    {"lon": -119.9880, "lat": 46.9540, "label": "Vantage", "color": "#41b6c4", "label_offset": [14, 10]},
    {"lon": -119.2805, "lat": 47.1311, "label": "Moses Lake", "color": "#f03b20", "label_offset": [14, 8]},
    {"lon": -119.3675, "lat": 47.5910, "label": "Dry Falls", "color": "#e31a1c", "label_offset": [14, -28]},
    {"lon": -118.9867, "lat": 47.9595, "label": "Grand Coulee Dam", "color": "#6a3d9a", "label_offset": [14, -10]}
  ],
  "segments": [
    {"indices": [0, 1, 2], "color": "#0066cc", "width": 5, "legend": "Day 1 (5/2)  Bellevue → Vantage → Moses Lake"},
    {"indices": [2, 3, 4],    "color": "#cc3300", "width": 5, "legend": "Day 2 (5/3)  Moses Lake → Dry Falls → Grand Coulee Dam"},
    {"indices": [4, 0],       "color": "#999999", "width": 3, "legend": "Return       Grand Coulee → Bellevue (~220 mi)"}
  ]
}
```

`indices` references the `waypoints` array in order. `label_offset` is the pixel offset for the label relative to the marker (defaults to `(12, -10)`).

### Step 3: Embed and link

Embed the PNG in the travelog (Obsidian wiki link):

```markdown
![[_files_/<filename>.png|720]]
```

Save the PNG under `Projects/Travelog/_files_/` (or the relevant `_files_/` folder for the document).

### Step 4: Generate Google Maps URL

Run the helper:

```bash
python3 <skill-dir>/render_route.py --gmap <config_json>
```

Outputs a Google Maps directions URL using `lat,lng` coordinates. Example:

```
https://www.google.com/maps/dir/?api=1&origin=47.6135,-122.1936&destination=47.6135,-122.1936&travelmode=driving&waypoints=46.954,-119.988|47.1311,-119.2805|47.591,-119.3675|47.9595,-118.9867
```

The URL form uses raw `lat,lng` so it's robust against geocoding ambiguity. If origin and destination point to the same place, Maps treats the trip as a loop.

You can also pass `--gmap-names` to use place names — the JSON entries should include an optional `place` field (e.g. `"place": "Wild Horse Monument, WA"`). The helper uses `+` for spaces and literal commas (NOT `%2C` / `%20`) — Google Maps will reject double-encoded values like `Bellevue%2C%20WA`, showing them as a literal search string instead of resolving to the place.

### Where to put the Google Maps link in markdown

**Default: place the link BELOW the metadata table, not inside a table cell.** The waypoint separator is `|`, which is also the markdown table-cell separator — a raw `|` inside a table cell silently breaks the table layout. Putting the link in its own paragraph or bullet list under the table sidesteps the entire encoding question.

Recommended pattern at the end of a travelog:

```markdown
## 메타데이터

| 항목 | 내용 |
|------|------|
| 기간 | ... |
| 거리 | ... |

**경로**: [Google Maps에서 열기](https://www.google.com/maps/dir/?api=1&origin=Bellevue,+WA&...&waypoints=Wild+Horse+Monument,+WA%7CMoses+Lake,+WA%7C...)
```

Even outside a table, encode `|` as `%7C` in the markdown URL portion. Some markdown renderers (Obsidian preview included) treat a literal `|` inside `[...](...)` as a hint to start parsing a table on the surrounding lines, which can produce surprising layout. `%7C` is universally safe. Spaces in place names should stay as `+` — do not let your editor re-encode them to `%20`.

**Default to one link, named-places only.** The named-places URL (`--gmap-names`) is what readers want — it shows recognizable destinations in the Google Maps UI. Skip the coordinate-based URL unless the named one fails to geocode (rare for major landmarks); a single link is cleaner than two near-duplicate links.

## Tips

- Padding: the script uses `padding_x=80, padding_y=80` so labels near the edge don't get clipped. Increase for very wide labels.
- Tile source: `https://a.tile.openstreetmap.org/{z}/{x}/{y}.png` — for heavy reuse, switch to a self-hosted or commercial tile provider per OSM tile usage policy.
- Korean labels: Pillow needs a CJK-capable font. The script tries `Apple SD Gothic Neo` then falls back to default.
- Marker style: each waypoint gets a colored outer circle + white inner dot, so it stays visible on any base map.

## Limitations

- Routes are drawn as straight polylines, not actual road geometry. For real road geometry, use the OSRM API to get a polyline and pass that as the `indices` segment (future enhancement).
- No automatic legend placement — bottom-left fixed. For very dense base maps, that area may be unreadable; in that case, render to a larger canvas or move the legend.

## Troubleshooting

- `ImportError: cannot import name '_lon_to_x' from 'staticmap'`: import path is `from staticmap.staticmap import _lon_to_x, _lat_to_y` — already handled in the renderer.
- Labels overlap markers: tune `label_offset` per waypoint in the JSON.
- Tiles look low-res: increase canvas size; staticmap auto-picks a higher zoom level for larger output.
