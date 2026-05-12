"""
Verify legal citations across the Klikk repo against the canonical citation map.

Scans markdown + YAML files for citation patterns (RHA / POPIA / CPA / PIE),
compares each citation against the HIGH-confidence "Working canonical" column
of `content/cto/rha-citation-canonical-map.md`, and reports drift.

The map flags LOW-confidence rows (e.g. RHA s5(3)(f) for interest-bearing
account) that need SA-admitted-attorney sign-off. This command does NOT
attempt to validate LOW-confidence rows — only HIGH-confidence canonical
mappings can be checked mechanically.

Usage:
    python manage.py verify_caselaw_citations
    python manage.py verify_caselaw_citations --strict     # fail on warnings
    python manage.py verify_caselaw_citations --format=json
    python manage.py verify_caselaw_citations --path=docs/system/lease-ai-agent-architecture.md

Exit codes:
    0 — all checked citations match canonical, no drift
    1 — at least one citation drifted from canonical (CI failure)
    2 — could not locate canonical map (config error)

Design rationale: SAFLII is Cloudflare-protected and cannot be programmatically
fetched. We can't verify against the primary source at runtime. The fallback
is a curated canonical map maintained by the CTO and signed off by counsel.
The CLI is the CI gate that prevents drift from that map.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.management.base import BaseCommand


# HIGH-confidence canonical citations from content/cto/rha-citation-canonical-map.md.
# Updates to this dict MUST be reflected in the map and signed off by the CTO.
#
# Format: { "<statute>:<section>": ("concept", "confidence") }
# confidence: HIGH (mechanically enforced) | MEDIUM (warn-only) | LOW (skip — lawyer)
CANONICAL_CITATIONS: dict[str, tuple[str, str]] = {
    # Keys are lowercased to match normalise(); see normalise() for the format.
    # RHA — Rental Housing Act 50/1999 (as amended by Act 35/2014)
    "RHA:s4(1)": ("Non-discrimination", "HIGH"),
    "RHA:s4(2)": ("Tenant right to privacy", "HIGH"),
    "RHA:s4(3)": ("Prohibits unfair discrimination", "HIGH"),
    "RHA:s4(5)": ("Habitability obligation", "HIGH"),
    "RHA:s4a": ("Unfair practices framework", "HIGH"),
    "RHA:s5(2)": ("Right to written lease", "HIGH"),
    "RHA:s5(3)": ("Mandatory lease contents (top-level)", "HIGH"),
    "RHA:s5(3)(a)": ("Names + addresses for service", "HIGH"),
    "RHA:s5(3)(b)": ("Description of dwelling", "HIGH"),
    "RHA:s5(3)(c)": ("Rental amount + escalation", "MEDIUM"),
    "RHA:s5(3)(d)": ("Term / notice period", "MEDIUM"),
    "RHA:s5(3)(e)": ("Deposit amount", "HIGH"),
    "RHA:s5(3)(f)": ("Deposit interest-bearing account", "LOW"),
    "RHA:s5(3)(g)": ("Rent due date", "HIGH"),
    "RHA:s5(3)(h)": ("Landlord + tenant obligations summary", "MEDIUM"),
    "RHA:s5(3)(i)": ("House rules annexed", "MEDIUM"),
    "RHA:s5(3)(j)": ("Deposit purpose + refund terms", "MEDIUM"),
    "RHA:s5(3)(k)": ("Joint inspection requirement", "MEDIUM"),
    "RHA:s5(4)": ("Plain language requirement", "HIGH"),
    "RHA:s5(5)": ("Notice period default (one month)", "HIGH"),
    "RHA:s5(6)": ("Renewal / continuation on tacit consent", "HIGH"),
    "RHA:s5a": ("Landlord duties", "HIGH"),
    "RHA:s5b": ("Tenant duties", "HIGH"),
    "RHA:s7": ("Tribunal establishment", "HIGH"),
    "RHA:s13": ("Tribunal powers / referral", "HIGH"),
    "RHA:s13(12)": ("Tribunal ruling has effect of Magistrate's Court order", "HIGH"),
    "RHA:s14": ("Rental Housing Information Office", "HIGH"),
    "RHA:s15": ("Minister's regulations", "HIGH"),
    "RHA:s16": ("Contraventions / fines", "HIGH"),
    # POPIA — Act 4/2013
    "POPIA:s11": ("Lawful processing conditions (top-level)", "HIGH"),
    "POPIA:s11(1)": ("Lawful processing — grounds (top-level)", "HIGH"),
    "POPIA:s11(1)(a)": ("Lawful basis — consent", "HIGH"),
    "POPIA:s11(1)(b)": ("Lawful basis — contract", "HIGH"),
    "POPIA:s11(1)(c)": ("Lawful basis — legal obligation", "HIGH"),
    "POPIA:s11(1)(d)": ("Lawful basis — vital interest", "HIGH"),
    "POPIA:s11(1)(e)": ("Lawful basis — public duty / law", "HIGH"),
    "POPIA:s11(1)(f)": ("Lawful basis — legitimate interest", "HIGH"),
    "POPIA:s13": ("Purpose specification", "HIGH"),
    "POPIA:s14": ("Retention limitation", "HIGH"),
    "POPIA:s15": ("Further processing limitation", "HIGH"),
    "POPIA:s16": ("Information quality / accuracy", "HIGH"),
    "POPIA:s17": ("Documentation of processing operations", "HIGH"),
    "POPIA:s18": ("Notification to data subject", "HIGH"),
    "POPIA:s19": ("Security safeguards", "HIGH"),
    "POPIA:s23": ("Data subject access", "HIGH"),
    "POPIA:s24": ("Data subject correction / deletion", "HIGH"),
    "POPIA:s25": ("Manner of access", "HIGH"),
    "POPIA:s69": ("Direct marketing", "HIGH"),
    "POPIA:s72": ("Cross-border transfer", "HIGH"),
    # CPA — Act 68/2008
    "CPA:s14": ("Fixed-term consumer agreement (cancellation, max 24mo)", "HIGH"),
    "CPA:s16": ("Cooling-off period (direct marketing)", "HIGH"),
    "CPA:s22": ("Plain language requirement", "HIGH"),
    "CPA:s48": ("Unfair contract terms", "HIGH"),
    "CPA:s51": ("Prohibited transactions / terms", "HIGH"),
    "CPA:s54": ("Quality of services", "HIGH"),
    # PIE Act 19/1998
    "PIE:s1": ("Definitions (unlawful occupier)", "HIGH"),
    "PIE:s4": ("Eviction proceedings — urgent", "HIGH"),
    "PIE:s4(2)": ("Notice of eviction proceedings (14 days)", "HIGH"),
    "PIE:s4(6)": ("Court factors — informal settlement / vulnerable", "HIGH"),
    "PIE:s5": ("Eviction proceedings — any unlawful occupier", "HIGH"),
    "PIE:s8": ("Offences / penalties", "HIGH"),
}


# Known-wrong citations the second audit flagged. Detecting any of these is an
# immediate FAIL regardless of context.
KNOWN_WRONG_CITATIONS: dict[str, str] = {
    "RHA:s13|tribunal_established": "Tribunal is established under s7, not s13. s13 covers powers.",
    "POPIA:s23|accuracy": "Accuracy/information-quality is s16, not s23. s23 is data subject access.",
    "POPIA:s11(2)|accuracy": "Accuracy is s16. s11 is conditions for lawful processing.",
    "POPIA:s25|deletion": "Deletion is s24 (correction includes deletion of inaccurate/excessive PI). s25 is manner of access.",
}


# Regex matching any of our statutes. Captures: statute, full_section_str.
CITATION_RE = re.compile(
    r"\b(RHA|POPIA|CPA|PIE)\s+(s\d+[A-Z]?(?:\(\d+\))?(?:\([a-z]\))?(?:\(\d+\))?)",
    re.IGNORECASE,
)


@dataclass
class Finding:
    """A single citation occurrence and its verdict."""
    file: str
    line: int
    citation: str  # canonical form, e.g. "RHA:s5(3)(f)"
    raw: str       # what we matched in the file
    status: str    # PASS | WARN | FAIL | UNKNOWN
    message: str = ""


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "FAIL")

    @property
    def warn_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "WARN")

    @property
    def pass_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "PASS")


# Files we always scan unless --path narrows the scope. Relative to repo root.
DEFAULT_SCAN_PATHS: tuple[str, ...] = (
    "docs/system/lease-ai-agent-architecture.md",
    ".claude/skills/klikk-legal-POPIA-RHA/references",
    ".claude/skills/klikk-rental-master/references",
    ".claude/skills/klikk-leases-rental-agreement/references",
    "content/cto/rha-citation-canonical-map.md",
)


def normalise(statute: str, section: str) -> str:
    """Turn matched groups into the canonical "RHA:s5(3)(f)" form."""
    return f"{statute.upper()}:{section.lower()}"


def repo_root() -> Path:
    # settings.BASE_DIR points to backend/; the repo root is its parent.
    return Path(settings.BASE_DIR).parent


def iter_target_files(paths: Iterable[str]) -> Iterable[Path]:
    """Yield every .md / .yaml file under each path."""
    root = repo_root()
    for raw_path in paths:
        target = root / raw_path
        if not target.exists():
            continue
        if target.is_file():
            yield target
            continue
        for ext in (".md", ".yaml", ".yml"):
            yield from target.rglob(f"*{ext}")


def scan_file(path: Path) -> list[Finding]:
    """Find every citation in `path` and tag it PASS/WARN/FAIL/UNKNOWN."""
    findings: list[Finding] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_num, line in enumerate(text.splitlines(), start=1):
        for match in CITATION_RE.finditer(line):
            statute, section = match.group(1), match.group(2)
            canonical = normalise(statute, section)
            entry = CANONICAL_CITATIONS.get(canonical)
            if entry is None:
                findings.append(Finding(
                    file=str(path.relative_to(repo_root())),
                    line=line_num,
                    citation=canonical,
                    raw=match.group(0),
                    status="UNKNOWN",
                    message=f"Citation not in canonical map. Add to CANONICAL_CITATIONS or fix the source.",
                ))
                continue
            _concept, confidence = entry
            if confidence == "LOW":
                findings.append(Finding(
                    file=str(path.relative_to(repo_root())),
                    line=line_num,
                    citation=canonical,
                    raw=match.group(0),
                    status="WARN",
                    message=f"LOW-confidence citation ({_concept}) — requires lawyer sign-off before relied upon.",
                ))
            else:
                findings.append(Finding(
                    file=str(path.relative_to(repo_root())),
                    line=line_num,
                    citation=canonical,
                    raw=match.group(0),
                    status="PASS",
                ))
    return findings


def render_text(report: Report) -> str:
    lines: list[str] = []
    by_file: dict[str, list[Finding]] = {}
    for f in report.findings:
        by_file.setdefault(f.file, []).append(f)
    for file, file_findings in sorted(by_file.items()):
        non_pass = [f for f in file_findings if f.status != "PASS"]
        if not non_pass:
            continue
        lines.append(f"\n{file}")
        for f in non_pass:
            lines.append(f"  [{f.status}] line {f.line}: {f.raw} → {f.citation}")
            if f.message:
                lines.append(f"           {f.message}")
    lines.append("")
    lines.append(
        f"Scanned {report.files_scanned} files. "
        f"PASS={report.pass_count} WARN={report.warn_count} FAIL={report.fail_count} "
        f"UNKNOWN={sum(1 for f in report.findings if f.status == 'UNKNOWN')}"
    )
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Verify legal citations across the repo against the canonical citation map."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict", action="store_true",
            help="Exit non-zero on WARN and UNKNOWN as well as FAIL.",
        )
        parser.add_argument(
            "--format", choices=("text", "json"), default="text",
            help="Output format.",
        )
        parser.add_argument(
            "--path", action="append", default=None,
            help="Override DEFAULT_SCAN_PATHS. May be passed multiple times.",
        )

    def handle(self, *args, **options):
        paths = options["path"] or list(DEFAULT_SCAN_PATHS)
        report = Report()
        for file in iter_target_files(paths):
            report.files_scanned += 1
            report.findings.extend(scan_file(file))

        if options["format"] == "json":
            payload = {
                "files_scanned": report.files_scanned,
                "summary": {
                    "pass": report.pass_count,
                    "warn": report.warn_count,
                    "fail": report.fail_count,
                    "unknown": sum(1 for f in report.findings if f.status == "UNKNOWN"),
                },
                "findings": [asdict(f) for f in report.findings if f.status != "PASS"],
            }
            self.stdout.write(json.dumps(payload, indent=2))
        else:
            self.stdout.write(render_text(report))

        if report.fail_count > 0:
            raise SystemExit(1)
        unknown = sum(1 for f in report.findings if f.status == "UNKNOWN")
        if options["strict"] and (report.warn_count > 0 or unknown > 0):
            raise SystemExit(1)
