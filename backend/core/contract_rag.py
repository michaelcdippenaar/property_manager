"""
ChromaDB vector store for files under CONTRACT_DOCUMENTS_ROOT (PDF, DOCX, TXT, MD).

Uses nomic-embed-text via sentence-transformers for high-quality embeddings
aligned with modern LLM retrieval patterns.
"""
from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "contracts"
AGENT_QA_COLLECTION = "agent_qa"
CHAT_KNOWLEDGE_COLLECTION = "chat_knowledge"


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


def _embedding_model() -> str:
    return getattr(settings, "RAG_EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")


_cached_ef = None


def get_embedding_function():
    """Return a SentenceTransformerEmbeddingFunction using nomic-embed-text."""
    global _cached_ef
    if _cached_ef is not None:
        return _cached_ef
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    model_name = _embedding_model()
    _cached_ef = SentenceTransformerEmbeddingFunction(
        model_name=model_name,
        trust_remote_code=True,
    )
    logger.info("RAG embedding model loaded: %s", model_name)
    return _cached_ef


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
        embedding_function=get_embedding_function(),
    )


def get_agent_qa_collection():
    """Collection for answered AgentQuestion Q&A pairs."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=AGENT_QA_COLLECTION,
        metadata={"description": "Staff-answered Q&A for agent knowledge"},
        embedding_function=get_embedding_function(),
    )


def get_chat_knowledge_collection():
    """Collection for knowledge extracted from successful chat interactions."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=CHAT_KNOWLEDGE_COLLECTION,
        metadata={"description": "Self-training knowledge from resolved chats"},
        embedding_function=get_embedding_function(),
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
    *,
    reset: bool = False,
    max_files: int | None = None,
    batch_size: int = 64,
    property_id: int | None = None,
) -> dict:
    """
    Walk CONTRACT_DOCUMENTS_ROOT, chunk text, upsert into Chroma (batched for speed).
    Optionally tag all chunks with a property_id for scoped queries.
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
            meta = {"source": rel, "chunk": idx}
            if property_id is not None:
                meta["property_id"] = property_id
            batch_meta.append(meta)
            if len(batch_ids) >= batch_size:
                flush_batch()
    flush_batch()

    return {
        "ok": True,
        "root": str(root),
        "chroma_path": str(_chroma_path()),
        "embedding_model": _embedding_model(),
        "files": files_done,
        "chunks": chunks_added,
        "errors": errors[:20],
    }


def query_contracts(
    query: str,
    n_results: int = 8,
    property_id: int | None = None,
) -> str:
    """
    Query the contracts collection. Optionally scope to a specific property.
    """
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
        kwargs: dict = {
            "query_texts": [query.strip()],
            "n_results": min(n_results, max(1, n)),
        }
        if property_id is not None:
            kwargs["where"] = {"property_id": property_id}
        res = col.query(**kwargs)
    except Exception:
        # Fall back without property filter if metadata doesn't exist yet
        try:
            res = col.query(
                query_texts=[query.strip()],
                n_results=min(n_results, max(1, n)),
            )
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


def query_agent_qa(query: str, n_results: int = 5) -> str:
    """Query the agent Q&A knowledge base."""
    if not (query or "").strip():
        return ""
    try:
        col = get_agent_qa_collection()
        n = col.count()
        if n == 0:
            return ""
    except Exception:
        return ""
    try:
        res = col.query(
            query_texts=[query.strip()],
            n_results=min(n_results, max(1, n)),
        )
    except Exception:
        return ""
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    parts: list[str] = []
    for i, doc in enumerate(docs):
        if not doc:
            continue
        meta = metas[i] if i < len(metas) else {}
        cat = meta.get("category", "?") if isinstance(meta, dict) else "?"
        parts.append(f"--- staff answer [{cat}] ---\n{doc}")
    return "\n\n".join(parts)


def ingest_agent_question(question_id: int, question: str, answer: str, category: str = "", property_id: int | None = None) -> bool:
    """Ingest a single answered AgentQuestion into the Q&A collection."""
    try:
        col = get_agent_qa_collection()
        doc = f"Q: {question.strip()}\nA: {answer.strip()}"
        cid = hashlib.sha256(f"aq|{question_id}".encode()).hexdigest()
        meta: dict = {"question_id": question_id, "category": category}
        if property_id is not None:
            meta["property_id"] = property_id
        col.upsert(ids=[cid], documents=[doc], metadatas=[meta])
        return True
    except Exception as e:
        logger.error("Failed to ingest AgentQuestion %s: %s", question_id, e)
        return False


def ingest_chat_knowledge(session_id: int, summary: str, category: str = "", property_id: int | None = None) -> bool:
    """Ingest a resolved chat summary into the self-training collection."""
    try:
        col = get_chat_knowledge_collection()
        cid = hashlib.sha256(f"chat|{session_id}".encode()).hexdigest()
        meta: dict = {"session_id": session_id, "category": category}
        if property_id is not None:
            meta["property_id"] = property_id
        col.upsert(ids=[cid], documents=[summary], metadatas=[meta])
        return True
    except Exception as e:
        logger.error("Failed to ingest chat knowledge %s: %s", session_id, e)
        return False


def query_chat_knowledge(query: str, n_results: int = 3) -> str:
    """Query the self-training knowledge base."""
    if not (query or "").strip():
        return ""
    try:
        col = get_chat_knowledge_collection()
        n = col.count()
        if n == 0:
            return ""
    except Exception:
        return ""
    try:
        res = col.query(
            query_texts=[query.strip()],
            n_results=min(n_results, max(1, n)),
        )
    except Exception:
        return ""
    docs = (res.get("documents") or [[]])[0]
    parts: list[str] = []
    for doc in docs:
        if doc:
            parts.append(f"--- learned from past interactions ---\n{doc}")
    return "\n\n".join(parts)


def rag_collection_stats() -> dict:
    try:
        col = get_contracts_collection()
        n = col.count()
        stats = {
            "collection": COLLECTION_NAME,
            "chunks": n,
            "chroma_path": str(_chroma_path()),
            "embedding_model": _embedding_model(),
        }
        # Also report Q&A and chat knowledge counts
        try:
            qa_col = get_agent_qa_collection()
            stats["agent_qa_chunks"] = qa_col.count()
        except Exception:
            stats["agent_qa_chunks"] = 0
        try:
            ck_col = get_chat_knowledge_collection()
            stats["chat_knowledge_chunks"] = ck_col.count()
        except Exception:
            stats["chat_knowledge_chunks"] = 0
        return stats
    except Exception as e:
        return {"collection": COLLECTION_NAME, "chunks": 0, "error": str(e)}
