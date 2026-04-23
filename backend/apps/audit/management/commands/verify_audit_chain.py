"""
Management command: verify_audit_chain

Walks the entire AuditEvent chain from genesis to the latest row and
recomputes each self_hash.  Any row whose stored self_hash does not match
the recomputed value is reported as a broken link.

Usage
-----
    python manage.py verify_audit_chain
    python manage.py verify_audit_chain --batch-size 5000
    python manage.py verify_audit_chain --fail-fast

Exit codes
----------
    0  — chain is intact
    1  — one or more broken links detected (or chain is empty with --fail-on-empty)
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from apps.audit.models import AuditEvent, compute_self_hash


class Command(BaseCommand):
    help = "Verify the tamper-evident hash chain of the AuditEvent log."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of rows to load per DB query (default: 1000)",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            default=False,
            help="Stop verification at the first broken link",
        )
        parser.add_argument(
            "--fail-on-empty",
            action="store_true",
            default=False,
            help="Exit with code 1 when the log is empty (useful in CI)",
        )

    def handle(self, *args, **options):
        batch_size: int = options["batch_size"]
        fail_fast: bool = options["fail_fast"]
        fail_on_empty: bool = options["fail_on_empty"]

        total = AuditEvent.objects.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("AuditEvent log is empty — nothing to verify."))
            if fail_on_empty:
                raise CommandError("Chain is empty.")
            return

        self.stdout.write(f"Verifying {total:,} AuditEvent rows...")

        broken: list[dict] = []
        verified = 0
        expected_prev_hash = ""

        # Walk in insertion order (ascending id)
        qs = AuditEvent.objects.order_by("id").only(
            "id",
            "actor_id",
            "actor_email",
            "action",
            "content_type_id",
            "object_id",
            "target_repr",
            "before_snapshot",
            "after_snapshot",
            "ip_address",
            "user_agent",
            "timestamp",
            "retention_years",
            "prev_hash",
            "self_hash",
        )

        last_id = 0
        while True:
            batch = list(qs.filter(id__gt=last_id)[:batch_size])
            if not batch:
                break

            for event in batch:
                # 1. Check prev_hash linkage
                if event.prev_hash != expected_prev_hash:
                    _issue = {
                        "id": event.id,
                        "error": "prev_hash mismatch",
                        "stored_prev": event.prev_hash,
                        "expected_prev": expected_prev_hash,
                    }
                    broken.append(_issue)
                    self.stderr.write(
                        self.style.ERROR(
                            f"  BREAK at id={event.id}: prev_hash mismatch "
                            f"(stored={event.prev_hash[:12]}... "
                            f"expected={expected_prev_hash[:12]}...)"
                        )
                    )
                    if fail_fast:
                        self._report(verified, broken)
                        raise CommandError("Chain broken — stopping at first error.")
                    # Even when broken, advance expected_prev using stored self_hash
                    # so we can detect further breaks independently.

                # 2. Check self_hash integrity
                recomputed = compute_self_hash(event.prev_hash, event.canonical_payload())
                if event.self_hash != recomputed:
                    _issue = {
                        "id": event.id,
                        "error": "self_hash mismatch",
                        "stored": event.self_hash,
                        "recomputed": recomputed,
                    }
                    broken.append(_issue)
                    self.stderr.write(
                        self.style.ERROR(
                            f"  TAMPER at id={event.id}: self_hash mismatch "
                            f"(stored={event.self_hash[:12]}... "
                            f"recomputed={recomputed[:12]}...)"
                        )
                    )
                    if fail_fast:
                        self._report(verified, broken)
                        raise CommandError("Chain broken — stopping at first error.")

                expected_prev_hash = event.self_hash
                verified += 1
                last_id = event.id

            if len(batch) < batch_size:
                break

        self._report(verified, broken)

        if broken:
            raise CommandError(f"Chain integrity FAILED — {len(broken)} broken link(s) detected.")

    def _report(self, verified: int, broken: list) -> None:
        if not broken:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Chain OK — {verified:,} event(s) verified, 0 broken links."
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"Chain FAILED — {verified:,} event(s) checked, "
                    f"{len(broken)} broken link(s) detected."
                )
            )
            self.stdout.write("Broken links:")
            for b in broken:
                self.stdout.write(f"  {b}")
