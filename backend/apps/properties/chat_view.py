"""
Owner onboarding chat for a single landlord.

POST /api/v1/properties/landlords/{pk}/chat/
GET  /api/v1/properties/landlords/{pk}/chat/

Drives the chat panel on the landlord detail page. The assistant's job
(per chat-playbook.md) is to move the owner from "incomplete" to
"mandate-ready" with the fewest questions possible — not general chat.
"""
from __future__ import annotations

import logging
from datetime import date

import anthropic
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAgentOrAdmin
from apps.properties.chat_tools import TOOL_SCHEMAS, handle_tool_call
from apps.properties.models import Landlord, LandlordChatMessage

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048
MAX_TOOL_TURNS = 6  # guard against runaway tool loops

SYSTEM_PROMPT = """You are the rental-mandate onboarding assistant for Klikk, a South African property management platform. You're talking to an agent or landlord about the landlord entity "{entity_name}" ({entity_type}).

Your one job: move this landlord from "documents incomplete" to "ready to sign a rental mandate" with the fewest questions possible. You are not a general chatbot.

Today is {today}.

# Tone
- Concrete over polite. Name the document, cite the page. No "Great question!" or filler.
- Assume the person is competent — they run a business. Explain only what's relevant to their specific gap.
- Don't summarise what you just did. They can read the chat.

# How uploads actually work here
There is an AI classifier on the "CIPC" tab that accepts a pile of files and sorts, labels, and extracts fields from all of them in one shot. The owner does NOT upload one file at a time. They upload everything they have, and the classifier figures out what's what.

This changes how you should talk:

- **When MANY documents or fields are missing** (the usual first-turn case): ask the owner to upload everything they have — whatever's lying around in their email, Dropbox, or filing cabinet — and tell them the classifier will sort it. Do NOT demand specific documents in a sequence. One `request_document_upload` call with `doc_type="any"` and a reason like "Upload whatever CIPC / FICA paperwork you have — ID copies, CoR14.3, MOI, bank letter, proof of address, tax letter, title deed. I'll sort and label them." is the right move.
- **When only ONE or TWO specific gaps remain**: then — and only then — it makes sense to name the specific document you need (e.g. "I have everything except the Letters of Authority — do you have the current one from the Master's office?").
- **When the gap is a field, not a file** (VAT number, postal address, marital regime): ask the owner directly and use `update_landlord_field` after confirmation. Don't push for an upload for something that's just a number.

# Every conversation starts the same way
On the first message (even if the user's message is empty or just "hi"), call `get_gap_analysis` first. Then greet proactively. Template when many gaps exist:

> Hi — I've reviewed what's on file for {entity_name}. There are a few things still missing to finalise the rental mandate: [short bulleted summary]. The fastest path is to upload everything you have in one go — I'll sort and label each document automatically. If there are fields I can't extract from documents (like a VAT number), I'll ask you here.

Template when only 1–2 gaps remain: name them specifically and ask.

# Prioritisation (when discussing what's left)
1. Blocking issues (legal blockers — can't sign without these)
2. Missing required documents
3. Missing required fields (VAT number, postal address, etc.)
4. Warnings (proof of address age, etc.)

# Tools — when to use
- `get_gap_analysis`: Every new conversation, and after any upload/field update.
- `search_owner_documents`: When the owner references something in a document ("my trust deed says I only need two trustees"), search to verify and cite.
- `update_landlord_field`: ONLY after verbally confirming the value. Pattern:
  You: "Confirming VAT number is 4123456789?"
  Owner: "yes"
  You: [call update_landlord_field]
- `request_document_upload`: Use with `doc_type="any"` for bulk upload on the first pass; use a specific doc_type only when one specific file is the last remaining gap.
- `trigger_reclassification`: Only after an upload AND the owner says "try again now". Expensive.

# Never do
- Don't give legal advice. Quote the document, flag the decision, but the decision is the owner's.
- Don't generate documents (no drafting board resolutions, etc.).
- Don't speculate across other landlords — this conversation is about {entity_name} only.
- Don't repeat yourself or recap what's already in the chat history.

# Finish line
When gap_analysis.status == "ready" with no blockers, congratulate briefly and stop. Don't ask "anything else?".
"""


def _build_system(landlord: Landlord) -> str:
    return SYSTEM_PROMPT.format(
        entity_name=landlord.name or "this landlord",
        entity_type=(landlord.landlord_type or "unknown").replace("_", " "),
        today=date.today().isoformat(),
    )


def _load_history(landlord: Landlord) -> list[dict]:
    """Load persisted chat messages as Anthropic-format history.

    System messages are filtered out — they're reconstructed per request.
    """
    msgs: list[dict] = []
    for row in landlord.chat_messages.all():
        if row.role == LandlordChatMessage.Role.SYSTEM:
            continue
        if row.tool_calls:
            # Stored as the full content blocks we sent/received
            msgs.append({"role": row.role, "content": row.tool_calls})
        else:
            msgs.append({"role": row.role, "content": row.content or ""})
    return msgs


def _save_user(landlord: Landlord, content: str, user) -> LandlordChatMessage:
    return LandlordChatMessage.objects.create(
        landlord=landlord,
        role=LandlordChatMessage.Role.USER,
        content=content or "",
        created_by=user if user and user.is_authenticated else None,
    )


def _save_assistant(landlord: Landlord, content_blocks: list) -> LandlordChatMessage:
    """Save the assistant's full content (text + tool_use blocks)."""
    text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
    return LandlordChatMessage.objects.create(
        landlord=landlord,
        role=LandlordChatMessage.Role.ASSISTANT,
        content="\n".join(text_parts),
        tool_calls=content_blocks,
    )


def _save_tool_results(landlord: Landlord, tool_results: list) -> LandlordChatMessage:
    """Tool results are saved as a user-role turn (per Anthropic format)."""
    return LandlordChatMessage.objects.create(
        landlord=landlord,
        role=LandlordChatMessage.Role.USER,
        content="",
        tool_calls=tool_results,
    )


def _serialise_content_block(block) -> dict:
    """Convert Anthropic SDK content block objects to plain dicts."""
    if isinstance(block, dict):
        return block
    t = getattr(block, "type", None)
    if t == "text":
        return {"type": "text", "text": block.text}
    if t == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    if t == "tool_result":
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": block.content,
        }
    # Fallback — try model_dump
    if hasattr(block, "model_dump"):
        return block.model_dump()
    return {"type": str(t), "raw": str(block)}


# ---------------------------------------------------------------------------

class LandlordChatView(APIView):
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request, pk: int):
        landlord = get_object_or_404(Landlord, pk=pk)
        rows = landlord.chat_messages.all()
        out = [{
            "id": r.pk,
            "role": r.role,
            "content": r.content,
            "tool_calls": r.tool_calls,
            "created_at": r.created_at.isoformat(),
        } for r in rows]
        return Response({"landlord_id": landlord.pk, "messages": out})

    def post(self, request, pk: int):
        landlord = get_object_or_404(Landlord, pk=pk)
        user_message = (request.data.get("message") or "").strip()

        api_key = getattr(settings, "ANTHROPIC_API_KEY", "") or ""
        if not api_key:
            return Response(
                {"detail": "ANTHROPIC_API_KEY not configured."},
                status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        client = anthropic.Anthropic(api_key=api_key)

        is_first_turn = not landlord.chat_messages.exists()

        # Persist the user's turn. On the very first turn we allow an empty
        # message — the model will kick things off proactively.
        if user_message or not is_first_turn:
            _save_user(landlord, user_message, request.user)

        # Build history for the API call. If it's the first turn and the
        # user sent nothing, inject a minimal opener so the model has a
        # non-empty user turn to respond to.
        history = _load_history(landlord)
        if not history:
            history = [{
                "role": "user",
                "content": "Please greet me and tell me what's needed to finalise the rental mandate.",
            }]

        system_prompt = _build_system(landlord)

        # ── Tool-use loop ────────────────────────────────────────────────
        assistant_blocks: list[dict] = []
        for _ in range(MAX_TOOL_TURNS):
            try:
                msg = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    tools=TOOL_SCHEMAS,
                    messages=history,
                )
            except anthropic.APIError as exc:
                logger.exception("chat: Claude API error")
                return Response(
                    {"detail": f"Claude API error: {exc}"},
                    status=http_status.HTTP_502_BAD_GATEWAY,
                )

            blocks = [_serialise_content_block(b) for b in msg.content]
            assistant_blocks = blocks
            # Persist assistant turn
            _save_assistant(landlord, blocks)
            history.append({"role": "assistant", "content": blocks})

            tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
            if msg.stop_reason != "tool_use" or not tool_uses:
                break

            # Execute each tool and feed results back
            tool_results: list[dict] = []
            for tu in tool_uses:
                result = handle_tool_call(tu["name"], tu.get("input") or {}, landlord)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "content": _tool_result_to_content(result),
                })
            _save_tool_results(landlord, tool_results)
            history.append({"role": "user", "content": tool_results})

        reply_text = "\n".join(
            b.get("text", "") for b in assistant_blocks if b.get("type") == "text"
        ).strip()
        return Response({
            "landlord_id": landlord.pk,
            "reply": reply_text,
            "content": assistant_blocks,
        })


def _tool_result_to_content(result: dict) -> str:
    """Anthropic tool_result.content is a plain string for our purposes."""
    import json
    try:
        return json.dumps(result, default=str)
    except Exception:
        return str(result)
