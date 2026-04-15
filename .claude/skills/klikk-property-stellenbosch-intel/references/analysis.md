# Full Pipeline, Market Analysis & Cost Awareness

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

# Cross-site duplicate rate by source
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

**Always run `classify_properties --dry-run` before a large batch to preview scope.**

---

## Backend Files

| File | Purpose |
|------|---------|
| `backend/apps/market_data/services/property_classifier.py` | Claude Vision classifier |
| `backend/apps/market_data/services/cross_site_matcher.py` | Cross-portal deduplication |
| `backend/apps/market_data/management/commands/scrape_winelands.py` | Winelands scrape wrapper |
| `backend/apps/market_data/management/commands/vectorize_listings.py` | Standalone vectorization |
| `backend/apps/market_data/management/commands/enrich_listings.py` | Winelands enrichment wrapper |
| `backend/apps/market_data/management/commands/classify_properties.py` | AI visual classifier command |
| `backend/apps/market_data/migrations/0002_ai_classification_deduplication.py` | DB migration |
