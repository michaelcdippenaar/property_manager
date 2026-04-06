# Stellenbosch Property Intel

Full 6-phase intelligence pipeline for Winelands properties (Stellenbosch, Paarl,
Franschhoek, Somerset West, Strand). Collects from 8 portals, enriches with Google
Street View, vectorizes, deduplicates cross-site, classifies via Claude Vision, and
exports to Google Maps.

## When to Use This Skill

- Looking up a specific property (e.g. "1 Bosch-en-Dal, Karindal")
- Running a market scan for Stellenbosch / Winelands
- Finding duplicate listings across portals
- Classifying properties by type, condition, architectural style
- Generating a Google Maps plot of available properties
- Phrases: "winelands intel", "market scan", "property map", "cross-site duplicates",
  "karindal", "bosch-en-dal", "classify properties"

## Areas & Sources

| Area slug      | Display name  |
|----------------|---------------|
| stellenbosch   | Stellenbosch  |
| paarl          | Paarl         |
| franschhoek    | Franschhoek   |
| somerset_west  | Somerset West |
| strand         | Strand        |

Sources: property24, private_property, gumtree, iol_property, rentfind, pam_golding, seeff, facebook

---

## Phase 0 — Single Property Lookup (POC)

Use this when given a specific address like "1 Bosch-en-Dal, Karindal, Stellenbosch".

### Step 1: Check if it's already in the DB

```python
# Django shell
from apps.market_data.models import MarketListing
results = MarketListing.objects.filter(
    area="stellenbosch",
    raw_address__icontains="karindal"
)
print(f"{results.count()} listings found")
for l in results:
    print(f"  [{l.source}] {l.raw_address} — {l.listing_type} R{l.active_price}")
```

### Step 2: Scrape Stellenbosch if not found

```bash
cd backend
python manage.py scrape_winelands --area=stellenbosch
```

### Step 3: Geocode the address (if no coordinates)

```python
from apps.market_data.services.google_maps import GoogleMapsService
import requests

api_key = "YOUR_GOOGLE_MAPS_API_KEY"
resp = requests.get(
    "https://maps.googleapis.com/maps/api/geocode/json",
    params={"address": "1 Bosch-en-Dal Karindal Stellenbosch", "key": api_key}
)
result = resp.json()["results"][0]
lat = result["geometry"]["location"]["lat"]
lng = result["geometry"]["location"]["lng"]
print(f"Coords: {lat}, {lng}")
# Expected: approx -33.93xx, 18.84xx
```

### Step 4: Fetch Street View

```python
from apps.market_data.services.google_maps import GoogleMapsService

svc = GoogleMapsService()
# Fetch from 4 headings for full coverage
for heading in [0, 90, 180, 270]:
    jpeg, status = svc.fetch_street_view(lat, lng, heading=heading, size="640x640")
    if jpeg:
        with open(f"/tmp/sv_{heading}.jpg", "wb") as f:
            f.write(jpeg)
        print(f"heading={heading}: {len(jpeg)} bytes")
```

### Step 5: Classify with Claude Vision

```python
from apps.market_data.services.property_classifier import PropertyClassifier

classifier = PropertyClassifier()

# From saved listing
listing = MarketListing.objects.filter(area="stellenbosch").select_related("street_view").first()
result = classifier.classify_from_street_view(listing)
print(result)

# From raw bytes (no listing needed)
jpeg, status = svc.fetch_street_view(lat, lng)
result = classifier.classify_from_bytes(jpeg)
print(result)
# Example: {"property_type": "house", "condition": "well-maintained",
#            "style": "cape-dutch", "confidence": 0.87, "reasoning": "..."}
```

### Step 6: Find it on other portals (cross-site)

```python
from apps.market_data.services.cross_site_matcher import find_cross_site_duplicates

groups = find_cross_site_duplicates(area="stellenbosch", commit=False)
# Filter groups near the target coords
target_lat, target_lng = -33.93, 18.84
from apps.market_data.services.cross_site_matcher import _haversine_m
nearby = [
    g for g in groups
    if g["listing_a"].latitude and _haversine_m(g["listing_a"].latitude, g["listing_a"].longitude, target_lat, target_lng) < 200
]
for g in nearby:
    a, b = g["listing_a"], g["listing_b"]
    print(f"[{g['score']:.2f}] {a.source}: {a.source_url}")
    print(f"         {b.source}: {b.source_url}")
```

### Step 7: View on map

```
GET /api/v1/market-data/map-export/?area=stellenbosch
```

---

## Phase 1 — Full Winelands Scrape

```bash
cd backend

# All 5 areas × 8 sources × rent + sale
python manage.py scrape_winelands

# Single area
python manage.py scrape_winelands --area=stellenbosch

# Single source (faster, for testing)
python manage.py scrape_winelands --area=stellenbosch --source=property24

# Dry run
python manage.py scrape_winelands --dry-run
```

Check results:
```python
from apps.market_data.models import ScrapeRun, WINELANDS_AREAS
runs = ScrapeRun.objects.filter(
    area__in=[a.value for a in WINELANDS_AREAS]
).order_by("-started_at")[:20]
for r in runs:
    print(f"{r.source}/{r.area}: {r.listings_saved} saved, {r.listings_updated} updated [{r.status}]")
```

---

## Phase 2 — Image Acquisition

```bash
# Download listing photos from portals
python manage.py download_market_photos --limit=500

# Fetch Street View + nearby places
python manage.py enrich_listings --area=stellenbosch --limit=200

# Street View only (skip places + vectorize)
python manage.py enrich_listings --skip-places --skip-vectorize --limit=200

# Re-enrich already-done listings (force refresh)
python manage.py enrich_listings --area=stellenbosch --re-enrich --limit=50
```

Check Street View coverage:
```python
from apps.market_data.models import MarketListing, ListingStreetView, WINELANDS_AREAS
winelands = [a.value for a in WINELANDS_AREAS]
total = MarketListing.objects.filter(area__in=winelands).count()
with_sv = ListingStreetView.objects.filter(listing__area__in=winelands, api_status="OK").count()
print(f"Street View coverage: {with_sv}/{total} ({100*with_sv/total:.1f}%)")
```

---

## Phase 3 — Vectorization

```bash
# Vectorize all winelands listings
python manage.py vectorize_listings

# Single area
python manage.py vectorize_listings --area=stellenbosch

# Reset + re-vectorize
python manage.py vectorize_listings --area=stellenbosch --reset
```

Test semantic search:
```
POST /api/v1/market-data/search/
{
  "query": "spacious family home with pool near Stellenbosch wine estate",
  "area": "stellenbosch",
  "listing_type": "sale",
  "n_results": 10
}
```

---

## Phase 4 — Cross-Site Deduplication

Find the same property listed on Property24, Gumtree, Seeff etc simultaneously:

```python
from apps.market_data.services.cross_site_matcher import find_cross_site_duplicates

# Find + mark (writes to DB)
groups = find_cross_site_duplicates(area="stellenbosch", commit=True)
print(f"Found {len(groups)} duplicate pairs")

# All winelands
groups = find_cross_site_duplicates(commit=True)

# Dry run
groups = find_cross_site_duplicates(area="stellenbosch", commit=False)
for g in groups[:5]:
    a, b = g["listing_a"], g["listing_b"]
    print(f"[{g['score']:.2f}] {a.source} vs {b.source}: {a.suburb} — R{a.active_price}")
```

---

## Phase 5 — AI Visual Classification

```bash
# Classify up to 50 listings (default — API cost control)
python manage.py classify_properties --area=stellenbosch

# Larger batch
python manage.py classify_properties --area=stellenbosch --limit=100

# Single listing
python manage.py classify_properties --listing-id=42

# Re-classify already done
python manage.py classify_properties --area=stellenbosch --force --limit=20

# Dry run (see what would be classified)
python manage.py classify_properties --dry-run --limit=20
```

Classification results per listing:
- `ai_property_type`: house | apartment | townhouse | cluster | simplex | duplex | farm | commercial | unknown
- `ai_condition`: well-maintained | average | poor | unknown
- `ai_style`: modern | contemporary | heritage | cape-dutch | victorian | art-deco | mediterranean | unknown
- `ai_classification_confidence`: float 0.0–1.0

---

## Phase 6 — Map Export

GeoJSON API (authenticated):
```
GET /api/v1/market-data/map-export/
GET /api/v1/market-data/map-export/?area=stellenbosch
GET /api/v1/market-data/map-export/?area=stellenbosch&listing_type=rent
GET /api/v1/market-data/map-export/?area=stellenbosch&listing_type=sale&min_price=2000000&max_price=8000000
GET /api/v1/market-data/map-export/?area=stellenbosch&bedrooms=3
GET /api/v1/market-data/map-export/?area=stellenbosch&include_duplicates=1
```

Response: GeoJSON `FeatureCollection` (max 2000 features). Each feature has:
```json
{
  "type": "Feature",
  "geometry": {"type": "Point", "coordinates": [lng, lat]},
  "properties": {
    "id": 142, "source": "property24", "listing_type": "sale",
    "property_type": "house", "ai_property_type": "house",
    "ai_condition": "well-maintained", "ai_style": "cape-dutch",
    "is_duplicate": false, "area": "stellenbosch", "suburb": "Paradyskloof",
    "bedrooms": 3, "price": 3850000, "title": "...", "cover_photo": "...",
    "source_url": "https://..."
  }
}
```

Generate standalone HTML map (paste in browser):
```python
import json, requests

token = "YOUR_JWT_TOKEN"
resp = requests.get(
    "http://localhost:8000/api/v1/market-data/map-export/",
    params={"area": "stellenbosch"},
    headers={"Authorization": f"Bearer {token}"}
)
geojson = resp.json()

# Generate HTML
google_maps_api_key = "YOUR_GOOGLE_MAPS_API_KEY"
center_lat, center_lng = -33.9321, 18.8602  # Stellenbosch

features_json = json.dumps(geojson["features"])
html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Stellenbosch Properties ({geojson['count']})</title>
<style>body,html{{margin:0;height:100%}}#map{{height:100%}}</style>
</head><body>
<div id="map"></div>
<script>
const FEATURES = {features_json};
function initMap() {{
  const map = new google.maps.Map(document.getElementById('map'), {{
    zoom: 13, center: {{lat: {center_lat}, lng: {center_lng}}}
  }});
  FEATURES.forEach(f => {{
    const p = f.properties;
    const [lng, lat] = f.geometry.coordinates;
    const color = p.listing_type === 'rent' ? '#2196F3' : '#FF9800';
    const marker = new google.maps.Marker({{
      position: {{lat, lng}}, map,
      icon: {{path: google.maps.SymbolPath.CIRCLE, scale: 7,
              fillColor: color, fillOpacity: 0.9, strokeWeight: 1, strokeColor: '#fff'}},
      title: p.title
    }});
    const info = new google.maps.InfoWindow({{content: `
      <div style="max-width:280px">
        ${{p.cover_photo ? '<img src="' + p.cover_photo + '" style="width:100%;border-radius:4px;margin-bottom:8px">' : ''}}
        <b>${{p.title}}</b><br>
        <b>R${{p.price?.toLocaleString()}}</b> · ${{p.bedrooms || '?'}} bed · ${{p.suburb}}<br>
        <small>${{p.ai_property_type || p.property_type}} / ${{p.ai_condition}} / ${{p.ai_style}}</small><br>
        <a href="${{p.source_url}}" target="_blank">${{p.source}}</a>
      </div>`
    }});
    marker.addListener('click', () => info.open(map, marker));
  }});
}}
</script>
<script src="https://maps.googleapis.com/maps/api/js?key={google_maps_api_key}&callback=initMap" async defer></script>
</body></html>"""

with open("/tmp/stellenbosch_map.html", "w") as f:
    f.write(html)
print("Map saved to /tmp/stellenbosch_map.html — open in browser")
```

---

## Full Pipeline (All Phases)

```bash
cd backend

# 1. Scrape
python manage.py scrape_winelands

# 2. Photos
python manage.py download_market_photos --limit=1000

# 3. Street View + Places
python manage.py enrich_listings --limit=500

# 4. Vectorize
python manage.py vectorize_listings

# 5. Deduplicate
python manage.py shell -c "
from apps.market_data.services.cross_site_matcher import find_cross_site_duplicates
g = find_cross_site_duplicates(commit=True)
print(f'{len(g)} duplicate pairs found')
"

# 6. Classify
python manage.py classify_properties --limit=100

# 7. Map export: GET /api/v1/market-data/map-export/
```

---

## Market Analysis Queries

```python
from apps.market_data.models import MarketListing, WINELANDS_AREAS
from django.db.models import Avg, Count, Q

winelands = [a.value for a in WINELANDS_AREAS]

# Average rent per area
for row in (MarketListing.objects
    .filter(area__in=winelands, listing_type="rent")
    .values("area")
    .annotate(avg=Avg("rental_price"), n=Count("id"))
    .order_by("area")):
    print(f"{row['area']}: R{row['avg']:,.0f}/mo ({row['n']} listings)")

# AI classification breakdown for Stellenbosch
for row in (MarketListing.objects
    .filter(area="stellenbosch")
    .exclude(ai_classified_at__isnull=True)
    .values("ai_property_type", "ai_condition")
    .annotate(n=Count("id"))
    .order_by("-n")):
    print(f"{row['ai_property_type']} / {row['ai_condition']}: {row['n']}")

# Cross-site duplicate rate
for row in (MarketListing.objects
    .filter(is_duplicate=True, area__in=winelands)
    .values("source")
    .annotate(n=Count("id"))
    .order_by("-n")):
    print(f"{row['source']}: {row['n']} duplicates")
```

---

## Cost Awareness

| API | Billed unit | Cost guidance |
|-----|-------------|---------------|
| Google Street View Static | Per image fetch | Metadata check (free) runs first to avoid charges |
| Google Places Nearby | Per request | Up to 60 results per listing (3 pages × 20) |
| Claude Vision (classify_properties) | Per image | ~$0.003/image at 256 max tokens — default `--limit=50` |

Always run `classify_properties --dry-run` before a large batch to preview scope.

---

## New Backend Files

| File | Purpose |
|------|---------|
| `backend/apps/market_data/services/property_classifier.py` | Claude Vision classifier |
| `backend/apps/market_data/services/cross_site_matcher.py` | Cross-portal deduplication |
| `backend/apps/market_data/management/commands/scrape_winelands.py` | Winelands scrape wrapper |
| `backend/apps/market_data/management/commands/vectorize_listings.py` | Standalone vectorization |
| `backend/apps/market_data/management/commands/enrich_listings.py` | Winelands enrichment wrapper |
| `backend/apps/market_data/management/commands/classify_properties.py` | AI visual classifier command |
| `backend/apps/market_data/migrations/0002_ai_classification_deduplication.py` | DB migration |
