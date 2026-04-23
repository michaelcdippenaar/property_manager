"""
SA Identity-document layout maps.

Each layout describes a fixed visual template (Smart ID Card 2013+,
Green ID Book 1986–2013, Unabridged Birth Certificate 2013+, etc.) as a
set of NORMALISED bounding boxes — coordinates are fractions of the
detected document area, so they scale to any image resolution.

Why fixed maps when an LLM could "just read it"?
  1. Bbox crops cut tokens (Claude vision sees a 200x80 px field crop
     instead of a 1700x1080 full image).
  2. Field-typed prompts ("read the digits in this crop") prevent
     hallucinated names being placed in the ID-number field.
  3. Cross-field validation (e.g. DOB extracted from the date field MUST
     equal first 6 digits of the ID number) becomes possible — vision
     models alone won't reliably catch this.

Coordinates are (x, y, w, h) where each value is a fraction in [0, 1]
relative to the detected document rectangle (NOT the raw image — see
detect_document_rect() for the perspective normalisation step).

Field types control downstream OCR/validation:
  digits, name, surname, date_yyyymmdd, gender, nationality,
  citizenship, country_iso2, mrz_line, date_dmy, place_of_birth,
  parents_name
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Field & Layout dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IDField:
    name: str                    # canonical key, snake_case
    bbox: tuple[float, float, float, float]   # x, y, w, h in [0,1]
    field_type: str              # digits | name | surname | date_yyyymmdd | gender | country_iso2 | mrz_line | text | date_dmy | place_of_birth
    required: bool = True
    hint: str = ""               # extra prompt context for the OCR model


@dataclass
class IDLayout:
    name: str                    # human label, e.g. "SA Smart ID Card 2013+"
    doc_type: str                # SA_SMART_ID_CARD | SA_GREEN_ID_BOOK | SA_BIRTH_CERT_UNABRIDGED | SA_PASSPORT | SA_DRIVERS_LICENCE
    aspect_ratio: float          # w / h of the document itself (after edge-detection crop)
    aspect_tolerance: float      # ± allowed match band
    side: str = "front"          # front | back | page
    fields: list[IDField] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)   # text strings that, if found anywhere, raise confidence in this layout
    notes: str = ""

    def field_by_name(self, name: str) -> Optional[IDField]:
        for f in self.fields:
            if f.name == name:
                return f
        return None


# ---------------------------------------------------------------------------
# SA SMART ID CARD (2013+)  — CR80 credit-card size 85.60 x 53.98 mm
# ---------------------------------------------------------------------------
# Aspect: 85.60 / 53.98 = 1.5858. Real-world capture (e.g. iPhone) lands in
# ~1.55–1.62 after deskew. The card is dual-language (English/Afrikaans)
# and has the photo on the LEFT. Layout below is for the FRONT face.
#
# Field positions are taken from the standard DHA template:
#   - "REPUBLIC OF SOUTH AFRICA" + coat of arms across the top strip
#   - Photo bottom-left, ~32% width, ~58% height
#   - Right column: Surname, Names, Sex, Nationality, Country of birth,
#     Date of birth, Identity number (largest, near bottom-right)
#   - Bottom strip: signature line + (back) MRZ-style machine-readable lines

SA_SMART_ID_CARD_FRONT = IDLayout(
    name="SA Smart ID Card 2013+ (front)",
    doc_type="SA_SMART_ID_CARD",
    aspect_ratio=1.586,
    aspect_tolerance=0.07,
    side="front",
    anchors=[
        "REPUBLIC OF SOUTH AFRICA",
        "REPUBLIEK VAN SUID-AFRIKA",
        "Identity Number",
        "Identiteitsnommer",
        "Surname",
        "Van",
        "Date of Birth",
    ],
    notes=(
        "Card is laminated polycarbonate. Photo at bottom-left, all text "
        "in right column. ID number is bottom-right, larger font than "
        "other fields."
    ),
    fields=[
        # Header band (mostly decorative, but useful as a layout-detection anchor)
        IDField("header_country", (0.05, 0.02, 0.90, 0.10), "text",
                required=False,
                hint="Should read 'REPUBLIC OF SOUTH AFRICA / REPUBLIEK VAN SUID-AFRIKA'"),

        # Right column data fields (x ~ 0.34..0.97)
        IDField("surname", (0.34, 0.16, 0.62, 0.09), "surname",
                hint="Last name only. ALL CAPS on most cards."),
        IDField("names", (0.34, 0.27, 0.62, 0.09), "name",
                hint="Given names, may include initials."),
        IDField("sex", (0.34, 0.38, 0.20, 0.07), "gender",
                hint="Single letter: M or F."),
        IDField("nationality", (0.55, 0.38, 0.41, 0.07), "country_iso2",
                hint="3-letter code, normally RSA for South African citizens."),
        IDField("country_of_birth", (0.34, 0.47, 0.35, 0.07), "country_iso2",
                hint="3-letter ISO country code, e.g. RSA, ZIM, NAM."),
        IDField("status", (0.70, 0.47, 0.26, 0.07), "text",
                required=False,
                hint="'Citizen' or 'Permanent Resident'."),
        IDField("date_of_birth", (0.34, 0.56, 0.35, 0.08), "date_dmy",
                hint="Format: DD MMM YYYY (e.g. 15 JAN 1980)."),
        IDField("id_number", (0.34, 0.72, 0.62, 0.13), "digits",
                hint="13-digit SA ID number, no spaces, large bold font."),

        # Bottom-left = photo region (not OCRed, but we crop & pHash it
        # so we can compare across documents for the same person)
        IDField("photo", (0.03, 0.20, 0.30, 0.65), "image",
                required=False,
                hint="Bust photo, blue/grey background."),
        IDField("signature", (0.03, 0.85, 0.94, 0.13), "image",
                required=False,
                hint="Holder signature beneath the photo line."),
    ],
)

# Back face — has the MRZ at the bottom and 'Date of Issue', 'Identity Number'
# (repeated), 'Conditions/Restrictions'. We mainly care about the MRZ for
# cross-validation against the front.
SA_SMART_ID_CARD_BACK = IDLayout(
    name="SA Smart ID Card 2013+ (back)",
    doc_type="SA_SMART_ID_CARD",
    aspect_ratio=1.586,
    aspect_tolerance=0.07,
    side="back",
    anchors=["IDZAF", "Date of Issue", "Conditions", "<<<<"],
    fields=[
        IDField("date_of_issue", (0.55, 0.10, 0.40, 0.08), "date_dmy",
                hint="Date the card was printed, format DD MMM YYYY."),
        IDField("conditions", (0.05, 0.20, 0.90, 0.20), "text",
                required=False),
        IDField("mrz_line_1", (0.02, 0.74, 0.96, 0.10), "mrz_line",
                hint="Begins with 'IDZAF'. 30 chars including '<' fillers."),
        IDField("mrz_line_2", (0.02, 0.83, 0.96, 0.08), "mrz_line",
                hint="Contains 13-digit ID number + DOB + sex + expiry."),
        IDField("mrz_line_3", (0.02, 0.91, 0.96, 0.08), "mrz_line",
                hint="Surname<<NAMES filled with '<' chars."),
    ],
)


# ---------------------------------------------------------------------------
# SA GREEN ID BOOK (1986–2013) — booklet, photo page (page 2 of the booklet)
# ---------------------------------------------------------------------------
# A6 booklet (105 x 148 mm).  We model the photo-data spread (left + right
# pages combined into one image, as people commonly scan the open booklet).
# When only one page is scanned, the layout below for SA_GREEN_ID_BOOK_PHOTO
# applies (the right-hand page).
#
# Aspect of the open spread: ~1.42 (close to A6×2 / A6).
# Aspect of the single photo page: ~0.71 (portrait).

SA_GREEN_ID_BOOK_PHOTO = IDLayout(
    name="SA Green ID Book — photo page",
    doc_type="SA_GREEN_ID_BOOK",
    aspect_ratio=0.71,
    aspect_tolerance=0.10,
    side="page",
    anchors=[
        "REPUBLIC OF SOUTH AFRICA",
        "REPUBLIEK VAN SUID-AFRIKA",
        "Identity Document",
        "Identiteitsdokument",
    ],
    notes=(
        "Green hard-cover booklet, photo on LEFT half of the photo page, "
        "ID number printed BELOW the photo, surname/names in the right "
        "column. Often scanned with the cover and so includes the gold "
        "embossed coat of arms."
    ),
    fields=[
        IDField("photo", (0.05, 0.10, 0.45, 0.45), "image",
                required=False,
                hint="Black-and-white or colour bust photo."),
        IDField("id_number", (0.05, 0.57, 0.45, 0.08), "digits",
                hint="13-digit ID number, printed under the photo."),
        IDField("surname", (0.52, 0.12, 0.45, 0.08), "surname"),
        IDField("names", (0.52, 0.22, 0.45, 0.10), "name"),
        IDField("country_of_birth", (0.52, 0.34, 0.45, 0.07), "text",
                required=False,
                hint="Country name in full, often abbreviated to 'RSA'."),
        IDField("date_of_birth", (0.52, 0.44, 0.45, 0.07), "date_dmy",
                hint="Format YY MM DD or DD MM YYYY depending on issue year."),
        IDField("sex", (0.52, 0.54, 0.20, 0.06), "gender"),
        IDField("citizenship_status", (0.52, 0.62, 0.45, 0.06), "text",
                required=False,
                hint="'SA Citizen' / 'SA Burger' or 'Permanent Resident'."),
    ],
)


# ---------------------------------------------------------------------------
# SA UNABRIDGED BIRTH CERTIFICATE (DHA-24, 2013+)
# ---------------------------------------------------------------------------
# A4 portrait, full colour, has a coat of arms watermark, a serial number
# in the top-right, and labelled fields in left-column / right-column pairs.
# This is the form used for minors in property/FICA packs (when the child
# has no SA ID yet, e.g. Lia Dippenaar).
#
# Field order (top-to-bottom):
#   1. Serial No (top-right)
#   2. Surname / Forenames
#   3. Date of Birth / Place of Birth
#   4. Sex / Country of Birth
#   5. ID Number (NEW — population-register ID for the child)
#   6. Father's Surname / Forenames / ID Number / Country of Birth
#   7. Mother's Maiden Surname / Forenames / ID Number / Country of Birth
#   8. Date of Registration / Date of Issue / Issuing Officer signature

SA_BIRTH_CERT_UNABRIDGED = IDLayout(
    name="SA Unabridged Birth Certificate (DHA-24, 2013+)",
    doc_type="SA_BIRTH_CERT_UNABRIDGED",
    aspect_ratio=0.707,            # A4 portrait = 1/√2
    aspect_tolerance=0.05,
    side="page",
    anchors=[
        "DEPARTMENT OF HOME AFFAIRS",
        "BINNELANDSE SAKE",
        "BIRTH CERTIFICATE",
        "GEBOORTESERTIFIKAAT",
        "Unabridged",
        "Onverkorte",
        "DHA-24",
        "Mother",
        "Father",
        "Date of Birth",
    ],
    notes=(
        "Used as root identity for minors (no SA ID yet) and for people "
        "born before 1970. Captures the parental relationship which feeds "
        "the EntityRelationship graph (CHILD_OF). The child's ID number "
        "block is filled in if/when DHA assigns one."
    ),
    fields=[
        IDField("serial_no", (0.65, 0.04, 0.32, 0.04), "text",
                hint="Top-right alphanumeric serial, e.g. 'D 1234567'."),
        IDField("date_of_registration", (0.10, 0.10, 0.40, 0.04), "date_dmy",
                required=False),

        # Child block
        IDField("child_surname", (0.40, 0.18, 0.55, 0.04), "surname"),
        IDField("child_forenames", (0.40, 0.23, 0.55, 0.04), "name"),
        IDField("child_date_of_birth", (0.40, 0.28, 0.55, 0.04), "date_dmy",
                hint="Date of birth of the child, DD/MM/YYYY."),
        IDField("child_place_of_birth", (0.40, 0.33, 0.55, 0.04), "place_of_birth"),
        IDField("child_sex", (0.40, 0.38, 0.15, 0.04), "gender"),
        IDField("child_country_of_birth", (0.60, 0.38, 0.35, 0.04), "country_iso2"),
        IDField("child_id_number", (0.40, 0.43, 0.55, 0.04), "digits",
                required=False,
                hint="May be blank for very recent births before population registration."),

        # Father block
        IDField("father_surname", (0.40, 0.52, 0.55, 0.04), "surname"),
        IDField("father_forenames", (0.40, 0.57, 0.55, 0.04), "name"),
        IDField("father_id_number", (0.40, 0.62, 0.55, 0.04), "digits"),
        IDField("father_country_of_birth", (0.40, 0.67, 0.55, 0.04), "country_iso2"),

        # Mother block
        IDField("mother_maiden_surname", (0.40, 0.74, 0.55, 0.04), "surname"),
        IDField("mother_forenames", (0.40, 0.79, 0.55, 0.04), "name"),
        IDField("mother_id_number", (0.40, 0.84, 0.55, 0.04), "digits"),
        IDField("mother_country_of_birth", (0.40, 0.89, 0.55, 0.04), "country_iso2"),

        # Footer
        IDField("date_of_issue", (0.10, 0.94, 0.30, 0.04), "date_dmy"),
        IDField("issuing_officer", (0.45, 0.94, 0.50, 0.04), "text",
                required=False),
    ],
)


# ---------------------------------------------------------------------------
# SA PASSPORT — biographical (data) page
# ---------------------------------------------------------------------------
# Standard ICAO 9303 layout (TD3): 125 x 88 mm, aspect 1.42.
# We mostly care about the MRZ (two lines of 44 chars each) at the bottom
# because it contains all the structured identity fields and a check
# digit per field — far more reliable than reading the data zone.

SA_PASSPORT_DATA_PAGE = IDLayout(
    name="SA Passport — biographical page",
    doc_type="SA_PASSPORT",
    aspect_ratio=1.42,
    aspect_tolerance=0.07,
    side="page",
    anchors=[
        "PASSPORT",
        "PASPOORT",
        "REPUBLIC OF SOUTH AFRICA",
        "P<ZAF",
        "Type",
        "Surname",
    ],
    fields=[
        IDField("photo", (0.02, 0.20, 0.28, 0.55), "image", required=False),
        IDField("type", (0.32, 0.18, 0.10, 0.06), "text", required=False),
        IDField("country_code", (0.45, 0.18, 0.15, 0.06), "country_iso2",
                hint="Should be 'ZAF'."),
        IDField("passport_no", (0.65, 0.18, 0.30, 0.07), "digits"),
        IDField("surname", (0.32, 0.30, 0.62, 0.06), "surname"),
        IDField("given_names", (0.32, 0.38, 0.62, 0.06), "name"),
        IDField("nationality", (0.32, 0.46, 0.30, 0.05), "country_iso2"),
        IDField("date_of_birth", (0.32, 0.52, 0.30, 0.05), "date_dmy"),
        IDField("sex", (0.62, 0.52, 0.10, 0.05), "gender"),
        IDField("place_of_birth", (0.32, 0.58, 0.62, 0.05), "place_of_birth"),
        IDField("date_of_issue", (0.32, 0.64, 0.30, 0.05), "date_dmy"),
        IDField("date_of_expiry", (0.62, 0.64, 0.30, 0.05), "date_dmy"),
        IDField("issuing_authority", (0.32, 0.70, 0.62, 0.05), "text"),
        IDField("id_number", (0.32, 0.76, 0.62, 0.05), "digits",
                hint="13-digit SA ID number — same as on the holder's ID card."),
        IDField("mrz_line_1", (0.02, 0.86, 0.96, 0.06), "mrz_line",
                hint="Starts 'P<ZAF', length exactly 44 chars."),
        IDField("mrz_line_2", (0.02, 0.92, 0.96, 0.06), "mrz_line",
                hint="Passport number + DOB + sex + expiry + ID number, 44 chars."),
    ],
)


# ---------------------------------------------------------------------------
# SA DRIVER'S LICENCE CARD
# ---------------------------------------------------------------------------
# CR80 size, aspect 1.586, but with portrait orientation in some captures.
# Layout below is for landscape-orientation front face.

SA_DRIVERS_LICENCE_FRONT = IDLayout(
    name="SA Driver's Licence (front)",
    doc_type="SA_DRIVERS_LICENCE",
    aspect_ratio=1.586,
    aspect_tolerance=0.07,
    side="front",
    anchors=[
        "DRIVING LICENCE",
        "BESTUURSLISENSIE",
        "REPUBLIC OF SOUTH AFRICA",
        "Code",
        "First issue",
        "Valid",
    ],
    fields=[
        IDField("photo", (0.02, 0.18, 0.28, 0.65), "image", required=False),
        IDField("surname", (0.32, 0.16, 0.62, 0.07), "surname"),
        IDField("initials_and_name", (0.32, 0.24, 0.62, 0.07), "name"),
        IDField("id_number", (0.32, 0.32, 0.62, 0.08), "digits"),
        IDField("date_of_birth", (0.32, 0.42, 0.30, 0.06), "date_dmy"),
        IDField("sex", (0.62, 0.42, 0.10, 0.06), "gender"),
        IDField("vehicle_codes", (0.32, 0.50, 0.62, 0.07), "text",
                hint="One or more of: A, A1, B, EB, C, C1, EC, EC1."),
        IDField("first_issue_date", (0.32, 0.58, 0.30, 0.06), "date_dmy"),
        IDField("valid_from", (0.32, 0.66, 0.30, 0.06), "date_dmy"),
        IDField("valid_until", (0.62, 0.66, 0.30, 0.06), "date_dmy"),
        IDField("licence_number", (0.32, 0.74, 0.62, 0.07), "text"),
        IDField("restrictions", (0.32, 0.82, 0.62, 0.07), "text", required=False),
    ],
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_LAYOUTS: list[IDLayout] = [
    SA_SMART_ID_CARD_FRONT,
    SA_SMART_ID_CARD_BACK,
    SA_GREEN_ID_BOOK_PHOTO,
    SA_BIRTH_CERT_UNABRIDGED,
    SA_PASSPORT_DATA_PAGE,
    SA_DRIVERS_LICENCE_FRONT,
]


def detect_layout(
    *,
    image_aspect: float,
    sample_text: str = "",
    filename: str = "",
) -> tuple[IDLayout, float, str]:
    """Pick the most likely layout for an image.

    Strategy:
      1. Filter by aspect ratio (must fall inside layout.aspect_tolerance)
      2. Add bonus for anchor strings found in sample_text
      3. Add bonus for filename hints (e.g. 'birth' → BIRTH_CERT)

    Returns (layout, score 0..1, reason).
    """
    fname = (filename or "").lower()
    text = (sample_text or "").upper()

    candidates: list[tuple[IDLayout, float, str]] = []
    for layout in ALL_LAYOUTS:
        # 1. aspect gate
        delta = abs(image_aspect - layout.aspect_ratio)
        if delta > layout.aspect_tolerance:
            continue
        aspect_score = 1.0 - (delta / layout.aspect_tolerance)  # 1.0 = perfect, 0.0 = on tolerance edge

        # 2. anchor hits
        anchor_hits = sum(1 for a in layout.anchors if a.upper() in text)
        anchor_score = min(anchor_hits / 3.0, 1.0)  # cap at 3 hits = full score

        # 3. filename hints
        fname_bonus = 0.0
        if layout.doc_type == "SA_BIRTH_CERT_UNABRIDGED" and any(w in fname for w in ("birth", "geboorte", "dha-24", "dha24")):
            fname_bonus = 0.3
        elif layout.doc_type == "SA_PASSPORT" and "passport" in fname:
            fname_bonus = 0.3
        elif layout.doc_type == "SA_DRIVERS_LICENCE" and any(w in fname for w in ("driver", "licence", "license", "bestuur")):
            fname_bonus = 0.3
        elif layout.doc_type == "SA_SMART_ID_CARD" and any(w in fname for w in ("id_front", "id_back", "smart", "id card", "id-card", "idcard")):
            fname_bonus = 0.2
        elif layout.doc_type == "SA_GREEN_ID_BOOK" and any(w in fname for w in ("id book", "id-book", "groen", "green id", "id_book")):
            fname_bonus = 0.2

        # combine: aspect is the most important gate, anchors confirm
        score = 0.55 * aspect_score + 0.30 * anchor_score + 0.15 * fname_bonus
        reason = f"aspect={aspect_score:.2f} anchors={anchor_hits} fname_bonus={fname_bonus:.2f}"
        candidates.append((layout, score, reason))

    if not candidates:
        # fallback: nothing matched aspect; still return the closest by aspect
        layout = min(ALL_LAYOUTS, key=lambda L: abs(L.aspect_ratio - image_aspect))
        return layout, 0.0, "no_layout_in_tolerance:aspect_only_fallback"

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0]


def crop_box(img_w: int, img_h: int, bbox: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    """Convert normalised (x,y,w,h) to (left, upper, right, lower) pixels."""
    x, y, w, h = bbox
    L = int(x * img_w)
    U = int(y * img_h)
    R = int((x + w) * img_w)
    D = int((y + h) * img_h)
    return (max(0, L), max(0, U), min(img_w, R), min(img_h, D))
