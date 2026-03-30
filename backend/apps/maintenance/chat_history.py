from __future__ import annotations

from typing import Iterable

from apps.maintenance.models import MaintenanceActivity, MaintenanceRequest


def persist_chat_history_to_request(
    request_obj: MaintenanceRequest,
    messages: Iterable[dict],
    *,
    created_by=None,
    session_id: int | None = None,
    source: str = "chat_history",
) -> int:
    """
    Copy chat-style messages into MaintenanceActivity rows so the issue detail
    page can display the transcript.

    Assistant messages are stored as system/AI entries (`created_by=None`,
    metadata.source='ai_agent'). Human messages are stored against `created_by`.
    Non-conversational helper cards from the monitor UI (e.g. skills, confirm)
    are skipped.

    **Deduplication:** Messages whose `chat_message_id` has already been
    persisted for this request are skipped so the function is safe to call
    on every chat turn (not just ticket creation).
    """
    # Build a set of chat_message_ids already persisted for this request
    existing_ids = set(
        MaintenanceActivity.objects.filter(
            request=request_obj,
            metadata__chat_source=source,
        )
        .exclude(metadata__chat_message_id=None)
        .values_list("metadata__chat_message_id", flat=True)
    )

    created = 0
    for msg in messages or []:
        role = (msg.get("role") or "").strip().lower()
        kind = (msg.get("type") or "").strip().lower()
        content = (msg.get("content") or "").strip()
        if not content or kind in {"skills", "confirm"}:
            continue

        # Skip messages already persisted (dedup by chat_message_id)
        msg_id = msg.get("id")
        if msg_id is not None and msg_id in existing_ids:
            continue

        is_ai = role == "assistant"
        metadata = {
            "source": "ai_agent" if is_ai else "user",
            "chat_source": source,
            "chat_role": role or ("assistant" if is_ai else "user"),
        }
        if session_id is not None:
            metadata["chat_session_id"] = session_id
        if msg_id is not None:
            metadata["chat_message_id"] = msg_id

        MaintenanceActivity.objects.create(
            request=request_obj,
            activity_type=MaintenanceActivity.ActivityType.NOTE,
            message=content,
            created_by=None if is_ai else created_by,
            metadata=metadata,
        )
        created += 1

    return created
