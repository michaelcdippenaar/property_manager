"""
SA Smart ID Card layout (front + back).

Coordinates are normalised (x, y, w, h) in [0, 1] relative to the
detected card rectangle. CR80 standard size 85.60 x 53.98 mm,
aspect 1.586. Tolerance ±0.07 absorbs perspective distortion from
hand-held captures.
"""
from __future__ import annotations

from apps.the_volt.classification.skills._shared.types import IDField, IDLayout


LAYOUT_FRONT = IDLayout(
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
        "Polycarbonate card, photo bottom-left, all text right column. "
        "ID number is bottom-right and is the largest text on the card."
    ),
    fields=[
        # Decorative top band — used as an anchor only
        IDField("header_country", (0.05, 0.02, 0.90, 0.10), "text",
                required=False,
                hint="Should read 'REPUBLIC OF SOUTH AFRICA / REPUBLIEK VAN SUID-AFRIKA'."),

        # Right column data fields
        IDField("surname", (0.34, 0.16, 0.62, 0.09), "surname",
                hint="Last name only. Usually ALL CAPS."),
        IDField("names", (0.34, 0.27, 0.62, 0.09), "name",
                hint="Given names, may include initials."),
        IDField("sex", (0.34, 0.38, 0.20, 0.07), "gender",
                hint="Single letter: M or F."),
        IDField("nationality", (0.55, 0.38, 0.41, 0.07), "country_iso2",
                hint="3-letter ISO code, normally RSA."),
        IDField("country_of_birth", (0.34, 0.47, 0.35, 0.07), "country_iso2",
                hint="3-letter ISO country code."),
        IDField("status", (0.70, 0.47, 0.26, 0.07), "text",
                required=False,
                hint="'Citizen' or 'Permanent Resident'."),
        IDField("date_of_birth", (0.34, 0.56, 0.35, 0.08), "date_dmy",
                hint="Format: DD MMM YYYY (e.g. 15 JAN 1980)."),
        IDField("id_number", (0.34, 0.72, 0.62, 0.13), "digits",
                hint="13-digit SA ID number, bold, no spaces."),

        # Image regions (cropped + pHashed, not OCRed)
        IDField("photo", (0.03, 0.20, 0.30, 0.65), "image",
                required=False,
                hint="Bust photo, blue/grey background."),
        IDField("signature", (0.03, 0.85, 0.94, 0.13), "image",
                required=False),
    ],
)


LAYOUT_BACK = IDLayout(
    name="SA Smart ID Card 2013+ (back)",
    doc_type="SA_SMART_ID_CARD",
    aspect_ratio=1.586,
    aspect_tolerance=0.07,
    side="back",
    anchors=["IDZAF", "Date of Issue", "Conditions", "<<<<"],
    fields=[
        IDField("date_of_issue", (0.55, 0.10, 0.40, 0.08), "date_dmy",
                hint="Date the card was printed, DD MMM YYYY."),
        IDField("conditions", (0.05, 0.20, 0.90, 0.20), "text",
                required=False),
        # PDF417 barcode (NOT a QR — though many users say "the QR")
        IDField("barcode_pdf417", (0.05, 0.40, 0.55, 0.30), "image",
                required=False,
                hint="2D PDF417 barcode encoding all the front-face fields."),
        IDField("mrz_line_1", (0.02, 0.74, 0.96, 0.10), "mrz_line",
                hint="Begins with 'IDZAF'. 30 chars including '<' fillers."),
        IDField("mrz_line_2", (0.02, 0.83, 0.96, 0.08), "mrz_line",
                hint="Contains 13-digit ID number + DOB + sex + expiry."),
        IDField("mrz_line_3", (0.02, 0.91, 0.96, 0.08), "mrz_line",
                hint="Surname<<NAMES filled with '<' chars."),
    ],
)
