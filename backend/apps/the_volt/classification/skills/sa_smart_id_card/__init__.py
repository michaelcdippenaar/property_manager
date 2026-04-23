"""SA Smart ID Card extraction skill (DHA, 2013+)."""
from apps.the_volt.classification.skills._shared.manifest import SkillManifest
from .layout import LAYOUT_FRONT, LAYOUT_BACK
from .run import extract  # entry point used by the router

MANIFEST = SkillManifest(
    name="sa_smart_id_card",
    version="skill:sa_smart_id_card@v1",
    doc_types=("SA_SMART_ID_CARD", "SA_ID_CARD"),
    extract=extract,
    file_kinds=(".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"),
    needs_anthropic_key=True,
    priority=10,                # specific skill — strongly preferred
    # Filename signals that should route here even without an explicit doc_type.
    # These match the actual corpus: "Certified_ID_MC_Dippenaar_Jnr.pdf",
    # "G_du_Preez_ID_card_-_certified_-_23.03.2026.pdf", "id_doc_*.pdf".
    accepts_when_filename_matches=(
        r"\bID[_ ]card\b",
        r"\bSmart[_ ]ID\b",
        r"^id[_ ]doc(?:[_.]|$)",
        r"\bcertified[_ ]id\b",
    ),
    description="SA Department of Home Affairs Smart ID Card (post-2013).",
)
