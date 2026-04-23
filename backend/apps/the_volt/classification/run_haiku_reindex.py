"""
Haiku re-indexer for LucaNaude (Pty) Ltd folder.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 backend/apps/the_volt/classification/run_haiku_reindex.py \
        --folder "/Users/mcdippenaar/Claude Co-Work Projects/Document Upload/Upload Document to MCP/LucaNaude Pty Ltd" \
        --prompt backend/apps/the_volt/classification/prompts/reindex_lucanaude_v1.md \
        --out   /tmp/lucanaude_haiku_index.jsonl \
        --model claude-haiku-4-5

Outputs:
    /tmp/lucanaude_haiku_index.jsonl — one extracted record per unique file
    /tmp/lucanaude_haiku_report.json — summary: cost, latency, schema pass rate,
                                       confidence distribution, group counts

Designed as the STUDENT runner in Opus→Haiku teacher/student loop.
Gold labels (Opus-authored) live next to this file at prompts/gold/lucanaude/*.json
so you can score Haiku vs gold with score_haiku_vs_gold.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    sys.exit("Missing dep: pip install pypdf")


GROUPS = {"CIPC","SHARE_CERTIFICATE","COMPANY_RESOLUTION","SARS","BANKING","FICA","HOA","TRANSFER_DEED","UNKNOWN"}


def classify_quality(p: Path) -> dict:
    info = {"pages": None, "chars_per_page": 0, "quality_tier": "?", "structure_tier": "?", "text": ""}
    ext = p.suffix.lower()
    if ext == ".pdf":
        try:
            r = PdfReader(str(p))
            pages = len(r.pages)
            info["pages"] = pages
            parts = []
            for i in range(min(pages, 8)):  # up to 8 pages sampled
                try:
                    parts.append(r.pages[i].extract_text() or "")
                except Exception:
                    pass
            text = "\n".join(parts)
            info["text"] = text[:15000]
            sampled = max(len(parts), 1)
            d = len(text) / sampled
            info["chars_per_page"] = int(d)
            if d > 500:
                info["quality_tier"] = "A_digital"
                info["structure_tier"] = "tagged" if d > 1500 else "semi_tagged"
            elif d > 50:
                info["quality_tier"] = "B_ocr_clean"; info["structure_tier"] = "flat"
            elif d > 0:
                info["quality_tier"] = "C_ocr_noisy"; info["structure_tier"] = "flat"
            else:
                info["quality_tier"] = "D_image_only"; info["structure_tier"] = "none"
        except Exception as e:
            info["quality_tier"] = "E_broken"; info["error"] = str(e)[:120]
    elif ext in (".docx", ".doc"):
        try:
            import docx
            doc = docx.Document(str(p))
            text = "\n".join(par.text for par in doc.paragraphs if par.text.strip())
            info["text"] = text[:15000]
            info["quality_tier"] = "A_digital"; info["structure_tier"] = "tagged"
        except Exception as e:
            info["quality_tier"] = "E_broken"; info["error"] = str(e)[:120]
    elif ext in (".xlsx", ".xls", ".csv"):
        info["quality_tier"] = "A_digital"; info["structure_tier"] = "tagged"
    return info


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_unique_files(folder: Path) -> list[tuple[Path, str, dict]]:
    """Dedupe by SHA, keep shortest path as canonical."""
    seen: dict[str, tuple[Path, dict]] = {}
    for p in folder.rglob("*"):
        if not p.is_file() or p.name.startswith("."):
            continue
        sha = sha256_of(p)
        q = classify_quality(p)
        if sha not in seen or len(str(p)) < len(str(seen[sha][0])):
            seen[sha] = (p, q)
    return [(p, sha, q) for sha, (p, q) in seen.items()]


def run_haiku(client, model: str, system_prompt: str, payload: dict) -> tuple[dict | None, int, int, float]:
    """One Haiku call. Returns (parsed_json, in_tokens, out_tokens, seconds)."""
    t0 = time.time()
    msg = client.messages.create(
        model=model,
        max_tokens=1500,
        system=system_prompt,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    dt = time.time() - t0
    body = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    # Haiku sometimes wraps in ``` — strip defensively
    if body.startswith("```"):
        body = body.split("```", 2)[1]
        if body.startswith("json"):
            body = body[4:]
        body = body.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        parsed = None
    return parsed, msg.usage.input_tokens, msg.usage.output_tokens, dt


def validate(rec: dict) -> list[str]:
    errs = []
    for k in ("sha256","document_group","document_type","primary_entity","confidence"):
        if k not in rec: errs.append(f"missing:{k}")
    if rec.get("document_group") not in GROUPS:
        errs.append(f"bad_group:{rec.get('document_group')}")
    pe = rec.get("primary_entity") or {}
    if not isinstance(pe, dict) or "kind" not in pe:
        errs.append("bad_primary_entity")
    c = rec.get("confidence")
    if not (isinstance(c, (int, float)) and 0.0 <= c <= 1.0):
        errs.append("bad_confidence")
    return errs


def price(model: str, in_tok: int, out_tok: int) -> float:
    # Rough board rates — update as needed. Haiku 4.5 pricing used here.
    rates = {
        "claude-haiku-4-5": (1.00, 5.00),  # $/MTok (in, out)
        "claude-sonnet-4-5": (3.00, 15.00),
    }
    rin, rout = rates.get(model, (1.0, 5.0))
    return (in_tok * rin + out_tok * rout) / 1_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", default="/tmp/lucanaude_haiku_index.jsonl")
    ap.add_argument("--model", default="claude-haiku-4-5")
    ap.add_argument("--dry-run", action="store_true", help="Classify only, no LLM call")
    args = ap.parse_args()

    folder = Path(args.folder)
    prompt_path = Path(args.prompt)
    system_prompt = prompt_path.read_text()

    print(f"→ Collecting + deduping files in {folder}")
    files = collect_unique_files(folder)
    print(f"  {len(files)} unique files")

    if args.dry_run:
        print("Dry run — writing quality-tier-only records")
        with open(args.out, "w") as out:
            for p, sha, q in files:
                rel = str(p.relative_to(folder))
                out.write(json.dumps({
                    "file_path": rel, "sha256": sha,
                    "quality_tier": q["quality_tier"],
                    "structure_tier": q["structure_tier"],
                    "pages": q.get("pages"),
                    "chars_per_page": q.get("chars_per_page"),
                }) + "\n")
        print(f"  wrote {args.out}"); return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set")
    try:
        import anthropic
    except ImportError:
        sys.exit("Missing dep: pip install anthropic")
    client = anthropic.Anthropic()

    schema_pass = schema_fail = 0
    total_in = total_out = 0
    t0 = time.time()
    out_f = open(args.out, "w")

    for i, (p, sha, q) in enumerate(files, 1):
        rel = str(p.relative_to(folder))
        payload = {
            "file_path": rel,
            "sha256": sha,
            "quality_tier": q["quality_tier"],
            "structure_tier": q["structure_tier"],
            "pages": q.get("pages"),
            "chars_per_page": q.get("chars_per_page"),
            "text": q.get("text", ""),
        }
        try:
            parsed, in_t, out_t, dt = run_haiku(client, args.model, system_prompt, payload)
            total_in += in_t; total_out += out_t
            if parsed is None:
                schema_fail += 1
                rec = {"sha256": sha, "file_path": rel, "_error": "invalid_json"}
            else:
                parsed.setdefault("sha256", sha)
                parsed["_file_path"] = rel
                parsed["_quality_tier"] = q["quality_tier"]
                errs = validate(parsed)
                if errs:
                    schema_fail += 1; parsed["_schema_errors"] = errs
                else:
                    schema_pass += 1
                rec = parsed
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_f.flush()
            print(f"  [{i:>3}/{len(files)}] {rec.get('document_group','?'):<18} {rec.get('document_type','?'):<38} "
                  f"conf={rec.get('confidence','-')!s:<5}  tok={in_t+out_t:>6}  {dt:.1f}s  {rel[:70]}")
        except Exception as e:
            schema_fail += 1
            out_f.write(json.dumps({"sha256": sha, "file_path": rel, "_error": str(e)[:200]}) + "\n")
            print(f"  [{i:>3}/{len(files)}] ERROR {rel}: {e}")

    out_f.close()
    elapsed = time.time() - t0
    cost = price(args.model, total_in, total_out)
    report = {
        "model": args.model,
        "files": len(files),
        "schema_pass": schema_pass,
        "schema_fail": schema_fail,
        "schema_pass_rate": round(schema_pass / len(files), 3) if files else 0,
        "input_tokens": total_in,
        "output_tokens": total_out,
        "total_tokens": total_in + total_out,
        "cost_usd": round(cost, 4),
        "elapsed_seconds": round(elapsed, 1),
        "seconds_per_file": round(elapsed / len(files), 2) if files else 0,
    }
    Path("/tmp/lucanaude_haiku_report.json").write_text(json.dumps(report, indent=2))
    print("\n=== REPORT ===")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
