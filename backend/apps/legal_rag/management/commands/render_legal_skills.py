"""Render canonical legal-fact YAML into skill ``.md`` reference files.

Reads facts from the active :class:`LegalCorpusVersion` via the public
query API and renders one Jinja2 template per target skill ``.md`` file.
The renderer ONLY rewrites the section between
``<!-- BEGIN AUTO-GENERATED legal-facts -->`` and
``<!-- END AUTO-GENERATED legal-facts -->`` — everything outside the
markers (intros, narrative, hand-written process guidance) is preserved
verbatim.

Behaviour locked by ``content/cto/centralised-legal-rag-store-plan.md`` §7.

Default mode is ``--check`` (the safe one): re-render in-memory, diff
against the on-disk file, exit ``1`` on drift with a unified diff to
stderr. ``--write`` is the explicit opt-in that actually mutates files.

Usage::

    python manage.py render_legal_skills                    # check, default
    python manage.py render_legal_skills --check --verbose  # check, loud
    python manage.py render_legal_skills --write            # mutate files
    python manage.py render_legal_skills --target=.claude/skills/.../06-rha-core-and-s5.md
"""
from __future__ import annotations

import difflib
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.legal_rag.models import LegalCorpusVersion
from apps.legal_rag.skill_rendering import (
    BEGIN_MARKER,
    END_MARKER,
    build_environment,
    default_template_root,
    extract_section,
    render_target,
    replace_section,
)

logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────── #


ADVISORY_LOCK_KEY = "render_legal_skills"

#: Map of repo-relative skill ``.md`` path → Jinja2 template name.
#: Day 1 ships only the two RHA targets per §7 of the plan. Adding a
#: skill in future = add a row + a template; no command changes needed.
DEFAULT_TARGETS: dict[str, str] = {
    ".claude/skills/klikk-legal-POPIA-RHA/references/06-rha-core-and-s5.md": (
        "klikk-legal-POPIA-RHA/06-rha-core-and-s5.md.j2"
    ),
    ".claude/skills/klikk-legal-POPIA-RHA/references/07-rha-s4a-unfair-practices.md": (
        "klikk-legal-POPIA-RHA/07-rha-s4a-unfair-practices.md.j2"
    ),
}


# ── Per-target result ─────────────────────────────────────────────────── #


@dataclass
class TargetResult:
    """Outcome of a single target after the render pass."""

    target_path: Path
    template_name: str
    drift: bool  # True if --check would fail or --write changed bytes
    diff: str  # Unified diff (empty when ``drift`` is False)
    written: bool  # True when --write mutated the on-disk file
    facts_used: tuple[str, ...]


# ── Command ──────────────────────────────────────────────────────────── #


class Command(BaseCommand):
    """Render skill ``.md`` files from the canonical legal-fact corpus.

    Default mode is ``--check`` (no writes). Use ``--write`` to mutate
    the on-disk files.
    """

    help = (
        "Render canonical legal-fact YAML into skill reference .md files. "
        "Default is --check (drift detector). Use --write to actually "
        "mutate the on-disk files."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--check",
            action="store_true",
            help=(
                "Re-render each target in memory; diff against the on-disk "
                "file. Exit 1 on any drift. This is the default mode."
            ),
        )
        parser.add_argument(
            "--write",
            action="store_true",
            help=(
                "Explicit opt-in: mutate on-disk skill .md files to match "
                "the rendered YAML. Mutually exclusive with --check."
            ),
        )
        parser.add_argument(
            "--target",
            action="append",
            default=[],
            help=(
                "Repo-relative path to a single target .md to render. "
                "Pass multiple times to narrow to several targets. "
                "Defaults to the full DEFAULT_TARGETS list."
            ),
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="One log line per target processed.",
        )

    # ── Entry point ──────────────────────────────────────────────────── #

    def handle(self, *args, **options) -> None:
        check: bool = bool(options.get("check"))
        write: bool = bool(options.get("write"))
        targets_filter: list[str] = options.get("target") or []
        verbose: bool = bool(options.get("verbose"))

        if check and write:
            raise CommandError(
                "--check and --write are mutually exclusive. "
                "Pass at most one."
            )
        # Default to check mode if neither flag was passed.
        if not check and not write:
            check = True

        repo_root = self._resolve_repo_root()
        selected = self._resolve_targets(targets_filter, repo_root)

        corpus_version = self._load_corpus_version()
        env = build_environment(default_template_root())

        try:
            self._acquire_advisory_lock()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(
                f"Could not acquire pg_advisory_lock for render: {exc}"
            ) from exc

        results: list[TargetResult] = []
        try:
            for rel_path, template_name in selected:
                target_path = repo_root / rel_path
                result = self._process_one(
                    target_path=target_path,
                    template_name=template_name,
                    corpus_version=corpus_version,
                    env=env,
                    write=write,
                    verbose=verbose,
                )
                results.append(result)
        finally:
            self._release_advisory_lock()

        drift_targets = [r for r in results if r.drift]
        if check:
            if not drift_targets:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"render_legal_skills --check: clean. "
                        f"{len(results)} target(s) match YAML "
                        f"(corpus_version={corpus_version})."
                    )
                )
                return
            # Emit unified diffs to stderr so callers can see what changed.
            for r in drift_targets:
                self.stderr.write(
                    self.style.ERROR(
                        f"DRIFT  {r.target_path.relative_to(repo_root)}"
                    )
                )
                if r.diff:
                    self.stderr.write(r.diff)
            self.stderr.write(
                self.style.ERROR(
                    f"render_legal_skills --check: {len(drift_targets)} "
                    f"target(s) drifted from YAML. Run with --write to fix."
                )
            )
            sys.exit(1)

        # --write path
        if drift_targets:
            for r in drift_targets:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"WROTE  {r.target_path.relative_to(repo_root)} "
                        f"({len(r.facts_used)} facts referenced)"
                    )
                )
        else:
            self.stdout.write(
                "render_legal_skills --write: no changes "
                "(all targets already in sync)."
            )

    # ── Repo-root resolution ────────────────────────────────────────── #

    def _resolve_repo_root(self) -> Path:
        """Repo root for relative target paths.

        Honour ``settings.LEGAL_RAG_RENDER_REPO_ROOT`` if set (tests use this
        to point at a temp directory). Otherwise fall back to
        ``BASE_DIR.parent`` — the same convention :mod:`sync_legal_facts`
        and :mod:`checks` use.
        """
        override = getattr(settings, "LEGAL_RAG_RENDER_REPO_ROOT", None)
        if override:
            return Path(override).resolve()
        return Path(settings.BASE_DIR).parent

    # ── Target resolution ───────────────────────────────────────────── #

    def _resolve_targets(
        self,
        targets_filter: list[str],
        repo_root: Path,
    ) -> list[tuple[str, str]]:
        """Return ``[(rel_path, template_name), ...]`` to render.

        If ``targets_filter`` is empty, return every entry in
        ``DEFAULT_TARGETS``. Otherwise return only the matching subset
        and raise ``CommandError`` if a requested target is unknown — the
        renderer must not silently no-op on a typo.
        """
        if not targets_filter:
            return list(DEFAULT_TARGETS.items())

        normalised = [self._normalise_target(t, repo_root) for t in targets_filter]
        unknown = [t for t in normalised if t not in DEFAULT_TARGETS]
        if unknown:
            raise CommandError(
                "Unknown --target value(s): "
                + ", ".join(unknown)
                + ". Known targets: "
                + ", ".join(sorted(DEFAULT_TARGETS.keys()))
            )
        return [(t, DEFAULT_TARGETS[t]) for t in normalised]

    @staticmethod
    def _normalise_target(target: str, repo_root: Path) -> str:
        """Allow ``--target`` to be passed absolute or repo-relative."""
        as_path = Path(target).expanduser()
        if as_path.is_absolute():
            try:
                return str(as_path.resolve().relative_to(repo_root))
            except ValueError:
                return target
        # If passed as ``./foo`` strip the leading ``./``.
        return str(as_path).lstrip("./") if as_path.parts and as_path.parts[0] == "." else str(as_path)

    # ── Corpus version lookup ───────────────────────────────────────── #

    def _load_corpus_version(self) -> str:
        """Return the active corpus version string for the footer.

        If no active row exists yet (the loader has not run), use a
        deterministic placeholder so check-mode can still operate during
        bootstrap. Render output remains diffable.
        """
        active = LegalCorpusVersion.objects.filter(is_active=True).first()
        if active is None:
            return "unsynced"
        return active.version

    # ── Per-target processing ───────────────────────────────────────── #

    def _process_one(
        self,
        *,
        target_path: Path,
        template_name: str,
        corpus_version: str,
        env,
        write: bool,
        verbose: bool,
    ) -> TargetResult:
        """Render one target and either diff-it or write-it.

        Returns a :class:`TargetResult` so the caller can aggregate
        outcomes across all targets before deciding the exit code.
        """
        if not target_path.is_file():
            raise CommandError(
                f"Target file not found: {target_path}. "
                "Add the markers to the file before running the renderer."
            )

        on_disk = target_path.read_text(encoding="utf-8")
        if BEGIN_MARKER not in on_disk or END_MARKER not in on_disk:
            raise CommandError(
                f"Target {target_path} is missing auto-generated markers. "
                f"Add {BEGIN_MARKER} ... {END_MARKER} before running the renderer."
            )

        render_result = render_target(
            template_name,
            corpus_version=corpus_version,
            env=env,
        )
        new_content = replace_section(on_disk, render_result.rendered_section)
        drift = new_content != on_disk

        diff = ""
        if drift:
            diff = "".join(
                difflib.unified_diff(
                    on_disk.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{target_path.name}",
                    tofile=f"b/{target_path.name}",
                )
            )

        written = False
        if write and drift:
            target_path.write_text(new_content, encoding="utf-8")
            written = True

        if verbose:
            if drift and write:
                self.stdout.write(f"  rendered  {target_path.name}  (wrote)")
            elif drift:
                self.stdout.write(f"  rendered  {target_path.name}  (drift)")
            else:
                self.stdout.write(f"  rendered  {target_path.name}  (clean)")

        return TargetResult(
            target_path=target_path,
            template_name=template_name,
            drift=drift,
            diff=diff,
            written=written,
            facts_used=render_result.facts_used,
        )

    # ── Advisory lock ───────────────────────────────────────────────── #

    def _acquire_advisory_lock(self) -> None:
        """``pg_advisory_lock(hashtext('render_legal_skills'))`` for the run."""
        if connection.vendor != "postgresql":
            logger.warning(
                "render_legal_skills: not running on PostgreSQL (vendor=%r) "
                "— skipping advisory lock. Tests / SQLite envs only.",
                connection.vendor,
            )
            return
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_lock(hashtext(%s))", [ADVISORY_LOCK_KEY]
            )

    def _release_advisory_lock(self) -> None:
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cur:
            cur.execute(
                "SELECT pg_advisory_unlock(hashtext(%s))",
                [ADVISORY_LOCK_KEY],
            )


__all__ = ["Command", "DEFAULT_TARGETS", "TargetResult"]
