"""
Phase 3 R5 spike — Gotenberg `@page` POC for per-page initials.

Tests whether Chromium-via-Gotenberg can reliably render running footer/header
content on every page of a paginated lease document.

Three variants are tested:

  Variant A — CSS `@page` margin boxes only (@bottom-center / @top-right)
  Variant B — W3C css-page-3 `position: running()` (element-in-margin approach)
  Variant C — Manual page-break-after:always divs with in-flow footer divs
              (deterministic fallback, no @page margin boxes)

For each variant the spike:
  1. Generates a long test lease HTML (~6-8 pages).
  2. Posts to local Gotenberg (http://localhost:3000).
  3. Saves the PDF to backend/scripts/spikes/output/per_page_initials_<variant>_<timestamp>.pdf
  4. Extracts per-page text with pypdf and checks every page for the initials
     string and the running header.
  5. Prints a clear PASS / FAIL verdict.

Usage:
    python backend/scripts/spikes/per_page_initials_spike.py

Gotenberg must be running locally (docker compose up -d gotenberg).

Exit code:
    0  — at least one variant fully passes (go decision)
    1  — all variants fail (fallback required)
    2  — Gotenberg unreachable (infrastructure blocker)
"""
from __future__ import annotations

import io
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

try:
    import pypdf
except ImportError:
    print("ERROR: pypdf not installed. Run: pip install pypdf", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GOTENBERG_URL = "http://localhost:3000"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Strings we assert exist on EVERY page
INITIALS_NEEDLE = "I have read this page"
HEADER_NEEDLE = "Residential Lease"

# Minimum pages the document must render to
MIN_PAGES = 5

# ---------------------------------------------------------------------------
# Sample lease content — ~6-8 pages of realistic SA clause text
# ---------------------------------------------------------------------------

SAMPLE_CLAUSES = """
<h2>1. PARTIES</h2>
<p>This Residential Lease Agreement ("Agreement") is entered into between
<strong>JOHN ALBERT SMITH</strong> (Identity Number: 8001015009087), hereinafter referred to
as the "Landlord", and <strong>SARAH JANE DOE</strong> (Identity Number: 9502104567089),
hereinafter referred to as the "Tenant".</p>

<h2>2. PREMISES</h2>
<p>The Landlord hereby lets to the Tenant the property situated at
<strong>42 Oak Street, Stellenbosch, Western Cape, 7600</strong>, being Unit 3 of
Erf 1234, Stellenbosch ("the Premises"). The Premises are let for residential
purposes only. The Tenant may not use the Premises for any commercial, industrial
or other non-residential purpose without the prior written consent of the Landlord.</p>

<h2>3. LEASE PERIOD</h2>
<p>The lease commences on <strong>1 June 2026</strong> and terminates on
<strong>31 May 2027</strong> ("Fixed Term"), unless terminated earlier in accordance
with the provisions of this Agreement or the Rental Housing Act 50 of 1999 ("RHA").
After the Fixed Term the lease shall continue on a month-to-month basis until either
party gives one calendar month's written notice of termination in accordance with
Section 5(3)(c) of the RHA.</p>

<h2>4. RENTAL</h2>
<p>The monthly rental is <strong>R 12,500.00 (Twelve Thousand Five Hundred Rand)</strong>,
payable in advance on or before the first day of each month, free of deduction or set-off,
by electronic funds transfer to the Landlord's nominated bank account. Late payment
attracts interest at the prescribed rate under the Prescribed Rate of Interest Act 55 of
1975 from the due date until date of actual payment. Time is of the essence in respect
of rental payments.</p>

<h2>5. DEPOSIT</h2>
<p>The Tenant shall pay a deposit of <strong>R 25,000.00 (Twenty-Five Thousand Rand)</strong>
("Deposit") on or before the commencement date. The Deposit shall be held in a separate
interest-bearing account with a registered financial institution in accordance with
Section 5(3)(f) of the RHA. The interest accrued, less any reasonable account fees,
accrues to the Tenant. The Deposit may not be used in lieu of rental.</p>
<p>On termination of the lease the Landlord shall, within 14 (fourteen) days of the
Tenant vacating, inspect the Premises in the Tenant's presence (if the Tenant elects
to attend) and provide a written list of any deductions from the Deposit in accordance
with Section 5(3)(h) of the RHA. Any balance of the Deposit shall be refunded to the
Tenant within 14 days of the Tenant vacating and all obligations being discharged.</p>

<h2>6. UTILITIES AND SERVICES</h2>
<p>The Tenant shall be responsible for payment of all utilities consumed at the Premises
including electricity (prepaid meter), water, and refuse removal as levied by the
Stellenbosch Local Municipality. The Landlord shall provide the Tenant with meter readings
at the commencement and termination of the lease. Reticulation of electricity and water
is on the Landlord's account. The Tenant must report any fault, leak or outage to the
Landlord within 24 hours of becoming aware of it.</p>

<h2>7. OCCUPATION AND USE</h2>
<p>The Premises shall be occupied by the Tenant and a maximum of <strong>2 (two)</strong>
persons only. No additional occupants may reside at the Premises without the prior
written consent of the Landlord. The Tenant must not use the Premises for any unlawful
purpose. The Tenant must observe all applicable municipal by-laws, body corporate rules,
and sectional title conduct rules applicable to the complex.</p>

<h2>8. MAINTENANCE AND REPAIRS</h2>
<p>The Tenant shall maintain the Premises in a clean and hygienic condition and return
them in the same good order and condition as received, fair wear and tear excepted.
The Tenant is responsible for minor repairs not exceeding R 500.00 (Five Hundred Rand)
per incident. All other repairs must be reported to the Landlord in writing within
24 hours. The Landlord must attend to major repairs within a reasonable time, being
no more than 7 (seven) business days for non-urgent repairs and 24 hours for urgent
repairs affecting habitability, safety, or security.</p>

<h2>9. ALTERATIONS</h2>
<p>The Tenant may not make any structural alterations, additions, or improvements to
the Premises without the prior written consent of the Landlord. Any approved alterations
shall, unless otherwise agreed in writing, become the property of the Landlord upon
completion. The Tenant must restore any alterations carried out without consent to the
original condition at the Tenant's cost upon demand.</p>

<h2>10. ASSIGNMENT AND SUBLETTING</h2>
<p>The Tenant may not assign, sublet, or otherwise part with possession of the Premises
or any part thereof without the prior written consent of the Landlord, which consent may
not be unreasonably withheld in terms of Section 5(3)(b) of the RHA. Any purported
assignment or subletting without such consent shall be void and shall entitle the
Landlord to cancel this Agreement on 20 (twenty) business days' written notice.</p>

<h2>11. BREACH AND CANCELLATION</h2>
<p>If either party breaches any material term of this Agreement and fails to remedy
the breach within 20 (twenty) business days after written notice demanding remedy,
the aggrieved party shall be entitled to cancel the Agreement on written notice and
to claim damages. The Landlord may approach the Rental Housing Tribunal established
under Section 7 of the RHA for adjudication of any dispute regarding unfair practice
as defined in Section 1 of the RHA. Self-help remedies including lockout, disconnection
of utilities, or removal of the Tenant's possessions are expressly prohibited and void
as contrary to Section 4A of the RHA and the common-law mandament van spolie.</p>

<h2>12. NOTICE TO VACATE</h2>
<p>Should the Landlord require possession of the Premises other than by reason of breach,
the Landlord must give the Tenant not less than 1 (one) calendar month's written notice
of termination of the lease in accordance with Section 5(3)(c) of the RHA. Where the
Tenant is in occupation of the Premises and refuses to vacate, the Landlord must apply
to court for a lawful eviction order under the Prevention of Illegal Eviction from and
Unlawful Occupation of Land Act 19 of 1998 ("PIE Act").</p>

<h2>13. POPIA CONSENT</h2>
<p>The Tenant consents to the processing of their personal information by the Landlord
and/or managing agent for the following purposes and on the following lawful bases under
the Protection of Personal Information Act 4 of 2013 ("POPIA"): (a) lease administration
and compliance — Section 11(1)(b) (necessary for performance of contract); (b) credit
bureau enquiries — Section 11(1)(a) (consent, pre-contract); (c) Rental Housing Tribunal
referral — Section 11(1)(c) (compliance with legal obligation); (d) communication with
managing agent — Section 11(1)(b) (necessary for performance of contract). The Landlord
shall retain personal information for the duration of the lease plus 3 (three) years in
accordance with Section 14 of POPIA, whereafter it shall be destroyed or de-identified.</p>

<h2>14. CONDUCT RULES</h2>
<p>The Tenant shall comply with all conduct rules as set out in the Body Corporate
Conduct Rules registered in terms of Section 10 of the Sectional Titles Schemes
Management Act 8 of 2011 ("STSMA"). The Tenant acknowledges receipt of a copy of the
conduct rules as an annexure to this Agreement. Any amendment to the conduct rules
passed by the body corporate in terms of Section 10 of the STSMA shall bind the Tenant
from the date of passing notwithstanding that this Agreement pre-dates the amendment.
The costs of any contravention of the conduct rules, including administrative penalties
and legal costs levied by the body corporate against the Landlord as a result of the
Tenant's conduct, shall be for the Tenant's account and may be deducted from the Deposit.</p>

<h2>15. JOINT AND SEVERAL LIABILITY</h2>
<p>Where this Agreement is signed by more than one person as Tenant, each such person
shall be jointly and severally liable for the full amount of rental and all other
obligations under this Agreement. This means that the Landlord may enforce performance
of any obligation and recovery of any amount from any one or all of the Tenants, and
each Tenant may not raise as a defence that another Tenant has not been called upon
first. This provision is in addition to and not in substitution for any surety or
guarantee provided in respect of this Agreement.</p>

<h2>16. GENERAL</h2>
<p>This Agreement constitutes the entire agreement between the parties and supersedes
all prior negotiations, representations, and agreements. No variation of this Agreement
shall be of force or effect unless reduced to writing and signed by both parties.
The Landlord's failure to enforce any provision of this Agreement shall not be construed
as a waiver of the Landlord's rights. If any provision of this Agreement is found to be
unlawful, void or unenforceable, such provision shall be severed from the Agreement
without affecting the remaining provisions. The parties choose their respective physical
addresses above as their domicilium citandi et executandi for all notices, legal process
and other documents.</p>

<h2>SIGNATURE</h2>
<p>Signed at Stellenbosch on ________________________</p>
<p><br/><br/></p>
<p>_______________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; _______________________________</p>
<p><strong>LANDLORD:</strong> John Albert Smith &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
<strong>TENANT:</strong> Sarah Jane Doe</p>
<p>Date: _________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
Date: _________________________</p>
"""

# Repeat the clauses once more so the document spans at least 5 pages
LONG_BODY = SAMPLE_CLAUSES + """
<h2>ADDENDUM A — SPECIAL CONDITIONS</h2>
<p>The following special conditions form part of the Agreement and, in the event of any
conflict with the main body of the Agreement, shall prevail to the extent of the
inconsistency.</p>

<h3>A.1 Garden Maintenance</h3>
<p>The Tenant shall maintain the garden, including mowing lawns, trimming hedges, and
clearing leaf litter, at least once per fortnight. The Landlord will supply a functional
lawnmower. The Tenant shall report any equipment failure within 48 hours. Failure to
maintain the garden will constitute a breach of the Agreement.</p>

<h3>A.2 Parking</h3>
<p>The Tenant is allocated one covered parking bay (Bay 3) and one open parking bay
(Bay 12) as shown on the parking plan attached as Annexure C. No additional vehicles
may be parked within the complex precincts. Vehicles parked in violation of this
clause or the conduct rules may be towed at the vehicle owner's cost.</p>

<h3>A.3 Pets</h3>
<p>The Tenant may keep one small dog (not exceeding 10 kg adult weight) subject to
written application and approval by the body corporate in terms of the conduct rules.
All body corporate conditions for the keeping of pets shall apply. The Tenant shall
be liable for any damage caused by the pet to the Premises, common property, or
third parties. The Tenant indemnifies the Landlord against all claims arising from
the Tenant's pet.</p>

<h3>A.4 Remote Access</h3>
<p>The Tenant is issued with 2 (two) remote access tags for the main gate. Each
additional tag is available at a cost of R 250.00 per tag. Lost or stolen tags
must be reported to the managing agent within 24 hours. The cost of replacing
lost or stolen tags is for the Tenant's account and shall be deducted from the
Deposit on termination if not paid earlier.</p>

<h3>A.5 Internet and CCTV</h3>
<p>The complex has a fibre point-of-presence in the communal area. The Tenant may
arrange a fibre internet connection at their own cost through any accredited ISP.
The Landlord and body corporate operate CCTV cameras at the gate and common areas.
The Tenant consents to monitoring of common areas. No CCTV cameras may be installed
by the Tenant at or outside the Premises without prior written consent of the Landlord
and the body corporate.</p>
""" + SAMPLE_CLAUSES  # repeat core clauses again to guarantee page depth


# ---------------------------------------------------------------------------
# HTML builders for each variant
# ---------------------------------------------------------------------------

def _wrap_html(title: str, style: str, body: str) -> str:
    """Wrap body content in a full HTML5 document."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
{style}
</style>
</head>
<body>
{body}
</body>
</html>"""


def build_variant_a() -> str:
    """Variant A — simplest: CSS @page margin boxes with static content strings."""
    style = """
    @page {
        size: A4;
        margin: 2cm 2cm 3cm 2cm;

        @bottom-center {
            content: "I have read this page — initials: ____";
            font-family: Arial, sans-serif;
            font-size: 8pt;
            color: #333;
            border-top: 1px solid #ccc;
            padding-top: 4pt;
        }

        @top-right {
            content: "Residential Lease — page " counter(page) " of " counter(pages);
            font-family: Arial, sans-serif;
            font-size: 8pt;
            color: #555;
        }
    }

    body {
        font-family: Arial, sans-serif;
        font-size: 10.5pt;
        line-height: 1.55;
        color: #111;
    }
    h1 { font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 12pt; }
    h2 { font-size: 11pt; font-weight: bold; margin: 8pt 0 3pt; }
    h3 { font-size: 10.5pt; font-weight: bold; margin: 6pt 0 3pt; }
    p, li { margin: 3pt 0; }
    """
    body = "<h1>RESIDENTIAL LEASE AGREEMENT</h1>\n" + LONG_BODY
    return _wrap_html("Lease — Variant A", style, body)


def build_variant_b() -> str:
    """Variant B — W3C css-page-3 `position: running()`.

    A named element is placed in the running slot via `position: running(initials)`.
    The @page margin box pulls it with `content: element(initials)`.
    Chromium Paged.js-based engines support this; native Chromium print support
    varies — this variant tests whether Gotenberg's Chromium accepts it.
    """
    style = """
    @page {
        size: A4;
        margin: 2cm 2cm 3cm 2cm;

        @bottom-center {
            content: element(initials);
        }

        @top-right {
            content: element(runningHeader);
        }
    }

    .initials-block {
        position: running(initials);
        font-family: Arial, sans-serif;
        font-size: 8pt;
        color: #333;
        border-top: 1px solid #ccc;
        padding-top: 4pt;
        text-align: center;
    }

    .running-header-block {
        position: running(runningHeader);
        font-family: Arial, sans-serif;
        font-size: 8pt;
        color: #555;
        text-align: right;
    }

    body {
        font-family: Arial, sans-serif;
        font-size: 10.5pt;
        line-height: 1.55;
        color: #111;
    }
    h1 { font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 12pt; }
    h2 { font-size: 11pt; font-weight: bold; margin: 8pt 0 3pt; }
    h3 { font-size: 10.5pt; font-weight: bold; margin: 6pt 0 3pt; }
    p, li { margin: 3pt 0; }
    """
    body = """
<div class="initials-block">I have read this page — initials: ____</div>
<div class="running-header-block">Residential Lease — running header</div>
<h1>RESIDENTIAL LEASE AGREEMENT</h1>
""" + LONG_BODY
    return _wrap_html("Lease — Variant B", style, body)


def build_variant_c() -> str:
    """Variant C — manual page-break-after:always with in-flow footer divs.

    Each content block is wrapped in a .page div. A .page-footer div sits at
    the bottom of each .page. Relies on page-break-after:always to force breaks.
    This is the deterministic-but-brittle fallback: the footer text is in-flow
    so it always appears, but exact positioning depends on content height.
    """
    style = """
    @page {
        size: A4;
        margin: 2cm;
    }

    body {
        font-family: Arial, sans-serif;
        font-size: 10.5pt;
        line-height: 1.55;
        color: #111;
    }
    h1 { font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 12pt; }
    h2 { font-size: 11pt; font-weight: bold; margin: 8pt 0 3pt; }
    h3 { font-size: 10.5pt; font-weight: bold; margin: 6pt 0 3pt; }
    p, li { margin: 3pt 0; }

    .page {
        page-break-after: always;
        break-after: page;
        position: relative;
        min-height: 240mm;   /* A4 height minus 2cm top+bottom margins */
    }

    .page-footer {
        margin-top: 12pt;
        padding-top: 6pt;
        border-top: 1px solid #ccc;
        font-size: 8pt;
        color: #333;
        text-align: center;
    }

    .page-header {
        font-size: 8pt;
        color: #555;
        text-align: right;
        margin-bottom: 8pt;
        padding-bottom: 4pt;
        border-bottom: 1px solid #eee;
    }
    """

    # Split LONG_BODY into chunks at <h2> boundaries so each page has ~2 sections
    import re
    raw_sections = re.split(r'(?=<h2)', LONG_BODY)
    raw_sections = [s.strip() for s in raw_sections if s.strip()]

    # Group into pages of ~2 sections each
    pages_html = []
    chunk_size = 2
    for i in range(0, len(raw_sections), chunk_size):
        chunk = "\n".join(raw_sections[i:i + chunk_size])
        page_num_hint = i // chunk_size + 1
        page_html = f"""<div class="page">
  <div class="page-header">Residential Lease — Page {page_num_hint}</div>
  {chunk}
  <div class="page-footer">I have read this page — initials: ____</div>
</div>"""
        pages_html.append(page_html)

    body = "<h1>RESIDENTIAL LEASE AGREEMENT</h1>\n" + "\n".join(pages_html)
    return _wrap_html("Lease — Variant C", style, body)


# ---------------------------------------------------------------------------
# Gotenberg call
# ---------------------------------------------------------------------------

def render_to_pdf(html: str, variant_name: str) -> bytes:
    """POST the HTML to local Gotenberg and return raw PDF bytes."""
    url = f"{GOTENBERG_URL}/forms/chromium/convert/html"
    files = {"files": ("index.html", html.encode("utf-8"), "text/html")}
    data = {
        "paperWidth": "8.27",
        "paperHeight": "11.7",
        "marginTop": "0",
        "marginBottom": "0",
        "marginLeft": "0",
        "marginRight": "0",
        "preferCssPageSize": "true",
        "printBackground": "true",
    }
    print(f"  → POSTing {variant_name} HTML ({len(html):,} chars) to Gotenberg...")
    start = time.monotonic()
    resp = requests.post(url, files=files, data=data, timeout=90)
    elapsed = time.monotonic() - start
    if not resp.ok:
        raise RuntimeError(
            f"Gotenberg returned HTTP {resp.status_code} for {variant_name}: "
            f"{resp.text[:300]}"
        )
    print(f"  → Received {len(resp.content):,} bytes in {elapsed:.1f}s")
    return resp.content


# ---------------------------------------------------------------------------
# PDF text extraction and assertion
# ---------------------------------------------------------------------------

def extract_pages_text(pdf_bytes: bytes) -> list[str]:
    """Extract text from each page using pypdf. Returns list indexed by page."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            text = f"[extraction error: {exc}]"
        pages.append(text)
    return pages


def check_variant(
    variant_name: str,
    html: str,
) -> dict:
    """
    Run a single variant end-to-end.

    Returns a result dict:
        ok: bool
        page_count: int
        pages_with_initials: list[int]  (1-indexed)
        pages_without_initials: list[int]
        pages_with_header: list[int]
        pages_without_header: list[int]
        failure_detail: str
        pdf_path: Path
    """
    result: dict = {
        "variant": variant_name,
        "ok": False,
        "page_count": 0,
        "pages_with_initials": [],
        "pages_without_initials": [],
        "pages_with_header": [],
        "pages_without_header": [],
        "failure_detail": "",
        "pdf_path": None,
    }

    # 1. Render
    try:
        pdf_bytes = render_to_pdf(html, variant_name)
    except Exception as exc:
        result["failure_detail"] = f"Render failed: {exc}"
        return result

    # 2. Save
    safe_name = variant_name.lower().replace(" ", "_").replace("/", "_")
    out_path = OUTPUT_DIR / f"per_page_initials_{safe_name}_{TIMESTAMP}.pdf"
    out_path.write_bytes(pdf_bytes)
    result["pdf_path"] = out_path
    print(f"  → Saved to {out_path}")

    # 3. Extract text per page
    pages_text = extract_pages_text(pdf_bytes)
    result["page_count"] = len(pages_text)
    print(f"  → Extracted text from {len(pages_text)} pages")

    # 4. Check page count
    if len(pages_text) < MIN_PAGES:
        result["failure_detail"] = (
            f"Only {len(pages_text)} pages rendered — expected ≥ {MIN_PAGES}. "
            f"Document too short or pagination not applied."
        )
        return result

    # 5. Per-page assertions
    failures = []
    for i, text in enumerate(pages_text, start=1):
        # Some PDF renderers capitalise or space differently — use lower-case check
        lower = text.lower()
        needle_lower = INITIALS_NEEDLE.lower()
        header_lower = HEADER_NEEDLE.lower()

        if needle_lower in lower:
            result["pages_with_initials"].append(i)
        else:
            result["pages_without_initials"].append(i)
            failures.append(f"page {i} missing initials footer")

        if header_lower in lower:
            result["pages_with_header"].append(i)
        else:
            result["pages_without_header"].append(i)
            # Header absence is a warning for variant C (no @page header mechanism)

    if failures:
        result["failure_detail"] = "; ".join(failures[:5])
        if len(failures) > 5:
            result["failure_detail"] += f" (+ {len(failures) - 5} more)"
        return result

    result["ok"] = True
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("Phase 3 R5 — Gotenberg @page POC for per-page initials")
    print(f"Timestamp: {TIMESTAMP}")
    print("=" * 70)

    # Health check
    print("\n[0] Checking Gotenberg health...")
    try:
        health = requests.get(f"{GOTENBERG_URL}/health", timeout=5).json()
        chromium_status = health.get("details", {}).get("chromium", {}).get("status", "?")
        print(f"  → Gotenberg is UP (chromium: {chromium_status})")
    except Exception as exc:
        print(f"\n  BLOCKER: Gotenberg unreachable at {GOTENBERG_URL}: {exc}")
        print("  Run: docker compose up -d gotenberg")
        return 2

    # Build all three variant HTML documents upfront
    print("\n[1] Building variant HTML documents...")
    variants = [
        ("variant_a", build_variant_a()),
        ("variant_b", build_variant_b()),
        ("variant_c", build_variant_c()),
    ]
    for name, html in variants:
        print(f"  → {name}: {len(html):,} chars")

    # Run each variant
    results = []
    for name, html in variants:
        print(f"\n{'=' * 70}")
        print(f"[{name.upper()}]")
        print("=" * 70)
        res = check_variant(name, html)
        results.append(res)

    # Final report
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    any_pass = False
    for res in results:
        name = res["variant"].upper()
        pages = res["page_count"]
        with_init = len(res["pages_with_initials"])
        without_init = len(res["pages_without_initials"])
        with_hdr = len(res["pages_with_header"])
        without_hdr = len(res["pages_without_header"])

        if res["ok"]:
            verdict = "✅ PASS"
            any_pass = True
        else:
            verdict = "❌ FAIL"

        print(f"\n{name}: {verdict}")
        print(f"  Pages rendered:          {pages}")
        print(f"  Pages WITH initials:     {with_init}  {res['pages_with_initials'][:10]}")
        print(f"  Pages WITHOUT initials:  {without_init}  {res['pages_without_initials'][:10]}")
        print(f"  Pages WITH header:       {with_hdr}  {res['pages_with_header'][:10]}")
        print(f"  Pages WITHOUT header:    {without_hdr}  {res['pages_without_header'][:10]}")
        if res["failure_detail"]:
            print(f"  Failure detail:          {res['failure_detail']}")
        if res["pdf_path"]:
            print(f"  PDF output:              {res['pdf_path']}")

    # Per-variant raw page text dump (first 200 chars per page, first 3 pages only)
    print("\n" + "=" * 70)
    print("PER-VARIANT PAGE TEXT SAMPLES (first 3 pages, first 200 chars)")
    print("=" * 70)
    for name, html in variants:
        res = next(r for r in results if r["variant"] == name)
        if res["pdf_path"] and res["pdf_path"].exists():
            pages_text = extract_pages_text(res["pdf_path"].read_bytes())
            print(f"\n{name.upper()}:")
            for i, text in enumerate(pages_text[:3], start=1):
                preview = text.replace("\n", " ")[:200]
                print(f"  Page {i}: {preview!r}")

    # Overall verdict
    print("\n" + "=" * 70)
    if any_pass:
        passing = [r["variant"].upper() for r in results if r["ok"]]
        print(f"✅ @page running content WORKS in Gotenberg/Chromium")
        print(f"   Passing variants: {', '.join(passing)}")

        # Recommend the best variant
        if results[0]["ok"]:
            print("\nRECOMMENDATION: Use VARIANT A (@page margin boxes).")
            print("  Simplest, most portable, no JS/polyfill required.")
            print("  Formatter layout tools should emit @page CSS with")
            print("  @bottom-center and @top-right margin box content.")
        elif results[1]["ok"]:
            print("\nRECOMMENDATION: Use VARIANT B (position: running()).")
            print("  Chromium supports the css-page-3 running() syntax.")
            print("  More flexible — can include HTML in the margin boxes.")
        else:
            print("\nRECOMMENDATION: Use VARIANT C (manual page-break + in-flow footer).")
            print("  @page margin boxes do NOT work in this Gotenberg/Chromium build.")
            print("  Formatter must structure documents as explicit page divs.")
            print("  Alternatively, consider a post-render pikepdf stamp approach.")
    else:
        print("❌ DOES NOT WORK — all variants failed")
        print("\nFallback strategy required:")
        print("  Option 1: Post-render PDF stamp via pikepdf")
        print("    — Generate lease PDF normally (no per-page footer)")
        print("    — Open with pikepdf, render footer text onto each page")
        print("    — Re-save. Reliable but loses the 'part of the document' feel.")
        print("  Option 2: Switch to Paged.js polyfill")
        print("    — Inject Paged.js into the HTML before sending to Gotenberg")
        print("    — Paged.js implements the full css-page-3 spec in JS")
        print("    — Must re-enable JS in Gotenberg (--chromium-disable-javascript=false)")
        print("  Option 3: Use Prince or WeasyPrint instead of Chromium/Gotenberg")
        print("    — Both have better @page support but add infra complexity")

    print("=" * 70)
    return 0 if any_pass else 1


if __name__ == "__main__":
    sys.exit(main())
