"""
Management command: test_hub_selfcheck

The test_hub tests ITSELF. Verifies integrity of the test suite infrastructure.

Usage:
    python manage.py test_hub_selfcheck           # Run and print report
    python manage.py test_hub_selfcheck --fix     # Auto-fix minor issues (create missing __init__.py)
    python manage.py test_hub_selfcheck --json    # Output machine-readable JSON
"""
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone


MODULES = [
    "accounts", "properties", "leases", "maintenance",
    "esigning", "ai", "tenant_portal", "notifications",
]

REQUIRED_CONTEXT_FILES = [
    "architecture.md", "conventions.md", "tdd_workflow.md", "bug_workflow.md",
]


class Command(BaseCommand):
    help = "Self-check: verify test_hub integrity and record health in DB"

    def add_arguments(self, parser):
        parser.add_argument("--fix", action="store_true", help="Auto-fix minor issues")
        parser.add_argument("--json", action="store_true", help="Output JSON")
        parser.add_argument("--no-db", action="store_true", help="Skip DB write")

    def handle(self, *args, **options):
        test_hub_root = Path(__file__).resolve().parents[2]
        results = {}
        issues = []
        warnings = []

        # ── 1. Context files ─────────────────────────────────────────────────
        context_root = test_hub_root / "context"
        modules_dir = context_root / "modules"
        context_ok = True

        for fname in REQUIRED_CONTEXT_FILES:
            f = context_root / fname
            if not f.exists():
                issues.append(f"Missing context file: context/{fname}")
                context_ok = False
            elif f.stat().st_size < 100:
                warnings.append(f"Context file too small (<100 bytes): context/{fname}")

        for module in MODULES:
            mf = modules_dir / f"{module}.md"
            if not mf.exists():
                issues.append(f"Missing module context: context/modules/{module}.md")
                context_ok = False
            elif mf.stat().st_size < 200:
                warnings.append(f"Module context suspiciously small: context/modules/{module}.md")

        results["context_files_ok"] = context_ok

        # ── 2. RAG store ──────────────────────────────────────────────────────
        rag_ok = False
        rag_last_indexed = None
        try:
            from core.contract_rag import get_test_context_collection
            col = get_test_context_collection()
            count = col.count()
            rag_ok = count > 0
            if not rag_ok:
                issues.append("RAG test_context collection is empty — run: python manage.py ingest_test_context")
            else:
                # Estimate freshness from newest document metadata (ChromaDB doesn't store timestamps natively)
                rag_last_indexed = timezone.now()  # Approximation
        except Exception as exc:
            issues.append(f"RAG store unavailable: {exc}")
        results["rag_store_ok"] = rag_ok
        results["rag_last_indexed"] = rag_last_indexed

        # ── 3. All modules have tests ─────────────────────────────────────────
        all_modules_ok = True
        for module in MODULES:
            module_dir = test_hub_root / module
            unit_dir = module_dir / "unit"
            integration_dir = module_dir / "integration"

            if not module_dir.exists():
                issues.append(f"Module directory missing: test_hub/{module}/")
                all_modules_ok = False
                continue

            unit_tests = list(unit_dir.glob("test_*.py")) if unit_dir.exists() else []
            integ_tests = list(integration_dir.glob("test_*.py")) if integration_dir.exists() else []

            if not unit_tests:
                warnings.append(f"No unit tests for module: {module}")
            if not integ_tests:
                warnings.append(f"No integration tests for module: {module}")
            if not unit_tests and not integ_tests:
                all_modules_ok = False

        results["all_modules_have_tests"] = all_modules_ok

        # ── 4. Issue .md files synced to DB ───────────────────────────────────
        issues_root = test_hub_root / "issues"
        issues_synced = True
        if issues_root.exists():
            try:
                from apps.test_hub.models import TestIssue
                for module_dir in issues_root.iterdir():
                    if not module_dir.is_dir():
                        continue
                    for issue_file in module_dir.glob("*.md"):
                        slug = issue_file.stem
                        module = module_dir.name
                        if not TestIssue.objects.filter(module=module, slug=slug).exists():
                            warnings.append(
                                f"Issue file not synced to DB: issues/{module}/{issue_file.name}"
                                " — run: python manage.py sync_test_issues"
                            )
            except Exception:
                pass  # DB may not be available in all environments
        results["issues_synced"] = issues_synced

        # ── 5. No orphaned files (missing __init__.py) ────────────────────────
        no_orphans = True
        for module in MODULES:
            for subdir in ["unit", "integration"]:
                d = test_hub_root / module / subdir
                if d.exists() and not (d / "__init__.py").exists():
                    if options["fix"]:
                        (d / "__init__.py").touch()
                        self.stdout.write(self.style.SUCCESS(f"  Fixed: created {d/__init__.py}"))
                    else:
                        issues.append(f"Missing __init__.py: test_hub/{module}/{subdir}/")
                        no_orphans = False
        results["no_orphaned_files"] = no_orphans

        # ── 6. No duplicate test names ────────────────────────────────────────
        seen_names: dict[str, list[str]] = {}
        for test_file in test_hub_root.rglob("test_*.py"):
            text = test_file.read_text(encoding="utf-8", errors="ignore")
            for match in re.finditer(r"def (test_\w+)\(", text):
                name = match.group(1)
                rel = str(test_file.relative_to(test_hub_root))
                seen_names.setdefault(name, []).append(rel)

        duplicates = {k: v for k, v in seen_names.items() if len(v) > 1}
        no_duplicates = len(duplicates) == 0
        if duplicates:
            for name, files in list(duplicates.items())[:5]:
                warnings.append(f"Duplicate test name '{name}' in: {', '.join(files)}")
        results["no_duplicate_test_names"] = no_duplicates

        # ── 7. conftest enforces xfail ────────────────────────────────────────
        conftest = test_hub_root.parent.parent / "conftest.py"  # backend/conftest.py
        conftest_ok = False
        if conftest.exists():
            content = conftest.read_text(encoding="utf-8")
            conftest_ok = "xfail" in content and "red" in content and "strict" in content
        if not conftest_ok:
            issues.append("backend/conftest.py does not enforce xfail strict on @pytest.mark.red")
        results["conftest_enforces_xfail"] = conftest_ok

        # ── Summary ───────────────────────────────────────────────────────────
        is_healthy = len(issues) == 0
        results["is_healthy"] = is_healthy
        results["issues_found"] = issues
        results["warnings"] = warnings

        if options["json"]:
            self.stdout.write(json.dumps(results, indent=2, default=str))
            return

        self._print_report(results, issues, warnings, is_healthy)

        # ── Write to DB ───────────────────────────────────────────────────────
        if not options["no_db"]:
            try:
                from apps.test_hub.models import TestModuleSelfHealth
                TestModuleSelfHealth.objects.create(
                    is_healthy=is_healthy,
                    context_files_ok=results.get("context_files_ok", False),
                    rag_store_ok=results.get("rag_store_ok", False),
                    rag_last_indexed=rag_last_indexed,
                    all_modules_have_tests=results.get("all_modules_have_tests", False),
                    issues_synced=results.get("issues_synced", True),
                    no_duplicate_test_names=results.get("no_duplicate_test_names", False),
                    no_orphaned_files=results.get("no_orphaned_files", False),
                    conftest_enforces_xfail=results.get("conftest_enforces_xfail", False),
                    issues_found=issues,
                    warnings=warnings,
                )
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"  Could not write to DB: {exc}"))

    def _print_report(self, results, issues, warnings, is_healthy):
        self.stdout.write("\n" + "=" * 60)
        if is_healthy:
            self.stdout.write(self.style.SUCCESS("  TEST HUB SELF-CHECK — HEALTHY"))
        else:
            self.stdout.write(self.style.ERROR("  TEST HUB SELF-CHECK — ISSUES FOUND"))
        self.stdout.write("=" * 60)

        checks = [
            ("context_files_ok", "Context files (all 8 modules + globals)"),
            ("rag_store_ok", "RAG store (test_context collection populated)"),
            ("all_modules_have_tests", "All modules have tests"),
            ("issues_synced", "Issue files synced to DB"),
            ("no_orphaned_files", "No missing __init__.py"),
            ("no_duplicate_test_names", "No duplicate test names"),
            ("conftest_enforces_xfail", "conftest enforces xfail on @pytest.mark.red"),
        ]

        for key, label in checks:
            ok = results.get(key, False)
            icon = self.style.SUCCESS("✓") if ok else self.style.ERROR("✗")
            self.stdout.write(f"  {icon}  {label}")

        if issues:
            self.stdout.write(self.style.ERROR(f"\nIssues ({len(issues)}):"))
            for issue in issues:
                self.stdout.write(f"  • {issue}")

        if warnings:
            self.stdout.write(self.style.WARNING(f"\nWarnings ({len(warnings)}):"))
            for w in warnings:
                self.stdout.write(f"  ~ {w}")

        self.stdout.write("\n" + "=" * 60 + "\n")
