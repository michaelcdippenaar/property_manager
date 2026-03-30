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
MAINTENANCE_ISSUES_COLLECTION = "maintenance_issues"


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


def get_maintenance_issues_collection():
    """Collection for vectorised maintenance issues (for similarity search)."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=MAINTENANCE_ISSUES_COLLECTION,
        metadata={"description": "Maintenance issues for RAG similarity search"},
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


def _build_folder_property_map(root: Path) -> dict[str, int]:
    """
    Map top-level document folder names to Property IDs by fuzzy matching.

    Compares folder names against property names and addresses in the DB.
    Uses simple word-overlap scoring — the folder name typically contains
    the street number and area (e.g. "18 Irene Park La Coline").
    """
    from apps.properties.models import Property

    properties = list(Property.objects.values("pk", "name", "address"))
    if not properties:
        return {}

    folder_map: dict[str, int] = {}
    top_dirs = [d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]

    for folder in top_dirs:
        folder_lower = folder.lower().replace("-", " ").replace("_", " ")
        folder_words = set(folder_lower.split())
        best_score = 0
        best_pk = None

        for prop in properties:
            # Compare against both name and address
            for field in (prop["name"], prop["address"]):
                if not field:
                    continue
                field_lower = field.lower().replace("-", " ").replace("_", " ")
                field_words = set(field_lower.split())
                overlap = len(folder_words & field_words)
                if overlap > best_score:
                    best_score = overlap
                    best_pk = prop["pk"]

        # Require at least 2 matching words to avoid false positives
        if best_score >= 2 and best_pk is not None:
            folder_map[folder] = best_pk

    return folder_map


def ingest_contract_documents(
    *,
    reset: bool = False,
    max_files: int | None = None,
    batch_size: int = 64,
    property_id: int | None = None,
) -> dict:
    """
    Walk CONTRACT_DOCUMENTS_ROOT, chunk text, upsert into Chroma (batched for speed).

    Auto-detects property_id from folder name when not explicitly provided.
    Top-level folders are matched against Property records in the DB by
    comparing words in the folder name against property names and addresses.
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

    # Build folder → property_id mapping
    folder_map = _build_folder_property_map(root)

    files_done = 0
    chunks_added = 0
    errors: list[str] = []
    property_stats: dict[str, int] = {}
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

        # Resolve property_id: explicit param > folder match > None
        file_property_id = property_id
        if file_property_id is None:
            top_folder = path.relative_to(root).parts[0] if path.relative_to(root).parts else None
            if top_folder and top_folder in folder_map:
                file_property_id = folder_map[top_folder]

        if file_property_id is not None:
            label = f"property_{file_property_id}"
            property_stats[label] = property_stats.get(label, 0) + 1

        for idx, chunk in enumerate(chunk_text(text)):
            cid = hashlib.sha256(f"{rel}|{idx}|{chunk[:120]}".encode()).hexdigest()
            batch_ids.append(cid)
            batch_docs.append(chunk)
            meta = {"source": rel, "chunk": idx}
            if file_property_id is not None:
                meta["property_id"] = file_property_id
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
        "folder_property_map": folder_map,
        "property_file_counts": property_stats,
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
        base_kwargs: dict = {
            "query_texts": [query.strip()],
            "n_results": min(n_results, max(1, n)),
        }
        res = None
        # Try property-scoped query first
        if property_id is not None:
            try:
                res = col.query(**{**base_kwargs, "where": {"property_id": property_id}})
            except Exception:
                pass
            # If scoped query returned no results, do NOT fall back to global —
            # returning another property's lease terms is worse than returning nothing.
            if not (res and (res.get("documents") or [[]])[0]):
                logger.info(
                    "No contract chunks found for property_id=%s query=%r — "
                    "returning empty rather than cross-property results",
                    property_id, query[:80],
                )
                return ""
        if res is None:
            # No property_id specified — global search is fine
            res = col.query(**base_kwargs)
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


def ingest_maintenance_issue(
    request_id: int,
    title: str,
    description: str,
    category: str = "",
    priority: str = "",
    status: str = "",
    property_id: int | None = None,
    resolution: str = "",
) -> bool:
    """
    Ingest a maintenance issue into the vector store for similarity search.

    This enables the AI to find similar past issues when handling new ones,
    creating a clear RAG path: new issue → vector search → similar past issues.
    """
    try:
        col = get_maintenance_issues_collection()
        doc = f"Issue: {title.strip()}\nDescription: {description.strip()}"
        if resolution:
            doc += f"\nResolution: {resolution.strip()}"
        cid = hashlib.sha256(f"mr|{request_id}".encode()).hexdigest()
        meta: dict = {
            "request_id": request_id,
            "category": category,
            "priority": priority,
            "status": status,
        }
        if property_id is not None:
            meta["property_id"] = property_id
        col.upsert(ids=[cid], documents=[doc], metadatas=[meta])
        return True
    except Exception as e:
        logger.error("Failed to ingest maintenance issue %s: %s", request_id, e)
        return False


def query_maintenance_issues(
    query: str,
    n_results: int = 5,
    property_id: int | None = None,
    category: str | None = None,
) -> str:
    """
    Find similar past maintenance issues via vector search.

    Returns matching issues with their category, priority, and resolution.
    Optionally scoped to a property or category.
    """
    if not (query or "").strip():
        return ""
    try:
        col = get_maintenance_issues_collection()
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
        where_clauses = {}
        if property_id is not None:
            where_clauses["property_id"] = property_id
        if category:
            where_clauses["category"] = category
        if where_clauses:
            kwargs["where"] = where_clauses
        res = col.query(**kwargs)
    except Exception:
        if where_clauses:
            # Scoped query failed — don't fall back to unscoped (cross-property risk)
            logger.warning(
                "Scoped maintenance issue query failed (where=%s), returning empty",
                where_clauses,
            )
            return ""
        return ""
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    parts: list[str] = []
    for i, doc in enumerate(docs):
        if not doc:
            continue
        meta = metas[i] if i < len(metas) else {}
        cat = meta.get("category", "?") if isinstance(meta, dict) else "?"
        pri = meta.get("priority", "?") if isinstance(meta, dict) else "?"
        rid = meta.get("request_id", "?") if isinstance(meta, dict) else "?"
        parts.append(f"--- past issue #{rid} [{cat}/{pri}] ---\n{doc}")
    return "\n\n".join(parts)


def classify_from_rag(
    message: str,
    *,
    property_id: int | None = None,
    n_results: int = 5,
) -> dict:
    """
    Classify a maintenance message using RAG similarity — no LLM call needed.

    Queries the maintenance_issues collection for similar past issues,
    then uses majority-vote on their category and priority metadata.
    Also scores against MaintenanceSkill symptom phrases as a second signal.

    Returns:
        {
            "category": str,          # e.g. "plumbing"
            "priority": str,          # e.g. "high"
            "confidence": float,      # 0.0–1.0
            "rag_matches": int,       # how many past issues contributed
            "skill_matches": list,    # matched skill trade names
            "sources": list[dict],    # [{request_id, category, priority}, ...]
        }
    """
    from collections import Counter

    result = {
        "category": "other",
        "priority": "medium",
        "confidence": 0.0,
        "rag_matches": 0,
        "skill_matches": [],
        "sources": [],
    }

    if not (message or "").strip():
        return result

    # ── Signal 1: Vector similarity against past maintenance issues ──
    rag_categories: list[str] = []
    rag_priorities: list[str] = []
    sources: list[dict] = []

    try:
        col = get_maintenance_issues_collection()
        n = col.count()
        if n > 0:
            kwargs: dict = {
                "query_texts": [message.strip()],
                "n_results": min(n_results, max(1, n)),
                "include": ["metadatas", "distances"],
            }
            if property_id is not None:
                try:
                    res = col.query(**{**kwargs, "where": {"property_id": property_id}})
                except Exception:
                    res = col.query(**kwargs)
            else:
                res = col.query(**kwargs)

            metas = (res.get("metadatas") or [[]])[0]
            distances = (res.get("distances") or [[]])[0]

            for i, meta in enumerate(metas):
                if not isinstance(meta, dict):
                    continue
                # ChromaDB distances: lower = more similar (L2 or cosine)
                dist = distances[i] if i < len(distances) else 999
                # Only count reasonably similar results (threshold tunable)
                if dist > 1.5:
                    continue
                cat = meta.get("category", "")
                pri = meta.get("priority", "")
                rid = meta.get("request_id", "?")
                if cat:
                    rag_categories.append(cat)
                if pri:
                    rag_priorities.append(pri)
                sources.append({"request_id": rid, "category": cat, "priority": pri, "distance": round(dist, 3)})
    except Exception as e:
        logger.warning("RAG classification query failed: %s", e)

    # ── Signal 2: Skill symptom phrase matching ──
    skill_trades: list[str] = []
    try:
        from apps.maintenance.models import MaintenanceSkill
        msg_lower = message.lower()
        stop_words = {"not", "is", "my", "a", "the", "in", "it", "i", "and", "or", "to", "of", "on", "at", "no"}
        msg_words = set(msg_lower.split()) - stop_words

        for skill in MaintenanceSkill.objects.filter(is_active=True):
            score = 0
            for phrase in (skill.symptom_phrases or []):
                if str(phrase).lower() in msg_lower:
                    score += 3
            if score == 0:
                for phrase in (skill.symptom_phrases or []):
                    phrase_words = set(str(phrase).lower().split()) - stop_words
                    if msg_words & phrase_words:
                        score += 1
            if score > 0:
                skill_trades.append(skill.trade)
    except Exception as e:
        logger.warning("Skill-based classification failed: %s", e)

    # ── Combine signals: majority vote ──
    all_categories = rag_categories + skill_trades
    all_priorities = rag_priorities

    if all_categories:
        cat_counts = Counter(all_categories)
        winner_cat, winner_count = cat_counts.most_common(1)[0]
        result["category"] = winner_cat
        # Confidence: proportion of votes for the winner
        result["confidence"] = round(winner_count / len(all_categories), 2)
    elif skill_trades:
        result["category"] = Counter(skill_trades).most_common(1)[0][0]
        result["confidence"] = 0.3  # skill-only signal is weaker

    if all_priorities:
        # For priority, bias toward the higher severity (safety-first)
        priority_order = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        pri_counts = Counter(all_priorities)
        # Weight by severity: pick most common, but if "urgent" appears at all, bump up
        winner_pri = pri_counts.most_common(1)[0][0]
        if pri_counts.get("urgent", 0) >= 1 and winner_pri != "urgent":
            # At least one similar issue was urgent — suggest high minimum
            winner_pri = max(winner_pri, "high", key=lambda p: priority_order.get(p, 0))
        result["priority"] = winner_pri

    result["rag_matches"] = len(sources)
    result["skill_matches"] = list(set(skill_trades))
    result["sources"] = sources

    return result


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
        try:
            mi_col = get_maintenance_issues_collection()
            stats["maintenance_issues_chunks"] = mi_col.count()
        except Exception:
            stats["maintenance_issues_chunks"] = 0
        return stats
    except Exception as e:
        return {"collection": COLLECTION_NAME, "chunks": 0, "error": str(e)}
