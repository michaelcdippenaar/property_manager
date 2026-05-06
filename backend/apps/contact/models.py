"""
Contact enquiries — submissions from the public marketing site contact form.

POPIA notes
-----------
- We record ``consent_at`` the moment the form is submitted with the consent
  box ticked. This is our POPIA s11(1)(a) lawful-basis evidence.
- ``ip_address`` and ``user_agent`` are captured for fraud/abuse investigation
  and kept only as long as the enquiry record itself. Remove via
  :meth:`anonymise` when retention is no longer justified (e.g. 12 months
  after ``responded_at`` or creation).
- The data subject can request access or deletion at any time via PAIA /
  POPIA data-subject request — see ``apps.accounts`` for the handler.
"""
from django.db import models
from django.utils import timezone

from apps.popia.choices import LawfulBasis, RetentionPolicy


class ContactEnquiry(models.Model):
    """A public contact-form submission from klikk.co.za/contact."""

    ROLE_CHOICES = [
        ("landlord", "Private landlord"),
        ("agency", "Rental agency"),
        ("owner", "Body corporate / owner"),
        ("tenant", "Tenant"),
        ("supplier", "Supplier / contractor"),
        ("other", "Other"),
    ]

    # Multi-tenant + POPIA scaffolding
    agency = models.ForeignKey(
        "accounts.Agency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contact_enquiries",
        help_text="Owning agency / tenant. Marketing leads usually have no agency yet.",
    )
    lawful_basis = models.CharField(
        max_length=32,
        choices=LawfulBasis.choices,
        default=LawfulBasis.CONSENT,
        help_text="POPIA s11 basis. Public form opt-in = consent (s11(1)(a)).",
    )
    retention_policy = models.CharField(
        max_length=32,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.MARKETING_CONSENT_LIFETIME,
        help_text="POPIA s14 retention. Marketing consent record (DM Guidance 2024).",
    )

    # Submission metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Enquirer-provided
    name = models.CharField(max_length=120)
    email = models.EmailField(max_length=254, db_index=True)
    organisation = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=60, choices=ROLE_CHOICES, default="other")
    message = models.TextField(max_length=4000)

    # POPIA consent — timestamp proves the consent box was ticked at submission
    consent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of POPIA s11(1)(a) consent acknowledgement.",
    )

    # Audit trail (fraud/abuse investigation; anonymise on retention expiry)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)

    # Delivery state
    email_sent = models.BooleanField(
        default=False,
        help_text="Whether the notification email to CONTACT_EMAIL was dispatched.",
    )

    # Internal workflow
    responded_at = models.DateTimeField(null=True, blank=True)
    handled = models.BooleanField(default=False, db_index=True)
    notes = models.TextField(blank=True, help_text="Internal notes, not shared.")

    class Meta:
        verbose_name = "contact enquiry"
        verbose_name_plural = "contact enquiries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agency", "created_at"], name="contact_enq_agency_ts_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}> · {self.created_at:%Y-%m-%d %H:%M}"

    def mark_responded(self) -> None:
        """Shortcut used from admin to close out an enquiry."""
        self.responded_at = timezone.now()
        self.handled = True
        self.save(update_fields=["responded_at", "handled"])

    def anonymise(self) -> None:
        """Strip PI once the retention window passes. Keeps the row for stats."""
        self.name = "[redacted]"
        self.email = "redacted@klikk.invalid"
        self.organisation = ""
        self.message = "[redacted per POPIA retention policy]"
        self.ip_address = None
        self.user_agent = ""
        self.save(
            update_fields=[
                "name", "email", "organisation", "message",
                "ip_address", "user_agent",
            ]
        )
