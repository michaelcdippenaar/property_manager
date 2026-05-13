"""AppConfig for the centralised legal RAG store.

The legal_rag app owns the runtime cache + query API for the canonical
SA legal-fact corpus that lives as versioned YAML in ``content/legal/``.

See ``content/cto/centralised-legal-rag-store-plan.md`` for the locked design.
This is the Day 1-2 scaffold pass; loaders + indexers + skill renderer land
in Day 3-5.
"""
from __future__ import annotations

from django.apps import AppConfig


class LegalRagConfig(AppConfig):
    """Django app config for ``apps.legal_rag``.

    Runtime cache (PostgreSQL) + Python query API for the centralised
    legal-fact corpus. Canonical source of truth is the YAML files in
    ``content/legal/`` (git). PostgreSQL is rebuilt by
    ``manage.py sync_legal_facts`` (not yet implemented; Day 3 of Phase A).
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.legal_rag"
    verbose_name = "Legal RAG"

    def ready(self) -> None:
        # Register Django system checks. The check validates content/legal/
        # YAML files against the JSON schema at startup (fail-soft warnings).
        from . import checks  # noqa: F401
