"""
Phase 2 — Consensus identifier extraction.

For each unique file in a folder, run deterministic regex extractors for
SA-specific identifiers (company reg, SA ID, tax number, VAT, dates).
Vote across documents to establish CANONICAL values for the entity.

Output:
  /tmp/<label>_consensus.json — per-identifier votes + canonical
  /tmp/<label>_consensus.tsv  — human-reviewable

The principle: in a high-quality legal-document pack (CIPC, banking, SARS),
the same identifiers appear many times. Disagreements are signal — they
flag either a bad extraction or a real data discrepancy worth investigating.

Zero LLM tokens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pip install pypdf")


# ---------------------------------------------------------------------------
# SA-specific patterns
# ---------------------------------------------------------------------------

PATTERNS = {
    # YYYY/NNNNNN/NN — CIPC company / CC registration number
    "company_reg": re.compile(r"\b(19|20)\d{2}\s*/\s*\d{6}\s*/\s*\d{2}\b"),
    # 13-digit SA ID (basic Luhn-ish check below)
    "sa_id":       re.compile(r"\b\d{13}\b"),
    # SARS taxpayer ref (10 digits, not preceded by another digit)
    "tax_number":  re.compile(r"(?<!\d)\d{10}(?!\d)"),
    # SA VAT number — 10 digits starting with 4
    "vat_number":  re.compile(r"\b4\d{9}\b"),
    # Trust ref — IT.../YYYY (Stellenbosch / Cape Town Master patterns vary)
    "trust_ref":   re.compile(r"\bIT\s*\d{3,6}\s*/\s*(19|20)\d{2}\b", re.I),
    # ISO-ish dates 2019-04-25 / 2019/04/25 / 25 April 2019
    "date_iso":    re.compile(r"\b(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b"),
    "date_long":   re.compile(r"\b(0?[1-9]|[12]\d|3[01])\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(19|20)\d{2}\b", re.I),
    # SA postal code 4 digits at end of an address line
    "postal_code": re.compile(r"\b\d{4}\b"),
}

# Patterns we KNOW apply only to specific document groups (reduces noise)
GROUP_FILTER = {
    "tax_number":  {"SARS", "BANKING", "CIPC"},  # only count tax# from these
    "vat_number":  {"SARS", "BANKING"},
    "trust_ref":   {"FICA"},
}


def normalize(kind: str, raw: str) -> str:
    """Canonicalise format so '2019/419725/07' == '2019 / 419725 / 07'."""
    if kind == "company_reg":
        return re.sub(r"\s+", "", raw)
    if kind in ("sa_id", "tax_number", "vat_number", "postal_code"):
        return re.sub(r"\D", "", raw)
    if kind == "trust_ref":
        return re.sub(r"\s+", "", raw.upper())
    return raw.strip()


def luhn_id_ok(id13: str) -> bool:
    """Cheap SA-ID sanity: 13 digits, valid date, valid Luhn check digit."""
    if len(id13) != 13 or not id13.isdigit():
        return False
    yy = int(id13[0:2]); mm = int(id13[2:4]); dd = int(id13[4:6])
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return False
    # Luhn
    total = 0
    for i, ch in enumerate(id13):
        d = int(ch)
        if i % 2 == 0: total += d
        else:
            d *= 2
            total += d if d < 10 else d - 9
    return total % 10 == 0


def reg_num_ok(reg: str) -> bool:
    """Year part must be 1900–current and look like a real CIPC number."""
    m = re.match(r"^(\d{4})/(\d{6})/(\d{2})$", reg)
    if not m: return False
    yr = int(m.group(1))
    return 1900 <= yr <= 2100


def read_text(p: Path, max_pages: int = 10) -> tuple[str, str]:
    """Return (full_text_sample, group). Group filled later from phase1 if available."""
    if p.suffix.lower() == ".pdf":
        try:
            r = PdfReader(str(p))
            parts = []
            for i in range(min(len(r.pages), max_pages)):
                try: parts.append(r.pages[i].extract_text() or "")
                except Exception: pass
            return "\n".join(parts), ""
        except Exception:
            return "", ""
    if p.suffix.lower() in (".docx", ".doc"):
        try:
            import docx
            d = docx.Document(str(p))
            return "\n".join(par.text for par in d.paragraphs if par.text.strip()), ""
        except Exception:
            return "", ""
    return "", ""


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_identifiers(text: str, group: str) -> dict[str, list[str]]:
    """Run all patterns. Apply group filters and validity checks."""
    found: dict[str, list[str]] = defaultdict(list)
    for kind, pat in PATTERNS.items():
        # Group filter
        allowed = GROUP_FILTER.get(kind)
        if allowed is not None and group and group not in allowed:
            continue
        for m in pat.finditer(text):
            raw = m.group(0)
            val = normalize(kind, raw)
            # Validity checks
            if kind == "sa_id" and not luhn_id_ok(val):
                continue
            if kind == "company_reg" and not reg_num_ok(val):
                continue
            if kind == "postal_code":
                # Reject if it's actually part of a longer number (year, ID) by
                # requiring the surrounding context to be address-like
                start, end = m.span()
                ctx = text[max(0, start - 30):min(len(text), end + 30)].lower()
                if not any(w in ctx for w in ("street","road","ave","avenue","lane","park","stellenbosch","western cape","gauteng","cape town",",7","postal")):
                    continue
            found[kind].append(val)
    # Dedupe within a single document but preserve count
    for k in list(found.keys()):
        found[k] = list(found[k])  # keep duplicates → vote weight
    return dict(found)


def build_consensus(per_file: dict[str, dict]) -> dict:
    """Tally votes across files. Winner = most occurrences across files (each
    file contributes 1 vote per distinct value it contains, capped at 1)."""
    by_kind: dict[str, Counter] = defaultdict(Counter)
    by_kind_files: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for path, data in per_file.items():
        for kind, vals in data["identifiers"].items():
            seen_in_file = set(vals)
            for v in seen_in_file:
                by_kind[kind][v] += 1
                by_kind_files[kind][v].append(path)
    consensus = {}
    for kind, counter in by_kind.items():
        if not counter: continue
        ranked = counter.most_common()
        top_val, top_count = ranked[0]
        total_files_with_kind = sum(counter.values())  # actually # of file-mentions
        # Number of files that have ANY value for this kind
        files_voting = len({f for v in counter for f in by_kind_files[kind][v]})
        share = top_count / files_voting if files_voting else 0
        consensus[kind] = {
            "canonical": top_val,
            "votes_for_canonical": top_count,
            "files_voting": files_voting,
            "share": round(share, 3),
            "all_values": [{"value": v, "votes": c, "files": by_kind_files[kind][v]}
                          for v, c in ranked],
        }
    return consensus


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--phase1", help="optional: path to phase1 JSON to inherit groups")
    args = ap.parse_args()

    folder = Path(args.folder)

    # Optionally pull groups from Phase 1 output
    group_by_path: dict[str, str] = {}
    if args.phase1 and Path(args.phase1).is_file():
        for r in json.loads(Path(args.phase1).read_text()):
            group_by_path[r["path"]] = r["group"]

    # Collect unique files (by SHA, shortest path wins)
    seen_sha: dict[str, Path] = {}
    for p in folder.rglob("*"):
        if not p.is_file() or p.name.startswith("."): continue
        sha = sha256_of(p)
        if sha not in seen_sha or len(str(p)) < len(str(seen_sha[sha])):
            seen_sha[sha] = p

    per_file = {}
    for sha, p in seen_sha.items():
        rel = str(p.relative_to(folder))
        text, _ = read_text(p)
        group = group_by_path.get(rel, "")
        ids = extract_identifiers(text, group)
        per_file[rel] = {
            "sha256": sha,
            "group": group,
            "chars": len(text),
            "identifiers": ids,
            "id_kinds_found": list(ids.keys()),
        }

    consensus = build_consensus(per_file)

    out = {"folder": str(folder), "files_scanned": len(per_file), "consensus": consensus, "per_file": per_file}
    Path(f"/tmp/{args.label}_consensus.json").write_text(json.dumps(out, indent=2))

    # TSV summary per identifier
    with open(f"/tmp/{args.label}_consensus.tsv", "w") as f:
        f.write("kind\tcanonical\tvotes\tfiles_voting\tshare\tdisagreements\n")
        for kind in sorted(consensus.keys()):
            c = consensus[kind]
            disagrees = [v for v in c["all_values"] if v["value"] != c["canonical"]]
            disagree_summary = "; ".join(f"{v['value']}({v['votes']})" for v in disagrees) or "—"
            f.write(f"{kind}\t{c['canonical']}\t{c['votes_for_canonical']}\t{c['files_voting']}\t{c['share']}\t{disagree_summary}\n")

    # Console report
    print(f"\n{'='*72}")
    print(f"PHASE 2 — CONSENSUS  ({args.label})  —  {len(per_file)} unique files")
    print(f"{'='*72}\n")
    for kind in sorted(consensus.keys()):
        c = consensus[kind]
        marker = "✓" if c["share"] >= 0.8 else ("?" if c["share"] >= 0.5 else "!")
        print(f"  {marker}  {kind:<14}  {c['canonical']:<22}  "
              f"votes={c['votes_for_canonical']}/{c['files_voting']}  share={c['share']}")
        if len(c["all_values"]) > 1:
            print(f"     dissent:")
            for v in c["all_values"][1:]:
                print(f"        {v['value']:<22} votes={v['votes']}  in: {v['files'][:3]}{'...' if len(v['files']) > 3 else ''}")
    print(f"\nWritten: /tmp/{args.label}_consensus.{{json,tsv}}")


if __name__ == "__main__":
    main()
