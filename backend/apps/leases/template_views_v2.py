"""Lease AI v2 chat endpoint — multi-agent cluster behind SSE.

Per ``docs/system/lease-ai-agent-architecture.md`` decision 17 and §10.2
the v2 endpoint streams SSE events from the Front Door + Drafter +
Reviewer pipeline. The view is ``async def`` so the SSE generator runs
as a native async iterator (not a sync-to-async shim — see
``docs/system/lease-ai-asgi-decision.md`` Option D §3 step 1).

Phase 2 Day 1-2 scope:
  * Build :class:`LeaseContext` from the request body.
  * Run the Front Door → if clarifying-question route, return JSON
    (non-SSE) so the frontend can prompt the user without opening a
    streaming connection.
  * Otherwise start a :class:`LeaseAgentRunner`, dispatch the route
    (Drafter, Reviewer) through it, and emit SSE events.
  * On error, emit an ``event: error`` SSE frame + capture to Sentry,
    then close the stream gracefully.

The pipeline beyond this scaffold (cache-hit telemetry, retry loop,
Formatter, persisted ``AILeaseAgentRun``) lights up over Day 3-7.

Caddy snippet at ``deploy/Caddyfile.lease_ai_v2_handler.snippet``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncIterator

from asgiref.sync import sync_to_async
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.leases.agent_runner import LeaseAgentBudgetExceeded, LeaseAgentRunner
from apps.leases.agents import (
    DrafterHandler,
    DrafterResult,
    FormatterHandler,
    FormatterResult,
    IntentEnum,
    LeaseContext,
    ReviewerHandler,
    ReviewerResult,
    ReviewerTruncatedError,
    build_dispatch,
    classify_intent,
)
from apps.leases.training.cassette import DAY_1_2_CORPUS_HASH
from apps.leases.training.corpus_hash import compute_combined_corpus_hash

logger = logging.getLogger(__name__)


# ── SSE constants ───────────────────────────────────────────────────── #


# Keepalive cadence per §10.2 — intermediaries (CDN, browser dev-proxy)
# garbage-collect idle SSE connections after 30-60s of silence. A 25s
# ``: ping`` comment frame keeps the connection warm without polluting
# the consumer's event stream (comments are ignored by EventSource and
# by the Vue 3 ``fetch + ReadableStream`` consumer).
SSE_KEEPALIVE_SECONDS: float = 25.0


# ── View ────────────────────────────────────────────────────────────── #


@method_decorator(csrf_exempt, name="dispatch")
class LeaseTemplateAIChatV2View(View):
    """``POST /api/v1/leases/templates/<id>/ai-chat-v2/``

    SSE endpoint for the multi-agent lease-AI pipeline. Async-native so
    the generator iterates without serialising other requests on the
    daphne worker.

    Uses plain Django :class:`View` rather than DRF's :class:`APIView`
    because the installed DRF (3.17) doesn't support ``async def``
    handlers — its sync dispatch wraps the coroutine in
    ``finalize_response`` which then crashes. We re-implement the
    JWT auth + agency scoping inline (matches the auth surface of v1's
    :class:`LeaseTemplateAIChatView`).
    """

    http_method_names = ["post", "options"]

    async def post(self, request, template_id: int):
        # ── 1. JWT auth + agency-scoped permission ──────────────── #
        auth_result = await _authenticate_request(request)
        if isinstance(auth_result, HttpResponse):
            return auth_result  # 401 / 403 short-circuit
        # ``request.user`` is populated by ``_authenticate_request``.

        # ── 2. Parse JSON body ──────────────────────────────────── #
        try:
            body = await _parse_json_body(request)
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "Body must be JSON."}, status=400
            )

        user_message = str(body.get("message") or "").strip()
        if not user_message:
            return JsonResponse(
                {"error": "message is required."}, status=400
            )

        # ── 3. Load template (sync_to_async for ORM) ─────────────── #
        try:
            template = await _load_template_for_request(request, template_id)
        except _TemplateNotFound:
            return JsonResponse(
                {"error": "Template not found."}, status=404
            )

        # ── 4. Build LeaseContext from request + template ───────── #
        context = _build_context(
            template=template,
            body=body,
            user_message=user_message,
        )

        # ── 5. Front Door dispatch (pure Python) ────────────────── #
        dispatch = build_dispatch(context)

        # ── 6. Clarifying question path → JSON, not SSE ──────────── #
        if dispatch.clarifying_question is not None:
            return JsonResponse(
                {
                    "kind": "clarifying_question",
                    "question": dispatch.clarifying_question,
                    "intent": dispatch.intent_label,
                },
                status=200,
            )

        # ── 7. Build the runner (with corpus version) ────────────── #
        request_id = body.get("request_id") or str(uuid.uuid4())
        corpus_version = compute_combined_corpus_hash() or DAY_1_2_CORPUS_HASH
        anthropic_client = _build_anthropic_client()

        runner = LeaseAgentRunner(
            request_id=str(request_id),
            intent=dispatch.intent_label,
            anthropic_client=anthropic_client,
            lease_id=None,
            corpus_version=corpus_version,
        )

        # ── 8. SSE response ─────────────────────────────────────── #
        generator = _sse_pipeline(
            runner=runner,
            dispatch=dispatch,
            context=context,
            request_id=str(request_id),
        )
        response = StreamingHttpResponse(
            generator,
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache, no-transform"
        response["X-Accel-Buffering"] = "no"
        response["Connection"] = "keep-alive"
        return response


# ── Helpers ─────────────────────────────────────────────────────────── #


class _TemplateNotFound(Exception):
    """Internal helper exception — keeps the view body flat."""


@sync_to_async
def _load_template_for_request(request, template_id: int):
    """Resolve the agency-scoped template or raise _TemplateNotFound.

    Imports happen inside the function so the module's top-level import
    list stays cheap (no Django ORM imported at module load time).
    """
    from apps.leases.models import LeaseTemplate
    from apps.leases.template_views import _scoped_lease_templates

    try:
        return _scoped_lease_templates(request).get(pk=template_id)
    except LeaseTemplate.DoesNotExist as exc:
        raise _TemplateNotFound() from exc


async def _authenticate_request(request) -> Any:
    """Authenticate the request via JWT (Authorization: Bearer ...).

    On success: sets ``request.user`` to the authenticated User and
    returns ``None``. On failure: returns a ``JsonResponse`` with the
    appropriate 401/403 — the view short-circuits on a Response-typed
    return value.

    The same auth pattern as v1's :class:`LeaseTemplateAIChatView`:
    ``IsAuthenticated`` + ``IsAgentOrAdmin``. We hand-roll it because
    DRF's APIView dispatch is sync (see class docstring rationale).
    """
    user = await sync_to_async(_resolve_user_from_request)(request)
    if user is None:
        return JsonResponse(
            {"detail": "Authentication credentials were not provided."},
            status=401,
        )
    if not await sync_to_async(_user_is_agent_or_admin)(user):
        return JsonResponse(
            {"detail": "You do not have permission to perform this action."},
            status=403,
        )
    request.user = user
    return None


def _resolve_user_from_request(request) -> Any | None:
    """JWT-bearer resolver. Mirrors simplejwt's authentication class.

    The async test client passes ASGI-style header names — ``Authorization``
    lands in ``request.headers`` (case-insensitive) reliably across both
    WSGI and ASGI paths, so we read it from there.
    """
    # ``request.headers`` is the canonical, case-insensitive accessor.
    auth_header = (
        request.headers.get("Authorization")
        or request.META.get("HTTP_AUTHORIZATION")
        or ""
    )
    if not auth_header.lower().startswith("bearer "):
        return None
    raw_token = auth_header.split(" ", 1)[1].strip()
    if not raw_token:
        return None
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication

        authenticator = JWTAuthentication()
        validated = authenticator.get_validated_token(raw_token)
        return authenticator.get_user(validated)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Lease AI v2 JWT auth failed: %s", exc)
        return None


def _user_is_agent_or_admin(user: Any) -> bool:
    """Mirror :class:`apps.accounts.permissions.IsAgentOrAdmin`.

    The permission class accepts ADMIN and AGENCY_ADMIN; this helper
    is sync so it can run inside ``sync_to_async`` without re-entering
    the ORM in a coroutine context.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    role = getattr(user, "role", None)
    try:
        from apps.accounts.models import User

        return role in {User.Role.ADMIN, User.Role.AGENCY_ADMIN}
    except Exception:  # noqa: BLE001
        return False


async def _parse_json_body(request) -> dict[str, Any]:
    """Parse the request body as JSON. ``await`` the body bytes safely."""
    body_bytes = request.body
    if not body_bytes:
        return {}
    if isinstance(body_bytes, bytes):
        body_text = body_bytes.decode("utf-8")
    else:
        body_text = str(body_bytes)
    data = json.loads(body_text)
    if not isinstance(data, dict):
        return {}
    return data


def _build_context(
    *,
    template: Any,
    body: dict[str, Any],
    user_message: str,
) -> LeaseContext:
    """Build the :class:`LeaseContext` from the request body.

    The frontend provides intent + structured context; if intent isn't
    supplied we fall back to the Python classifier in
    :func:`classify_intent`.
    """
    intent_raw = body.get("intent")
    if intent_raw:
        try:
            intent = IntentEnum(str(intent_raw))
        except ValueError:
            intent = classify_intent(user_message)
    else:
        intent = classify_intent(user_message)

    chat_history_raw = body.get("chat_history") or []
    chat_history: tuple[dict[str, str], ...] = tuple(
        {"role": str(t.get("role", "user")), "content": str(t.get("content", ""))}
        for t in chat_history_raw
        if isinstance(t, dict)
    )

    template_html = ""
    if hasattr(template, "content_html"):
        try:
            from apps.leases.template_views import _extract_html

            template_html = _extract_html(template.content_html or "")
        except Exception:  # noqa: BLE001 — never fail the request on HTML extraction
            template_html = template.content_html or ""

    conditions = body.get("conditions") or []
    conditions_tuple: tuple[str, ...] = tuple(
        str(c) for c in conditions if isinstance(c, (str, int))
    )

    return LeaseContext(
        intent=intent,
        user_message=user_message,
        property_type=_opt_str(body.get("property_type")),
        tenant_count=_opt_int(body.get("tenant_count")),
        lease_type=_opt_str(body.get("lease_type")),
        lease_term_months=_opt_int(body.get("lease_term_months")),
        deposit_amount=_opt_float(body.get("deposit_amount")),
        monthly_rent=_opt_float(body.get("monthly_rent")),
        province=_opt_str(body.get("province")),
        conditions=conditions_tuple,
        with_case_law=bool(body.get("with_case_law")),
        fast_mode=bool(body.get("fast_mode")),
        template_html=template_html,
        chat_history=chat_history,
    )


def _opt_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _opt_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _opt_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_anthropic_client():
    """Construct the live ``anthropic.Anthropic`` client.

    The cassette battery uses :class:`CassetteAnthropicClient` injected
    directly into the runner, NOT through this helper. This builder is
    only hit by real HTTP traffic. The import is lazy so unit tests can
    monkey-patch the symbol without anthropic installed.
    """
    try:
        import anthropic  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001
        return None

    from apps.leases.template_views import _get_anthropic_api_key

    api_key = _get_anthropic_api_key()
    if not api_key:
        return None
    return anthropic.Anthropic(api_key=api_key, timeout=120.0)


# ── SSE generator ───────────────────────────────────────────────────── #


def _sse(event: str, data: dict[str, Any]) -> bytes:
    """Format one SSE frame.

    ``data:`` lines are JSON-encoded; ``event:`` precedes them; the
    frame is terminated by an empty line per the SSE spec.
    """
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {body}\n\n".encode("utf-8")


def _ping() -> bytes:
    """SSE comment frame — keeps the connection warm. Consumers ignore it."""
    return b": ping\n\n"


async def _sse_pipeline(
    *,
    runner: LeaseAgentRunner,
    dispatch: Any,
    context: LeaseContext,
    request_id: str,
) -> AsyncIterator[bytes]:
    """Yield SSE events for the full Drafter (+ Reviewer) pipeline.

    Wrapped end-to-end in a try/except so any exception emits a final
    ``event: error`` frame + Sentry capture before the stream closes.
    """
    t0 = time.monotonic()
    drafter_result: DrafterResult | None = None
    reviewer_result: ReviewerResult | None = None
    formatter_result: FormatterResult | None = None

    yield _sse(
        "status",
        {
            "phase": "front_door",
            "message": (
                f"Routing intent={dispatch.intent_label} → {'+'.join(dispatch.route) or 'none'}."
            ),
            "request_id": request_id,
        },
    )

    try:
        # Drafter pass
        if "drafter" in dispatch.route:
            yield _sse(
                "agent_started",
                {"agent": "drafter", "phase": "drafting", "request_id": request_id},
            )
            drafter_result = await sync_to_async(_run_drafter, thread_sensitive=False)(
                runner=runner,
                context=context,
                system_blocks=dispatch.system_blocks,
            )
            for tc in drafter_result.tool_calls:
                yield _sse(
                    "tool_use",
                    {
                        "agent": "drafter",
                        "tool_name": tc.get("name"),
                        "input_summary": _summarise_tool_input(tc.get("input")),
                    },
                )
            if drafter_result.conversational_reply:
                yield _sse(
                    "text_chunk",
                    {
                        "agent": "drafter",
                        "text": drafter_result.conversational_reply,
                    },
                )
            yield _sse(
                "agent_finished",
                {
                    "agent": "drafter",
                    "llm_calls": drafter_result.internal_turns,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                },
            )

        # Hand-off
        if "reviewer" in dispatch.route:
            yield _sse(
                "agent_handoff",
                {
                    "from_agent": "drafter" if drafter_result else "front_door",
                    "to_agent": "reviewer",
                    "reason": "gate",
                },
            )
            yield _sse(
                "agent_started",
                {"agent": "reviewer", "phase": "audit", "request_id": request_id},
            )
            document_html = (
                drafter_result.rendered_html if drafter_result else context.template_html
            )
            reviewer_result = await sync_to_async(_run_reviewer, thread_sensitive=False)(
                runner=runner,
                context=context,
                document_html=document_html,
                system_blocks=dispatch.system_blocks,
            )
            yield _sse(
                "audit_report",
                {
                    "agent": "reviewer",
                    "verdict": reviewer_result.verdict,
                    "summary": reviewer_result.summary,
                    "report": reviewer_result.raw_input,
                },
            )
            yield _sse(
                "agent_finished",
                {
                    "agent": "reviewer",
                    "llm_calls": reviewer_result.internal_turns,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                },
            )

        # Formatter pass — runs after Reviewer for generate + format intents;
        # skipped for audit (read-only, no reformatting).
        if "formatter" in dispatch.route:
            yield _sse(
                "agent_handoff",
                {
                    "from_agent": "reviewer" if reviewer_result else (
                        "drafter" if drafter_result else "front_door"
                    ),
                    "to_agent": "formatter",
                    "reason": "layout",
                },
            )
            yield _sse(
                "agent_started",
                {"agent": "formatter", "phase": "formatting", "request_id": request_id},
            )
            # Use the most up-to-date HTML (post-Reviewer if it ran, else post-Drafter).
            document_for_formatter = (
                drafter_result.rendered_html
                if drafter_result
                else context.template_html
            )
            formatter_result = await sync_to_async(
                _run_formatter, thread_sensitive=False
            )(
                runner=runner,
                context=context,
                document_html=document_for_formatter,
                system_blocks=dispatch.system_blocks,
            )
            for tc in formatter_result.tool_calls:
                yield _sse(
                    "tool_use",
                    {
                        "agent": "formatter",
                        "tool_name": tc.get("name"),
                        "input_summary": _summarise_tool_input(tc.get("input")),
                    },
                )
            # text_chunk carries the change summary (not the document body)
            if formatter_result.applied_changes:
                summary_text = "; ".join(formatter_result.applied_changes)
                yield _sse(
                    "text_chunk",
                    {"agent": "formatter", "text": summary_text},
                )
            elif formatter_result.conversational_reply:
                yield _sse(
                    "text_chunk",
                    {"agent": "formatter", "text": formatter_result.conversational_reply},
                )
            yield _sse(
                "agent_finished",
                {
                    "agent": "formatter",
                    "llm_calls": formatter_result.internal_turns,
                    "changes_applied": len(formatter_result.applied_changes),
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                },
            )

        # Resolve final document HTML (post-Formatter if it ran, else post-Drafter).
        final_html = (
            formatter_result.html
            if formatter_result is not None
            else (
                drafter_result.rendered_html
                if drafter_result
                else context.template_html
            )
        )

        # Final done frame
        yield _sse(
            "done",
            {
                "reply": (
                    drafter_result.conversational_reply
                    if drafter_result and drafter_result.conversational_reply
                    else (reviewer_result.summary if reviewer_result else "")
                ),
                "html": final_html,
                "total_calls": runner.llm_call_count,
                "total_latency_ms": int((time.monotonic() - t0) * 1000),
                "total_cost_usd": round(runner.running_cost_usd, 6),
                "corpus_version": runner.corpus_version,
                "terminated_reason": runner.terminated_reason or "completed",
                "request_id": request_id,
            },
        )

        # Persist AILeaseAgentRun row BEFORE the stream closes so a
        # frontend that listens for ``audit_persisted`` can query the
        # audit trail by request_id immediately after ``done``.
        async for frame in _finalize_and_emit(
            runner=runner,
            request_id=request_id,
            terminated_reason="completed",
        ):
            yield frame

    except LeaseAgentBudgetExceeded as exc:
        logger.warning(
            "Lease AI v2: budget exceeded — reason=%s request_id=%s",
            exc.terminated_reason,
            request_id,
        )
        yield _sse(
            "error",
            {
                "message": f"Pipeline halted: {exc.terminated_reason}.",
                "recoverable": True,
                "terminated_reason": exc.terminated_reason,
            },
        )
        async for frame in _finalize_and_emit(
            runner=runner,
            request_id=request_id,
            terminated_reason=exc.terminated_reason,
        ):
            yield frame
    except ReviewerTruncatedError as exc:
        _capture_exception(exc)
        yield _sse(
            "error",
            {
                "message": "Reviewer truncated — please retry.",
                "recoverable": True,
                "terminated_reason": "reviewer_truncated",
            },
        )
        async for frame in _finalize_and_emit(
            runner=runner,
            request_id=request_id,
            terminated_reason="error",
        ):
            yield frame
    except Exception as exc:  # noqa: BLE001 — last-resort SSE error
        logger.exception(
            "Lease AI v2 unhandled error request_id=%s", request_id
        )
        _capture_exception(exc)
        yield _sse(
            "error",
            {
                "message": "Internal error in pipeline.",
                "recoverable": False,
            },
        )
        async for frame in _finalize_and_emit(
            runner=runner,
            request_id=request_id,
            terminated_reason="error",
        ):
            yield frame


async def _finalize_and_emit(
    *,
    runner: LeaseAgentRunner,
    request_id: str,
    terminated_reason: str,
) -> AsyncIterator[bytes]:
    """Persist the ``AILeaseAgentRun`` row and emit ``audit_persisted``.

    Wrapped in try/except so a persistence failure never breaks the SSE
    stream — we log + skip the event but still close the stream cleanly.
    """
    try:
        run = await sync_to_async(runner.finalize, thread_sensitive=False)(
            terminated_reason=terminated_reason
        )
    except Exception as exc:  # noqa: BLE001 — never raise out of SSE
        logger.exception(
            "Lease AI v2: runner.finalize failed request_id=%s", request_id
        )
        _capture_exception(exc)
        return

    yield _sse(
        "audit_persisted",
        {
            "run_id": str(getattr(run, "pk", "") or ""),
            "request_id": getattr(run, "request_id", request_id),
            "terminated_reason": getattr(run, "terminated_reason", terminated_reason),
        },
    )


def _run_drafter(
    *,
    runner: LeaseAgentRunner,
    context: LeaseContext,
    system_blocks: list[dict[str, Any]],
) -> DrafterResult:
    """Sync helper so we can ``sync_to_async`` the call."""
    handler = DrafterHandler()
    return handler.run(runner=runner, context=context, system_blocks=system_blocks)


def _run_reviewer(
    *,
    runner: LeaseAgentRunner,
    context: LeaseContext,
    document_html: str,
    system_blocks: list[dict[str, Any]],
) -> ReviewerResult:
    """Sync helper so we can ``sync_to_async`` the call."""
    handler = ReviewerHandler()
    return handler.run(
        runner=runner,
        context=context,
        document_html=document_html,
        system_blocks=system_blocks,
    )


def _run_formatter(
    *,
    runner: LeaseAgentRunner,
    context: LeaseContext,
    document_html: str,
    system_blocks: list[dict[str, Any]],
) -> FormatterResult:
    """Sync helper so we can ``sync_to_async`` the call."""
    handler = FormatterHandler()
    return handler.run(
        runner=runner,
        context=context,
        document_html=document_html,
        system_blocks=system_blocks,
    )


def _summarise_tool_input(input_dict: Any) -> str:
    """Render a 1-line summary of a tool_use input for SSE telemetry."""
    if not isinstance(input_dict, dict):
        return ""
    keys = list(input_dict.keys())
    return ", ".join(keys[:6])


def _capture_exception(exc: Exception) -> None:
    """Best-effort Sentry capture — never raises."""
    try:
        import sentry_sdk  # type: ignore[import-not-found]

        sentry_sdk.capture_exception(exc)
    except Exception:  # noqa: BLE001
        pass


# ── Optional keepalive task ─────────────────────────────────────────── #


async def _keepalive(queue: asyncio.Queue[bytes], stop: asyncio.Event) -> None:
    """Background coroutine for the keepalive pings.

    Currently unused: the Day 1-2 pipeline finishes well inside the
    SSE_KEEPALIVE_SECONDS interval, so the simple sequential generator
    never goes idle. The hook is here so Phase 3 can wire a long-running
    Formatter / RAG path without rewriting the SSE surface.
    """
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=SSE_KEEPALIVE_SECONDS)
        except asyncio.TimeoutError:
            await queue.put(_ping())


__all__ = ["LeaseTemplateAIChatV2View"]
