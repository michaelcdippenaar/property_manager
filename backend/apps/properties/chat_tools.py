"""
Anthropic tool-use definitions + server-side handlers for the landlord chat.

All tools are scoped to a single landlord — callers pass `landlord_id` into
the handler, never trusting the model to supply it. This prevents the chat
from leaking or editing data across tenants of the platform.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.properties.models import Landlord
from apps.properties.gap_analysis import compute_gap_analysis
from core import owner_rag

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool schemas (sent to Claude)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "search_owner_documents",
        "description": (
            "Semantic search across this landlord's uploaded FICA/CIPC documents. "
            "Use whenever you need to cite a clause, verify the owner's claim, or find "
            "a value that should be on a document (e.g. 'who are the current trustees', "
            "'what does the MOI say about signing'). Always cite by filename and page."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query.",
                },
                "doc_type": {
                    "type": "string",
                    "description": "Optional filter to one doc type (e.g. 'letters_of_authority', 'moi').",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_gap_analysis",
        "description": (
            "Return the current readiness snapshot for this landlord against a scenario "
            "(default: rental_mandate). Use on the first message of every conversation, "
            "and after any upload/field change, to know what's still missing. Cheap."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario": {
                    "type": "string",
                    "enum": ["rental_mandate", "purchase"],
                    "description": "Which readiness scenario to compute. V1 supports rental_mandate.",
                },
            },
        },
    },
    {
        "name": "update_landlord_field",
        "description": (
            "Write a confirmed factual value to the Landlord record. NEVER call this "
            "without first verbally confirming the value with the owner in the previous "
            "message — an incorrect VAT number on a mandate is a real-world problem."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "enum": [
                        "name", "registration_number", "vat_number", "id_number",
                        "email", "phone",
                        "representative_name", "representative_id_number",
                        "representative_email", "representative_phone",
                    ],
                    "description": "The Landlord model field to update.",
                },
                "value": {
                    "type": "string",
                    "description": "The confirmed value. Must match exactly what the owner confirmed.",
                },
            },
            "required": ["field", "value"],
        },
    },
    {
        "name": "request_document_upload",
        "description": (
            "Surface an upload call-to-action in the chat UI. Use when the gap is a "
            "file, not a field. The `reason` appears on the button tooltip so the owner "
            "knows why we need it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "description": "Snake-case doc type key, e.g. 'letters_of_authority', 'bank_confirmation', 'moi'.",
                },
                "reason": {
                    "type": "string",
                    "description": "Short human-readable reason the UI shows next to the button.",
                },
            },
            "required": ["doc_type", "reason"],
        },
    },
    {
        "name": "trigger_reclassification",
        "description": (
            "Re-run the AI document classifier on this landlord's folder. Expensive — "
            "only call after the owner has uploaded a new file AND explicitly asked to "
            "'try again' or similar. Never speculative."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

_ALLOWED_FIELDS = {
    "name", "registration_number", "vat_number", "id_number",
    "email", "phone",
    "representative_name", "representative_id_number",
    "representative_email", "representative_phone",
}


def handle_tool_call(name: str, tool_input: dict, landlord: Landlord) -> dict:
    """Dispatch a single tool call. Returns JSON-serialisable dict.

    Every handler is scoped to the caller-provided `landlord` — the model
    cannot target a different landlord even if it tried.
    """
    try:
        if name == "search_owner_documents":
            return _tool_search(landlord, tool_input)
        if name == "get_gap_analysis":
            return _tool_gap_analysis(landlord, tool_input)
        if name == "update_landlord_field":
            return _tool_update_field(landlord, tool_input)
        if name == "request_document_upload":
            return _tool_request_upload(landlord, tool_input)
        if name == "trigger_reclassification":
            return _tool_trigger_reclassification(landlord, tool_input)
    except Exception as exc:
        logger.exception("chat_tools: handler %s failed", name)
        return {"error": f"Tool {name} failed: {exc}"}
    return {"error": f"Unknown tool: {name}"}


def _tool_search(landlord: Landlord, args: dict) -> dict:
    query = (args.get("query") or "").strip()
    if not query:
        return {"error": "query is required"}
    doc_type = args.get("doc_type") or None
    results = owner_rag.query_owner_documents(
        query=query,
        landlord_id=landlord.pk,
        doc_type=doc_type,
        n_results=5,
    )
    hits = []
    for r in results:
        meta = r.get("metadata") or {}
        hits.append({
            "filename": meta.get("filename"),
            "doc_type": meta.get("doc_type"),
            "page": meta.get("page_number"),
            "text": (r.get("text") or "")[:1200],
            "distance": r.get("distance"),
        })
    return {"hits": hits, "count": len(hits)}


def _tool_gap_analysis(landlord: Landlord, args: dict) -> dict:
    scenario = args.get("scenario") or "rental_mandate"
    result = compute_gap_analysis(landlord, scenario)
    if result is None:
        return {
            "scenario": scenario,
            "note": "Not computed — scenario is reserved for v2.",
        }
    return {"scenario": scenario, **result}


def _tool_update_field(landlord: Landlord, args: dict) -> dict:
    field = (args.get("field") or "").strip()
    value = args.get("value")
    if field not in _ALLOWED_FIELDS:
        return {"error": f"Field '{field}' is not updatable via chat."}
    if value is None:
        return {"error": "value is required"}
    value = str(value).strip()
    old = getattr(landlord, field, None)
    setattr(landlord, field, value)
    landlord.save(update_fields=[field, "updated_at"])
    logger.info(
        "chat_tools: landlord %s field %s updated old=%r new=%r",
        landlord.pk, field, old, value,
    )
    return {"ok": True, "field": field, "old_value": old, "new_value": value}


def _tool_request_upload(landlord: Landlord, args: dict) -> dict:
    """UI-only: the tool result is surfaced to the frontend, which renders
    the CTA. Backend doesn't create anything yet."""
    doc_type = (args.get("doc_type") or "").strip()
    reason = (args.get("reason") or "").strip()
    if not doc_type:
        return {"error": "doc_type is required"}
    return {
        "ui_action": "request_upload",
        "doc_type": doc_type,
        "reason": reason,
        "landlord_id": landlord.pk,
    }


def _tool_trigger_reclassification(landlord: Landlord, args: dict) -> dict:
    """Re-enqueue the RAG ingestion. Full re-classify via Claude Vision
    remains a separate endpoint — this just refreshes retrieval so gap
    analysis is accurate. If/when a dedicated reclassify task is added
    server-side, wire it here."""
    from apps.properties.tasks import enqueue_owner_ingestion
    enqueue_owner_ingestion(landlord.pk)
    return {
        "ok": True,
        "note": "Re-ingestion enqueued. For full AI re-classification, hit POST /landlords/{id}/classify/.",
    }
