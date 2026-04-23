"""
Ingest tenant-facing knowledge-base articles into ChromaDB.

Articles live in backend/apps/chat/knowledge/ as plain Markdown files.
They are ingested into the `contracts` ChromaDB collection with no
property_id (globally accessible to all tenant chat RAG queries).

Usage:
    python manage.py ingest_chat_kb
    python manage.py ingest_chat_kb --reset
    python manage.py ingest_chat_kb --dry-run
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from django.core.management.base import BaseCommand

_KB_DIR = Path(__file__).resolve().parents[4] / "chat" / "knowledge"


class Command(BaseCommand):
    help = "Ingest tenant KB articles (apps/chat/knowledge/) into the ChromaDB contracts collection"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing tenant-kb chunks before re-ingesting (identified by metadata source prefix 'tenant-kb/')",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be ingested without writing to ChromaDB",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        dry_run = options["dry_run"]

        if not _KB_DIR.is_dir():
            self.stderr.write(
                self.style.ERROR(f"KB directory not found: {_KB_DIR}")
            )
            return

        md_files = sorted(_KB_DIR.glob("*.md"))
        if not md_files:
            self.stdout.write(self.style.WARNING("No .md files found in KB directory."))
            return

        from core.contract_rag import get_contracts_collection, chunk_text

        col = get_contracts_collection()

        if reset and not dry_run:
            # Delete existing tenant-kb chunks by ID prefix
            self.stdout.write("Removing existing tenant-kb chunks...")
            try:
                existing = col.get(where={"source": {"$regex": "^tenant-kb/"}})
                if existing and existing.get("ids"):
                    col.delete(ids=existing["ids"])
                    self.stdout.write(
                        self.style.SUCCESS(f"  Deleted {len(existing['ids'])} existing chunks.")
                    )
            except Exception as exc:
                self.stdout.write(
                    self.style.WARNING(f"  Could not clean existing chunks: {exc}")
                )

        total_files = 0
        total_chunks = 0

        for path in md_files:
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                self.stdout.write(self.style.WARNING(f"  Skipping empty file: {path.name}"))
                continue

            chunks = chunk_text(text)
            source_key = f"tenant-kb/{path.name}"

            if dry_run:
                self.stdout.write(
                    f"  [dry-run] Would ingest {len(chunks)} chunk(s) from {path.name}"
                )
                total_files += 1
                total_chunks += len(chunks)
                continue

            ids, docs, metas = [], [], []
            for idx, chunk in enumerate(chunks):
                cid = hashlib.sha256(
                    f"tenant-kb|{path.name}|{idx}|{chunk[:80]}".encode()
                ).hexdigest()
                ids.append(cid)
                docs.append(chunk)
                metas.append({"source": source_key, "chunk": idx})

            try:
                col.upsert(ids=ids, documents=docs, metadatas=metas)
                self.stdout.write(f"  Ingested {len(ids)} chunk(s) from {path.name}")
                total_files += 1
                total_chunks += len(ids)
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"  Failed to ingest {path.name}: {exc}")
                )

        action = "Would ingest" if dry_run else "Ingested"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{action} {total_files} file(s), {total_chunks} chunk(s) "
                f"into the ChromaDB contracts collection."
            )
        )
