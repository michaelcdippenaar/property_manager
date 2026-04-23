"""
THE VOLT — Submitter context.

Captures WHO uploaded a document, HOW, WHEN, and FROM WHERE. This metadata
travels with the doc throughout its lifecycle (and is embedded into the
file via `stamp.py`).

Channels:
  WEB   — uploaded via the admin/owner SPA
  MOBILE — uploaded via the tenant/landlord mobile app
  EMAIL — auto-ingested from a monitored inbox (e.g. fica@klikk.co.za)
  MCP   — pushed via the tremly-mcp Vault33 ingestion server
  API   — direct REST upload by a 3rd-party subscriber via the gateway
  AGENT — minted by an internal extraction job (no human submitter)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


VALID_CHANNELS = frozenset({"WEB", "MOBILE", "EMAIL", "MCP", "API", "AGENT"})


@dataclass(frozen=True)
class SubmitterContext:
    """Who/how/when/where a document entered the Volt."""
    submitter_user_id: Optional[int]    # Django auth user id, or None for AGENT/EMAIL
    submitter_display: str              # human-readable: "Michael Dippenaar" / "fica@klikk.co.za"
    channel: str                        # one of VALID_CHANNELS
    submitted_at: datetime = field(default_factory=datetime.utcnow)

    # Optional forensic fields — populated when the channel can supply them
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None     # e.g. mobile install id
    on_behalf_of_vault_id: Optional[int] = None  # which silo received it
    source_url: Optional[str] = None             # for EMAIL: message-id://
    notes: str = ""

    def __post_init__(self):
        if self.channel not in VALID_CHANNELS:
            raise ValueError(f"invalid channel {self.channel!r}; "
                             f"must be one of {sorted(VALID_CHANNELS)}")

    def to_dict(self) -> dict:
        return {
            "submitter_user_id": self.submitter_user_id,
            "submitter_display": self.submitter_display,
            "channel": self.channel,
            "submitted_at": self.submitted_at.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_fingerprint": self.device_fingerprint,
            "on_behalf_of_vault_id": self.on_behalf_of_vault_id,
            "source_url": self.source_url,
            "notes": self.notes,
        }
