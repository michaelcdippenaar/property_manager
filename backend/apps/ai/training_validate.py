"""Validate tenant AI training fixture entries (parse regression + schema)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.ai.parsing import parse_maintenance_draft_response, parse_tenant_ai_response

FIXTURE_NAME = "tenant_ai_training_cases.json"


def training_fixture_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / FIXTURE_NAME


def load_training_cases() -> dict[str, Any]:
    p = training_fixture_path()
    if not p.is_file():
        raise FileNotFoundError(str(p))
    return json.loads(p.read_text(encoding="utf-8"))


def _one_of(actual: str, spec: Any) -> bool:
    if isinstance(spec, str):
        return actual == spec
    if isinstance(spec, dict) and "one_of" in spec:
        return actual in spec["one_of"]
    return False


def validate_case_parse(case: dict[str, Any]) -> list[str]:
    """Return human-readable errors for this case's optional parse regression fields."""
    errors: list[str] = []
    cid = case.get("id", "?")

    raw_chat = case.get("sample_chat_assistant_raw")
    exp_chat = case.get("expect_chat_parse")
    if raw_chat is not None and exp_chat is not None:
        reply, mt, ok, ctitle = parse_tenant_ai_response(raw_chat)
        if exp_chat.get("json_ok") is not None and bool(exp_chat["json_ok"]) != ok:
            errors.append(f"{cid} chat: json_ok want {exp_chat['json_ok']} got {ok}")
        if exp_chat.get("maintenance_ticket_null") and mt is not None:
            errors.append(f"{cid} chat: expected maintenance_ticket null")
        if exp_chat.get("maintenance_ticket_non_null") and mt is None:
            errors.append(f"{cid} chat: expected maintenance_ticket non-null")
        if exp_chat.get("ticket_priority") is not None and mt is not None:
            want = str(exp_chat["ticket_priority"]).lower()
            got = str(mt.get("priority") or "").lower()
            if got != want:
                errors.append(f"{cid} chat: ticket priority want {want!r} got {got!r}")
        tcontains = exp_chat.get("ticket_title_contains")
        if tcontains and mt is not None:
            if str(tcontains).lower() not in (mt.get("title") or "").lower():
                errors.append(f"{cid} chat: ticket title should contain {tcontains!r}")
        if exp_chat.get("reply_nonempty") and not (reply or "").strip():
            errors.append(f"{cid} chat: reply should be non-empty")
        ct = exp_chat.get("conversation_title_contains")
        if ct is not None:
            if str(ct).lower() not in (ctitle or "").lower():
                errors.append(f"{cid} chat: conversation_title should contain {ct!r} got {ctitle!r}")
        if exp_chat.get("conversation_title_non_null") and not (ctitle or "").strip():
            errors.append(f"{cid} chat: expected conversation_title non-null")

    raw_draft = case.get("sample_draft_model_raw")
    exp_draft = case.get("expect_draft_parse")
    if raw_draft is not None and exp_draft is not None:
        d = parse_maintenance_draft_response(raw_draft)
        if exp_draft.get("non_null") and d is None:
            errors.append(f"{cid} draft: expected non-null draft")
        if exp_draft.get("null") and d is not None:
            errors.append(f"{cid} draft: expected null draft")
        if d is not None:
            if "category" in exp_draft:
                if not _one_of(d["category"], exp_draft["category"]):
                    errors.append(
                        f"{cid} draft: category want {exp_draft['category']!r} got {d['category']!r}"
                    )
            if "priority" in exp_draft:
                if not _one_of(d["priority"], exp_draft["priority"]):
                    errors.append(
                        f"{cid} draft: priority want {exp_draft['priority']!r} got {d['priority']!r}"
                    )
            tc = exp_draft.get("title_contains")
            if tc and str(tc).lower() not in d["title"].lower():
                errors.append(f"{cid} draft: title should contain {tc!r}")
            dc = exp_draft.get("description_contains")
            if dc and str(dc).lower() not in d["description"].lower():
                errors.append(f"{cid} draft: description should contain {dc!r}")

    return errors


def validate_all_cases(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    cases = data.get("cases")
    if not isinstance(cases, list):
        return ["top-level 'cases' must be a list"]
    seen: set[str] = set()
    for i, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"case[{i}] is not an object")
            continue
        cid = case.get("id")
        if not cid:
            errors.append(f"case[{i}] missing id")
            continue
        if cid in seen:
            errors.append(f"duplicate case id: {cid}")
        seen.add(str(cid))
        errors.extend(validate_case_parse(case))
    return errors
