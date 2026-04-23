"""
THE VOLT — Skill manifest.

Every skill folder under `classification/skills/<name>/` declares a
`MANIFEST = SkillManifest(...)` at module top level. The identity router
auto-discovers skills by importing each sub-package and pulling its
manifest — no central registry to keep in sync, no markdown parsing.

A manifest tells the router:
  • which canonical doc_types this skill claims (one or many)
  • the entry-point callable: `extract(path, **kwargs) -> ExtractionResult`
  • supported file kinds (".pdf", ".jpg", ".png", …)
  • whether the skill needs ANTHROPIC_API_KEY (vision skills do)
  • soft hints to bias the router when filename signals are ambiguous
    (e.g. `accepts_when_filename_matches=[r"id[_ ]doc"]`)

Routing precedence (highest first):
  1. Explicit `doc_type` in the request → exact manifest match
  2. Filename signal `doc_type` (Layer 0) → exact match
  3. Filename signal hits any `accepts_when_filename_matches` regex
  4. Multi-skill candidates → resolved via `priority` (low = preferred)
  5. No skill matches → request goes to L4 generic LLM extractor (or
     queued for L5 auto-train if the corpus_observer is interested)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence


@dataclass(frozen=True)
class SkillManifest:
    """Self-description published by each skill package."""
    name: str                                    # "sa_smart_id_card"
    version: str                                 # "skill:sa_smart_id_card@v1"
    doc_types: tuple[str, ...]                   # canonical doc_types this skill produces
    extract: Callable                            # signature: extract(path, **kwargs) -> ExtractionResult
    file_kinds: tuple[str, ...] = (".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")
    needs_anthropic_key: bool = True
    priority: int = 100                          # lower wins when multiple skills match
    accepts_when_filename_matches: tuple[str, ...] = ()
    # Bilingual / regional hints — the router can prefer this skill when
    # the language hint from the filename signal matches (e.g. "af" for
    # Afrikaans documents like "Geboorte sertifikaat")
    language_hints: tuple[str, ...] = ()
    description: str = ""

    def supports_doc_type(self, doc_type: str) -> bool:
        return (doc_type or "").upper() in {dt.upper() for dt in self.doc_types}

    def supports_extension(self, ext: str) -> bool:
        return (ext or "").lower() in {e.lower() for e in self.file_kinds}

    def filename_matches(self, filename: str) -> bool:
        if not self.accepts_when_filename_matches:
            return False
        return any(re.search(rx, filename, flags=re.IGNORECASE)
                   for rx in self.accepts_when_filename_matches)
