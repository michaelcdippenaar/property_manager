"""
THE VOLT — Layer 0: filename signal extractor.

Cheapest possible classification layer: PURE STRING PARSING of the path
itself. Zero file I/O. Zero LLM tokens. Runs before L1 (entity table)
and seeds it with provisional Claims that deeper layers confirm or
overturn.

Why bother — examples from the actual corpus:

  G_du_Preez_ID_card_-_certified_-_23.03.2026.pdf
    → person="G du Preez", doc_type=SA_ID_CARD, certified=True,
      certification_date=2026-03-23

  Certified_ID_MC_Dippenaar_Jnr.pdf
    → person="MC Dippenaar", suffix="Jnr",
      doc_type=SA_ID_CARD, certified=True

  Bevestiging van adres, Michaelis christoffel dippenaar.pdf
    → person="Michaelis Christoffel Dippenaar",
      doc_type=PROOF_OF_ADDRESS, language=af

  MC Dippenaar Snr Mariage Certificate.pdf  ← (typo OK)
    → person="MC Dippenaar", suffix="Snr",
      doc_type=MARRIAGE_CERTIFICATE

  04_Mandate_Klikk_GZsO34V.pdf
    → doc_type=MANDATE, counterparty="Klikk",
      django_uniquifier="GZsO34V" (stripped for dedup)

  10944640-20260316-51439_1.pdf
    → ref_numbers=[10944640, 51439], date=2026-03-16, page_no=1

The signals are emitted as Claims with `citation.field_name="<filename>"`
and a low confidence (0.5 default) — Layer 2+ will either CONFIRM or
overturn them. But for empty silos, even a provisional doc-type tag
saves a Sonnet round-trip.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Doc-type lexicon (English + Afrikaans, regex per token)
# ---------------------------------------------------------------------------
#
# Order matters: more-specific patterns first. The matcher walks top to
# bottom and short-circuits on the first hit, so e.g. "MARRIAGE CERT" must
# come before bare "CERT".
#
# Each entry: (compiled regex, doc_type, base_confidence, language_hint)

DOC_TYPE_PATTERNS: list[tuple[re.Pattern, str, float, Optional[str]]] = [
    # -------- SA-specific identity & vital records --------
    (re.compile(r"\bbevestiging\s+van\s+adres\b", re.I), "PROOF_OF_ADDRESS", 0.85, "af"),
    (re.compile(r"\bproof\s+of\s+address\b", re.I), "PROOF_OF_ADDRESS", 0.85, "en"),
    (re.compile(r"\bid\s*card\b", re.I), "SA_ID_CARD", 0.75, "en"),
    (re.compile(r"\bid\s*copy\b", re.I), "SA_ID_CARD", 0.7, "en"),
    (re.compile(r"\b(certified[_\s-]+)?id\b(?!\w)", re.I), "SA_ID_CARD", 0.6, "en"),
    (re.compile(r"\bsmart\s*id\b", re.I), "SA_SMART_ID_CARD", 0.85, "en"),
    (re.compile(r"\bgreen\s*(book|id)\b", re.I), "SA_GREEN_ID_BOOK", 0.85, "en"),
    # Afrikaans: "ID-kaart" / "kaart" used for ID card
    (re.compile(r"\bid[\s_-]*kaart\b|(?<=[\s_])kaart\b", re.I), "SA_ID_CARD", 0.7, "af"),
    (re.compile(r"\bpassport\b", re.I), "PASSPORT", 0.85, "en"),
    (re.compile(r"\bpaspoort\b", re.I), "PASSPORT", 0.85, "af"),
    (re.compile(r"\bdriver'?s?\s*licen[cs]e\b|\brijbewijs\b|\brybewys\b", re.I),
     "DRIVERS_LICENCE", 0.85, None),

    # -------- Vital records --------
    # "marriage" / "mariage" / "marage" — typos are common
    (re.compile(r"\bma?rr?i?age\s+cert(ificate)?\b", re.I), "MARRIAGE_CERTIFICATE", 0.85, "en"),
    (re.compile(r"\bhuweliks?ert(ifikaat)?\b", re.I), "MARRIAGE_CERTIFICATE", 0.85, "af"),
    (re.compile(r"\bbirth\s+cert(ificate)?\b", re.I), "BIRTH_CERTIFICATE", 0.9, "en"),
    (re.compile(r"\bgeboorte[\s_-]*sert(ifikaat)?\b", re.I), "BIRTH_CERTIFICATE", 0.9, "af"),
    (re.compile(r"\bdeath\s+cert(ificate)?\b", re.I), "DEATH_CERTIFICATE", 0.9, "en"),
    (re.compile(r"\bdivorce\s+(decree|order|cert)", re.I), "DIVORCE_DECREE", 0.85, "en"),
    (re.compile(r"\bantenuptial|\bhuweliks?\s*voor", re.I), "ANTE_NUPTIAL_CONTRACT", 0.8, None),
    (re.compile(r"\bmarital\s+status\s+declaration\b", re.I), "MARITAL_STATUS_DECL", 0.9, "en"),

    # -------- Estates / wills --------
    # Afrikaans plural "testamente" + English "testament"
    (re.compile(r"\btestament[ae]?\b", re.I), "WILL_TESTAMENT", 0.8, None),
    (re.compile(r"\blast\s+will\b|\bwill\s+and\s+testament\b", re.I), "WILL_TESTAMENT", 0.9, "en"),
    (re.compile(r"\btestament[ae]r[ae]?\s+trust\b|\btestamentary\s+trust\b", re.I),
     "TESTAMENTARY_TRUST_DOC", 0.9, None),
    # SA Antenuptial Contract abbreviation HVK / HVH
    (re.compile(r"\bhvk\b|\bhuwelik(s|se)?\s+voor", re.I), "ANTE_NUPTIAL_CONTRACT", 0.85, "af"),
    (re.compile(r"\b(letter|certificate)\s+of\s+executorship\b", re.I), "EXECUTORSHIP_LETTER", 0.9, "en"),
    (re.compile(r"\bmaster'?s?[_\s]+cert(ificate)?\b", re.I), "MASTERS_CERTIFICATE", 0.9, "en"),
    (re.compile(r"\bcertificate\s+issued\s+by\s+the\s+commissioner\b", re.I),
     "COMMISSIONER_CERTIFICATE", 0.95, "en"),

    # -------- Court / consents / resolutions --------
    (re.compile(r"\bcourt\s+order\b", re.I), "COURT_ORDER", 0.9, "en"),
    (re.compile(r"\bhof\s*bevel\b", re.I), "COURT_ORDER", 0.9, "af"),
    (re.compile(r"\bconsent\b", re.I), "CONSENT_LETTER", 0.7, "en"),
    (re.compile(r"\btoestemming\b", re.I), "CONSENT_LETTER", 0.7, "af"),
    (re.compile(r"\bresolution\b", re.I), "RESOLUTION", 0.75, "en"),
    (re.compile(r"\bbesluit\b", re.I), "RESOLUTION", 0.7, "af"),
    (re.compile(r"\bpower\s+of\s+attorney\b|\bvolmag\b", re.I), "POWER_OF_ATTORNEY", 0.9, None),
    (re.compile(r"\bspecial\s+power\s+of\s+attorney\b|\bspesiale\s+volmag\b", re.I),
     "SPECIAL_POWER_OF_ATTORNEY", 0.95, None),

    # -------- CIPC company forms --------
    (re.compile(r"\bcor\s*14[\._\s-]*3\b", re.I), "COR14_3", 0.95, "en"),
    (re.compile(r"\bcor\s*14[\._\s-]*1a?\b", re.I), "COR14_1A", 0.95, "en"),
    (re.compile(r"\bcor\s*14[\._\s-]*1\b", re.I), "COR14_1", 0.95, "en"),
    (re.compile(r"\bcor\s*15[\._\s-]*1[a-z]?\b", re.I), "COR15_1", 0.9, "en"),
    (re.compile(r"\bcor\s*21[\._\s-]*1\b", re.I), "COR21_1", 0.95, "en"),
    (re.compile(r"\bcor\s*39\b", re.I), "COR39", 0.95, "en"),
    (re.compile(r"\bmoi\b", re.I), "MOI", 0.85, "en"),
    (re.compile(r"\bmemorandum\s+of\s+incorporation\b", re.I), "MOI", 0.95, "en"),
    (re.compile(r"\bbeneficial\s+owner(ship)?\s+register\b", re.I),
     "BENEFICIAL_OWNERSHIP_REGISTER", 0.95, "en"),
    (re.compile(r"\bsecurities\s+register\b", re.I), "SECURITIES_REGISTER", 0.95, "en"),
    (re.compile(r"\bshare\s+cert(ificate)?\b", re.I), "SHARE_CERTIFICATE", 0.9, "en"),
    (re.compile(r"\bdisclosure\s+structure\b", re.I), "DISCLOSURE_STRUCTURE", 0.9, "en"),
    # Afrikaans CIPC pack: "Registrasie dokumentasie"
    (re.compile(r"\bregistrasie\s+dokumentasie\b", re.I), "CIPC_REGISTRATION_PACK", 0.9, "af"),
    (re.compile(r"\bregistration\s+pack\b|\bregistration\s+documents?\b", re.I),
     "CIPC_REGISTRATION_PACK", 0.85, "en"),
    # Master's of the High Court forms (estates)
    (re.compile(r"\bj\s*246\b", re.I), "MASTER_FORM_J246", 0.95, None),
    (re.compile(r"\bj\s*155\b", re.I), "MASTER_FORM_J155", 0.95, None),
    (re.compile(r"\bj\s*295\b", re.I), "MASTER_FORM_J295", 0.95, None),
    # Affidavits
    (re.compile(r"\bfounding\s+affidavit\b", re.I), "FOUNDING_AFFIDAVIT", 0.95, "en"),
    (re.compile(r"\baffidavit\b|\bbeëdigde\s+verklaring\b", re.I), "AFFIDAVIT", 0.85, None),

    # -------- SARS / banking / FICA --------
    (re.compile(r"\b(sars|tax)\s+(clearance|cert|nor)\b|\bnotice\s+of\s+registration\b", re.I),
     "SARS_NOTICE_OF_REGISTRATION", 0.9, "en"),
    (re.compile(r"\bvat\s+registration\b", re.I), "SARS_VAT_REGISTRATION", 0.95, "en"),
    (re.compile(r"\bbank\s+(confirmation|letter|stamp)\b", re.I), "BANK_CONFIRMATION", 0.9, "en"),
    (re.compile(r"\bbank\s+statement\b|\bbankstaat\b", re.I), "BANK_STATEMENT", 0.9, None),
    (re.compile(r"\b(facility|fasiliteit)\s+letter\b|\bfacility\s+letter\b", re.I),
     "BANK_FACILITY_LETTER", 0.9, None),
    (re.compile(r"\breference[_\s]+letter[s]?\b|\bpba\b", re.I), "BANK_REFERENCE_LETTER", 0.85, "en"),
    (re.compile(r"\bfica\b", re.I), "FICA_DOCUMENT", 0.7, None),
    (re.compile(r"\bpopi(?:a)?\b|\bconsent.*processing\b", re.I), "POPI_CONSENT", 0.8, None),

    # -------- Mandates / leases / property --------
    (re.compile(r"\bmandate\b", re.I), "MANDATE", 0.85, "en"),
    (re.compile(r"\bopdrag\b", re.I), "MANDATE", 0.7, "af"),
    (re.compile(r"\b(rental|lease)\s+(agreement|procurement)\b", re.I), "LEASE", 0.9, "en"),
    (re.compile(r"\bhuur(kontrak|ooreenkoms)\b", re.I), "LEASE", 0.9, "af"),
    (re.compile(r"\btitle\s+deed\b|\btitelakte\b", re.I), "TITLE_DEED", 0.95, None),
    (re.compile(r"\bbond\b|\bverband\b", re.I), "BOND", 0.7, None),
    (re.compile(r"\belectrical\s+compliance\b|\bcoc\b", re.I), "ELECTRICAL_COC", 0.9, "en"),
    (re.compile(r"\bclearance\s+cert(ificate)?\b|\bvryf?stelling", re.I),
     "MUNICIPAL_CLEARANCE", 0.9, None),

    # -------- MFP scanner output (Sharp/Konica/Ricoh/Canon fingerprints) --
    (re.compile(r"^skm[_\s-]*c\d", re.I), "SCAN_UNCATEGORISED", 0.4, None),
    (re.compile(r"\bscan[_\s-]*itec\d", re.I), "SCAN_UNCATEGORISED", 0.4, None),
    (re.compile(r"^img[_\s-]?\d{4,}", re.I), "SCAN_UNCATEGORISED", 0.4, None),
    (re.compile(r"^cce\d{6,}", re.I), "SCAN_UNCATEGORISED", 0.4, None),
    # CIPC submission receipts: <8-9 digits>-<YYYYMMDD>-<5 digits>[_<page>]
    (re.compile(r"^\d{7,10}[-_]20\d{6}[-_]\d{4,6}\b", re.I),
     "CIPC_SUBMISSION_RECEIPT", 0.85, None),

    # -------- Catch-all for invoices etc. (low confidence) --------
    (re.compile(r"\binvoice\b|\bfaktuur\b", re.I), "INVOICE", 0.85, None),
    (re.compile(r"\bquote\b|\bkwotasie\b|\bqte\d+", re.I), "QUOTE", 0.8, None),
    (re.compile(r"\bledger\b|\bgrootboek\b", re.I), "LEDGER", 0.9, None),
    (re.compile(r"\breceipt\b|\bkwitansie\b", re.I), "RECEIPT", 0.9, None),
]


# ---------------------------------------------------------------------------
# Person tokens
# ---------------------------------------------------------------------------
#
# Filenames hide person identity in many shapes:
#   • initials + surname:  "MC Dippenaar", "G du Preez", "J Smit Dippenaar"
#   • surname-comma-init:  "Dippenaar, MC", "Dippenaar, MC (jnr)"
#   • full name:           "Michaelis christoffel dippenaar"
#   • Snr / Jnr / Sr / Jr disambiguator
#
# We capture (surname, initials_or_first, suffix) tuples with confidence.

_SUFFIX_RX = re.compile(r"\b(snr|sr|jnr|jr|junior|senior)\b", re.I)
_SUFFIX_PARENS_RX = re.compile(r"\(\s*(snr|sr|jnr|jr)\s*\)", re.I)

# "Dippenaar, MC" / "Dippenaar, MC (jnr)"
_SURNAME_COMMA_INIT_RX = re.compile(
    r"\b([A-Z][a-z]{1,30})\s*,\s*([A-Z]{1,4})(?:\s*\(\s*(snr|jnr|sr|jr)\s*\))?\b",
    re.I,
)

# "MC Dippenaar", "G du Preez", "J Smit Dippenaar" (initials then 1-2 surname tokens)
# We deliberately cap surname run at 2 capitalised tokens — over-greedy
# matches grabbed "DU PREEZ ID" and "DIPPENAAR SNR MARIAGE" in early tests.
_INIT_SURNAME_RX = re.compile(
    r"(?<![A-Za-z])([A-Z]{1,4})[_\s]+"
    r"((?:du|van|de|le|la|von|der|den|ter|el)[_\s]+)?"
    r"([A-Z][a-zA-Z'-]{1,30})"
    r"(?:[_\s]+([A-Z][a-zA-Z'-]{1,30}))?"
    r"(?![A-Za-z])"
)

# "Michaelis christoffel dippenaar" — three+ alpha tokens, often lowercased
_FULL_NAME_RX = re.compile(
    r"\b([A-Za-z][a-z]{2,20})\s+([a-z]{2,20})\s+([a-z]{2,20})\b"
)


@dataclass(frozen=True)
class PersonToken:
    surname: str
    initials_or_first: str
    suffix: Optional[str] = None
    full_name: Optional[str] = None
    confidence: float = 0.5

    def normalised(self) -> str:
        """Stable key for matching against entity table."""
        s = self.surname.upper().replace("_", " ")
        i = self.initials_or_first.upper().replace("_", " ")
        suf = f" {self.suffix.upper()}" if self.suffix else ""
        return f"{s}, {i}{suf}".strip()


# ---------------------------------------------------------------------------
# Date patterns
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    # 23.03.2026  /  14-11-2023  /  14_11_2023
    # Note: `\b` doesn't fire between `_` and a digit (both are word chars),
    # so we use explicit non-digit lookarounds.
    (re.compile(r"(?<!\d)(\d{1,2})[._\-/](\d{1,2})[._\-/](\d{4})(?!\d)"),
     lambda m: _safe_date(int(m.group(3)), int(m.group(2)), int(m.group(1)))),
    # 2018.08.07  /  2018-08-07  /  2018_08_07
    (re.compile(r"(?<!\d)(20\d{2})[._\-/](\d{1,2})[._\-/](\d{1,2})(?!\d)"),
     lambda m: _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    # 20260316  (compact YYYYMMDD)
    (re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
     lambda m: _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
    # "2017 10"  → year+month only
    (re.compile(r"(?<!\d)(20\d{2})\s+(0?[1-9]|1[0-2])(?!\d)"),
     lambda m: _safe_date(int(m.group(1)), int(m.group(2)), 1)),
]


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Django uniquifier strip + page suffix
# ---------------------------------------------------------------------------
#
# Django's FileSystemStorage appends a 7-char base62 token when it has to
# rename a colliding upload (e.g. `Certified_ID_MC_Dippenaar_Jnr_8vTnShL.pdf`).
# We strip it for dedup AND emit a `duplicate_upload` flag.

# Django's FileSystemStorage inserts a 7-char base62 token immediately
# before the extension (or before a single .<digits>. form-version segment).
# Real tokens are HIGH-ENTROPY (digits + mixed case interspersed) — we test
# both the position AND the entropy to avoid false-stripping the English
# word "Mandate" (also 7 chars, TitleCase-only) inside e.g.
# `04_Mandate_Klikk.pdf`.
_DJANGO_UNIQUIFIER_RX = re.compile(
    r"_([A-Za-z0-9]{7})(?=\.(?:\d+\.)?[A-Za-z]{2,4}$)"
)


def _looks_like_uniquifier(token: str) -> bool:
    """Reject TitleCase English words; require digit OR genuinely mixed case."""
    if not token or len(token) != 7:
        return False
    has_upper = any(c.isupper() for c in token)
    has_lower = any(c.islower() for c in token)
    has_digit = any(c.isdigit() for c in token)
    if has_digit:
        return True
    if has_upper and has_lower:
        # Pure TitleCase ("Mandate", "Letters") has uppercase only at idx 0
        upper_positions = [i for i, c in enumerate(token) if c.isupper()]
        return upper_positions != [0]
    return False
# Trailing _1 / _2 / (1) page numbers
_PAGE_SUFFIX_RX = re.compile(r"[_\s]*(?:_(\d{1,3})|\((\d{1,3})\))(?=\.[A-Za-z0-9]+$)")
# Numeric reference IDs (CIPC, SARS, municipal) — 6+ digits
_NUMERIC_REF_RX = re.compile(r"\b(\d{6,12})\b")


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class FilenameSignal:
    """Everything we can learn from a filename without opening the file."""
    raw_path: str
    stem_clean: str                       # filename stem after strip (no uniquifier, no page no)
    extension: str                        # ".pdf"
    folder_breadcrumbs: list[str] = field(default_factory=list)

    doc_type: Optional[str] = None
    doc_type_confidence: float = 0.0
    language_hint: Optional[str] = None   # "en" | "af" | None

    persons: list[PersonToken] = field(default_factory=list)
    dates: list[date] = field(default_factory=list)
    certified: bool = False
    certification_date: Optional[date] = None

    counterparty: Optional[str] = None    # e.g. "Klikk" in 04_Mandate_Klikk.pdf
    ref_numbers: list[str] = field(default_factory=list)
    page_number: Optional[int] = None

    duplicate_upload: bool = False        # Django uniquifier was present
    django_uniquifier: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def overall_confidence(self) -> float:
        """Cap on confidence we'd quote upstream — never above 0.7 for L0."""
        if not self.doc_type:
            return 0.0
        return min(0.7, self.doc_type_confidence)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_filename_signal(path: str | Path) -> FilenameSignal:
    """Parse a path → FilenameSignal. PURE FUNCTION, never opens the file."""
    p = Path(path)
    raw_stem = p.stem
    ext = p.suffix.lower()

    # ── 1. Strip Django uniquifier (entropy-checked to avoid mis-stripping
    #      real 7-char English words like "Mandate") ─────────────────────
    uniq_match = _DJANGO_UNIQUIFIER_RX.search(p.name)
    if uniq_match and _looks_like_uniquifier(uniq_match.group(1)):
        duplicate = True
        uniq = uniq_match.group(1)
        cleaned = _DJANGO_UNIQUIFIER_RX.sub("", p.name)
    else:
        duplicate = False
        uniq = None
        cleaned = p.name

    # ── 2. Strip page suffix ────────────────────────────────────────────
    page_match = _PAGE_SUFFIX_RX.search(cleaned)
    page_no = None
    if page_match:
        page_no = int(page_match.group(1) or page_match.group(2))
        cleaned = _PAGE_SUFFIX_RX.sub("", cleaned)
    stem_clean = Path(cleaned).stem

    sig = FilenameSignal(
        raw_path=str(p),
        stem_clean=stem_clean,
        extension=ext,
        folder_breadcrumbs=[part for part in p.parent.parts if part not in ("/", "")],
        duplicate_upload=duplicate,
        django_uniquifier=uniq,
        page_number=page_no,
    )

    # Two views of the stem:
    #   • `haystack` — separators flattened to spaces (used for word matching)
    #   • `stem_for_dates` — separators preserved (used for date regex)
    haystack = re.sub(r"[_\-.]+", " ", stem_clean)
    haystack = re.sub(r"\s+", " ", haystack).strip()
    stem_for_dates = stem_clean

    # ── 3. Doc-type ─────────────────────────────────────────────────────
    for rx, doc_type, conf, lang in DOC_TYPE_PATTERNS:
        if rx.search(haystack):
            sig.doc_type = doc_type
            sig.doc_type_confidence = conf
            if lang:
                sig.language_hint = lang
            break

    # ── 4. Certification flag ───────────────────────────────────────────
    if re.search(r"\bcertif(ied|icate)?\b", haystack, re.I) \
       or re.search(r"\bgesertifiseer", haystack, re.I):
        sig.certified = True

    # ── 5. Dates (extract on un-flattened stem; ".", "-", "_" are date seps) ─
    seen: set[str] = set()
    for rx, parser in _DATE_PATTERNS:
        for m in rx.finditer(stem_for_dates):
            d = parser(m)
            if d and d.isoformat() not in seen:
                seen.add(d.isoformat())
                sig.dates.append(d)
    # Heuristic: "certified" within ~16 chars of a date → certification_date.
    if sig.certified and sig.dates:
        for d in sig.dates:
            for fmt in ("%d.%m.%Y", "%Y.%m.%d", "%d-%m-%Y", "%Y-%m-%d",
                        "%d_%m_%Y", "%Y_%m_%d", "%Y%m%d"):
                token = d.strftime(fmt)
                if token in stem_for_dates and re.search(
                    rf"certified[^0-9]{{0,16}}{re.escape(token)}|"
                    rf"{re.escape(token)}[^0-9]{{0,16}}certified",
                    stem_for_dates, re.I,
                ):
                    sig.certification_date = d
                    break
            if sig.certification_date:
                break
        if not sig.certification_date:
            # Fallback: most recent date wins
            sig.certification_date = max(sig.dates)

    # ── 6. Person tokens ────────────────────────────────────────────────
    sig.persons = _extract_persons(haystack)

    # ── 7. Counterparty (e.g. "Mandate Klikk" → counterparty=Klikk) ────
    if sig.doc_type in {"MANDATE", "RESOLUTION", "INVOICE", "QUOTE", "LEASE",
                        "BENEFICIAL_OWNERSHIP_REGISTER", "SECURITIES_REGISTER"}:
        cp = _extract_counterparty(haystack, sig.doc_type)
        if cp:
            sig.counterparty = cp

    # ── 8. Reference numbers (CIPC / SARS / municipal) ──────────────────
    sig.ref_numbers = sorted(set(_NUMERIC_REF_RX.findall(haystack)))

    # ── 9. Folder-context boosts ────────────────────────────────────────
    breadcrumbs_lc = " / ".join(sig.folder_breadcrumbs).lower()
    if "registration" in breadcrumbs_lc and sig.doc_type in (None, "SA_ID_CARD"):
        sig.notes.append("folder=Registration → likely conveyancing-pack doc")
    if "rental agreements" in breadcrumbs_lc and not sig.doc_type:
        sig.doc_type = "LEASE"
        sig.doc_type_confidence = max(sig.doc_type_confidence, 0.6)
    if "fica" in breadcrumbs_lc and not sig.doc_type:
        sig.doc_type = "FICA_DOCUMENT"
        sig.doc_type_confidence = max(sig.doc_type_confidence, 0.6)

    return sig


# ---------------------------------------------------------------------------
# Helpers — person extraction
# ---------------------------------------------------------------------------

_NAME_NOISE_TOKENS = {
    "ID", "Card", "Certified", "Certificate", "Cert", "Mandate",
    "Marriage", "Mariage", "Bond", "Lease", "Bevestiging", "Adres",
    "Consent", "Court", "Order", "Will", "Testament", "Master", "Masters",
    "Statement", "Bank", "Invoice", "Faktuur", "Quote", "Receipt",
    "Resolution", "Besluit", "Registration", "Register", "Disclosure",
    "Securities", "Beneficial", "Ownership", "Mandate", "Klikk",
    "Power", "Attorney", "Special", "Consent", "Marital", "Status",
    "Declaration", "MOI", "CoR", "Scan", "Page", "Annexure", "Schedule",
}


def _looks_like_doc_word(tok: str) -> bool:
    return tok in _NAME_NOISE_TOKENS or tok.upper() in _NAME_NOISE_TOKENS


_PREFIX_NOISE_RX = re.compile(
    r"^(?:certified|copy|original|scan|scanned|page\s*\d+|\d{1,3}\s*[-_\s]*)+\s*",
    re.I,
)
_INFIX_DOC_TOKEN_RX = re.compile(
    r"\b(?:id|id\s*card|id\s*copy|cert|certificate|consent|mandate|"
    r"resolution|registration|invoice|quote|receipt|share|register|"
    r"ma?rr?i?age|birth|death|divorce|moi|cor\d*[\._]?\d*[a-z]?|"
    r"bevestiging\s+van\s+adres|proof\s+of\s+address)\b",
    re.I,
)


def _extract_persons(haystack: str) -> list[PersonToken]:
    persons: list[PersonToken] = []
    seen: set[str] = set()

    # Strip leading "Certified" / "Copy" / sequence numbers and remove
    # in-line doc-type words so the person regex sees a clean name run.
    name_haystack = _PREFIX_NOISE_RX.sub("", haystack)
    name_haystack = _INFIX_DOC_TOKEN_RX.sub(" ", name_haystack)
    name_haystack = re.sub(r"\s+", " ", name_haystack).strip()

    # Pass 1: "Surname, Initials"
    for m in _SURNAME_COMMA_INIT_RX.finditer(name_haystack):
        surname, initials, suffix = m.group(1), m.group(2), m.group(3)
        if _looks_like_doc_word(surname):
            continue
        pt = PersonToken(
            surname=surname.title(),
            initials_or_first=initials.upper(),
            suffix=suffix.title() if suffix else None,
            confidence=0.75,
        )
        if pt.normalised() not in seen:
            seen.add(pt.normalised())
            persons.append(pt)

    # Pass 2: "Initials Surname" with optional 'du/van/de' particle
    for m in _INIT_SURNAME_RX.finditer(name_haystack):
        initials = m.group(1)
        particle = (m.group(2) or "").strip()
        surname1 = m.group(3)
        surname2 = m.group(4) or ""

        # Reject obvious doc tokens (initials side, OR primary surname token)
        if _looks_like_doc_word(initials) or _looks_like_doc_word(surname1):
            continue
        # Reject CIPC/SARS form-code initials
        if initials.upper() in {"MOI", "COR", "CIPC", "SARS", "ID"}:
            continue
        # Suffix tokens that leaked into surname2 belong as a suffix, not surname
        suffix = None
        if surname2 and surname2.lower() in {"snr", "sr", "jnr", "jr", "junior", "senior"}:
            suffix = surname2.title()
            surname2 = ""
        # Reject if surname2 is a doc word — keep just surname1
        if surname2 and _looks_like_doc_word(surname2):
            surname2 = ""

        full_surname = " ".join(t for t in
                                (particle, surname1, surname2) if t).replace("_", " ").title()

        # Look for nearby suffix in tail if not already captured
        if not suffix:
            tail = name_haystack[m.end(): m.end() + 16]
            sm = _SUFFIX_RX.search(tail) or _SUFFIX_PARENS_RX.search(tail)
            if sm:
                suffix = sm.group(1).title()

        pt = PersonToken(
            surname=full_surname,
            initials_or_first=initials.upper(),
            suffix=suffix,
            confidence=0.75 if suffix else 0.7,
        )
        if pt.normalised() not in seen:
            seen.add(pt.normalised())
            persons.append(pt)

    # Pass 3: full lowercase name "michaelis christoffel dippenaar"
    for m in _FULL_NAME_RX.finditer(haystack.lower()):
        first, mid, last = m.group(1), m.group(2), m.group(3)
        if any(_looks_like_doc_word(t.title()) for t in (first, mid, last)):
            continue
        pt = PersonToken(
            surname=last.title(),
            initials_or_first=first.title(),
            full_name=f"{first.title()} {mid.title()} {last.title()}",
            confidence=0.6,
        )
        # Suppress if Pass 2 already captured the same surname
        if any(p.surname.lower() == last for p in persons):
            continue
        if pt.normalised() not in seen:
            seen.add(pt.normalised())
            persons.append(pt)

    return persons


# ---------------------------------------------------------------------------
# Helpers — counterparty extraction
# ---------------------------------------------------------------------------

def _extract_counterparty(haystack: str, doc_type: str) -> Optional[str]:
    """Pull the trailing capitalised token after the doc-type word.

    Examples:
      "04 Mandate Klikk"          → "Klikk"
      "Mandate Marlex Properties" → "Marlex Properties"
    """
    anchors = {
        "MANDATE": "mandate", "RESOLUTION": "resolution",
        "INVOICE": "invoice", "QUOTE": "quote", "LEASE": "lease",
        "BENEFICIAL_OWNERSHIP_REGISTER": "register",
        "SECURITIES_REGISTER": "register",
    }
    anchor = anchors.get(doc_type)
    if not anchor:
        return None
    m = re.search(rf"\b{anchor}\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){{0,3}})",
                  haystack, re.I)
    if not m:
        return None
    cand = m.group(1).strip()
    # Reject only if first token is a *doc-meta* word — but allow legit
    # organisation names like "Klikk" / "Marlex" that appear in
    # NAME_NOISE_TOKENS (those are blocked from being parsed as people,
    # but here they're exactly what we want).
    first_tok = cand.split()[0]
    if first_tok.upper() in _DOC_META_TOKENS:
        return None
    return cand


# Tighter set than NAME_NOISE: just doc-form codes, not organisation names
_DOC_META_TOKENS = {
    "ID", "CARD", "CERT", "CERTIFICATE", "CERTIFIED", "COPY", "ORIGINAL",
    "SCAN", "PAGE", "ANNEXURE", "SCHEDULE", "MOI", "COR", "CIPC", "SARS",
}


# ---------------------------------------------------------------------------
# Convert to provisional Claims (so the lazy pipeline can pre-seed L1)
# ---------------------------------------------------------------------------

def signal_to_provisional_claims(sig: FilenameSignal) -> list[dict]:
    """Emit zero-cost provisional Claims from a FilenameSignal.

    These are written with status=PROPOSED and a low confidence cap (≤0.7)
    so deeper layers can override. Each carries `citation.field_name=
    "<filename>"` and `extracted_by="filename_signal@v1"` so we can audit
    later which facts came from L0.
    """
    out: list[dict] = []
    base_cit = {
        "document_path": sig.raw_path,
        "document_sha256": "",
        "page": None,
        "bbox": None,
        "field_name": "<filename>",
        "extracted_quote": sig.stem_clean,
        "extracted_by": "filename_signal@v1",
    }

    if sig.doc_type:
        out.append({
            "attribute": "doc_type",
            "value": sig.doc_type,
            "confidence": sig.overall_confidence(),
            "citation": dict(base_cit),
        })
    if sig.certification_date:
        out.append({
            "attribute": "certification_date",
            "value": sig.certification_date.isoformat(),
            "confidence": min(0.8, sig.doc_type_confidence + 0.1),
            "citation": dict(base_cit),
        })
    if sig.certified:
        out.append({
            "attribute": "is_certified",
            "value": True,
            "confidence": 0.85,
            "citation": dict(base_cit),
        })
    for person in sig.persons:
        out.append({
            "attribute": "candidate_person",
            "value": person.normalised(),
            "confidence": person.confidence,
            "citation": dict(base_cit),
        })
    if sig.counterparty:
        out.append({
            "attribute": "candidate_counterparty",
            "value": sig.counterparty,
            "confidence": 0.6,
            "citation": dict(base_cit),
        })
    for ref in sig.ref_numbers:
        out.append({
            "attribute": "candidate_reference_number",
            "value": ref,
            "confidence": 0.5,
            "citation": dict(base_cit),
        })
    return out


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":   # pragma: no cover
    import json, sys
    samples = sys.argv[1:] or [
        "G_du_Preez_ID_card_-_certified_-_23.03.2026.pdf",
        "Certified_ID_MC_Dippenaar_Jnr.pdf",
        "Certified_ID_MC_Dippenaar_Jnr_8vTnShL.pdf",
        "Bevestiging van adres, Michaelis christoffel dippenaar.pdf",
        "MC Dippenaar Snr Mariage Certificate.pdf",
        "04_Mandate_Klikk_GZsO34V.pdf",
        "Consent_J_Smit_Dippenaar__14.11.2023.doc",
        "10944640-20260316-51439_1.pdf",
        "Dippenaar, MC (jnr) (1).pdf",
        "Registration certificate CoR14.3 (1).pdf",
        "Beneficial_Ownership_Register_Klikk.pdf",
    ]
    for s in samples:
        sig = extract_filename_signal(s)
        print(f"\n── {s}")
        print(f"  doc_type   : {sig.doc_type}  conf={sig.doc_type_confidence}")
        print(f"  language   : {sig.language_hint}")
        print(f"  certified  : {sig.certified}  cert_date={sig.certification_date}")
        print(f"  persons    : {[p.normalised() for p in sig.persons]}")
        print(f"  counterpty : {sig.counterparty}")
        print(f"  dates      : {[d.isoformat() for d in sig.dates]}")
        print(f"  refs       : {sig.ref_numbers}")
        print(f"  duplicate  : {sig.duplicate_upload}  uniq={sig.django_uniquifier}")
        print(f"  claims     : {json.dumps(signal_to_provisional_claims(sig), indent=2)}")
