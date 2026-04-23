"""
THE VOLT — Volt Classification Number (VCN).

A VCN is a credit-card-style identifier minted for every classified
document. Format:

    VOLT-XXXX-YYYY-MM-NNNN-CCCC

  • XXXX  → 4-letter doc-class abbreviation (e.g. SAID, COR3, BNKS)
  • YYYY-MM → year-month minted (collisions across months are fine)
  • NNNN  → owner-scoped sequence (zero-padded, base32-safe)
  • CCCC  → Luhn-style check digits (mod-10 over the rest)

Properties:

  • Stable: once minted, never changes (even if the doc is re-classified
    to a different doc-type — we mint a NEW VCN and link them).
  • Human-readable: a person can read it over the phone.
  • Tamper-evident: the trailing 4 check digits validate the rest.
  • Owner-scoped: the sequence is per-vault-owner, so two owners can
    have VCN-SAID-2026-04-0001 simultaneously without collision (the
    full primary key is owner_id + VCN).

The doc-class abbreviation table is OPEN — we add codes as new skill
folders ship. Unknown doc-types map to "DOCX" (generic).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional


# 4-letter codes per doc-type (extend as new skills land)
DOC_CLASS_CODES: dict[str, str] = {
    # Identity
    "SA_SMART_ID_CARD": "SAID",
    "SA_GREEN_ID_BOOK": "SAGB",
    "SA_ID_CARD": "SAID",
    "PASSPORT": "PASS",
    "DRIVERS_LICENCE": "DRVR",
    "BIRTH_CERTIFICATE": "BRTH",
    "UNABRIDGED_BIRTH_CERTIFICATE": "UBRT",
    "DEATH_CERTIFICATE": "DTH0",
    "MARRIAGE_CERTIFICATE": "MRRG",
    "DIVORCE_DECREE": "DVRC",
    "ANTE_NUPTIAL_CONTRACT": "ANCC",
    "MARITAL_STATUS_DECL": "MSDC",

    # Address / banking
    "PROOF_OF_ADDRESS": "ADDR",
    "BANK_CONFIRMATION": "BNKC",
    "BANK_STATEMENT": "BNKS",
    "BANK_FACILITY_LETTER": "BNKF",
    "BANK_REFERENCE_LETTER": "BNKR",

    # SARS / FICA
    "SARS_NOTICE_OF_REGISTRATION": "SRNR",
    "SARS_VAT_REGISTRATION": "VATR",
    "FICA_DOCUMENT": "FICA",
    "POPI_CONSENT": "POPI",

    # CIPC / company
    "COR14_3": "CR43",
    "COR14_1A": "CR41",
    "COR14_1": "CR41",
    "COR15_1": "CR51",
    "COR21_1": "CR21",
    "COR39": "CR39",
    "MOI": "MOI0",
    "BENEFICIAL_OWNERSHIP_REGISTER": "BORE",
    "SECURITIES_REGISTER": "SCRG",
    "SHARE_CERTIFICATE": "SHRC",
    "DISCLOSURE_STRUCTURE": "DSCS",
    "CIPC_REGISTRATION_PACK": "CRPK",
    "CIPC_SUBMISSION_RECEIPT": "CSRC",

    # Trusts / estates / wills
    "TRUST_DEED": "TRDD",
    "TRUST_AMENDMENT": "TRAM",
    "TRUST_LETTERS_OF_AUTHORITY": "TRLA",
    "WILL_TESTAMENT": "WILL",
    "TESTAMENTARY_TRUST_DOC": "TTRD",
    "EXECUTORSHIP_LETTER": "EXEC",
    "MASTERS_CERTIFICATE": "MSTR",
    "MASTER_FORM_J246": "J246",
    "MASTER_FORM_J155": "J155",
    "MASTER_FORM_J295": "J295",
    "COMMISSIONER_CERTIFICATE": "CMMR",

    # Affidavits / consents / resolutions
    "FOUNDING_AFFIDAVIT": "FAFD",
    "AFFIDAVIT": "AFFD",
    "CONSENT_LETTER": "CNST",
    "RESOLUTION": "RESL",
    "POWER_OF_ATTORNEY": "POAT",
    "SPECIAL_POWER_OF_ATTORNEY": "SPOA",
    "COURT_ORDER": "CRTO",

    # Property / mandates
    "MANDATE": "MAND",
    "LEASE": "LEAS",
    "TITLE_DEED": "TDED",
    "BOND": "BOND",
    "ELECTRICAL_COC": "ECOC",
    "MUNICIPAL_CLEARANCE": "MUNC",

    # Generic
    "INVOICE": "INVC",
    "QUOTE": "QUOT",
    "RECEIPT": "RCPT",
    "LEDGER": "LDGR",
    "SCAN_UNCATEGORISED": "SCAN",
}

GENERIC_CODE = "DOCX"
VCN_PREFIX = "VOLT"

# Regex: VOLT-XXXX-YYYY-MM-NNNN-CCCC  (NNNN is base32 alphanumeric, CCCC digits)
_VCN_RX = re.compile(
    r"^VOLT-([A-Z0-9]{4})-(\d{4})-(\d{2})-([A-Z0-9]{4})-(\d{4})$"
)


@dataclass(frozen=True)
class VoltClassificationNumber:
    """A parsed VCN. Use `format()` / `__str__()` to get the canonical form."""
    doc_class_code: str
    year: int
    month: int
    sequence: str            # 4-char base32 (e.g. '0001', 'A37B')
    check: str               # 4-digit checksum

    def format(self) -> str:
        return (f"{VCN_PREFIX}-{self.doc_class_code}-{self.year:04d}-"
                f"{self.month:02d}-{self.sequence}-{self.check}")

    def __str__(self) -> str:
        return self.format()

    def is_valid(self) -> bool:
        return self.check == _checksum(self._payload())

    def _payload(self) -> str:
        return f"{self.doc_class_code}{self.year:04d}{self.month:02d}{self.sequence}"


# ---------------------------------------------------------------------------
# Mint
# ---------------------------------------------------------------------------

def mint_vcn(
    *,
    doc_type: Optional[str],
    sequence: int,
    when: Optional[date] = None,
) -> VoltClassificationNumber:
    """Issue a new VCN. `sequence` is the per-(owner, doc_class) counter."""
    when = when or date.today()
    code = DOC_CLASS_CODES.get((doc_type or "").upper(), GENERIC_CODE)
    seq = _encode_seq(sequence)
    payload = f"{code}{when.year:04d}{when.month:02d}{seq}"
    return VoltClassificationNumber(
        doc_class_code=code,
        year=when.year,
        month=when.month,
        sequence=seq,
        check=_checksum(payload),
    )


def parse_vcn(text: str) -> Optional[VoltClassificationNumber]:
    """Parse a printed VCN string. Returns None if malformed OR checksum fails."""
    m = _VCN_RX.match(text.strip().upper())
    if not m:
        return None
    code, year, month, seq, chk = m.groups()
    vcn = VoltClassificationNumber(
        doc_class_code=code,
        year=int(year),
        month=int(month),
        sequence=seq,
        check=chk,
    )
    return vcn if vcn.is_valid() else None


def format_vcn(vcn: VoltClassificationNumber) -> str:
    return vcn.format()


# ---------------------------------------------------------------------------
# Internals — base32 sequence + Luhn-ish checksum
# ---------------------------------------------------------------------------

# Crockford base32 alphabet (no I, L, O, U) — easier to read aloud
_B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

def _encode_seq(n: int) -> str:
    """Encode a positive integer to 4-char Crockford base32, zero-padded."""
    if n < 0:
        raise ValueError("sequence must be non-negative")
    if n >= 32 ** 4:
        raise ValueError(f"sequence overflow (>{32**4-1}); roll the month or class code")
    out = []
    for _ in range(4):
        n, rem = divmod(n, 32)
        out.append(_B32[rem])
    return "".join(reversed(out))


def _checksum(payload: str) -> str:
    """4-digit decimal checksum: sum of (char_code * (i+1)) mod 10000.

    Not cryptographic — purely to catch transcription errors when a human
    reads the VCN over the phone. We're after Luhn-class detection of
    single-digit slips and adjacent transpositions.
    """
    total = 0
    for i, ch in enumerate(payload):
        total += ord(ch) * (i + 1)
    return f"{total % 10000:04d}"
