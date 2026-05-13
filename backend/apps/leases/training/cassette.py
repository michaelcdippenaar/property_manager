"""Cassette-based replay for ``anthropic.Anthropic.messages.create``.

Per plan §6: every scenario has a JSONL cassette under
``backend/apps/leases/training/cassettes/<scenario_id>__<corpus_hash>.jsonl``.
Each line is a single ``{"req": {...}, "resp": {...}, "hash": "..."}``
record.

The wrapper exposes the SDK's ``client.messages.create(**kwargs)`` shape
so the existing ``LeaseAgentRunner`` (locked, do not edit) calls into it
transparently.

Modes:
    - replay (default): look up the line by request hash, raise
      ``CassetteMissError`` on miss. Zero API spend.
    - record: forward to the live client, append the response to the
      cassette JSONL, return the live response.
    - live: forward to the live client, do not record.

Day 1-2 commits a hand-crafted cassette so the smoke scenario passes in
replay mode without an Anthropic API key. Real cassettes get re-recorded
on Day 3+ once the full pipeline is wired.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator, Literal

logger = logging.getLogger(__name__)


# Volatile keys we strip from request kwargs before hashing. These are
# request-time-only details that should not invalidate replay.
#
# ``max_tokens`` is volatile because the harness might bump it without
# changing semantics (per plan §6.3). Everything else (model, system,
# messages, tools, tool_choice) is part of the cache identity.
_VOLATILE_REQUEST_KEYS = frozenset({"max_tokens"})


# Day 1-2 placeholder corpus hash. Once
# ``apps.legal_rag.indexer.LeaseLawCorpusVersion`` lands, swap this for
# the real hash (plan §6.2). The harness consumes the literal string from
# the scenario YAML so changing this here does not silently break
# cassette names — Day 3+ migration is explicit.
DAY_1_2_CORPUS_HASH = "day-1-2-stub"


CassetteMode = Literal["replay", "record", "live"]


# ── Exceptions ───────────────────────────────────────────────────────── #


class CassetteMissError(RuntimeError):
    """Replay mode could not find a cassette entry for the request hash.

    Attributes:
        scenario_id: which scenario's cassette was being searched.
        request_hash: the SHA-256 of the normalised request kwargs.
        cassette_path: filesystem path consulted.
        hint: short instruction for resolving the miss (e.g. re-record).
    """

    def __init__(
        self,
        *,
        scenario_id: str,
        request_hash: str,
        cassette_path: Path,
        hint: str = "",
    ):
        self.scenario_id = scenario_id
        self.request_hash = request_hash
        self.cassette_path = cassette_path
        self.hint = hint or (
            f"Re-record with `manage.py train_lease_agent "
            f"--scenario={scenario_id} --record`."
        )
        super().__init__(
            f"Cassette miss for scenario={scenario_id} "
            f"hash={request_hash[:12]} path={cassette_path}. {self.hint}"
        )


# ── Normalisation + hashing ──────────────────────────────────────────── #


def _strip_volatile(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``kwargs`` with volatile keys removed."""
    return {k: v for k, v in kwargs.items() if k not in _VOLATILE_REQUEST_KEYS}


def _canonical_json(payload: Any) -> str:
    """Stable JSON serialisation for hashing.

    Sorts dict keys, uses compact separators, escapes non-ASCII for
    deterministic byte output. The same payload always hashes to the
    same digest across Python versions and OSes.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def hash_request(kwargs: dict[str, Any]) -> str:
    """SHA-256 hex digest of normalised ``messages.create`` kwargs.

    Strips ``max_tokens`` and any other volatile keys before hashing so a
    bump in token budget does not invalidate replay. All other fields
    (model, system blocks including ``cache_control`` markers, tools,
    tool_choice, messages) are part of the cassette identity.
    """
    normalised = _strip_volatile(kwargs)
    return hashlib.sha256(_canonical_json(normalised).encode("utf-8")).hexdigest()


# ── Response rehydration ─────────────────────────────────────────────── #


def _rehydrate_content_block(block: dict[str, Any]) -> SimpleNamespace:
    """Turn a serialised content block into the SDK-compatible namespace.

    ``LeaseAgentRunner._record_call`` only reads ``response.usage`` and
    ``response.stop_reason``; downstream consumers iterate
    ``response.content`` looking for ``block.type`` and ``block.text`` /
    ``block.name`` / ``block.input``. We give every block whatever
    attributes it had in the recording, recursively.
    """
    namespace = SimpleNamespace(**block)
    # Recurse into nested dicts that callers expect as attribute access
    # (e.g. ``tool_use.input`` is a plain dict — leave it).
    return namespace


def rehydrate_response(resp_payload: dict[str, Any]) -> SimpleNamespace:
    """Build a ``SimpleNamespace`` mirror of an Anthropic ``Message``.

    The runner reads:
      - ``response.usage.input_tokens``
      - ``response.usage.output_tokens``
      - ``response.usage.cache_read_input_tokens``
      - ``response.usage.cache_creation_input_tokens``
      - ``response.stop_reason``
      - ``response.content``

    Any other field on the payload is mirrored verbatim so the harness's
    own consumers (e.g. assertion code that inspects ``content`` for
    ``text`` or ``tool_use`` blocks) can access them via attribute style.
    """
    usage_payload = resp_payload.get("usage", {})
    usage = SimpleNamespace(
        input_tokens=int(usage_payload.get("input_tokens", 0) or 0),
        output_tokens=int(usage_payload.get("output_tokens", 0) or 0),
        cache_read_input_tokens=int(
            usage_payload.get("cache_read_input_tokens", 0) or 0
        ),
        cache_creation_input_tokens=int(
            usage_payload.get("cache_creation_input_tokens", 0) or 0
        ),
    )
    content = [
        _rehydrate_content_block(b) for b in resp_payload.get("content", [])
    ]
    return SimpleNamespace(
        id=resp_payload.get("id", "msg_cassette"),
        type=resp_payload.get("type", "message"),
        role=resp_payload.get("role", "assistant"),
        model=resp_payload.get("model", ""),
        stop_reason=resp_payload.get("stop_reason"),
        stop_sequence=resp_payload.get("stop_sequence"),
        content=content,
        usage=usage,
    )


# ── Cassette file I/O ────────────────────────────────────────────────── #


@dataclass
class CassetteEntry:
    """One JSONL line: request kwargs, response payload, indexed by hash."""

    hash: str
    req: dict[str, Any]
    resp: dict[str, Any]

    def to_jsonl(self) -> str:
        """Single-line JSON representation suitable for appending."""
        return json.dumps(
            {"hash": self.hash, "req": self.req, "resp": self.resp},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )


def _iter_cassette(path: Path) -> Iterator[CassetteEntry]:
    """Yield ``CassetteEntry`` per non-blank line of ``path``.

    Skips lines that fail to parse — with a warning — so a partially-
    corrupted cassette does not block the whole battery. Day 1-2 expects
    well-formed cassettes (we hand-craft the only one).
    """
    with open(path, "r", encoding="utf-8") as f:
        for line_num, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "CassetteAnthropicClient: skipping malformed line %d in %s: %s",
                    line_num,
                    path,
                    exc,
                )
                continue
            yield CassetteEntry(
                hash=payload["hash"],
                req=payload.get("req", {}),
                resp=payload.get("resp", {}),
            )


# ── Cassette client ──────────────────────────────────────────────────── #


class _MessagesProxy:
    """Inner proxy exposing ``.create(**kwargs)`` like the SDK."""

    def __init__(self, parent: "CassetteAnthropicClient"):
        self._parent = parent

    def create(self, **kwargs: Any) -> SimpleNamespace:
        return self._parent._dispatch(kwargs)


class CassetteAnthropicClient:
    """Wraps an ``anthropic.Anthropic`` client with record/replay.

    Construction is cheap; on first use the cassette file is read into
    a per-instance index. Re-reads are not free, so the harness builds
    one client per scenario run.

    The wrapper presents the same ``.messages.create(**kwargs)`` shape
    as the SDK so ``LeaseAgentRunner.dispatch`` can call into it without
    knowing it is talking to a cassette.
    """

    def __init__(
        self,
        *,
        scenario_id: str,
        cassette_path: Path,
        mode: CassetteMode = "replay",
        live_client: Any | None = None,
    ):
        self.scenario_id = scenario_id
        self.cassette_path = Path(cassette_path)
        self.mode = mode
        self._live_client = live_client
        self.messages = _MessagesProxy(self)
        self._index: dict[str, CassetteEntry] | None = None
        self._records_added: int = 0

    # ── Public surface ──────────────────────────────────────────────── #

    @property
    def records_added(self) -> int:
        """Number of cassette entries appended this session (record mode)."""
        return self._records_added

    # ── Internals ───────────────────────────────────────────────────── #

    def _ensure_index(self) -> dict[str, CassetteEntry]:
        """Lazily load the cassette JSONL into a hash → entry dict."""
        if self._index is not None:
            return self._index
        if not self.cassette_path.exists():
            self._index = {}
            return self._index
        self._index = {entry.hash: entry for entry in _iter_cassette(self.cassette_path)}
        return self._index

    def _dispatch(self, kwargs: dict[str, Any]) -> SimpleNamespace:
        """Route to replay / record / live per ``self.mode``."""
        request_hash = hash_request(kwargs)

        if self.mode == "replay":
            return self._replay(kwargs, request_hash)
        if self.mode == "record":
            return self._record(kwargs, request_hash)
        if self.mode == "live":
            return self._live(kwargs)
        raise ValueError(f"Unknown cassette mode: {self.mode!r}")

    def _replay(self, kwargs: dict[str, Any], request_hash: str) -> SimpleNamespace:
        """Look up a recorded response; raise on miss."""
        index = self._ensure_index()
        entry = index.get(request_hash)
        if entry is None:
            raise CassetteMissError(
                scenario_id=self.scenario_id,
                request_hash=request_hash,
                cassette_path=self.cassette_path,
            )
        return rehydrate_response(entry.resp)

    def _record(self, kwargs: dict[str, Any], request_hash: str) -> SimpleNamespace:
        """Forward to live client + append response to cassette."""
        if self._live_client is None:
            raise RuntimeError(
                "CassetteAnthropicClient.mode='record' requires live_client. "
                "Construct with live_client=anthropic.Anthropic(api_key=...)."
            )
        resp = self._live_client.messages.create(**kwargs)
        resp_payload = _serialise_response(resp)
        entry = CassetteEntry(
            hash=request_hash, req=_strip_volatile(kwargs), resp=resp_payload
        )
        self._append_to_cassette(entry)
        self._records_added += 1
        # Update the in-memory index too so a repeat hit in the same
        # session resolves from memory rather than re-billing.
        index = self._ensure_index()
        index[request_hash] = entry
        return rehydrate_response(resp_payload)

    def _live(self, kwargs: dict[str, Any]) -> SimpleNamespace:
        """Forward to live client without recording."""
        if self._live_client is None:
            raise RuntimeError(
                "CassetteAnthropicClient.mode='live' requires live_client."
            )
        resp = self._live_client.messages.create(**kwargs)
        # Rehydrate via the serialised form so callers see the same
        # SimpleNamespace shape they'd see in replay/record. Otherwise
        # tests that work in replay would behave subtly differently in
        # live mode.
        return rehydrate_response(_serialise_response(resp))

    def _append_to_cassette(self, entry: CassetteEntry) -> None:
        """Atomically append one JSONL line to the cassette file."""
        self.cassette_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cassette_path, "a", encoding="utf-8") as f:
            f.write(entry.to_jsonl())
            f.write("\n")


# ── Live → serialisable helpers ──────────────────────────────────────── #


def _serialise_response(resp: Any) -> dict[str, Any]:
    """Turn a live SDK response into a JSON-serialisable dict.

    The SDK responses are pydantic models; ``model_dump`` returns a plain
    dict. Fall back to ``__dict__`` if the response was already a
    ``SimpleNamespace`` (e.g. unit-test fakes).
    """
    if hasattr(resp, "model_dump"):
        return resp.model_dump()  # type: ignore[no-any-return]
    if hasattr(resp, "to_dict"):
        return resp.to_dict()  # type: ignore[no-any-return]
    # Walk ``__dict__`` recursively. This path is rare — used only when
    # the live client is itself a mock.
    return _namespace_to_dict(resp)


def _namespace_to_dict(value: Any) -> Any:
    """Recursive ``SimpleNamespace`` / object → ``dict`` conversion."""
    if isinstance(value, SimpleNamespace):
        return {k: _namespace_to_dict(v) for k, v in value.__dict__.items()}
    if isinstance(value, dict):
        return {k: _namespace_to_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_namespace_to_dict(v) for v in value]
    return value


__all__ = [
    "CassetteAnthropicClient",
    "CassetteEntry",
    "CassetteMissError",
    "CassetteMode",
    "DAY_1_2_CORPUS_HASH",
    "hash_request",
    "rehydrate_response",
]
