"""
Phase 1 — DEDUPE then GROUP.  Zero LLM tokens.

Two goals only:
  1. Detect duplicates with a multi-signal vote (filename, size, char count,
     SHA-256, first-page text hash). Flag, don't silently drop — the human
     decides what to keep.
  2. Cluster the survivors into document GROUPS (CIPC, FICA, BANKING, HOA, ...)
     using filename patterns + first-page anchor strings. No extraction.

Output:
  /tmp/<folder>_phase1.json      — full per-file record + group assignment
  /tmp/<folder>_phase1.tsv       — human-reviewable table
  /tmp/<folder>_phase1_dupes.tsv — only the duplicate clusters

Usage:
  python3 phase1_group.py --folder "<path>" --label lucanaude
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("pip install pypdf")


# ---------------------------------------------------------------------------
# Anchor-based group rules (deterministic, ordered — first match wins)
# ---------------------------------------------------------------------------

GROUP_RULES = [
    # (group, type, filename_regex, first-page anchor regex)
    ("CIPC", "COR14_3_CERT",  r"(?i)cor\s*14\.?3.*cert|registration\s*certificate", r"Certificate of Incorporation"),
    ("CIPC", "COR14_3",       r"(?i)cor\s*14\.?3", r"COR\s*14\.?3|Notice of Incorporation"),
    ("CIPC", "COR14_1A",      r"(?i)cor\s*14\.?1\s*a", r"Initial Directors"),
    ("CIPC", "COR14_1",       r"(?i)cor\s*14\.?1", r"Notice of Incorporation"),
    ("CIPC", "COR15_1A",      r"(?i)cor\s*15\.?1\s*a", r"Memorandum of Incorporation"),
    ("CIPC", "COR_BUNDLE",    r"(?i)company[_\s]*docs", r"Memorandum of Incorporation|Initial Directors"),

    ("SHARE_CERTIFICATE", "SHARE_CERT", r"(?i)share\s*certificate", r"Share Certificate"),

    ("COMPANY_RESOLUTION", "RES_INCORP",         r"(?i)resolution.*incorporator", None),
    ("COMPANY_RESOLUTION", "RES_SHARE_TRANSFER", r"(?i)resolution.*transfer\s*of\s*shares", None),
    ("COMPANY_RESOLUTION", "RES_AUTH_SIGN",      r"(?i)resolution.*authorisation|auth.*sign", None),
    ("COMPANY_RESOLUTION", "RES_GENERIC",        r"(?i)^resolution|\\bresolution\\b", None),

    ("SARS", "SARS_NOR",       r"(?i)taxnumber|notice\s*of\s*registration", r"SARS|South African Revenue Service"),
    ("SARS", "SARS_DATASHEET", r"(?i)datasheet.*sars", None),

    ("BANKING", "INVESTEC_APP",                 r"(?i)application.*form.*company", r"Investec"),
    ("BANKING", "INVESTEC_ANNEXURE_1",          r"(?i)annexure\s*1.*additional\s*persons", r"Investec"),
    ("BANKING", "INVESTEC_DECL_SHAREHOLDING",   r"(?i)declaration.*shareholding", r"Investec"),
    ("BANKING", "INVESTEC_RES_PBA",             r"(?i)resolution.*pba", r"Investec"),
    ("BANKING", "BANKING_CONFIRMATION",         r"(?i)confirmation.*banking|banking.*confirmation", None),

    ("FICA", "FICA_QUEST_NATPERSON",  r"(?i)fica.*question.*natural\s*person|natural\s*person.*fica", None),
    ("FICA", "FICA_QUEST_COMPANY",    r"(?i)fica.*question.*\(?pty\)?|fica.*question.*ltd|fica.*question.*company", None),
    ("FICA", "POPI_CONSENT",          r"(?i)popi\s*consent", None),
    ("FICA", "INSTRUCTION_INVEST_TRUST", r"(?i)instruction.*invest.*trust", None),

    ("HOA", "OTP_PAM_GOLDING",         r"(?i)\botp\b|offer.*to.*purchase", r"Pam Golding"),
    ("HOA", "HOA_CONSTITUTION",        r"(?i)voliere?.*constitution|constitution.*voliere?", None),
    ("HOA", "HOA_ARCH_GUIDELINES",     r"(?i)arch.*guidelines", None),
    ("HOA", "HOA_BUILDING_GUIDELINES", r"(?i)building.*guidelines", None),
    ("HOA", "HOA_CONDUCT_RULES",       r"(?i)conduct.*rules", None),
    ("HOA", "HOA_ADDENDUM",            r"(?i)hoa.*addendum|addendum.*hoa|addendum\s*p\d", None),
    ("HOA", "HOA_PROPERTY_DIAGRAM",    r"(?i)property\s*diagram", None),
    ("HOA", "HOA_SDP",                 r"(?i)\bsdp\b", None),

    ("TRANSFER_DEED", "TRANSFER_DEED", r"(?i)transfer\s*deed", None),

    ("FINANCIAL", "FIN_STATEMENTS",    r"(?i)financial\s*statements", None),
]


# ---------------------------------------------------------------------------
# File reading
# ---------------------------------------------------------------------------

def normalize_filename(name: str) -> str:
    """Lowercase, strip extension, collapse whitespace + punctuation."""
    n = Path(name).stem.lower()
    n = re.sub(r"[\s_\-\.\(\)\[\]]+", " ", n)
    n = re.sub(r"\s*\d+\s*$", "", n)  # trailing copy counter "(1)", " 2"
    return n.strip()


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(p: Path, max_pages: int = 3) -> tuple[str, dict]:
    """Return (text, quality_info). text is first N pages joined."""
    info = {"pages": None, "chars": 0, "quality": "?", "structure": "?"}
    ext = p.suffix.lower()
    text = ""
    if ext == ".pdf":
        try:
            r = PdfReader(str(p))
            info["pages"] = len(r.pages)
            parts = []
            for i in range(min(len(r.pages), max_pages)):
                try:
                    parts.append(r.pages[i].extract_text() or "")
                except Exception:
                    pass
            text = "\n".join(parts)
        except Exception as e:
            info["error"] = str(e)[:120]
    elif ext in (".docx", ".doc"):
        try:
            import docx
            d = docx.Document(str(p))
            text = "\n".join(par.text for par in d.paragraphs if par.text.strip())
        except Exception as e:
            info["error"] = str(e)[:120]

    info["chars"] = len(text)
    sample_pages = max(min(info["pages"] or 1, max_pages), 1) if ext == ".pdf" else 1
    density = len(text) / sample_pages
    if ext in (".docx", ".doc", ".xlsx", ".xls", ".csv"):
        info["quality"] = "A_digital"; info["structure"] = "tagged"
    elif density > 1500:
        info["quality"] = "A_digital"; info["structure"] = "tagged"
    elif density > 500:
        info["quality"] = "A_digital"; info["structure"] = "semi_tagged"
    elif density > 50:
        info["quality"] = "B_ocr_clean"; info["structure"] = "flat"
    elif density > 0:
        info["quality"] = "C_ocr_noisy"; info["structure"] = "flat"
    else:
        info["quality"] = "D_image_only"; info["structure"] = "none"
    return text, info


# ---------------------------------------------------------------------------
# Group classification (anchor-only, no LLM)
# ---------------------------------------------------------------------------

def classify_group(filename: str, first_page_text: str) -> tuple[str, str, str]:
    """Return (group, type, reason). Returns ('UNGROUPED','UNKNOWN', why)."""
    fname = filename
    text = first_page_text or ""
    for group, type_, fn_re, txt_re in GROUP_RULES:
        fn_hit = bool(re.search(fn_re, fname)) if fn_re else False
        txt_hit = bool(re.search(txt_re, text)) if txt_re else False
        if fn_re and txt_re:
            if fn_hit and txt_hit:
                return group, type_, f"filename+anchor:{fn_re}"
            if fn_hit:  # filename strong enough
                return group, type_, f"filename:{fn_re}"
        elif fn_re and fn_hit:
            return group, type_, f"filename:{fn_re}"
        elif txt_re and txt_hit:
            return group, type_, f"anchor:{txt_re}"
    return "UNGROUPED", "UNKNOWN", "no rule matched"


# ---------------------------------------------------------------------------
# Multi-signal duplicate detection
# ---------------------------------------------------------------------------

def detect_duplicates(records: list[dict]) -> None:
    """Annotate each record with `dupe_status` and `dupe_cluster_id`.

    Signals counted per pair:
      - sha256 exact          (weight 4 — definitive)
      - normalized filename   (weight 2)
      - size within 5%        (weight 1)
      - char count within 5%  (weight 1)
      - first-page text hash  (weight 2)

    score >= 4  → exact_duplicate  (almost always SHA match)
    score >= 3  → likely_duplicate (filename + one of size/chars/text)
    score >= 2  → suspect_variant  (e.g. unsigned vs signed of same template)
    """
    # Bucket by SHA first (fast)
    by_sha: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        by_sha[r["sha256"]].append(i)

    cluster_id = 0
    for r in records:
        r["dupe_status"] = "unique"
        r["dupe_cluster_id"] = None
        r["dupe_peers"] = []

    # SHA exact dupes
    for sha, idxs in by_sha.items():
        if len(idxs) > 1:
            cluster_id += 1
            for i in idxs:
                records[i]["dupe_status"] = "exact_duplicate"
                records[i]["dupe_cluster_id"] = f"C{cluster_id}"
                records[i]["dupe_peers"] = [records[j]["path"] for j in idxs if j != i]

    # Pairwise multi-signal among non-SHA-dupes
    survivors = [i for i, r in enumerate(records) if r["dupe_status"] == "unique"]
    for ai in range(len(survivors)):
        i = survivors[ai]
        if records[i]["dupe_status"] != "unique":
            continue
        for bj in range(ai + 1, len(survivors)):
            j = survivors[bj]
            if records[j]["dupe_status"] != "unique":
                continue
            score = 0
            ra, rb = records[i], records[j]
            if ra["norm_filename"] == rb["norm_filename"] and ra["norm_filename"]:
                score += 2
            if ra["bytes"] and rb["bytes"]:
                rel = abs(ra["bytes"] - rb["bytes"]) / max(ra["bytes"], rb["bytes"])
                if rel < 0.05:
                    score += 1
            if ra["chars"] and rb["chars"]:
                rel = abs(ra["chars"] - rb["chars"]) / max(ra["chars"], rb["chars"])
                if rel < 0.05:
                    score += 1
            if ra.get("first_page_hash") and ra["first_page_hash"] == rb.get("first_page_hash"):
                score += 2
            if score >= 3:
                cluster_id += 1
                tag = "likely_duplicate" if score >= 4 else "suspect_variant"
                records[i]["dupe_status"] = tag
                records[j]["dupe_status"] = tag
                records[i]["dupe_cluster_id"] = f"C{cluster_id}"
                records[j]["dupe_cluster_id"] = f"C{cluster_id}"
                records[i]["dupe_peers"] = [rb["path"]]
                records[j]["dupe_peers"] = [ra["path"]]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_folder(folder: Path) -> list[dict]:
    files = [p for p in folder.rglob("*") if p.is_file() and not p.name.startswith(".")]
    records = []
    for p in files:
        rel = str(p.relative_to(folder))
        text, q = read_text(p)
        first_page = text[:2000]
        first_page_hash = hashlib.sha1(re.sub(r"\s+", " ", first_page.lower()).encode()).hexdigest()[:12] if first_page.strip() else None
        group, type_, reason = classify_group(p.name, first_page)
        records.append({
            "path": rel,
            "norm_filename": normalize_filename(p.name),
            "bytes": p.stat().st_size,
            "sha256": sha256_of(p),
            "pages": q.get("pages"),
            "chars": q.get("chars", 0),
            "quality": q["quality"],
            "structure": q["structure"],
            "first_page_hash": first_page_hash,
            "group": group,
            "type": type_,
            "match_reason": reason,
        })
    detect_duplicates(records)
    return records


def write_outputs(records: list[dict], label: str) -> None:
    base = Path(f"/tmp/{label}_phase1")
    base.with_suffix(".json").write_text(json.dumps(records, indent=2))

    # Main TSV — sorted by group, then type, then path
    headers = ["group", "type", "dupe_status", "dupe_cluster_id", "quality", "structure",
               "pages", "chars", "bytes", "match_reason", "path"]
    rows = sorted(records, key=lambda r: (r["group"], r["type"], r["path"]))
    with open(base.with_suffix(".tsv"), "w") as f:
        f.write("\t".join(headers) + "\n")
        for r in rows:
            f.write("\t".join(str(r.get(h, "") or "") for h in headers) + "\n")

    # Dupes-only TSV
    dupe_rows = [r for r in records if r["dupe_status"] != "unique"]
    dupe_rows.sort(key=lambda r: (r["dupe_cluster_id"] or "", r["path"]))
    with open(str(base) + "_dupes.tsv", "w") as f:
        f.write("\t".join(["dupe_cluster_id", "dupe_status", "group", "type", "bytes", "chars", "path"]) + "\n")
        for r in dupe_rows:
            f.write("\t".join(str(r.get(h, "") or "") for h in
                ["dupe_cluster_id","dupe_status","group","type","bytes","chars","path"]) + "\n")

    # Summary
    from collections import Counter
    g = Counter(r["group"] for r in records)
    t = Counter(r["type"] for r in records)
    d = Counter(r["dupe_status"] for r in records)
    q = Counter(r["quality"] for r in records)

    print(f"\n{'='*72}")
    print(f"PHASE 1 — DEDUPE & GROUP   ({label})")
    print(f"{'='*72}")
    print(f"Files:             {len(records)}")
    print(f"Unique by SHA:     {len({r['sha256'] for r in records})}")
    print(f"Dupe clusters:     {len({r['dupe_cluster_id'] for r in records if r['dupe_cluster_id']})}")
    print(f"\nDuplicate status counts:")
    for k, v in d.most_common(): print(f"  {v:>3}  {k}")
    print(f"\nQuality distribution:")
    for k, v in q.most_common(): print(f"  {v:>3}  {k}")
    print(f"\nGROUPS (anchor classification, 0 LLM tokens):")
    for k, v in g.most_common(): print(f"  {v:>3}  {k}")
    print(f"\nTYPES within groups:")
    for k, v in t.most_common(): print(f"  {v:>3}  {k}")
    print(f"\nWritten:")
    print(f"  {base.with_suffix('.json')}")
    print(f"  {base.with_suffix('.tsv')}")
    print(f"  {str(base)}_dupes.tsv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--label", required=True, help="output filename prefix, e.g. lucanaude")
    args = ap.parse_args()
    records = process_folder(Path(args.folder))
    write_outputs(records, args.label)


if __name__ == "__main__":
    main()
