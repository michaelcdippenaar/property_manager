"""Seed five production-quality SA residential lease templates for a given agency.

Usage:
    python manage.py seed_demo_templates --agency-id <id>
    python manage.py seed_demo_templates --agency-id <id> --dry-run

The command is idempotent: if a template with the same name + agency already
exists it is skipped (never overwritten, so hand-edits on staging are safe).

Context metadata (property_type, tenant_count, lease_type) that does not yet
exist as dedicated model columns is stored inside the ``fields_schema`` JSON
field as a top-level ``"_meta"`` key alongside the canonical merge-field name
list. This allows the lease-AI v2 cluster to read it without a migration.

Template HTML files live in:
    backend/apps/leases/fixtures/demo_templates/
"""
from __future__ import annotations

import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

# ── Fixture directory (sibling of management/) ────────────────────────── #

_FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent  # apps/leases/
    / "fixtures"
    / "demo_templates"
)

# ── Template manifest ─────────────────────────────────────────────────── #

# Each entry: (name, property_type, tenant_count, lease_type, html_filename)
_TEMPLATES: list[tuple[str, str, int, str, str]] = [
    (
        "Sectional Title — 1 Tenant — Fixed Term (12mo)",
        "sectional_title",
        1,
        "fixed_term",
        "sectional_title_1_tenant_fixed.html",
    ),
    (
        "Sectional Title — 2 Tenants — Fixed Term (12mo)",
        "sectional_title",
        2,
        "fixed_term",
        "sectional_title_2_tenants_fixed.html",
    ),
    (
        "Freehold House — 1 Tenant — Fixed Term (12mo)",
        "freehold",
        1,
        "fixed_term",
        "freehold_1_tenant_fixed.html",
    ),
    (
        "Freehold House — Family of 2 — Fixed Term (12mo)",
        "freehold",
        2,
        "fixed_term",
        "freehold_family_2_fixed.html",
    ),
    (
        "Apartment — 1 Tenant — Month-to-Month",
        "apartment",
        1,
        "month_to_month",
        "apartment_1_tenant_month_to_month.html",
    ),
]


# ── Merge-field extractor ──────────────────────────────────────────────── #

_MERGE_FIELD_RE = re.compile(r'data-merge-field="([^"]+)"')


def _extract_merge_fields(html: str) -> list[str]:
    """Return a deduplicated ordered list of merge field names found in the HTML."""
    seen: dict[str, None] = {}
    for name in _MERGE_FIELD_RE.findall(html):
        seen[name] = None
    return list(seen.keys())


# ── Command ────────────────────────────────────────────────────────────── #


class Command(BaseCommand):
    help = (
        "Seed five production-quality SA residential lease templates into a "
        "specific agency. Idempotent — skips templates that already exist."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--agency-id",
            type=int,
            required=True,
            help=(
                "ID of the agency to seed templates into. "
                "Required — run "
                "User.objects.get(email='mc@klikk.co.za').agency_id "
                "on staging to find MC's agency ID."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without touching the database.",
        )

    def handle(self, *args, **options) -> None:
        from apps.accounts.models import Agency, User
        from apps.leases.models import LeaseTemplate

        agency_id: int = options["agency_id"]
        dry_run: bool = options["dry_run"]

        # ── Resolve agency ────────────────────────────────────────────── #
        try:
            agency = Agency.objects.get(pk=agency_id)
        except Agency.DoesNotExist:
            raise CommandError(
                f"Agency with id={agency_id} does not exist. "
                "Query the staging DB for the correct ID: "
                "User.objects.get(email='mc@klikk.co.za').agency_id"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] agency_id={agency_id} ({agency})"
                )
            )

        created_count = 0
        skipped_count = 0

        for name, prop_type, tenant_count, lease_type, html_file in _TEMPLATES:
            # ── Idempotency check ────────────────────────────────────── #
            exists = LeaseTemplate.objects.filter(
                agency_id=agency_id, name=name
            ).exists()

            if exists:
                self.stdout.write(f"  skipped (already exists): {name!r}")
                skipped_count += 1
                continue

            # ── Load HTML ────────────────────────────────────────────── #
            html_path = _FIXTURES_DIR / html_file
            if not html_path.is_file():
                raise CommandError(
                    f"Fixture file not found: {html_path}. "
                    "Ensure the file is committed alongside this command."
                )
            content_html = html_path.read_text(encoding="utf-8")

            # ── Build fields_schema ──────────────────────────────────── #
            # Merge field names extracted from the HTML chips, plus a
            # _meta block for property_type / tenant_count / lease_type
            # (these columns don't yet exist on LeaseTemplate).
            merge_fields = _extract_merge_fields(content_html)
            fields_schema = {
                "_meta": {
                    "property_type": prop_type,
                    "tenant_count": tenant_count,
                    "lease_type": lease_type,
                    "is_starter_template": True,
                },
                "merge_fields": merge_fields,
            }

            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] would create: {name!r} "
                    f"({prop_type}, {tenant_count}T, {lease_type}) "
                    f"— {len(merge_fields)} merge fields"
                )
                created_count += 1
                continue

            # ── Create template ──────────────────────────────────────── #
            LeaseTemplate.objects.create(
                agency=agency,
                name=name,
                content_html=content_html,
                fields_schema=fields_schema,
                # docx_file is a FileField with no blank=True, but Django
                # stores FileField as a plain VARCHAR; seeding with an empty
                # path is intentional — these templates are HTML-only and
                # have no DOCX. The content_html column is the source of truth.
                docx_file="",
                is_active=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  created: {name!r} "
                    f"({prop_type}, {tenant_count}T, {lease_type}) "
                    f"— {len(merge_fields)} merge fields"
                )
            )
            created_count += 1

        # ── Summary ──────────────────────────────────────────────────── #
        total_now = LeaseTemplate.objects.filter(agency_id=agency_id).count()
        verb = "[DRY RUN] would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb} {created_count} template(s), "
                f"skipped {skipped_count}, "
                f"agency_id={agency_id}, "
                f"total_now={'(dry-run — not incremented)' if dry_run else total_now}"
            )
        )
