"""
ChromaDB vector store for files under CONTRACT_DOCUMENTS_ROOT (PDF, DOCX, TXT, MD).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from django.conf import settings

COLLECTION_NAME = "contracts"


def _root() -> Path:
    p = getattr(settings, "CONTRACT_DOCUMENTS_ROOT", None)
    if p is None:
        return Path(settings.BASE_DIR) / "documents"
    return Path(p)


def _chroma_path() -> Path:
    p = getattr(settings, "RAG_CHROMA_PATH", None)
    if p is None:
        return Path(settings.BASE_DIR) / "rag_chroma"
    return Path(p)


def get_chroma_client():
    import chromadb

    path = _chroma_path()
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path))


def get_contracts_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Leases, house rules, contracts"},
    )


def chunk_text(text: str, size: int = 1200, overlap: int = 150) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return chunks


def extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    cap = int(getattr(settings, "RAG_PDF_MAX_PAGES", 120))
    for page in reader.pages[:cap]:
        try:
            t = page.extract_text()
            if t:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if (p.text or "").strip())


def read_document_file(path: Path) -> str:
    suf = path.suffix.lower()
    if suf == ".pdf":
        return extract_pdf(path)
    if suf == ".docx":
        return extract_docx(path)
    if suf in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")
    return ""


def iter_ingest_files(root: Path):
    skip = {
        ".zip",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".exe",
        ".bin",
        ".mp4",
        ".mov",
    }
    max_bytes = int(getattr(settings, "RAG_MAX_FILE_BYTES", 40 * 1024 * 1024))
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        suf = p.suffix.lower()
        if suf in skip:
            continue
        if suf not in (".pdf", ".docx", ".txt", ".md"):
            continue
        try:
            if p.stat().st_size > max_bytes:
                continue
        except OSError:
            continue
        yield p


def ingest_contract_documents(
    *, reset: bool = False, max_files: int | None = None, batch_size: int = 64
) -> dict:
    """
    Walk CONTRACT_DOCUMENTS_ROOT, chunk text, upsert into Chroma (batched for speed).
    """
    root = _root()
    if not root.is_dir():
        return {"ok": False, "error": f"Missing documents directory: {root}", "chunks": 0, "files": 0}

    client = get_chroma_client()
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    col = get_contracts_collection()
    files_done = 0
    chunks_added = 0
    errors: list[str] = []
    batch_ids: list[str] = []
    batch_docs: list[str] = []
    batch_meta: list[dict] = []

    def flush_batch() -> None:
        nonlocal batch_ids, batch_docs, batch_meta, chunks_added
        if not batch_ids:
            return
        try:
            col.upsert(ids=batch_ids, documents=batch_docs, metadatas=batch_meta)
            chunks_added += len(batch_ids)
        except Exception as e:
            errors.append(f"batch upsert: {e}")
        batch_ids, batch_docs, batch_meta = [], [], []

    for path in iter_ingest_files(root):
        if max_files is not None and max_files > 0 and files_done >= max_files:
            break
        try:
            text = read_document_file(path)
        except Exception as e:
            errors.append(f"{path.name}: {e}")
            continue
        if len(text.strip()) < 40:
            continue
        rel = str(path.relative_to(root))
        files_done += 1
        for idx, chunk in enumerate(chunk_text(text)):
            cid = hashlib.sha256(f"{rel}|{idx}|{chunk[:120]}".encode()).hexdigest()
            batch_ids.append(cid)
            batch_docs.append(chunk)
            batch_meta.append({"source": rel, "chunk": idx})
            if len(batch_ids) >= batch_size:
                flush_batch()
    flush_batch()

    return {
        "ok": True,
        "root": str(root),
        "chroma_path": str(_chroma_path()),
        "files": files_done,
        "chunks": chunks_added,
        "errors": errors[:20],
    }


def query_contracts(query: str, n_results: int = 8) -> str:
    if not (query or "").strip():
        return ""
    try:
        col = get_contracts_collection()
        n = col.count()
        if n == 0:
            return ""
    except Exception:
        return ""
    try:
        res = col.query(query_texts=[query.strip()], n_results=min(n_results, max(1, n)))
    except Exception:
        return ""
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    parts: list[str] = []
    for i, doc in enumerate(docs):
        if not doc:
            continue
        meta = metas[i] if i < len(metas) else {}
        src = meta.get("source", "?") if isinstance(meta, dict) else "?"
        ch = meta.get("chunk", i) if isinstance(meta, dict) else i
        parts.append(f"--- source: {src} (chunk {ch}) ---\n{doc}")
    return "\n\n".join(parts)


def rag_collection_stats() -> dict:
    try:
        col = get_contracts_collection()
        n = col.count()
        return {"collection": COLLECTION_NAME, "chunks": n, "chroma_path": str(_chroma_path())}
    except Exception as e:
        return {"collection": COLLECTION_NAME, "chunks": 0, "error": str(e)}
