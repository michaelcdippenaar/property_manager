"""
THE VOLT — Identity router.

The router sits between an ingested document and the right per-doc-type
extraction skill. It:

  1. Discovers all skills under `classification/skills/<name>/` whose
     package exposes a `MANIFEST = SkillManifest(...)`.
  2. Resolves an incoming `RouteRequest` to AT MOST one skill, using
     this precedence:
        explicit doc_type  >  filename signal doc_type  >
        filename regex     >  language hint
     Ties are broken by `manifest.priority` (low wins).
  3. Dispatches to the skill's `extract(...)`.
  4. Optionally calls `attach_provenance(...)` to mint VCN + stamp +
     register fingerprint, returning a `RouteResult` bundle.

If no skill matches, the request returns `RouteResult(no_skill=True)`
and the caller is expected to:
  • drop into the L4 generic LLM extractor, OR
  • enqueue the doc for `corpus_observer` so it counts toward L5
    auto-training of a new skill.

The router has zero knowledge of Django — it accepts injectables for
the broker, sequence supplier and secret lookup. Production wires real
Django-backed implementations; tests pass in-memory ones.
"""
from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from apps.the_volt.classification.document_provenance import (
    DuplicateBroker, ProvenanceRecord, SequenceSupplier,
    SubmitterContext, VaultSecretLookup, attach_provenance,
)
from apps.the_volt.classification.entity_engine.filename_signals import (
    extract_filename_signal,
)
from apps.the_volt.classification.skills._shared.manifest import SkillManifest
from apps.the_volt.classification.skills._shared.types import ExtractionResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / response
# ---------------------------------------------------------------------------

@dataclass
class RouteRequest:
    """Everything the router needs to decide where a doc goes."""
    doc_path: Path
    doc_id: str                                  # storage backend id (string)
    vault_id: int
    submitter: SubmitterContext
    explicit_doc_type: Optional[str] = None      # caller may force a doc_type
    extra_kwargs: dict[str, Any] = field(default_factory=dict)
    # Provenance toggles (default on; tests may disable)
    write_provenance: bool = True


@dataclass
class RouteResult:
    """Bundle returned by the router."""
    skill_name: Optional[str]                    # None when no_skill=True
    skill_version: Optional[str]
    extraction: Optional[ExtractionResult]
    provenance: Optional[ProvenanceRecord]
    no_skill: bool = False
    no_skill_reason: str = ""
    candidates_considered: list[str] = field(default_factory=list)
    chosen_via: str = ""                         # 'explicit'|'filename_doc_type'|'filename_regex'|'language_hint'

    @property
    def vcn(self) -> Optional[str]:
        return self.provenance.vcn if self.provenance else None

    @property
    def doc_type(self) -> Optional[str]:
        return self.extraction.doc_type if self.extraction else None


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class IdentityRouter:
    """Dispatch incoming docs to the right skill + attach provenance."""

    def __init__(
        self,
        *,
        broker: DuplicateBroker,
        sequence_supplier: SequenceSupplier,
        vault_secret_lookup: VaultSecretLookup,
        manifests: Optional[list[SkillManifest]] = None,
        skills_package: str = "apps.the_volt.classification.skills",
        sidecar_dir: Optional[Path] = None,
        pdf_out_dir: Optional[Path] = None,
    ):
        self.broker = broker
        self.sequence_supplier = sequence_supplier
        self.vault_secret_lookup = vault_secret_lookup
        self.sidecar_dir = sidecar_dir
        self.pdf_out_dir = pdf_out_dir
        self._manifests: list[SkillManifest] = (
            list(manifests) if manifests is not None
            else discover_skill_manifests(skills_package)
        )
        # Index by upper-cased doc_type for fast lookup
        self._by_doc_type: dict[str, list[SkillManifest]] = {}
        for m in self._manifests:
            for dt in m.doc_types:
                self._by_doc_type.setdefault(dt.upper(), []).append(m)

    # ── Discovery introspection ────────────────────────────────────────

    def known_skills(self) -> list[str]:
        return [m.name for m in self._manifests]

    def known_doc_types(self) -> list[str]:
        return sorted(self._by_doc_type.keys())

    # ── Resolution ──────────────────────────────────────────────────────

    def resolve(self, req: RouteRequest) -> tuple[Optional[SkillManifest], str, list[str]]:
        """Pick the right skill (or None). Returns (manifest, chosen_via, candidates)."""
        candidates: list[str] = []
        ext = req.doc_path.suffix.lower()
        filename = req.doc_path.name

        # 1. explicit doc_type wins
        if req.explicit_doc_type:
            cands = [m for m in self._by_doc_type.get(req.explicit_doc_type.upper(), [])
                     if m.supports_extension(ext)]
            candidates.extend(m.name for m in cands)
            if cands:
                return _pick(cands), "explicit", candidates

        # 2. filename signal doc_type
        sig = extract_filename_signal(req.doc_path)
        if sig.doc_type:
            cands = [m for m in self._by_doc_type.get(sig.doc_type.upper(), [])
                     if m.supports_extension(ext)]
            candidates.extend(m.name for m in cands)
            if cands:
                return _pick(cands), "filename_doc_type", candidates

        # 3. filename regex hints from each manifest
        cands = [m for m in self._manifests
                 if m.supports_extension(ext) and m.filename_matches(filename)]
        candidates.extend(m.name for m in cands)
        if cands:
            return _pick(cands), "filename_regex", candidates

        # 4. language hint (e.g. Afrikaans-only skill variants)
        if sig.language_hint:
            cands = [m for m in self._manifests
                     if m.supports_extension(ext)
                     and sig.language_hint in m.language_hints]
            candidates.extend(m.name for m in cands)
            if cands:
                return _pick(cands), "language_hint", candidates

        return None, "", candidates

    # ── Dispatch ────────────────────────────────────────────────────────

    def route(self, req: RouteRequest) -> RouteResult:
        manifest, chosen_via, candidates = self.resolve(req)
        if manifest is None:
            return RouteResult(
                skill_name=None, skill_version=None,
                extraction=None, provenance=None,
                no_skill=True,
                no_skill_reason=("no manifest matched explicit doc_type / filename "
                                 "signal / filename regex / language hint"),
                candidates_considered=candidates,
            )

        if manifest.needs_anthropic_key and not os.environ.get("ANTHROPIC_API_KEY"):
            return RouteResult(
                skill_name=manifest.name, skill_version=manifest.version,
                extraction=None, provenance=None,
                no_skill=True,
                no_skill_reason=f"skill {manifest.name} needs ANTHROPIC_API_KEY",
                candidates_considered=candidates,
                chosen_via=chosen_via,
            )

        # Run the skill
        try:
            extraction = manifest.extract(req.doc_path, **req.extra_kwargs)
        except Exception as e:  # noqa: BLE001
            logger.exception("skill %s failed for %s", manifest.name, req.doc_path)
            return RouteResult(
                skill_name=manifest.name, skill_version=manifest.version,
                extraction=None, provenance=None,
                no_skill=True,
                no_skill_reason=f"skill_raised: {type(e).__name__}: {e}",
                candidates_considered=candidates,
                chosen_via=chosen_via,
            )

        # Attach provenance (fingerprint → dedup → VCN → stamp → register)
        provenance = None
        if req.write_provenance:
            provenance = attach_provenance(
                extraction_result=extraction,
                doc_path=req.doc_path,
                doc_id=req.doc_id,
                vault_id=req.vault_id,
                submitter=req.submitter,
                classified_by=manifest.version,
                broker=self.broker,
                sequence_supplier=self.sequence_supplier,
                vault_secret_lookup=self.vault_secret_lookup,
                sidecar_dir=self.sidecar_dir,
                pdf_out_dir=self.pdf_out_dir,
            )

        return RouteResult(
            skill_name=manifest.name,
            skill_version=manifest.version,
            extraction=extraction,
            provenance=provenance,
            candidates_considered=candidates,
            chosen_via=chosen_via,
        )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_skill_manifests(
    skills_package: str = "apps.the_volt.classification.skills",
) -> list[SkillManifest]:
    """Walk `skills/`, import each sub-package, collect every `MANIFEST`.

    Sub-packages without a MANIFEST (empty scaffolds, _shared/, etc.) are
    skipped silently. Import errors are logged but don't crash discovery —
    a single broken skill should never take down the router.
    """
    pkg = importlib.import_module(skills_package)
    found: list[SkillManifest] = []
    seen_names: set[str] = set()
    for info in pkgutil.iter_modules(pkg.__path__, prefix=f"{skills_package}."):
        if not info.ispkg:
            continue
        # Skip private packages (_shared, etc.)
        leaf = info.name.rsplit(".", 1)[-1]
        if leaf.startswith("_"):
            continue
        try:
            mod = importlib.import_module(info.name)
        except Exception as e:  # noqa: BLE001
            logger.warning("skill discovery: cannot import %s: %s", info.name, e)
            continue
        manifest = getattr(mod, "MANIFEST", None)
        if not isinstance(manifest, SkillManifest):
            continue
        if manifest.name in seen_names:
            logger.warning("skill discovery: duplicate name %s — skipping later one",
                           manifest.name)
            continue
        seen_names.add(manifest.name)
        found.append(manifest)
    return found


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick(candidates: list[SkillManifest]) -> SkillManifest:
    """Lowest priority wins; ties broken by name for determinism."""
    return sorted(candidates, key=lambda m: (m.priority, m.name))[0]
