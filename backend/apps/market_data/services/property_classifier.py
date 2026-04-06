"""
AI visual property classifier using Claude Vision.

Classifies a property's type, condition, and architectural style from a
Google Street View JPEG image.

Usage:
    from apps.market_data.services.property_classifier import PropertyClassifier

    classifier = PropertyClassifier()

    # From a saved listing (requires street_view with photo_file)
    result = classifier.classify_from_street_view(listing)

    # From raw JPEG bytes (POC / ad-hoc use)
    result = classifier.classify_from_bytes(jpeg_bytes)

    # result: {
    #   "property_type": "house",
    #   "condition": "well-maintained",
    #   "style": "cape-dutch",
    #   "confidence": 0.87,
    #   "reasoning": "Stone facade, gabled entrance typical of Cape Dutch..."
    # }
"""
from __future__ import annotations

import base64
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are a South African property analyst. Analyze this street view image of a property.

Classify the property on three dimensions:

1. **Property Type** (pick one): house | apartment | townhouse | cluster | simplex | duplex | farm | commercial | unknown
2. **Condition** (pick one): well-maintained | average | poor | unknown
3. **Architectural Style** (pick one): modern | contemporary | heritage | cape-dutch | victorian | art-deco | mediterranean | unknown

Also estimate your confidence (0.0–1.0) for the overall classification.

Respond ONLY as valid JSON with no extra text:
{
  "property_type": "...",
  "condition": "...",
  "style": "...",
  "confidence": 0.0,
  "reasoning": "one sentence max"
}"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        # parts[1] is the content block (may start with "json\n")
        inner = parts[1] if len(parts) > 1 else text
        if inner.startswith("json"):
            inner = inner[4:]
        return inner.strip()
    return text


class PropertyClassifier:
    MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 256

    def __init__(self):
        api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
        if api_key:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            self.client = None
            logger.warning("ANTHROPIC_API_KEY not set — PropertyClassifier unavailable")

    @property
    def available(self) -> bool:
        return self.client is not None

    def classify_from_bytes(self, jpeg_bytes: bytes) -> dict | None:
        """Classify a property from raw JPEG bytes. Returns classification dict or None."""
        if not self.client or not jpeg_bytes:
            return None

        image_data = base64.standard_b64encode(jpeg_bytes).decode("utf-8")
        return self._call_claude(image_data)

    def classify_from_street_view(self, listing) -> dict | None:
        """
        Classify a property from its saved street view photo.
        listing must have a related ListingStreetView with photo_file saved.
        Returns classification dict or None.
        """
        if not self.client:
            return None

        try:
            sv = listing.street_view
        except Exception:
            logger.debug("Listing %s has no street_view relation", listing.pk)
            return None

        if not sv or sv.api_status != "OK" or not sv.photo_file:
            return None

        try:
            with sv.photo_file.open("rb") as f:
                jpeg_bytes = f.read()
        except Exception as e:
            logger.warning("Could not read street view file for listing %s: %s", listing.pk, e)
            return None

        image_data = base64.standard_b64encode(jpeg_bytes).decode("utf-8")
        return self._call_claude(image_data)

    def _call_claude(self, image_data_b64: str) -> dict | None:
        try:
            message = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data_b64,
                            },
                        },
                        {"type": "text", "text": CLASSIFICATION_PROMPT},
                    ],
                }],
            )
            raw = message.content[0].text
            cleaned = _strip_code_fences(raw)
            result = json.loads(cleaned)
            return result
        except json.JSONDecodeError as e:
            logger.warning("PropertyClassifier: failed to parse JSON response: %s", e)
            return None
        except Exception as e:
            logger.warning("PropertyClassifier: Claude API error: %s", e)
            return None
