"""
Management command: ingest_test_context

Vectorises all test_hub context documents into the ChromaDB test_context collection.
This is the AI entry point for the testing process — agents query this store before
writing any test.

Usage:
    python manage.py ingest_test_context              # Ingest all context
    python manage.py ingest_test_context --reset      # Clear collection then re-ingest
    python manage.py ingest_test_context --module leases   # Single module only
    python manage.py ingest_test_context --dry-run    # Show what would be ingested

Document types indexed:
    module_context  — context/modules/<module>.md (domain knowledge, business rules, gaps)
    architecture    — context/architecture.md
    convention      — context/conventions.md, context/tdd_workflow.md
    bug_workflow    — context/bug_workflow.md
    issue           — issues/<module>/<date>_<slug>.md (bug history)
"""
from pathlib import Path

from django.core.management.base import BaseCommand


# Maps filename stems to doc_type
DOC_TYPE_MAP = {
    "architecture": "architecture",
    "conventions": "convention",
    "tdd_workflow": "convention",
    "bug_workflow": "bug_workflow",
}

MODULES = [
    "accounts", "properties", "leases", "maintenance",
    "esigning", "ai", "tenant_portal", "notifications",
]


class Command(BaseCommand):
    help = "Ingest test_hub context documents into the ChromaDB test_context RAG collection"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the test_context collection before re-ingesting",
        )
        parser.add_argument(
            "--module",
            choices=MODULES,
            help="Only ingest context for a specific module",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be ingested without writing to Chroma",
        )

    def handle(self, *args, **options):
        from core.contract_rag import get_chroma_client, get_test_context_collection, ingest_test_context_document, TEST_CONTEXT_COLLECTION

        dry_run = options["dry_run"]
        module_filter = options.get("module")

        if options["reset"] and not dry_run:
            self.stdout.write(self.style.WARNING("Resetting test_context collection..."))
            client = get_chroma_client()
            try:
                client.delete_collection(TEST_CONTEXT_COLLECTION)
                self.stdout.write(self.style.SUCCESS("  Collection deleted."))
            except Exception:
                pass

        test_hub_root = Path(__file__).resolve().parents[2]  # apps/test_hub/
        context_root = test_hub_root / "context"
        issues_root = test_hub_root / "issues"

        docs_to_ingest = []

        # --- Global context files ---
        if not module_filter:
            for md_file in context_root.glob("*.md"):
                if md_file.name == "README.md":
                    continue
                stem = md_file.stem
                doc_type = DOC_TYPE_MAP.get(stem, "convention")
                docs_to_ingest.append({
                    "doc_id": f"global:{stem}",
                    "path": md_file,
                    "module": "global",
                    "doc_type": doc_type,
                })

        # --- Module context files ---
        modules_dir = context_root / "modules"
        if modules_dir.exists():
            for md_file in sorted(modules_dir.glob("*.md")):
                module = md_file.stem
                if module_filter and module != module_filter:
                    continue
                docs_to_ingest.append({
                    "doc_id": f"module:{module}",
                    "path": md_file,
                    "module": module,
                    "doc_type": "module_context",
                })

        # --- Issue files ---
        if issues_root.exists():
            for module_dir in sorted(issues_root.iterdir()):
                if not module_dir.is_dir():
                    continue
                module = module_dir.name
                if module_filter and module != module_filter:
                    continue
                for issue_file in sorted(module_dir.glob("*.md")):
                    docs_to_ingest.append({
                        "doc_id": f"issue:{module}:{issue_file.stem}",
                        "path": issue_file,
                        "module": module,
                        "doc_type": "issue",
                    })

        if not docs_to_ingest:
            self.stdout.write(self.style.WARNING("No documents found to ingest."))
            return

        self.stdout.write(f"\nDocuments to ingest: {len(docs_to_ingest)}")
        self.stdout.write("-" * 50)

        ingested = 0
        skipped = 0

        for doc in docs_to_ingest:
            path: Path = doc["path"]
            rel_path = str(path.relative_to(test_hub_root))

            if dry_run:
                self.stdout.write(f"  [DRY RUN] {rel_path}  ({doc['doc_type']}, module={doc['module']})")
                continue

            text = path.read_text(encoding="utf-8").strip()
            if not text:
                self.stdout.write(self.style.WARNING(f"  SKIP (empty): {rel_path}"))
                skipped += 1
                continue

            success = ingest_test_context_document(
                doc_id=doc["doc_id"],
                text=text,
                module=doc["module"],
                doc_type=doc["doc_type"],
                source_path=rel_path,
            )

            if success:
                self.stdout.write(self.style.SUCCESS(f"  OK  {rel_path}"))
                ingested += 1
            else:
                self.stdout.write(self.style.ERROR(f"  FAIL {rel_path}"))
                skipped += 1

        if not dry_run:
            self.stdout.write("\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS(f"Ingested: {ingested}"))
            if skipped:
                self.stdout.write(self.style.WARNING(f"Skipped:  {skipped}"))
            self.stdout.write(
                "\nRAG store updated. AI agents can now query test context with:\n"
                "  from core.contract_rag import query_test_context\n"
                "  query_test_context('what should I test in the leases module?', module='leases')\n"
            )
