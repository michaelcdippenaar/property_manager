from django.core.management.base import BaseCommand

from core.contract_rag import ingest_contract_documents


class Command(BaseCommand):
    help = (
        "Chunk and vectorize PDF/DOCX/TXT/MD under CONTRACT_DOCUMENTS_ROOT into local ChromaDB."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the contracts collection before re-ingesting.",
        )
        parser.add_argument(
            "--max-files",
            type=int,
            default=0,
            help="Ingest at most this many files (0 = no limit). Useful for testing.",
        )

    def handle(self, *args, **options):
        mf = options["max_files"] or None
        result = ingest_contract_documents(reset=options["reset"], max_files=mf)
        if not result.get("ok"):
            self.stderr.write(self.style.ERROR(result.get("error", "failed")))
            return
        self.stdout.write(self.style.SUCCESS(f"Root: {result['root']}"))
        self.stdout.write(f"Chroma: {result['chroma_path']}")
        self.stdout.write(self.style.SUCCESS(f"Files: {result['files']}  Chunks: {result['chunks']}"))
        for e in result.get("errors") or []:
            self.stderr.write(self.style.WARNING(e))
