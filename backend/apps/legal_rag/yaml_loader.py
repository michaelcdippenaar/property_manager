"""Shared YAML SafeLoader for the legal RAG store.

PyYAML's default ``SafeLoader`` auto-resolves ISO-8601 date strings
(``2026-05-12``, ``2026-05-12T10:00:00Z``) into ``datetime.date`` /
``datetime.datetime`` objects. The schema validators we use elsewhere
(``jsonschema.Draft202012Validator``) expect those values as strings
because the JSON Schema ``"format": "date"`` constraint operates on
strings. Auto-resolution would convert them to Python objects that fail
``isinstance(..., str)`` checks and produce confusing schema errors.

This module exposes a single SafeLoader subclass that strips the
implicit ``timestamp`` resolver. Use it via :func:`load_safe_yaml`:

.. code-block:: python

    from apps.legal_rag.yaml_loader import load_safe_yaml
    data = load_safe_yaml(Path("content/legal/statutes/rha/s7.yaml"))

Both :mod:`apps.legal_rag.checks` and :mod:`apps.legal_rag.management.commands.sync_legal_facts`
share this loader so a single fix lands everywhere.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class StringDateLoader(yaml.SafeLoader):
    """A SafeLoader subclass that keeps ISO-8601 strings as strings.

    The standard PyYAML ``SafeLoader`` has an implicit resolver for
    ``tag:yaml.org,2002:timestamp`` that turns date-shaped strings into
    :class:`datetime.date` instances. For the legal RAG store we want
    those to remain strings so the JSON Schema ``"format": "date"``
    validator can do its job. This subclass copies the resolver table
    and drops the timestamp entry.
    """


# Copy SafeLoader's implicit-resolver table minus the timestamp resolver.
# Done at class definition time so every instance sees the modified table.
StringDateLoader.yaml_implicit_resolvers = {
    first_char: [
        (tag, regex)
        for tag, regex in resolvers
        if tag != "tag:yaml.org,2002:timestamp"
    ]
    for first_char, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def load_safe_yaml(path: Path) -> Any:
    """Load a YAML file, returning native Python types with dates as strings.

    Raises :class:`yaml.YAMLError` on parse failure (caller decides whether
    to swallow + log or propagate). Returns ``None`` for empty files —
    consistent with PyYAML's default behaviour.
    """
    return yaml.load(path.read_text(encoding="utf-8"), Loader=StringDateLoader)


def load_safe_yaml_text(text: str) -> Any:
    """In-memory variant of :func:`load_safe_yaml` for tests and string inputs."""
    return yaml.load(text, Loader=StringDateLoader)


__all__ = ["StringDateLoader", "load_safe_yaml", "load_safe_yaml_text"]
