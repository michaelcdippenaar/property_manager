"""
AI-powered conversational lease builder.

Endpoints:
  POST /api/v1/leases/builder/sessions/              — create session
  POST /api/v1/leases/builder/sessions/{id}/message/ — chat turn
  POST /api/v1/leases/builder/sessions/{id}/finalize/ — create Lease from session
"""
import json
import os
import re
from datetime import date
from functools import lru_cache

import anthropic
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import IsAgentOrAdmin
from apps.accounts.decorators import requires_feature
from apps.properties.access import get_accessible_property_ids
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.scoping import _is_admin
from .models import LeaseBuilderSession, LeaseTemplate, Lease
from .import_view import ImportLeaseView, _get_or_create_person
from .template_views import _get_anthropic_api_key, _scoped_lease_templates


def _scoped_builder_sessions(request):
    """LeaseBuilderSession queryset scoped to the caller's agency."""
    user = getattr(request, "user", None)
    qs = LeaseBuilderSession.objects.all()
    if _is_admin(user):
        return qs
    agency_id = getattr(user, "agency_id", None) if user else None
    if agency_id is None:
        return qs.none()
    return qs.filter(agency_id=agency_id)


def _scoped_leases(request):
    """Lease queryset scoped to the caller's agency."""
    user = getattr(request, "user", None)
    qs = Lease.objects.all()
    if _is_admin(user):
        return qs
    agency_id = getattr(user, "agency_id", None) if user else None
    if agency_id is None:
        return qs.none()
    return qs.filter(agency_id=agency_id)


# Path to the legal reference maintained in .claude/skills/
_LEGAL_REF_PATH = os.path.join(
    settings.BASE_DIR,          # backend/
    "..",                       # project root
    ".claude", "skills", "rental-agreement", "references", "sa-rental-law.md",
)


@lru_cache(maxsize=1)
def _load_legal_reference() -> str:
    """Load sa-rental-law.md once and cache it for the process lifetime."""
    path = os.path.normpath(_LEGAL_REF_PATH)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""  # degrade gracefully if file is missing


REQUIRED_FIELDS = [
    "landlord_name",
    "property_address",
    "unit_number",
    "tenant_name",
    "lease_start",
    "lease_end",
    "monthly_rent",
    "deposit",
    "notice_period_days",
]

BUILDER_SYSTEM_PROMPT = """You are an expert South African residential lease drafter helping a landlord or agent build a legally compliant lease agreement.

Your job: guide them through filling in all required fields by having a friendly, efficient conversation. Ask ONE focused question at a time.

## South African Legal Reference
{legal_reference}

## Current Session State
Extracted fields so far:
{state_json}

Required fields still missing:
{missing_fields}

## Instructions
1. Extract any field values mentioned in the user's message and merge them into `updated_state`.
2. Validate compliance using the legal reference above:
   - deposit must be <= 2 × monthly_rent (RHA s5(3)(g))
   - notice_period_days must be >= 30 / ~20 business days (RHA s5(3)(c))
   - lease term must not exceed 24 months without tenant's explicit request (CPA s14)
   - lease_end must be after lease_start
   - cancellation penalty must be reasonable, not full remaining rent (CPA s48)
3. Flag any violations in `rha_flags` as {{"field": "...", "severity": "error|warning", "message": "plain English explanation citing the relevant section"}}.
4. If nothing is missing and no errors exist, set `ready_to_finalize: true` and `next_question: null`.
5. For each tenant (primary and co-tenants), ask for their **payment reference** — the unique string the tenant should use when paying rent (e.g. "18 Irene - Smith"). The primary tenant's ref is `payment_reference` on the lease state; co-tenants each have a `payment_reference` field on their object in `co_tenants[]`. Don't volunteer a default — ask the user.
6. Keep your reply conversational and brief (1-2 sentences max). Never repeat information the user already provided.

Respond with ONLY valid JSON — no markdown, no preamble:
{{
  "reply": "...",
  "updated_state": {{...all extracted fields merged with existing state...}},
  "rha_flags": [...],
  "next_question": "... or null",
  "ready_to_finalize": false
}}"""


def _missing_required(state: dict) -> list[str]:
    return [f for f in REQUIRED_FIELDS if not state.get(f)]


def _call_claude(system: str, messages: list) -> dict:
    client = anthropic.Anthropic(api_key=_get_anthropic_api_key())
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    raw = resp.content[0].text.strip()

    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Best-effort repair: ask Claude to fix it
        repair_resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system="Output only valid JSON. No markdown, no explanation.",
            messages=[{"role": "user", "content": f"Fix this malformed JSON:\n{raw}"}],
        )
        return json.loads(repair_resp.content[0].text.strip())


class LeaseBuilderDraftListView(APIView):
    """GET /api/v1/leases/builder/drafts/ — list user's draft sessions."""
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        drafts = _scoped_builder_sessions(request).filter(
            created_by=request.user,
            status__in=[LeaseBuilderSession.Status.DRAFTING, LeaseBuilderSession.Status.REVIEW],
        ).values("id", "current_state", "status", "updated_at", "template_id")
        results = []
        for d in drafts:
            state = d["current_state"] or {}
            # Build a human-readable summary line
            form = state.get("form", state)  # form_state wraps in "form" key
            prop_name = ""
            tenant_name = ""
            if isinstance(form.get("property"), dict):
                prop_name = form["property"].get("name", "")
            elif isinstance(state.get("selectedUnit"), dict):
                prop_name = state["selectedUnit"].get("propertyName", "")
            if isinstance(form.get("primary_tenant"), dict):
                tenant_name = form["primary_tenant"].get("full_name", "")
            parts = [p for p in [prop_name, tenant_name] if p]
            summary = " — ".join(parts) if parts else "Untitled draft"

            results.append({
                "id": d["id"],
                "status": d["status"],
                "updated_at": d["updated_at"],
                "template_id": d["template_id"],
                "summary": summary,
                "current_state": state,
            })
        return Response(results)


class LeaseBuilderDraftSaveView(APIView):
    """
    PUT /api/v1/leases/builder/drafts/{id}/ — save form state to a draft.
    POST /api/v1/leases/builder/drafts/ — create a new draft.
    """
    permission_classes = [IsAgentOrAdmin]

    def post(self, request):
        template_id = request.data.get("template_id")
        template = None
        if template_id:
            try:
                template = _scoped_lease_templates(request).get(pk=template_id)
            except LeaseTemplate.DoesNotExist:
                pass

        agency_id = getattr(request.user, "agency_id", None)
        if agency_id is None and not _is_admin(request.user):
            return Response(
                {"detail": "Your user account is not linked to an agency. Contact your administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session = LeaseBuilderSession.objects.create(
            agency_id=agency_id,
            created_by=request.user,
            template=template,
            messages=[],
            current_state=request.data.get("form_state", {}),
            rha_flags=[],
        )
        return Response({"id": session.id}, status=status.HTTP_201_CREATED)

    def put(self, request, pk=None):
        if not pk:
            return Response({"error": "Draft ID required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = _scoped_builder_sessions(request).get(pk=pk, created_by=request.user)
        except LeaseBuilderSession.DoesNotExist:
            return Response({"error": "Draft not found."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == LeaseBuilderSession.Status.FINALIZED:
            return Response({"error": "Cannot update a finalized session."}, status=status.HTTP_400_BAD_REQUEST)

        session.current_state = request.data.get("form_state", session.current_state)
        if "template_id" in request.data:
            session.template_id = request.data["template_id"]
        session.save(update_fields=["current_state", "template_id", "updated_at"])
        return Response({"id": session.id, "updated_at": session.updated_at})

    def delete(self, request, pk=None):
        if not pk:
            return Response({"error": "Draft ID required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            session = _scoped_builder_sessions(request).get(pk=pk, created_by=request.user)
        except LeaseBuilderSession.DoesNotExist:
            return Response({"error": "Draft not found."}, status=status.HTTP_404_NOT_FOUND)
        if session.status == LeaseBuilderSession.Status.FINALIZED:
            return Response({"error": "Cannot delete a finalized session."}, status=status.HTTP_400_BAD_REQUEST)
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeaseBuilderSessionCreateView(APIView):
    """POST /api/v1/leases/builder/sessions/ — start a new builder session.

    Optional body:
      existing_lease_id (int) — pre-populate session state from an existing lease.
      template_id       (int) — use a specific template (defaults to active template).
    """
    permission_classes = [IsAgentOrAdmin]

    @requires_feature("ai_lease_generation")
    def post(self, request):
        # Resolve template — explicit ID takes priority, else fall back to active
        template_id = request.data.get("template_id")
        scoped_templates = _scoped_lease_templates(request)
        if template_id:
            try:
                template = scoped_templates.get(pk=template_id)
            except LeaseTemplate.DoesNotExist:
                return Response({"error": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            template = scoped_templates.filter(is_active=True).first()

        # Pre-populate state from an existing lease if requested
        initial_state = {}
        existing_lease_id = request.data.get("existing_lease_id")
        if existing_lease_id:
            try:
                lease = _scoped_leases(request).select_related(
                    "unit__property"
                ).prefetch_related("co_tenants__person").get(pk=existing_lease_id)
            except Lease.DoesNotExist:
                return Response(
                    {"error": "Lease not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # IDOR guard: the requesting user must have access to the property that
            # owns this lease.  Uses the canonical helper so that AGENCY_ADMIN,
            # co-managing agents (PropertyAgentAssignment), ACCOUNTANT, VIEWER, and
            # ADMIN are all respected.  Return 403 (not 404) to avoid enumeration —
            # the resource exists, the caller is simply not permitted to access it.
            # Defence-in-depth: treat a missing unit/property as forbidden too.
            if not (lease.unit and lease.unit.property):
                return Response(
                    {"error": "You do not have permission to access this lease."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            accessible_property_ids = set(get_accessible_property_ids(request.user))
            if lease.unit.property_id not in accessible_property_ids:
                return Response(
                    {"error": "You do not have permission to access this lease."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            initial_state = _lease_to_state(lease)

        agency_id = getattr(request.user, "agency_id", None)
        if agency_id is None and not _is_admin(request.user):
            return Response(
                {"detail": "Your user account is not linked to an agency. Contact your administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        session = LeaseBuilderSession.objects.create(
            agency_id=agency_id,
            created_by=request.user,
            template=template,
            messages=[],
            current_state=initial_state,
            rha_flags=[],
        )

        # Build template context for the opening message
        tmpl_context = ""
        if template and template.fields_schema:
            tmpl_context = (
                f" Your uploaded template \"{template.name}\" has these merge fields: "
                f"{', '.join(template.fields_schema)}."
            )

        # Kick off with an opening AI message (stored separately — NOT in messages
        # array used for Anthropic API calls, which must start with a user message).
        if initial_state:
            missing = _missing_required(initial_state)
            if missing:
                opening = (
                    f"I've loaded the existing lease details.{tmpl_context} "
                    f"Still need: {', '.join(missing)}. "
                    "Update any fields or tell me what you'd like to change."
                )
            else:
                opening = (
                    f"I've loaded the existing lease details.{tmpl_context} Everything looks complete. "
                    "Tell me what you'd like to change, or click Finalize to create a new lease."
                )
        elif template and template.fields_schema:
            opening = (
                f"I can see your template \"{template.name}\" has {len(template.fields_schema)} merge fields: "
                f"{', '.join(template.fields_schema[:8])}{'…' if len(template.fields_schema) > 8 else ''}. "
                "Tell me about the tenant and property and I'll fill them all in."
            )
        else:
            opening = (
                "Welcome! Let's build your lease. "
                "Start by telling me the property address and the tenant's name, "
                "or describe the lease you need and I'll ask for anything that's missing."
            )

        # messages stays empty — the opening is only in the API response, not persisted
        # to the conversation history used for Claude API calls.

        return Response(
            {
                "session_id": session.id,
                "message": opening,
                "current_state": session.current_state,
                "rha_flags": session.rha_flags,
                "ready_to_finalize": False,
                "required_fields": REQUIRED_FIELDS,
                "missing_fields": _missing_required(initial_state),
                "template": {"id": template.id, "name": template.name} if template else None,
            },
            status=status.HTTP_201_CREATED,
        )


class LeaseBuilderChatView(APIView):
    """POST /api/v1/leases/builder/sessions/{id}/message/ — send a message."""
    permission_classes = [IsAgentOrAdmin]

    @requires_feature("ai_lease_generation")
    def post(self, request, pk):
        try:
            session = _scoped_builder_sessions(request).get(pk=pk, created_by=request.user)
        except LeaseBuilderSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == LeaseBuilderSession.Status.FINALIZED:
            return Response({"error": "This session has already been finalized."}, status=status.HTTP_400_BAD_REQUEST)

        user_message = (request.data.get("message") or "").strip()
        if not user_message:
            return Response({"error": "message is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Append user turn to stored history
        messages = list(session.messages)
        messages.append({"role": "user", "content": user_message})

        # Build system prompt with current state context + legal reference
        missing = _missing_required(session.current_state)
        legal_ref = _load_legal_reference()

        # Include template field list in system prompt if available
        tmpl_note = ""
        if session.template and session.template.fields_schema:
            tmpl_note = (
                f"\n\n## Active Template: {session.template.name}\n"
                f"Merge fields in this template: {', '.join(session.template.fields_schema)}\n"
                "Ensure all these fields are filled before marking ready_to_finalize."
            )

        system = BUILDER_SYSTEM_PROMPT.format(
            legal_reference=(legal_ref if legal_ref else "(reference file not found — apply standard RHA rules)") + tmpl_note,
            state_json=json.dumps(session.current_state, indent=2),
            missing_fields=", ".join(missing) if missing else "none",
        )

        # Anthropic API requires the messages array to start with a user message.
        # Strip any leading assistant turns (e.g. the opening greeting) before the call.
        api_messages = messages
        while api_messages and api_messages[0].get("role") != "user":
            api_messages = api_messages[1:]

        # Call Claude — pass full conversation history
        try:
            result = _call_claude(system, api_messages)
        except Exception as exc:
            return Response({"error": f"AI error: {exc}"}, status=status.HTTP_502_BAD_GATEWAY)

        # Merge updated state
        updated_state = {**session.current_state, **(result.get("updated_state") or {})}
        rha_flags = result.get("rha_flags") or []
        reply = result.get("reply", "")
        next_question = result.get("next_question")
        ready = bool(result.get("ready_to_finalize", False)) and not any(
            f.get("severity") == "error" for f in rha_flags
        )

        # Append assistant reply to stored history
        messages.append({"role": "assistant", "content": reply})

        # Persist full history (including any leading assistant turns for display)
        session.messages = messages
        session.current_state = updated_state
        session.rha_flags = rha_flags
        if ready:
            session.status = LeaseBuilderSession.Status.REVIEW
        session.save(update_fields=["messages", "current_state", "rha_flags", "status", "updated_at"])

        return Response(
            {
                "reply": reply,
                "current_state": updated_state,
                "rha_flags": rha_flags,
                "next_question": next_question,
                "ready_to_finalize": ready,
                "missing_fields": _missing_required(updated_state),
            }
        )


class LeaseBuilderFinalizeView(APIView):
    """
    POST /api/v1/leases/builder/sessions/{id}/finalize/

    Validate the session state and create a Lease record via the same logic
    as ImportLeaseView (reuses _get_or_create_person).
    """
    permission_classes = [IsAgentOrAdmin]

    @requires_feature("ai_lease_generation")
    def post(self, request, pk):
        try:
            session = _scoped_builder_sessions(request).get(pk=pk, created_by=request.user)
        except LeaseBuilderSession.DoesNotExist:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        if session.status == LeaseBuilderSession.Status.FINALIZED:
            return Response(
                {"error": "Already finalized.", "lease_id": session.lease_id},
                status=status.HTTP_400_BAD_REQUEST,
            )

        s = session.current_state
        missing = _missing_required(s)
        if missing:
            return Response(
                {"error": "Missing required fields.", "missing_fields": missing},
                status=status.HTTP_400_BAD_REQUEST,
            )

        errors = [f for f in session.rha_flags if f.get("severity") == "error"]
        if errors:
            return Response(
                {"error": "RHA compliance errors must be resolved before finalizing.", "rha_flags": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build request.data compatible payload for ImportLeaseView logic
        # The session state uses builder field names; map to import field names.
        import_payload = _build_import_payload(s, request)

        # Delegate to ImportLeaseView to handle property/unit/person resolution atomically
        import_view = ImportLeaseView()
        import_view.request = request

        # Inject session AI state as audit trail
        import_payload["ai_parse_result"] = {"source": "builder", "session_id": session.id, "state": s}

        # Monkey-patch request.data for reuse
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        fake_request = factory.post("/", import_payload, format="json")
        fake_request.user = request.user

        from rest_framework.request import Request
        drf_request = Request(fake_request)
        drf_request.user = request.user

        response = import_view.post(drf_request)
        if response.status_code != 201:
            return response

        lease_id = response.data["id"]
        lease_number = response.data["lease_number"]

        # Link session to the new lease
        session.lease_id = lease_id
        session.status = LeaseBuilderSession.Status.FINALIZED
        session.save(update_fields=["lease", "status", "updated_at"])

        return Response(
            {"lease_id": lease_id, "lease_number": lease_number},
            status=status.HTTP_201_CREATED,
        )


def _build_import_payload(state: dict, request) -> dict:
    """
    Map LeaseBuilderSession.current_state field names to ImportLeaseView payload format.
    """
    payload = {
        "property": {
            "name": state.get("property_name") or state.get("property_address", ""),
            "address": state.get("property_address", ""),
            "city": state.get("city", ""),
            "province": state.get("province", ""),
            "property_type": "house",
        },
        "unit": {
            "unit_number": state.get("unit_number", "1"),
        },
        "primary_tenant": {
            "full_name": state.get("tenant_name", ""),
            "id_number": state.get("tenant_id", ""),
            "phone": state.get("tenant_phone", ""),
            "email": state.get("tenant_email", ""),
            "phone_country_code": state.get("tenant_phone_country_code", "") or state.get("phone_country_code", ""),
            "country": state.get("tenant_country", "") or state.get("country", ""),
        },
        "co_tenants": _parse_co_tenants(state.get("co_tenants")),
        "start_date": state.get("lease_start"),
        "end_date": state.get("lease_end"),
        "monthly_rent": _to_number(state.get("monthly_rent")),
        "deposit": _to_number(state.get("deposit")),
        "notice_period_days": _to_int(state.get("notice_period_days"), 30),
        "early_termination_penalty_months": _to_int(state.get("early_termination_months"), 3),
        "max_occupants": _to_int(state.get("max_occupants"), 1),
        "water_included": _to_bool(state.get("water_included"), True),
        "electricity_prepaid": _to_bool(state.get("electricity_prepaid"), True),
        "payment_reference": state.get("payment_reference", ""),
        "status": "pending",
    }
    # Forward the per-lease services overrides when the builder session
    # captured them — empty/None values are dropped so the import view's
    # property-inherit signal still fires.
    for key in (
        "water_arrangement",
        "electricity_arrangement",
        "gardening_service_included",
        "wifi_included",
        "security_service_included",
    ):
        val = state.get(key)
        if val not in (None, ""):
            payload[key] = val
    return payload


def _parse_co_tenants(value) -> list:
    """
    Normalise builder-state co_tenants into a list of dicts each carrying at
    minimum ``full_name`` and ``payment_reference``. Per-lessee payment refs
    flow through to the import view's LeaseTenant get_or_create call.
    """
    if not value:
        return []
    if isinstance(value, list):
        out: list = []
        for v in value:
            if isinstance(v, str):
                out.append({"full_name": v, "payment_reference": ""})
            elif isinstance(v, dict):
                merged = dict(v)
                merged.setdefault("payment_reference", "")
                # Preserve country / phone_country_code if the builder captured
                # them — _get_or_create_person uses these on Person creation.
                for k in ("country", "phone_country_code"):
                    if k in v and v[k]:
                        merged[k] = v[k]
                out.append(merged)
            else:
                out.append({"full_name": str(v), "payment_reference": ""})
        return out
    if isinstance(value, str) and value.strip():
        return [
            {"full_name": name.strip(), "payment_reference": ""}
            for name in value.split(",") if name.strip()
        ]
    return []


def _to_number(value, default=0):
    if value is None:
        return default
    try:
        return float(str(value).replace(",", "").replace("R", "").strip())
    except (ValueError, TypeError):
        return default


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value, default=True):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() not in ("false", "no", "excluded", "0", "prepaid")
    return default


def _lease_to_state(lease) -> dict:
    """
    Convert an existing Lease ORM object into a LeaseBuilderSession current_state dict.
    Used when starting a builder session from an existing contract.
    """
    unit = lease.unit
    prop = unit.property if unit else None
    primary = lease.primary_tenant  # ForeignKey(Person)

    co_tenants = [
        {
            "full_name": ct.person.full_name if ct.person else "",
            "payment_reference": ct.payment_reference or "",
        }
        for ct in lease.co_tenants.select_related("person").order_by("id")
    ]

    state = {
        "property_address": prop.address if prop else "",
        "property_name": prop.name if prop else "",
        "city": prop.city if prop else "",
        "province": prop.province if prop else "",
        "unit_number": unit.unit_number if unit else "",
        "landlord_name": "",  # not stored on Lease currently
        "tenant_name": primary.full_name if primary else "",
        "tenant_id": primary.id_number if primary else "",
        "tenant_phone": primary.phone if primary else "",
        "tenant_email": primary.email if primary else "",
        "co_tenants": co_tenants,
        "lease_start": str(lease.start_date) if lease.start_date else "",
        "lease_end": str(lease.end_date) if lease.end_date else "",
        "monthly_rent": str(lease.monthly_rent) if lease.monthly_rent else "",
        "deposit": str(lease.deposit) if lease.deposit else "",
        "notice_period_days": str(lease.notice_period_days) if lease.notice_period_days else "30",
        "payment_reference": lease.payment_reference or "",
        "water_included": lease.water_included,
        "electricity_prepaid": lease.electricity_prepaid,
        "max_occupants": str(lease.max_occupants) if lease.max_occupants else "",
    }
    # Remove empty strings so _missing_required() works correctly
    return {k: v for k, v in state.items() if v != "" and v is not None}
