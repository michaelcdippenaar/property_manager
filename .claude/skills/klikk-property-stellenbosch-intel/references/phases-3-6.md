# Phases 3-6: Vectorize, Deduplicate, Classify, Map Export

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

Find the same property listed across Property24, Gumtree, Seeff etc simultaneously:

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

Response: GeoJSON `FeatureCollection` (max 2000 features). Each feature:
```json
{
  "type": "Feature",
  "geometry": {"type": "Point", "coordinates": [lng, lat]},
  "properties": {
    "id": 142, "source": "property24", "listing_type": "sale",
    "ai_property_type": "house", "ai_condition": "well-maintained", "ai_style": "cape-dutch",
    "is_duplicate": false, "area": "stellenbosch", "suburb": "Paradyskloof",
    "bedrooms": 3, "price": 3850000, "title": "...", "cover_photo": "...", "source_url": "..."
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
        <small>${{p.ai_property_type}} / ${{p.ai_condition}} / ${{p.ai_style}}</small><br>
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
