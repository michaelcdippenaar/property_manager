"""
Background work for the properties app.

No Celery in this project — we use a detached thread fired from
`transaction.on_commit` so the web request doesn't block on embedding.
If/when Celery is added, swap `_run_in_thread` for `@shared_task.delay`.
"""
from __future__ import annotations

import io
import logging
import threading
from pathlib import Path

from django.db import transaction

from core import owner_rag

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# File → list[page_text]
# ---------------------------------------------------------------------------

def _extract_pdf_pages(data: bytes, max_pages: int = 120) -> list[str]:
    """Return per-page text for a PDF. Empty pages preserved as ''."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
    except Exception:
        logger.exception("owner_rag: failed to open PDF")
        return []
    pages: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def _extract_docx_pages(data: bytes) -> list[str]:
    """DOCX has no pages; return the whole doc as a single 'page'."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
    except Exception:
        return []
    text = "\n".join(p.text for p in doc.paragraphs if (p.text or "").strip())
    return [text] if text else []


def _extract_text_pages(data: bytes) -> list[str]:
    try:
        return [data.decode("utf-8", errors="ignore")]
    except Exception:
        return []


def _read_file_pages(file_field) -> list[str]:
    """Read a Django FileField and return per-page text."""
    try:
        file_field.open("rb")
        data = file_field.read()
    except Exception:
        logger.exception("owner_rag: could not read file %s", getattr(file_field, "name", "?"))
        return []
    finally:
        try:
            file_field.close()
        except Exception:
            pass

    name = (getattr(file_field, "name", "") or "").lower()
    suffix = Path(name).suffix
    if suffix == ".pdf":
        return _extract_pdf_pages(data)
    if suffix == ".docx":
        return _extract_docx_pages(data)
    if suffix in (".txt", ".md"):
        return _extract_text_pages(data)
    return []


# ---------------------------------------------------------------------------
# classification_data → per-document enrichment
# ---------------------------------------------------------------------------

def _classified_doc_index(classification_data: dict | None) -> dict[str, dict]:
    """Build filename → classified-doc dict from owner_classification.json.

    Looks across fica.documents, cipc.documents, and trust_entity.*.documents.
    """
    if not isinstance(classification_data, dict):
        return {}
    out: dict[str, dict] = {}
    for bucket_key in ("fica", "cipc"):
        bucket = classification_data.get(bucket_key) or {}
        for doc in bucket.get("documents") or []:
            fn = (doc or {}).get("filename")
            if fn:
                out[fn] = doc
    trust = classification_data.get("trust_entity") or {}
    for bucket_key in ("fica", "cipc"):
        bucket = trust.get(bucket_key) or {}
        for doc in bucket.get("documents") or []:
            fn = (doc or {}).get("filename")
            if fn:
                out[fn] = doc
    return out


def _summarise_extracted(extracted: dict | None) -> str:
    """Render extracted fields as a short natural-language string."""
    if not isinstance(extracted, dict):
        return ""
    parts: list[str] = []
    for k, v in extracted.items():
        if v is None or v == "" or v == []:
            continue
        parts.append(f"{k}={v}")
    return "; ".join(parts)


def _person_ids_from_extracted(extracted: dict | None) -> list[str]:
    if not isinstance(extracted, dict):
        return []
    ids: set[str] = set()
    for key in ("id_number", "director_id", "trustee_id", "member_id"):
        v = extracted.get(key)
        if isinstance(v, str) and v.strip():
            ids.add(v.strip())
    return sorted(ids)


# ---------------------------------------------------------------------------
# Main ingestion task
# ---------------------------------------------------------------------------

def ingest_owner_documents(landlord_id: int) -> int:
    """Re-ingest every LandlordDocument (and the registration_document) for one
    landlord. Returns total chunks written.

    Idempotent: drops existing chunks for this landlord before re-ingesting.
    """
    from apps.properties.models import Landlord

    try:
        landlord = Landlord.objects.get(pk=landlord_id)
    except Landlord.DoesNotExist:
        logger.warning("owner_rag: landlord %s not found", landlord_id)
        return 0

    owner_rag.delete_by_landlord(landlord_id)

    classified = _classified_doc_index(landlord.classification_data)
    entity_type = landlord.landlord_type or ""
    entity_subtype = None  # subtype lives inside classification_data if needed
    entity_name = landlord.name or ""

    total_chunks = 0

    # All LandlordDocument files
    docs = list(landlord.documents.all())
    # Plus the legacy single registration_document, synthesised as pk=0
    reg = landlord.registration_document
    if reg and getattr(reg, "name", ""):
        docs.append(_RegistrationDocShim(landlord, reg))

    for doc in docs:
        filename = getattr(doc, "filename", None) or Path(doc.file.name).name
        classified_doc = classified.get(filename) or {}
        doc_type = classified_doc.get("type") or "other"
        extracted = classified_doc.get("extracted") or {}

        try:
            pages = _read_file_pages(doc.file)
        except Exception:
            logger.exception("owner_rag: failed to read %s", filename)
            continue
        if not pages:
            continue

        try:
            n = owner_rag.ingest_landlord_document(
                landlord_id=landlord.pk,
                document_id=doc.pk or 0,
                filename=filename,
                doc_type=_normalise_doc_type(doc_type),
                entity_type=entity_type,
                entity_subtype=entity_subtype,
                pages=pages,
                person_ids=_person_ids_from_extracted(extracted),
                expiry_date=classified_doc.get("expiry_date"),
                extracted_fields_summary=_summarise_extracted(extracted),
                entity_name=entity_name,
            )
            total_chunks += n
        except Exception:
            logger.exception("owner_rag: ingest failed for %s", filename)

    logger.info(
        "owner_rag: finished ingestion landlord=%s chunks=%d", landlord_id, total_chunks
    )
    return total_chunks


class _RegistrationDocShim:
    """Treat Landlord.registration_document as a pseudo-LandlordDocument."""
    def __init__(self, landlord, file_field):
        self.pk = 0
        self.landlord = landlord
        self.file = file_field
        self.filename = landlord.registration_document_name or Path(file_field.name).name


def _normalise_doc_type(raw: str) -> str:
    """Map classifier labels like 'CoR14.3' to snake_case keys."""
    if not raw:
        return "other"
    s = raw.strip().lower()
    s = s.replace(".", "_").replace("-", "_").replace(" ", "_").replace("/", "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_") or "other"


# ---------------------------------------------------------------------------
# Dispatch helpers
# ---------------------------------------------------------------------------

def _run_in_thread(fn, *args, **kwargs) -> None:
    """Fire-and-forget worker thread. No Celery in this project."""
    t = threading.Thread(
        target=fn, args=args, kwargs=kwargs, daemon=True,
        name=f"owner_rag_ingest_{args[0] if args else ''}",
    )
    t.start()


def enqueue_owner_ingestion(landlord_id: int) -> None:
    """Call from signals. Deferred until after the DB transaction commits."""
    def _go():
        try:
            ingest_owner_documents(landlord_id)
        except Exception:
            logger.exception("owner_rag: background ingestion crashed for %s", landlord_id)

    transaction.on_commit(lambda: _run_in_thread(_go))
