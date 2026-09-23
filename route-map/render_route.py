#!/usr/bin/env python3
"""Render a static route map PNG and/or generate a Google Maps URL.

Usage:
    python3 render_route.py <config_json> <output_png>      # render PNG
    python3 render_route.py --gmap <config_json>            # print Google Maps URL (lat,lng)
    python3 render_route.py --gmap-names <config_json>      # print Google Maps URL (place names)

Config JSON schema:
{
  "title": "...",
  "size": [width, height],                       # optional, default [1200, 800]
  "waypoints": [
    {
      "lon": <float>, "lat": <float>,
      "label": <str>,
      "color": <hex>,                            # marker color
      "label_offset": [dx, dy],                  # optional, default [12, -10]
      "place": <str>                             # optional, used by --gmap-names
    },
    ...
  ],
  "segments": [
    {"indices": [i, j, ...], "color": <hex>, "width": <int>, "legend": <str>},
    ...
  ]
}
"""
import json
import sys
from urllib.parse import quote_plus


def render_png(cfg, out_path):
    from staticmap import StaticMap, CircleMarker, Line
    from staticmap.staticmap import _lon_to_x, _lat_to_y
    from PIL import Image, ImageDraw, ImageFont

    W, H = cfg.get("size", [1200, 800])
    title = cfg.get("title", "")
    waypoints = cfg["waypoints"]
    segments = cfg["segments"]

    m = StaticMap(
        W, H,
        padding_x=cfg.get("padding_x", 80),
        padding_y=cfg.get("padding_y", 80),
        url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
    )

    # Draw segments first (under markers)
    for seg in segments:
        coords = [(waypoints[i]["lon"], waypoints[i]["lat"]) for i in seg["indices"]]
        m.add_line(Line(coords, seg.get("color", "#cc0000"), seg.get("width", 4)))

    # Markers (colored outer + white inner)
    for wp in waypoints:
        m.add_marker(CircleMarker((wp["lon"], wp["lat"]), wp.get("color", "#cc0000"), 18))
        m.add_marker(CircleMarker((wp["lon"], wp["lat"]), "#ffffff", 8))

    img = m.render()
    draw = ImageDraw.Draw(img)

    # Fonts (try CJK-capable first)
    font = None
    title_font = None
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            font = ImageFont.truetype(path, 22)
            title_font = ImageFont.truetype(path, 28)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
        title_font = font

    zoom = m.zoom

    def to_px(lon, lat):
        x = _lon_to_x(lon, zoom)
        y = _lat_to_y(lat, zoom)
        px = (x - m.x_center) * 256 + W / 2
        py = (y - m.y_center) * 256 + H / 2
        return int(px), int(py)

    def text_with_halo(xy, text, fnt, fill="black", halo="white", halo_size=2):
        x, y = xy
        for dx in range(-halo_size, halo_size + 1):
            for dy in range(-halo_size, halo_size + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, font=fnt, fill=halo)
        draw.text((x, y), text, font=fnt, fill=fill)

    # Labels
    for wp in waypoints:
        px, py = to_px(wp["lon"], wp["lat"])
        ox, oy = wp.get("label_offset", [12, -10])
        text_with_halo((px + ox, py + oy), wp["label"], font)

    # Title
    if title:
        text_with_halo((20, 20), title, title_font)

    # Legend
    ly = H - 20 - 28 * len(segments)
    for seg in segments:
        legend = seg.get("legend")
        if not legend:
            continue
        draw.rectangle([20, ly, 60, ly + 18], fill=seg.get("color", "#cc0000"))
        text_with_halo((70, ly - 2), legend, font)
        ly += 28

    img.save(out_path)
    return out_path


def gmap_url(cfg, use_names=False):
    waypoints = cfg["waypoints"]
    if len(waypoints) < 2:
        raise ValueError("need at least 2 waypoints")

    def fmt(wp):
        if use_names and wp.get("place"):
            # Google Maps wants spaces as '+' and literal commas (NOT %2C / %20).
            # quote_plus encodes commas; replace them back to literals.
            return quote_plus(wp["place"]).replace("%2C", ",")
        return f"{wp['lat']},{wp['lon']}"

    origin = fmt(waypoints[0])
    # Loop trip: if user wants to return to start, they can repeat the first waypoint at end of segments;
    # for the URL we treat last waypoint as destination (not necessarily a loop).
    destination = fmt(waypoints[-1])
    middle = waypoints[1:-1]
    parts = [
        "https://www.google.com/maps/dir/?api=1",
        f"origin={origin}",
        f"destination={destination}",
        "travelmode=driving",
    ]
    if middle:
        parts.append("waypoints=" + "|".join(fmt(w) for w in middle))
    return "&".join(parts)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)

    if args[0] == "--gmap":
        cfg = json.load(open(args[1]))
        print(gmap_url(cfg, use_names=False))
        return
    if args[0] == "--gmap-names":
        cfg = json.load(open(args[1]))
        print(gmap_url(cfg, use_names=True))
        return

    if len(args) < 2:
        print("Usage: render_route.py <config_json> <output_png>")
        sys.exit(2)

    cfg = json.load(open(args[0]))
    out = render_png(cfg, args[1])
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
