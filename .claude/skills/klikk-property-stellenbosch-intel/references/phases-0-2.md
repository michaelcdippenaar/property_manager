# Phases 0-2: Lookup, Scrape, and Image Acquisition

---

## Phase 0 — Single Property Lookup

Use when given a specific address (e.g. "1 Bosch-en-Dal, Karindal, Stellenbosch").

### Step 1: Check DB first
```python
from apps.market_data.models import MarketListing
results = MarketListing.objects.filter(area="stellenbosch", raw_address__icontains="karindal")
print(f"{results.count()} listings found")
for l in results:
    print(f"  [{l.source}] {l.raw_address} — {l.listing_type} R{l.active_price}")
```

### Step 2: Scrape if not found
```bash
cd backend
python manage.py scrape_winelands --area=stellenbosch
```

### Step 3: Geocode the address
```python
import requests
api_key = "YOUR_GOOGLE_MAPS_API_KEY"
resp = requests.get(
    "https://maps.googleapis.com/maps/api/geocode/json",
    params={"address": "1 Bosch-en-Dal Karindal Stellenbosch", "key": api_key}
)
result = resp.json()["results"][0]
lat = result["geometry"]["location"]["lat"]
lng = result["geometry"]["location"]["lng"]
print(f"Coords: {lat}, {lng}")  # Expected: approx -33.93xx, 18.84xx
```

### Step 4: Fetch Street View
```python
from apps.market_data.services.google_maps import GoogleMapsService
svc = GoogleMapsService()
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
listing = MarketListing.objects.filter(area="stellenbosch").select_related("street_view").first()
result = classifier.classify_from_street_view(listing)
# OR from raw bytes: result = classifier.classify_from_bytes(jpeg)
# {"property_type": "house", "condition": "well-maintained", "style": "cape-dutch", "confidence": 0.87}
```

### Step 6: Find cross-site matches
```python
from apps.market_data.services.cross_site_matcher import find_cross_site_duplicates, _haversine_m
groups = find_cross_site_duplicates(area="stellenbosch", commit=False)
target_lat, target_lng = -33.93, 18.84
nearby = [
    g for g in groups
    if g["listing_a"].latitude and _haversine_m(
        g["listing_a"].latitude, g["listing_a"].longitude, target_lat, target_lng
    ) < 200
]
for g in nearby:
    a, b = g["listing_a"], g["listing_b"]
    print(f"[{g['score']:.2f}] {a.source}: {a.source_url}\n         {b.source}: {b.source_url}")
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
