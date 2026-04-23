"""
THE VOLT — Identity router package.

Single public surface: `IdentityRouter` + `RouteRequest` / `RouteResult`.
"""
from .identity_router import (
    IdentityRouter,
    RouteRequest,
    RouteResult,
    discover_skill_manifests,
)

__all__ = [
    "IdentityRouter",
    "RouteRequest",
    "RouteResult",
    "discover_skill_manifests",
]
