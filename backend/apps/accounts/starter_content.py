"""
Starter content seeding for newly-registered agencies (Phase 3.1).

When an Agency is created (registration, Google complete-signup, etc.), call
``seed_starter_content(agency)`` to copy a curated set of lease templates and
supplier directory entries from ``backend/fixtures/starter_pack.json`` into the
new agency's namespace.

Idempotent — if the agency already has any LeaseTemplate, the function skips
seeding and returns ``{"templates": 0, "suppliers": 0, "skipped": True}``.

Failure to seed must NOT roll back account creation; callers should wrap
the call in a try/except or run it outside the registration transaction and
log the error.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction

if TYPE_CHECKING:  # pragma: no cover
    from apps.accounts.models import Agency

logger = logging.getLogger(__name__)


def _fixture_path() -> Path:
    """Resolve the starter_pack.json path relative to BASE_DIR/fixtures."""
    base = Path(getattr(settings, "BASE_DIR", "."))
    return base / "fixtures" / "starter_pack.json"


def _load_fixture(path: Path | None = None) -> dict:
    path = path or _fixture_path()
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.warning("starter_content: fixture not found at %s — skipping seed", path)
        return {}
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("starter_content: failed to load fixture %s: %s", path, exc)
        return {}


def seed_starter_content(agency: "Agency", *, fixture_path: Path | None = None) -> dict:
    """Seed lease templates + suppliers for a fresh agency.

    Idempotent: returns early with ``skipped: True`` if the agency already
    has any LeaseTemplate. Errors are logged and swallowed; the function
    never raises (so it can't break account creation).
    """
    from apps.leases.models import LeaseTemplate
    from apps.maintenance.models import Supplier

    if agency is None or not getattr(agency, "pk", None):
        logger.warning("starter_content: agency missing or unsaved; nothing to seed")
        return {"templates": 0, "suppliers": 0, "skipped": True}

    # Idempotency — never double-seed.
    if LeaseTemplate.objects.filter(agency=agency).exists():
        return {"templates": 0, "suppliers": 0, "skipped": True}

    fixture = _load_fixture(fixture_path)
    if not fixture:
        return {"templates": 0, "suppliers": 0, "skipped": True}

    templates_payload = fixture.get("lease_templates") or []
    suppliers_payload = fixture.get("suppliers") or []

    template_count = 0
    supplier_count = 0

    try:
        with transaction.atomic():
            for tpl in templates_payload:
                if not isinstance(tpl, dict) or not tpl.get("name"):
                    continue
                LeaseTemplate.objects.create(
                    agency=agency,
                    name=tpl.get("name", "")[:200],
                    version=str(tpl.get("version", "1.0"))[:20],
                    province=tpl.get("province", "")[:100],
                    docx_file="",  # placeholder; agency uploads/edits later
                    fields_schema=tpl.get("fields_schema") or [],
                    content_html=tpl.get("content_html", "") or "",
                    header_html=tpl.get("header_html", "") or "",
                    footer_html=tpl.get("footer_html", "") or "",
                    is_active=True,
                )
                template_count += 1

            for sup in suppliers_payload:
                if not isinstance(sup, dict) or not sup.get("name"):
                    continue
                Supplier.objects.create(
                    agency=agency,
                    name=sup.get("name", "")[:200],
                    phone=sup.get("phone", "")[:20],
                    email=sup.get("email", "") or "",
                    city=sup.get("city", "") or "",
                    province=sup.get("province", "") or "",
                    notes=sup.get("notes", "") or "",
                    is_active=True,
                )
                supplier_count += 1
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("starter_content: seed failed for agency %s: %s", agency.pk, exc)
        return {"templates": 0, "suppliers": 0, "error": str(exc)}

    logger.info(
        "starter_content: seeded agency %s — %d templates, %d suppliers",
        agency.pk, template_count, supplier_count,
    )
    return {"templates": template_count, "suppliers": supplier_count, "skipped": False}
