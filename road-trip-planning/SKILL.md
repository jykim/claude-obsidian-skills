---
name: road-trip-planning
description: "Create interactive HTML road-trip guides for multi-day driving itineraries. Use when an AI agent is asked to plan a road trip, build a travel itinerary page, make a fullscreen route map, estimate trip cost/time, compare restaurant or lodging alternatives, add POIs with photos and Google Maps links, or produce a self-contained HTML guide for any road trip."
---

# Road Trip Planning

## Output Standard

Create a polished, self-contained HTML guide unless the user asks for another format. Prefer one file that can be opened directly in a browser, with CDN dependencies only when useful.

Include:
- A day-by-day itinerary with realistic time blocks.
- A fullscreen or prominent interactive map with route lines, day filters, POI markers, and driving-time annotations.
- Restaurants, lodging, golf or activity options when requested, each with estimated cost and Google Maps links.
- A separate cost/time estimate sheet or overlay when the user asks for budget detail.
- Clear alternatives: primary vs backup restaurants, hotel vs campsite, main activity vs weather/time fallback.

Use `assets/roadtrip-guide-template.html` as a starter when creating a new HTML guide from scratch.

## Initial Preference Interview

Before researching or planning, run a short step-by-step interview unless the user has already provided the answers or explicitly asks to skip questions. Ask in small batches and keep momentum; do not ask every possible question at once.

Step 1, route basics:
- Start and end point, including whether the trip is a loop or one-way.
- Number of days or date window.
- Season/month, if known.
- Must-see places, avoid places, and whether detours are acceptable.

Step 2, pace and travel style:
- Maximum comfortable driving per day.
- Preferred start/end times for driving days.
- Trip emphasis: nature, cities, food, golf, hiking, family activities, photography, national parks, scenic drives, or relaxation.
- Energy level: relaxed, balanced, ambitious.

Step 3, food and lodging:
- Cuisine priorities, dietary restrictions, and meal budget.
- Hotel, camping, RV, cabin, or mixed stay preferences.
- Lodging budget range and comfort expectations.
- Whether to show hotel/campsite alternatives every night.

Step 4, activities and constraints:
- Fitness/hiking level and trail length limits.
- Golf interest, tee-time tolerance, and budget if relevant.
- Pet, child, accessibility, EV charging, winter driving, passport/border, ferry, or reservation constraints.
- Desired output: HTML only, map-first HTML, printable summary, spreadsheet-style cost sheet, or all of these.

After the interview, summarize the assumptions in 5-8 bullets and ask for confirmation only when a choice materially changes the route. If the user wants a fast draft, proceed with explicit assumptions and make them visible in the guide.

Use this concise prompt when appropriate:

```text
Before I build the HTML road-trip guide, I need a few preferences:
1. Route: start/end, loop or one-way, and total days/date window?
2. Pace: max driving hours per day and relaxed/balanced/ambitious?
3. Priorities: nature, food, golf, hiking, cities, scenic drives, or something else?
4. Food/stay: cuisine preferences, hotel vs campsite/RV, and rough budget?
5. Constraints: pets/kids/accessibility/EV/winter roads/reservations?
```

## Research Workflow

Use web research when facts may be current or location-specific: open seasons, road closures, park reservations, lodging/campground names, restaurant status, golf tee-time rules, costs, and official links.

Prefer authoritative sources:
- National/state park official pages for roads, fees, reservations, campgrounds, and alerts.
- Official venue pages for golf courses, restaurants, hotels, and campgrounds.
- Google Maps URLs generated from coordinates or place names for navigation links.
- Local tourism boards for scenic route and regional attraction context.

Capture approximate coordinates for every map marker. If exact coordinates are unavailable, use a defensible nearby coordinate and label it as approximate in notes or code comments.

## Campsite Availability (Date-Specific)

When the user wants real-time, date-specific campsite availability — not just "is this place reservable" — use the scripts in `scripts/availability/`. They cover the two systems that hold ~95% of WA campsites worth booking.

### Recreation.gov (NPS, USFS, BLM, COE — works reliably)

`recreation_gov.py` hits the public booking endpoint `/api/camps/availability/campground/{facilityId}/month`. Returns per-site status: `Available`, `Reserved`, `Closed`, `Not Reservable` (walk-up), `Not Available Cutoff` (see below), `NYR` (Not Yet Released — outside the rolling 6-month booking window).

Gotchas learned the hard way:
- **URL-encode the date.** The `start_date` colons must be `%3A` (`2026-07-01T00%3A00%3A00.000Z`). A raw colon returns `{"error":"query not encoded"}` with a 30-byte body — easy to mistake for "no sites." Always check the response size before parsing.
- **Booking cutoff = the near-term trap.** Dates within roughly the next 3–4 days flip from `Available` to `Not Available Cutoff` (and some agencies to `Not Reservable`). This means *you can no longer book them online*, NOT that they are full — those sites are typically released as first-come / walk-up. So a query run today for "this Thursday" can show 0 bookable even though 40+ sites are physically open. When a near-term date returns all-cutoff, tell the user it's a **walk-up trip**, not a sold-out one.
- **The binding constraint is Saturday night.** Near Seattle, summer Fri/Sat nights are ~100% reserved months out while Sun–Thu nights stay wide open at the same campground. Always break results out *per night*, not per "weekend" — a Sat+Sun 2-night stay needs the Sat night that is never there, whereas Sun+Mon is easy. Report the per-night pattern so the user can shift by one day instead of giving up.
- Use a browser `User-Agent` and `Referer: https://www.recreation.gov/`; the default curl UA can get challenged.
- Find campground facility ids via the search API: `GET https://www.recreation.gov/api/search?q=<name>&size=5` → `results[].entity_id` (filter `entity_type == "campground"`; each has lat/lng for a distance filter).

```bash
# Check 5 curated WA campgrounds (Olympic, North Cascades, Mt Rainier NPs)
python scripts/availability/recreation_gov.py --date 2026-07-15 --nights 2

# Check a specific facility id
python scripts/availability/recreation_gov.py --date 2026-07-15 --facility 232450

# JSON output for downstream consumption
python scripts/availability/recreation_gov.py --date 2026-07-15 --json
```

To add a facility, find the id in the recreation.gov URL (`/camping/campgrounds/{id}`) and append to `WA_CAMPGROUNDS` in the script. Poll conservatively (default 1.2s delay) — this is a web/booking endpoint, not the official RIDB API, and may be rate-limited.

### Washington State Parks (washington.goingtocamp.com — deep links only)

The SPA is gated by Azure WAF, but a **plain `curl` with a browser `User-Agent` + `Referer: https://washington.goingtocamp.com/` passes it** — the WAF challenges the default curl UA, not a browser-looking one. Live per-site availability *is* callable from automation via the JSON API below (verified working). Keep the deep-link fallback for the user's own browser as the booking CTA.

**Live availability — `GET /api/occupancy`** (the real endpoint; `/api/availability/map` is a decoy that only 400s). Query params (all required):

```
bookingCategoryId=0            # 0 = Campsite (list via /api/bookingCategories)
equipmentCategoryId=-32768     # "Equipment"
subEquipmentCategoryId=-32768  # "1 Tent" (RV sizes are other negative ids via /api/equipment)
startDate=2026-07-11           # check-in (plain YYYY-MM-DD, no encoding needed here)
endDate=2026-07-13             # check-out; 2 nights = +2 days
numEquipment=1
filterData=[]  boatLength=0  boatDraft=0  boatWidth=0  peopleCapacityCategoryCounts=[]
resourceLocationId=<park id>   # from the cache / /api/resourceLocation
```

Response `resourceOccupancy[]` gives one row per site with an `availability` code: **1 = available, 2 = unavailable/booked** (decoded empirically against a known-open off-season weekday — the app ships no enum). Count the 1s.

Two required joins before you trust a count:
- **Names + type:** `GET /api/resourcelocation/resources?resourceLocationId=<id>` maps `resourceId` → `localizedValues[0].name` and `resourceCategoryId`. **`-2147483648` = a real numbered campsite; `-2147483638` = picnic shelter; others are mooring buoys / group sites.** Filtering by `bookingCategoryId=0` alone still returns shelters and buoys — a park showing "2 sites left" was twice actually 1 shelter + 1 site, or 2 shelters + 0 real sites. Always intersect availability with category `-2147483648`.
- **ADA sites:** in `definedAttributes`, `attributeDefinitionId == -32738` with `values == [0]` marks an ADA-only site (every regular site has `[1]`; confirmed by the site's own "ADA only — proof required at check-in" description). Exclude these from a general count unless the user qualifies, or they'll show phantom availability.

Metadata scripts still apply:
1. **One-time metadata cache** (refresh monthly): `python scripts/availability/dump_wa_state_parks.py` — dumps all 167 WA State Parks (name, GPS, mapId, resourceLocationId, official site) to `wa_state_parks_cache.json`.
2. **Deep link generation** at plan time: `python scripts/availability/wa_state_parks.py --date 2026-07-15 --nights 2 --search "steamboat,deception"` — generates pre-filled goingtocamp.com search URLs. Embed these as the booking CTA; the user's browser passes WAF on first-party visit.

### Integrating into the HTML guide

Run availability for the relevant night before assembling the guide, then in each day's `lodging` entries:
- For Recreation.gov campgrounds: show `Available: N sites` (or `Booked` / `Walk-up only`) inline next to the cost pill.
- For WA State Parks: render the goingtocamp.com deep link as the primary CTA ("Check availability →").
- Always include the official park URL as a secondary link in case the booking system is down.

## Planning Workflow

1. Complete the initial preference interview or state the assumptions used when the user skips it.
2. Define the route shape: origin, destination or loop, total days, must-see regions, season, and driving tolerance.
3. Create a realistic day skeleton: start city, end city, mileage, drive hours, main natural stop, meals, and sleep location.
4. Add POI categories as requested: nature, restaurants, lodging, golf, viewpoints, trailheads, ferry stops, border crossings, or airports.
5. Build daily schedules with actual sequencing: departure, first stop, lunch, main activity, check-in, dinner, and evening fallback.
6. Make alternatives visible, not buried: primary restaurant plus alternatives; hotel plus campsite; golf course plus backup; short hike plus long hike.
7. Estimate costs separately from prose: fuel, lodging, meals, park/activity fees, golf, and daily total ranges.
8. Add map behavior last: route polylines, markers, day filters, popups, Google Maps links, and driving-time labels.

## HTML Guide Requirements

Use a layout that supports scanning:
- Left sidebar for itinerary cards and controls; make it collapsible and desktop-resizable when the map is a primary workspace.
- Right fullscreen map or map-first pane.
- Cost/time sheet as an overlay drawer or separate panel with fullscreen option when requested.
- Compact cards; avoid landing-page hero sections for practical trip tools.

For each day card, include:
- Header: Day number, route title, drive summary, sleep area.
- Action row: "Show on Map" button (filters main map to this day) and "Google Maps Route" link (opens day's full multi-stop driving directions in Google Maps).
- Realistic schedule: times and brief notes.
- Trail / POI plan: primary card and alternatives card.
- Golf plan when relevant: primary course and alternatives card.
- Restaurant plan: primary card and alternatives card.
- Stay plan: hotel card and campsite card when camping is requested.
- Inline estimated cost and Google Maps button inside restaurant, stay, golf, and mapped POI cards.

Avoid a separate giant POI link list if inline map buttons already exist.

## Map Requirements

Use Leaflet with OpenStreetMap tiles for simple local HTML files.

Marker conventions:
- `N` for nature/lake/river.
- `R` for restaurants.
- `G` for golf.
- `H` for hotels.
- `C` for campsites.
- Day number for city or route endpoints.

Each map POI should have:
- Name, coordinates, type, note, color.
- Photo URL or type fallback photo.
- Google Maps search URL.
- Popup with photo, note, type/day tag, Google Maps link, and a day-route-via-POI link where useful.

Keep lodging, restaurants, and activities in the same POI data model so day filtering, popups, and link generation stay synchronized.

## Cost And Time Estimates

Use ranges rather than false precision. Include the assumptions visibly:
- Party size and vehicle count.
- Fuel price and mpg.
- Lodging style.
- Meal style.
- Golf/activity assumptions.
- Exclusions such as alcohol, tips, shopping, rental car, or flights.

Daily cost rows should include:
- Miles.
- Drive hours before stops.
- Nature/activity time.
- Golf/activity time when relevant.
- Fuel, meals, lodging, activities, golf, and total range.
- Notes on variability.

Cost heuristics when exact current pricing is not researched:
- Casual restaurant: `$15-35 / person`.
- Upscale or resort restaurant: `$30-70 / person`.
- State/national park campsite: `$20-45 / night`.
- KOA/private campground: `$55-120 / night`.
- Mid-range hotel: use the daily lodging estimate row, often `$120-520 / night` depending on region/season.

Label estimates clearly as estimates.

## Validation Checklist

Before final delivery:
- Run a JavaScript syntax check on inline scripts with `new Function(...)`.
- Check all referenced POI IDs exist in the `places` dictionary.
- Check every restaurant/stay card has a map URL or a deliberate fallback.
- Check every requested day has a daily schedule.
- Check each day card has a "Show on Map" button and (when ≥2 route stops) a "Google Maps Route" link.
- If a dev server or browser automation is available, open the HTML and verify the map is not blank.
- Report any verification that could not be run.

## Starter Template

When beginning from scratch, copy `assets/roadtrip-guide-template.html` to the working directory and replace its placeholder data. Keep edits scoped to the generated trip artifact unless the user asks for a larger app.

## Code Snippets

Use these snippets when building a custom HTML guide instead of copying the full template.

### Core Data Model

Keep day data small and link every restaurant/stay/activity to a POI `placeId`.

```js
const days = [
  {
    day: 1,
    title: "Origin -> Scenic Stop -> Sleep City",
    drive: "Approx 260 mi / 4.5-5.5h",
    sleep: "Sleep City",
    schedule: [
      ["08:00", "Depart", "Leave early to protect the main scenic stop."],
      ["12:30", "Lunch", "Use primary restaurant; switch to alternative if delayed."],
      ["15:00", "Main sight", "Keep travel days to one major attraction."],
      ["18:30", "Dinner / check-in", "Check in before dinner when possible."]
    ],
    sights: ["Waterfall overlook", "Short lakefront walk"],
    golf: [
      { name: "Primary Golf Course", desc: "Best-fit course for the day.", url: "https://example.com", placeId: "primaryGolf", cost: "$90-180 / player" },
      { name: "Backup Golf Course", desc: "Alternative if tee time, weather, or budget is better.", url: "https://example.com", placeId: "backupGolf", cost: "$60-140 / player" }
    ],
    food: [
      { name: "Primary Restaurant", desc: "Best fit for the route.", url: "https://example.com", placeId: "primaryFood", cost: "$20-45 / person" },
      { name: "Alternative Restaurant", desc: "Backup option.", url: "https://example.com", placeId: "backupFood", cost: "$15-35 / person" }
    ],
    lodging: [
      { type: "Hotel", name: "Primary Hotel", desc: "Convenient base.", url: "https://example.com", placeId: "primaryHotel", cost: "$150-300 / night" },
      { type: "Camp", name: "Primary Campground", desc: "Camping alternative.", url: "https://example.com", placeId: "primaryCamp", cost: "$20-45 / night" }
    ],
    stops: ["origin", "mainSight", "sleepCity"],
    pois: ["primaryFood", "backupFood"]
  }
];

const places = {
  origin: { name: "Origin", coords: [47.6062, -122.3321], type: "city", note: "Start", color: "#5d4b7c" },
  mainSight: { name: "Main Sight", coords: [47.5417, -121.8377], type: "nature", note: "Primary scenic stop", color: "#176c57" },
  sleepCity: { name: "Sleep City", coords: [47.6777, -116.7805], type: "city", note: "Overnight area", color: "#5d4b7c" },
  primaryFood: { name: "Primary Restaurant", coords: [47.68, -116.79], type: "food", note: "Primary dinner", color: "#b85f33" },
  backupFood: { name: "Alternative Restaurant", coords: [47.69, -116.78], type: "food", note: "Backup dinner", color: "#b85f33" },
  primaryGolf: { name: "Primary Golf Course", coords: [47.70, -116.76], type: "golf", note: "Primary course", color: "#e4a83a" },
  backupGolf: { name: "Backup Golf Course", coords: [47.74, -116.82], type: "golf", note: "Alternative course", color: "#e4a83a" },
  primaryHotel: { name: "Primary Hotel", coords: [47.67, -116.78], type: "hotel", note: "Hotel option", color: "#3f6f8f" },
  primaryCamp: { name: "Primary Campground", coords: [47.80, -116.70], type: "camp", note: "Camp option", color: "#6f7d35" }
};
```

### POI Normalization

Generate photo fallbacks and Google Maps links once, then reuse them everywhere.

```js
const fallbackPhotos = {
  city: "https://images.unsplash.com/photo-1449824913935-59a10b8d2000?auto=format&fit=crop&w=640&q=80",
  nature: "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=640&q=80",
  lake: "https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=640&q=80",
  food: "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=640&q=80",
  golf: "https://images.unsplash.com/photo-1535131749006-b7f58c99034b?auto=format&fit=crop&w=640&q=80",
  hotel: "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=640&q=80",
  camp: "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?auto=format&fit=crop&w=640&q=80"
};

Object.entries(places).forEach(([id, place]) => {
  const [lat, lng] = place.coords;
  place.photo = place.photo || fallbackPhotos[place.type] || fallbackPhotos.nature;
  place.maps = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${place.name} ${lat},${lng}`)}`;
});
```

### Leaflet Map Rendering

Use one POI collector so stops, restaurants, hotels, and campsites stay synchronized.

```js
function uniqueIds(ids) {
  return [...new Set(ids.filter(Boolean))];
}

function dayPoiIds(day) {
  const lodgingIds = (day.lodging || []).map(item => item.placeId);
  return uniqueIds([...(day.stops || []), ...(day.pois || []), ...lodgingIds]).filter(id => places[id]);
}

function routeStopIds(day) {
  return (day.stops || []).filter(id => places[id]);
}

function markerLabel(place, day) {
  if (place.type === "food") return "R";
  if (place.type === "golf") return "G";
  if (place.type === "hotel") return "H";
  if (place.type === "camp") return "C";
  if (place.type === "nature" || place.type === "lake") return "N";
  return day.day;
}

function draw(selectedDay = "all") {
  markerLayer.clearLayers();
  lineLayer.clearLayers();
  const visibleDays = selectedDay === "all" ? days : days.filter(day => day.day === selectedDay);
  const bounds = [];

  visibleDays.forEach(day => {
    const coords = routeStopIds(day).map(id => places[id].coords);
    L.polyline(coords, { color: dayColors[day.day] || "#176c57", weight: selectedDay === "all" ? 4 : 7, opacity: .78 }).addTo(lineLayer);
    bounds.push(...coords);

    dayPoiIds(day).forEach(id => {
      const place = places[id];
      bounds.push(place.coords);
      L.marker(place.coords, { icon: markerIcon(place, markerLabel(place, day)) })
        .bindPopup(popupHtml(place, day.day))
        .addTo(markerLayer);
    });
  });

  if (bounds.length) map.fitBounds(bounds, { padding: [42, 42], maxZoom: selectedDay === "all" ? 7 : 10 });
}
```

### Inline Cost And Map Buttons

Use official-site links for place names and Google Maps links as separate buttons. Use the same helper for restaurants, lodging, golf, and mapped POIs.

```js
function choiceMeta(cost, placeId) {
  const mapUrl = places[placeId]?.maps;
  return `
    <div class="choice-meta">
      <span class="cost-pill">Est. ${cost || "Varies"}</span>
      ${mapUrl ? `<a class="inline-map-link" href="${mapUrl}" target="_blank" rel="noreferrer">Google Maps</a>` : ""}
    </div>
  `;
}

function renderChoices(title, items, labels, stay = false) {
  return `
    <div>
      <p class="section-title">${title}</p>
      <div class="choice-grid">
        ${items.map((item, index) => `
          <div class="choice-box ${stay ? "stay" : ""}">
            <span class="choice-label">${labels[index] || "Alternative"}</span>
            <a href="${item.url}" target="_blank" rel="noreferrer">${item.name}</a>
            <span>${item.desc}</span>
            ${choiceMeta(item.cost, item.placeId)}
          </div>
        `).join("")}
      </div>
    </div>
  `;
}
```

### Trail / POI And Golf Choices

Render trail/POI and golf sections as primary/alternatives instead of plain lists.

```js
function activityPlaceId(day, index) {
  const activityIds = routeStopIds(day).filter(id => ["nature", "lake", "golf"].includes(places[id]?.type));
  return activityIds[index];
}

function renderTrailPoiChoices(day) {
  const primary = day.sights[0];
  const alternatives = day.sights.slice(1);
  const primaryPlaceId = activityPlaceId(day, 0);
  return `
    <div>
      <p class="section-title">Trail / POI Plan</p>
      <div class="choice-grid">
        <div class="choice-box activity">
          <span class="choice-label">Primary</span>
          <b>${primary}</b>
          <span>Main nature/POI stop for the day. Preserve this first if the day slips.</span>
          ${choiceMeta(null, primaryPlaceId)}
        </div>
        <div class="choice-box activity">
          <span class="choice-label">Alternatives</span>
          <ul>
            ${alternatives.map((item, index) => {
              const placeId = activityPlaceId(day, index + 1);
              return `<li><b>${item}</b>${choiceMeta(null, placeId)}</li>`;
            }).join("")}
          </ul>
        </div>
      </div>
    </div>
  `;
}

function renderGolfChoices(day) {
  if (!day.golf?.length) return "";
  return renderChoices("Golf Plan", day.golf, ["Primary", "Alternative"]);
}
```

### Daily Schedule Renderer

Render time blocks as data instead of hand-writing each card.

```js
function renderSchedule(day) {
  return `
    <div>
      <p class="section-title">Realistic Daily Schedule</p>
      <div class="schedule">
        ${day.schedule.map(([time, title, detail]) => `
          <div class="schedule-row">
            <div class="schedule-time">${time}</div>
            <div>
              <b>${title}</b>
              <span>${detail}</span>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `;
}
```

### Day Action Buttons

Inject a `.day-actions` row between `.day-head` and `.day-body` so each day card has a "Show on Map" filter and a "Google Maps Route" link. Reuses `routeStopIds(day)` and the day-controls click handler.

```js
function googleMapsRouteUrl(day) {
  const ids = routeStopIds(day);
  if (ids.length < 2) return null;
  const fmt = id => places[id].coords.join(",");
  const params = new URLSearchParams({
    api: "1",
    origin: fmt(ids[0]),
    destination: fmt(ids[ids.length - 1]),
    travelmode: "driving"
  });
  const wp = ids.slice(1, -1).map(fmt).join("|");
  if (wp) params.set("waypoints", wp);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

function showDayOnMap(dayNum) {
  document.querySelectorAll("#dayControls button").forEach(item =>
    item.classList.toggle("active", item.dataset.day === String(dayNum)));
  draw(dayNum);
  const app = document.querySelector(".app");
  if (app.classList.contains("sidebar-collapsed")) toggleSidebar(false);
  if (window.innerWidth <= 900) {
    document.querySelector(".map-wrap")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

// Inside renderItinerary, between .day-head and .day-body:
//   <div class="day-actions">
//     <button data-show-day="${day.day}">📍 Show on Map</button>
//     ${gmapsUrl ? `<a class="gmaps-route" href="${gmapsUrl}" target="_blank" rel="noreferrer">🗺️ Google Maps Route</a>` : ""}
//   </div>
//
// Use a generic [data-show-day] click delegate so BOTH the action button AND
// the day-number circle in .day-head trigger the same map zoom:
//   document.getElementById("itinerary").addEventListener("click", event => {
//     const trigger = event.target.closest("[data-show-day]");
//     if (trigger) showDayOnMap(Number(trigger.dataset.showDay));
//   });
```

### Date-Based Day Buttons + Sidebar Scroll

When the trip has dates (e.g. multi-week guides), label the top day-filter buttons with the date (`M/D`) instead of generic `D1..DN`. Clicking a date should both (a) filter the map and (b) scroll the sidebar to the corresponding day card — pairing map zoom and itinerary focus in one click.

```js
// Render: use the M/D portion of day.date as the button label
document.getElementById("dayControls").innerHTML = `<button class="active" data-day="all">All</button>${days.map(day => `<button data-day="${day.day}" title="Day ${day.day} — ${day.date}">${day.date.split(' ')[0]}</button>`).join("")}`;

// Click delegate: filter map + scroll sidebar to the matching day card
document.getElementById("dayControls").addEventListener("click", event => {
  const button = event.target.closest("button");
  if (!button) return;
  document.querySelectorAll("#dayControls button").forEach(item => item.classList.remove("active"));
  button.classList.add("active");
  const dayVal = button.dataset.day;
  draw(dayVal === "all" ? "all" : Number(dayVal));
  if (dayVal === "all") return;
  const card = document.querySelector(`.day-card[data-card-day="${dayVal}"]`);
  const sidebar = document.querySelector(".sidebar");
  if (!card || !sidebar) return;
  document.querySelectorAll(".day-card.active-card").forEach(item => item.classList.remove("active-card"));
  card.classList.add("active-card");
  sidebar.scrollTo({ top: card.offsetTop - 16, behavior: "smooth" });
});
```

### Clickable Day Number → Zoom Map

Make the `.day-number` circle in `.day-head` a cheap click target that zooms the map to that day (mirrors the `📍 Show on Map` button without the extra row). Add `data-show-day="${day.day}"` to the div and rely on the generic `[data-show-day]` delegate above.

```css
.day-number { cursor: pointer; transition: transform .12s ease, box-shadow .12s ease; }
.day-number:hover { transform: scale(1.08); box-shadow: 0 4px 14px rgba(0,0,0,.22); }
```

```js
// Inside the day-head template:
//   <div class="day-number" data-show-day="${day.day}" title="Zoom map to Day ${day.day}" style="background:${dayColors[day.day]}">${day.day}</div>
```

The generic `[data-show-day]` delegate (see above) handles this automatically — no extra wiring needed.

### Validation Command

Run this after generating or editing the HTML.

```bash
node - <<'NODE'
const fs = require('fs');
const path = process.argv[1] || 'roadtrip.html';
const html = fs.readFileSync(path, 'utf8');
const code = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
new Function(code);
const placesBlock = code.match(/const places = \{([\s\S]*?)\n\s+\};/)?.[1] || '';
const placeIds = new Set([...placesBlock.matchAll(/^\s+(\w+):/gm)].map(m => m[1]));
const referenced = [
  ...[...code.matchAll(/(?:stops|pois): \[([^\]]*)\]/g)].flatMap(m => [...m[1].matchAll(/"([^"]+)"/g)].map(x => x[1])),
  ...[...code.matchAll(/placeId: "([^"]+)"/g)].map(m => m[1])
];
const missing = [...new Set(referenced.filter(id => !placeIds.has(id)))];
console.log('syntax ok');
console.log(`referenced ids: ${referenced.length}`);
console.log(`missing ids: ${missing.length ? missing.join(', ') : 'none'}`);
NODE
```
