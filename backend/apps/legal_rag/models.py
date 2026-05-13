"""Django models for the centralised legal RAG store (runtime cache layer).

The canonical source of truth is YAML in ``content/legal/`` (git). These rows
are a refreshed-on-deploy cache populated by ``manage.py sync_legal_facts``
(not yet implemented — Day 3 of Phase A).

Models in this file:

    LegalCorpusVersion
        One row per published corpus snapshot. Merkle-root hash of every
        fact's content_hash. Workers refuse to serve query_* if their
        in-process corpus_version drifts from the active row.

    LegalFact
        One row per concept_id. Latest published view of the fact for
        cheap keyed lookup. Mutable across deploys — but each mutation
        spawns a new LegalFactVersion row, so history is preserved.

    LegalFactVersion
        Append-only history table. Every published version of every fact
        is here, keyed by (fact, version). Carries the full JSON body so
        we can reconstruct what the corpus said on any date.

    LegalAttestation
        Append-only record of an attorney opinion event. Lists which
        ``(concept_id, fact_version)`` pairs the attestation covers.
        Pre-save raises if you try to update an existing row.

See ``content/cto/centralised-legal-rag-store-plan.md`` §3 (architecture)
and §4 (schema) for the locked design.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models


# ── Choice enums ──────────────────────────────────────────────────────── #


class FactType(models.TextChoices):
    """Top-level kind of legal fact. See plan §4."""

    STATUTE_PROVISION = "statute_provision", "Statute Provision"
    CASE_LAW = "case_law", "Case Law"
    PITFALL = "pitfall", "Pitfall Pattern"
    CONCEPT = "concept", "Cross-Statute Concept"


class CitationConfidence(models.TextChoices):
    """Per the canonical citation map taxonomy.

    HIGH    — multiple authoritative sources concur; safe to assert.
    MEDIUM  — mostly concurring sources, minor disagreement; usable with disclaimer.
    LOW     — sources disagree or single source only; flag legal_provisional.
    """

    HIGH = "high", "High"
    MEDIUM = "medium", "Medium"
    LOW = "low", "Low"


class VerificationStatus(models.TextChoices):
    """Editorial state of the fact.

    ai_curated      — drafted by Claude, not yet human-reviewed. Internal only.
    mc_reviewed     — MC has read + merged the YAML PR. Usable by Drafter
                      with legal_provisional disclaimers if confidence != high.
                      NOT usable in externally-facing marketing copy.
    lawyer_reviewed — Admitted attorney attested via opinion letter. Usable
                      anywhere, including externally-facing legal claims.
    """

    AI_CURATED = "ai_curated", "AI Curated"
    MC_REVIEWED = "mc_reviewed", "MC Reviewed"
    LAWYER_REVIEWED = "lawyer_reviewed", "Lawyer Reviewed"


class AttestationMethod(models.TextChoices):
    """How the attorney attested. Per plan §4."""

    EMAIL_PDF_SIGNED = "email_pdf_signed", "Email PDF Signed"
    IN_PERSON_REVIEW = "in_person_review", "In-Person Review"
    COUNSEL_OPINION_LETTER = "counsel_opinion_letter", "Counsel Opinion Letter"


class AttestationFinding(models.TextChoices):
    """Per-fact attorney finding within an attestation event."""

    CONFIRMED = "confirmed", "Confirmed"
    CORRECTED = "corrected", "Corrected"
    REJECTED = "rejected", "Rejected"


# ── Models ────────────────────────────────────────────────────────────── #


class LegalCorpusVersion(models.Model):
    """A published snapshot of the entire legal corpus.

    One row per corpus build. The ``version`` string is the corpus_hash
    (SHA256 of the deterministic JSON of all fact content_hashes, in
    concept_id order). ``merkle_root`` is the same value, exposed as its
    own column for index-only lookups.

    Workers assert ``corpus_version == latest_active.version`` at startup
    and on every query — mismatch means the ChromaDB index has drifted
    from PostgreSQL, which raises a sev-1 alert. See plan §3.
    """

    version = models.CharField(
        max_length=64,
        unique=True,
        help_text="Corpus hash (sha256 hex of concatenated fact hashes).",
    )
    merkle_root = models.CharField(
        max_length=64,
        help_text="Merkle-root-style sha256 over all fact content_hashes.",
    )
    embedding_model = models.CharField(
        max_length=128,
        help_text=(
            "Embedding model name locked at index time (e.g. "
            "'text-embedding-3-small'). Drift = full re-index."
        ),
    )
    fact_count = models.PositiveIntegerField(
        help_text="Total LegalFact rows captured by this corpus version.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True for the version the runtime currently serves.",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Legal Corpus Version"
        verbose_name_plural = "Legal Corpus Versions"

    def __str__(self) -> str:
        marker = " [active]" if self.is_active else ""
        return f"LegalCorpusVersion {self.version[:12]} ({self.fact_count} facts){marker}"


class LegalFact(models.Model):
    """Latest published view of a single legal fact.

    Keyed by ``concept_id`` (unique, kebab-case, max 80 chars per JSON
    Schema). Every column except FKs is a denormalised copy of the latest
    ``LegalFactVersion.content`` for cheap lookup.

    Editing the fact = bumping ``current_version`` to point at a new
    ``LegalFactVersion`` row. The historical version remains queryable
    for reconstructing what the corpus said on any past date.
    """

    # ── Identity ──────────────────────────────────────────────────────── #
    concept_id = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
        help_text="Globally unique kebab-case slug, e.g. 'rha-s5-3-f-deposit-interest-bearing-account'.",
    )
    type = models.CharField(
        max_length=32,
        choices=FactType.choices,
        db_index=True,
        help_text="Top-level fact kind. See FactType.",
    )

    # ── Citation grounding ───────────────────────────────────────────── #
    citation_string = models.CharField(
        max_length=120,
        db_index=True,
        help_text="Canonical render, e.g. 'RHA s5(3)(f)'.",
    )

    # ── Substance ────────────────────────────────────────────────────── #
    plain_english_summary = models.TextField(
        help_text="The fact in 1-3 sentences, suitable for end-user display.",
    )
    statute_text = models.TextField(
        blank=True,
        help_text="Statute text body. May be paraphrased; see statute_text_verbatim.",
    )
    statute_text_verbatim = models.BooleanField(
        default=False,
        help_text=(
            "True only when an admitted attorney has confirmed the text against the "
            "current consolidated Act. Setting True requires verification_status=lawyer_reviewed."
        ),
    )

    # ── Confidence ──────────────────────────────────────────────────── #
    citation_confidence = models.CharField(
        max_length=16,
        choices=CitationConfidence.choices,
        db_index=True,
        help_text="Per the canonical citation map taxonomy.",
    )
    legal_provisional = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "If true, consumers MUST surface uncertainty to the end user "
            "(disclaimers + UI affordance)."
        ),
    )

    # ── Editorial state ─────────────────────────────────────────────── #
    verification_status = models.CharField(
        max_length=32,
        choices=VerificationStatus.choices,
        db_index=True,
        help_text="Editorial review state.",
    )

    # ── Hashes + versioning ─────────────────────────────────────────── #
    corpus_version = models.ForeignKey(
        LegalCorpusVersion,
        on_delete=models.PROTECT,
        related_name="facts",
        help_text="Corpus snapshot this row was published in.",
    )
    fact_version = models.PositiveIntegerField(
        default=1,
        help_text="Monotonic version counter — bumps on every content change.",
    )
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA256 of the canonical YAML source for this version.",
    )

    # ── Current-version pointer ─────────────────────────────────────── #
    # Nullable to break the chicken-and-egg with LegalFactVersion.fact_id at
    # create time — the loader inserts the fact, then the version, then sets
    # current_version. See loader (Day 3) for the transaction pattern.
    current_version = models.ForeignKey(
        "LegalFactVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="FK to the LegalFactVersion row whose content matches the columns above.",
    )

    # ── Structured payload fields ───────────────────────────────────── #
    applicability = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Retrieval filter. Shape: {property_types, tenant_counts, "
            "lease_types, jurisdictions}. See plan §4."
        ),
    )
    topic_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="List[str]. Used for tag-and-filter retrieval.",
    )
    disclaimers = models.JSONField(
        default=list,
        blank=True,
        help_text="List[str] of consumer-mandatory disclaimers attached to this fact.",
    )

    # ── Lifecycle ───────────────────────────────────────────────────── #
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="False = the YAML was deleted; row retained for history.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("concept_id",)
        verbose_name = "Legal Fact"
        verbose_name_plural = "Legal Facts"
        indexes = [
            models.Index(fields=["type", "verification_status"]),
            models.Index(fields=["citation_string", "verification_status"]),
            models.Index(fields=["citation_confidence", "legal_provisional"]),
        ]

    def __str__(self) -> str:
        return f"{self.concept_id} ({self.citation_string})"


class LegalFactVersion(models.Model):
    """Append-only history of every published version of a LegalFact.

    The ``content`` JSON field stores the full canonical body for the
    version — exactly what the YAML file said at the time. This makes
    historical reconstruction trivial: pick a row by ``(fact, version)``
    and you have the fact as it existed at that point in time.

    Never updated. Deletion is forbidden in app logic; the FK from
    ``LegalFact.current_version`` is PROTECT-on-delete.
    """

    fact = models.ForeignKey(
        LegalFact,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version = models.PositiveIntegerField(
        help_text="Matches LegalFact.fact_version at the time this row was created.",
    )
    content = models.JSONField(
        help_text="Full canonical YAML body for this version, as a dict.",
    )
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA256 of the canonical YAML source for this version.",
    )
    attestation = models.ForeignKey(
        "LegalAttestation",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="fact_versions",
        help_text=(
            "If non-null, this version was attested by the linked attorney "
            "opinion event. Null until first attestation lands."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("fact_id", "-version")
        verbose_name = "Legal Fact Version"
        verbose_name_plural = "Legal Fact Versions"
        constraints = [
            models.UniqueConstraint(
                fields=("fact", "version"),
                name="legal_rag_fact_version_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.fact.concept_id} v{self.version}"


class LegalAttestation(models.Model):
    """Append-only record of an attorney opinion event.

    Saved when an admitted attorney signs off on a batch of facts. The
    ``facts_attested`` JSON field is a list of
    ``{concept_id, fact_version, finding, correction_summary?}`` entries
    — one per fact covered by the opinion letter.

    Rows are insert-only. Calling ``save()`` on an existing row raises a
    ``ValidationError``. Delete is allowed only via the Django shell for
    test cleanup (no app code may delete).
    """

    attestation_id = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
        help_text="Stable id, e.g. '2026-Q2-attorney-review'.",
    )
    attorney_name = models.CharField(max_length=200)
    attorney_admission_number = models.CharField(
        max_length=64,
        help_text="LPC admission number, e.g. 'LPC-WC-12345'.",
    )
    attorney_firm = models.CharField(max_length=200, blank=True)
    attestation_method = models.CharField(
        max_length=32,
        choices=AttestationMethod.choices,
    )
    attestation_date = models.DateField(db_index=True)

    opinion_letter_pdf_sha256 = models.CharField(
        max_length=64,
        blank=True,
        help_text="SHA256 of the signed opinion letter PDF for tamper-evidence.",
    )
    opinion_letter_storage = models.CharField(
        max_length=512,
        blank=True,
        help_text="Storage URI for the opinion letter PDF (e.g. 'vault33://...').",
    )

    scope = models.TextField(
        help_text="Human-readable scope of the opinion letter.",
    )
    cost_zar = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fee in ZAR for this attestation.",
    )

    facts_attested = models.JSONField(
        default=list,
        help_text=(
            "List of {concept_id, fact_version, finding, correction_summary?} "
            "entries — one per fact covered. See AttestationFinding for the "
            "allowed `finding` values."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-attestation_date",)
        verbose_name = "Legal Attestation"
        verbose_name_plural = "Legal Attestations"

    def __str__(self) -> str:
        return f"{self.attestation_id} ({self.attorney_name}, {self.attestation_date})"

    def save(self, *args, **kwargs) -> None:
        """Enforce append-only: raise on any update of an existing row."""
        if self.pk is not None:
            # Existing row: re-saving is forbidden.
            raise ValidationError(
                "LegalAttestation rows are append-only. Create a new "
                "attestation event instead of updating an existing one."
            )
        super().save(*args, **kwargs)
