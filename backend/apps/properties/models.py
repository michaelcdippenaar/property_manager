from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.accounts.models import User, Person


class Property(models.Model):
    class PropertyType(models.TextChoices):
        APARTMENT = "apartment", "Apartment"
        HOUSE = "house", "House"
        TOWNHOUSE = "townhouse", "Townhouse"
        COMMERCIAL = "commercial", "Commercial"

    owner = models.ForeignKey(
        Person, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="owned_properties",
        help_text="Person or company that owns this property"
    )
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_properties")
    name = models.CharField(max_length=200)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices)
    address = models.TextField()
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    house_rules = models.TextField(blank=True, help_text="House rules shown to tenants — parking, noise, pets, visitors, etc.")
    information_items = models.JSONField(
        default=list, blank=True,
        help_text="Landlord notes ingested into the tenant maintenance RAG. Each item: {id, label, body, category, updated_at}."
    )
    image = models.ImageField(upload_to="properties/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "properties"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class Unit(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        MAINTENANCE = "maintenance", "Under Maintenance"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="units")
    unit_number = models.CharField(max_length=20)
    bedrooms = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=1)
    toilets = models.PositiveSmallIntegerField(default=1)
    floor_size_m2 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE)
    floor = models.PositiveSmallIntegerField(null=True, blank=True)
    ad_description = models.TextField(blank=True, help_text="Advertising copy used in rental listings")
    amenities = models.JSONField(default=list, blank=True, help_text="List of amenity strings, e.g. ['Pool', 'Garden', 'Braai area']")

    def __str__(self):
        return f"{self.property.name} — Unit {self.unit_number}"


class Room(models.Model):
    class RoomType(models.TextChoices):
        BEDROOM = "bedroom", "Bedroom"
        BATHROOM = "bathroom", "Bathroom"
        KITCHEN = "kitchen", "Kitchen"
        LIVING_ROOM = "living_room", "Living Room"
        DINING_ROOM = "dining_room", "Dining Room"
        STUDY = "study", "Study"
        GARAGE = "garage", "Garage"
        STOREROOM = "storeroom", "Storeroom"
        LAUNDRY = "laundry", "Laundry"
        BALCONY = "balcony", "Balcony"
        PATIO = "patio", "Patio"
        OTHER = "other", "Other"

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="rooms")
    room_type = models.CharField(max_length=20, choices=RoomType.choices)
    name = models.CharField(max_length=100, blank=True, help_text="e.g. Main bedroom, En-suite")
    size_m2 = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "room_type"]

    def __str__(self):
        label = self.name or self.get_room_type_display()
        return f"{label} ({self.size_m2} m\u00b2)" if self.size_m2 else label


class UnitInfo(models.Model):
    class IconType(models.TextChoices):
        WIFI = "wifi", "WiFi"
        ALARM = "alarm", "Alarm"
        GARBAGE = "garbage", "Garbage"
        PARKING = "parking", "Parking"
        ELECTRICITY = "electricity", "Electricity"
        WATER = "water", "Water"
        GAS = "gas", "Gas"
        INTERCOM = "intercom", "Intercom"
        LAUNDRY = "laundry", "Laundry"
        OTHER = "other", "Other"

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="info_items")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name="info_items", null=True, blank=True)
    icon_type = models.CharField(max_length=20, choices=IconType.choices, default=IconType.OTHER)
    label = models.CharField(max_length=100)
    value = models.TextField()
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "label"]

    def __str__(self):
        return f"{self.label}: {self.value[:50]}"


class PropertyAgentConfig(models.Model):
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name="agent_config")
    maintenance_playbook = models.TextField(blank=True, help_text="Instructions for how the AI agent should handle maintenance requests for this property")
    ai_notes = models.TextField(blank=True, help_text="Additional context the AI agent should know about this property")
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Agent config for {self.property.name}"


class Landlord(models.Model):
    """
    A landlord entity (individual, company, or trust) that can own multiple properties.
    Linked to Person for system identity.
    """
    class LandlordType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        COMPANY = "company", "Company"
        TRUST = "trust", "Trust"
        CC = "cc", "Close Corporation"
        PARTNERSHIP = "partnership", "Partnership"

    person = models.OneToOneField(
        Person, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='landlord_profile',
        help_text="Link to Person record for shared identity"
    )
    name = models.CharField(max_length=200, help_text="Legal name of landlord/company/trust")
    landlord_type = models.CharField(max_length=20, choices=LandlordType.choices, default=LandlordType.INDIVIDUAL)
    owned_by_trust = models.BooleanField(default=False, help_text="For companies/CCs — indicates beneficial ownership through a trust (triggers trust FICA/CIPC doc requirements)")
    classification_data = models.JSONField(null=True, blank=True, help_text="Structured output from the AI document classifier (owner_classification.json)")
    id_number = models.CharField(max_length=20, blank=True, help_text="SA ID or passport")
    registration_number = models.CharField(max_length=50, blank=True, help_text="Company/trust reg number")
    vat_number = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.JSONField(default=dict, blank=True, help_text="street, city, province, postal_code")

    # Representative (person who signs leases on behalf of company/trust)
    representative_name = models.CharField(max_length=200, blank=True)
    representative_id_number = models.CharField(max_length=20, blank=True)
    representative_email = models.EmailField(blank=True)
    representative_phone = models.CharField(max_length=20, blank=True)

    # Registration document (CIPC, trust deed, ID copy, etc.)
    registration_document = models.FileField(
        upload_to='landlords/registration_docs/', blank=True, null=True,
        help_text="CIPC certificate, trust deed, or ID document"
    )
    registration_document_name = models.CharField(max_length=255, blank=True, help_text="Original filename")

    # DEPRECATED: Use RentalMandate model (per-property) instead.
    # These fields will be removed in a future migration after data migration.
    mandate_document = models.FileField(
        upload_to='landlords/mandates/', blank=True, null=True,
        help_text="DEPRECATED — use RentalMandate. Signed management mandate / agency agreement"
    )
    mandate_document_name = models.CharField(max_length=255, blank=True, help_text="DEPRECATED — original filename")
    mandate_start_date = models.DateField(null=True, blank=True)
    mandate_end_date = models.DateField(null=True, blank=True)
    mandate_status = models.CharField(
        max_length=20, blank=True, default='',
        choices=[('', '—'), ('active', 'Active'), ('expired', 'Expired'), ('pending', 'Pending')],
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class LandlordDocument(models.Model):
    """A supporting document uploaded for owner FICA/CIPC compliance (multiple per landlord)."""
    landlord = models.ForeignKey(Landlord, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField(upload_to='landlords/documents/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.landlord.name} — {self.filename}"


class BankAccount(models.Model):
    """Bank account linked to a landlord. One landlord can have multiple accounts."""
    landlord = models.ForeignKey(Landlord, on_delete=models.CASCADE, related_name='bank_accounts')
    label = models.CharField(max_length=100, blank=True, help_text="e.g. 'Main rental account'")
    bank_name = models.CharField(max_length=100)
    branch_code = models.CharField(max_length=20)
    account_number = models.CharField(max_length=30)
    account_type = models.CharField(max_length=30, blank=True, help_text="e.g. Cheque, Savings, Transmission")
    account_holder = models.CharField(max_length=200)
    is_default = models.BooleanField(default=False)
    confirmation_letter = models.FileField(
        upload_to='bank_accounts/confirmation_letters/',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "label"]

    def __str__(self):
        return f"{self.bank_name} — {self.account_number[-4:]}" if self.account_number else self.bank_name


class LandlordChatMessage(models.Model):
    """A single message in the owner-onboarding chat for a landlord.

    Persisted so the chat has memory across sessions — the agent can come
    back a week later and the conversation picks up where it left off.
    """
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"

    landlord = models.ForeignKey(Landlord, on_delete=models.CASCADE, related_name="chat_messages")
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField(blank=True, help_text="Plain-text content of the message.")
    tool_calls = models.JSONField(null=True, blank=True, help_text="Tool use / tool result blocks for this turn.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["landlord", "created_at"])]

    def __str__(self):
        return f"[{self.role}] {self.landlord.name}: {self.content[:40]}"


class PropertyOwnership(models.Model):
    """
    Tracks ownership of a property over time.
    A property can change owners (e.g. sold), and existing leases
    remain linked to the ownership record that was active when signed.
    """
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="ownerships")
    landlord = models.ForeignKey(Landlord, on_delete=models.SET_NULL, null=True, blank=True, related_name='ownerships')

    # Owner entity (company/trust/individual that owns the property)
    owner_name = models.CharField(max_length=200, help_text="Company or individual name")
    owner_type = models.CharField(max_length=20, choices=[
        ("individual", "Individual"),
        ("company", "Company"),
        ("trust", "Trust"),
    ], default="company")
    registration_number = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=30, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)
    owner_address = models.JSONField(default=dict, blank=True, help_text="street, city, province, postal_code")

    # Representative / landlord (person acting on behalf of owner)
    representative_name = models.CharField(max_length=200, blank=True)
    representative_id_number = models.CharField(max_length=20, blank=True)
    representative_email = models.EmailField(blank=True)
    representative_phone = models.CharField(max_length=20, blank=True)

    # Bank details (where rent is paid)
    bank_details = models.JSONField(default=dict, blank=True, help_text="bank_name, branch_code, account_number, account_type, account_holder")

    # Ownership period
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Null = current owner")
    is_current = models.BooleanField(default=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_current", "-start_date"]

    def __str__(self):
        return f"{self.owner_name} → {self.property.name} ({'current' if self.is_current else 'ended'})"


class RentalMandate(models.Model):
    """
    A digitally signed rental management mandate between a property owner and the agency.
    One mandate per property — the authoritative record replacing the deprecated Landlord
    mandate fields. Required before a property can be listed or managed.
    """

    class MandateType(models.TextChoices):
        FULL_MANAGEMENT = "full_management", "Full Management"
        LETTING_ONLY    = "letting_only",    "Letting Only"
        RENT_COLLECTION = "rent_collection", "Rent Collection Only"
        FINDERS_FEE     = "finders_fee",     "Finders Fee"

    class Exclusivity(models.TextChoices):
        SOLE = "sole", "Sole Mandate"
        OPEN = "open", "Open Mandate"

    class CommissionPeriod(models.TextChoices):
        MONTHLY  = "monthly",  "Monthly"
        ONCE_OFF = "once_off", "Once-off"

    class Status(models.TextChoices):
        DRAFT            = "draft",            "Draft"
        SENT             = "sent",             "Sent for Signing"
        PARTIALLY_SIGNED = "partially_signed", "Partially Signed"
        ACTIVE           = "active",           "Active"
        EXPIRED          = "expired",          "Expired"
        CANCELLED        = "cancelled",        "Cancelled"

    property  = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="mandates")
    landlord  = models.ForeignKey(
        Landlord, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="mandates",
        help_text="Linked landlord entity (denormalised from PropertyOwnership for convenience)",
    )

    mandate_type      = models.CharField(max_length=20, choices=MandateType.choices)
    exclusivity       = models.CharField(max_length=10, choices=Exclusivity.choices, default=Exclusivity.SOLE)
    commission_rate   = models.DecimalField(
        max_digits=6, decimal_places=2,
        help_text="Percentage for monthly mandates (e.g. 10.00 = 10%) or month count for once-off (e.g. 1.00 = 1 month)",
    )
    commission_period = models.CharField(max_length=10, choices=CommissionPeriod.choices, default=CommissionPeriod.MONTHLY)
    start_date        = models.DateField()
    end_date          = models.DateField(null=True, blank=True)
    notice_period_days = models.PositiveSmallIntegerField(
        default=60,
        help_text="Days' written notice required to terminate the mandate",
    )
    maintenance_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=2000,
        help_text="Full Management: max spend per incident the agent may authorise without owner approval (ZAR)",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    esigning_submission = models.OneToOneField(
        "esigning.ESigningSubmission",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",  # reverse accessor suppressed — use submission.mandate (FK) instead
        help_text="The e-signing submission that captured both owner and agent signatures",
    )
    signed_document = models.FileField(
        upload_to="mandates/signed/", blank=True, null=True,
        help_text="Final countersigned mandate PDF (auto-populated when e-signing completes)",
    )
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_mandates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_mandate_type_display()} — {self.property.name} ({self.status})"


class PropertyGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    properties = models.ManyToManyField(Property, related_name="groups", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ── Physical property detail ──────────────────────────────────────────────────

class PropertyDetail(models.Model):
    """
    Physical and legal details for a managed property.
    OneToOne with Property — extends the core record without bloating it.
    Populated from deeds, lease agreements, compliance certificates, and plans.
    """
    class ConstructionType(models.TextChoices):
        FACE_BRICK   = "face_brick",   "Face Brick"
        PLASTER      = "plaster",      "Plastered Brick"
        TIMBER_FRAME = "timber_frame", "Timber Frame"
        STEEL_FRAME  = "steel_frame",  "Steel Frame"
        MIXED        = "mixed",        "Mixed"
        OTHER        = "other",        "Other"

    class RoofType(models.TextChoices):
        CEMENT_TILE  = "cement_tile",  "Cement Tile"
        CLAY_TILE    = "clay_tile",    "Clay Tile"
        IBR_SHEETING = "ibr",          "IBR Sheeting"
        THATCH       = "thatch",       "Thatch"
        FLAT         = "flat",         "Flat Roof"
        OTHER        = "other",        "Other"

    property = models.OneToOneField(
        Property, on_delete=models.CASCADE, related_name="detail"
    )

    # Deeds / legal
    erf_number        = models.CharField(max_length=30, blank=True, unique=True, null=True, help_text="e.g. ERF 3587")
    title_deed_number = models.CharField(max_length=50, blank=True)
    municipality      = models.CharField(max_length=100, blank=True, help_text="e.g. Stellenbosch Municipality")
    suburb            = models.CharField(max_length=100, blank=True)
    zoning            = models.CharField(max_length=100, blank=True, help_text="e.g. Residential 1")

    # Dimensions
    erf_size_m2   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Stand/erf area m²")
    floor_size_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Gross livable area m²")

    # GPS (primary location reference)
    latitude  = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Construction
    year_built        = models.PositiveSmallIntegerField(null=True, blank=True)
    construction_type = models.CharField(max_length=20, choices=ConstructionType.choices, blank=True)
    roof_type         = models.CharField(max_length=20, choices=RoofType.choices, blank=True)
    number_of_storeys = models.PositiveSmallIntegerField(default=1)
    has_garage        = models.BooleanField(default=False)
    has_pool          = models.BooleanField(default=False)
    has_flatlet       = models.BooleanField(default=False, help_text="Self-contained secondary unit on the erf")
    garden_type       = models.CharField(max_length=100, blank=True, help_text="e.g. Established garden, low maintenance")

    # Financial
    purchase_price       = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    purchase_date        = models.DateField(null=True, blank=True)
    current_valuation    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    valuation_date       = models.DateField(null=True, blank=True)
    municipal_value      = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Council valuation roll value")
    municipal_value_date = models.DateField(null=True, blank=True)

    # Google Drive
    drive_photos_url    = models.URLField(max_length=500, blank=True, help_text="Google Drive folder — property photos")
    drive_documents_url = models.URLField(max_length=500, blank=True, help_text="Google Drive folder — all documents")
    drive_plans_url     = models.URLField(max_length=500, blank=True, help_text="Google Drive folder — house plans")

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Detail: {self.property.name} — ERF {self.erf_number}"


# ── Photo gallery ─────────────────────────────────────────────────────────────

class PropertyPhoto(models.Model):
    class Category(models.TextChoices):
        EXTERIOR  = "exterior",  "Exterior"
        INTERIOR  = "interior",  "Interior"
        FLATLET   = "flatlet",   "Flatlet"
        GARDEN    = "garden",    "Garden"
        PLANS     = "plans",     "Floor Plans"
        OTHER     = "other",     "Other"

    property    = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="photos")
    unit        = models.ForeignKey("Unit", on_delete=models.SET_NULL, null=True, blank=True, related_name="photos", help_text="Leave blank for property-level photos")
    photo       = models.ImageField(upload_to="properties/photos/")
    thumbnail   = models.ImageField(upload_to="properties/thumbnails/", blank=True)
    caption     = models.CharField(max_length=200, blank=True)
    category    = models.CharField(max_length=20, choices=Category.choices, default=Category.EXTERIOR)
    position    = models.PositiveSmallIntegerField(default=0, help_text="Display order — 0 = cover photo")
    is_cover    = models.BooleanField(default=False)
    drive_url   = models.URLField(max_length=500, blank=True, help_text="Original Google Drive URL if synced from Drive")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "-uploaded_at"]

    def __str__(self):
        return f"{self.property.name} — {self.category} #{self.position}"


# ── Property documents ────────────────────────────────────────────────────────

class PropertyDocument(models.Model):
    class DocType(models.TextChoices):
        # Purchase & transfer
        OFFER_TO_PURCHASE = "offer_to_purchase", "Offer to Purchase"
        TITLE_DEED        = "title_deed",        "Title Deed"
        TRANSFER_DOCS     = "transfer_docs",     "Transfer Documents"
        VALUATION         = "valuation",         "Valuation Report"
        # Compliance certificates
        COMPLIANCE_CERT   = "compliance_cert",   "Compliance Certificate (general)"
        ELECTRICAL_COC    = "electrical_coc",    "Electrical Certificate of Compliance"
        GAS_COC           = "gas_coc",           "Gas Compliance Certificate"
        PLUMBING_COC      = "plumbing_coc",      "Plumbing Compliance Certificate"
        BEETLE_CERT       = "beetle_cert",       "Beetle / Pest Certificate"
        FENCE_CERT        = "fence_cert",        "Electric Fence Certificate"
        # Municipal & rates
        MUNICIPAL         = "municipal",         "Municipal Account / Bill"
        RATES_CLEARANCE   = "rates_clearance",   "Rates Clearance Certificate"
        ZONING_CERT       = "zoning_cert",       "Zoning Certificate"
        BUILDING_PLANS    = "building_plans",    "Approved Building Plans"
        # Technical & developer handover
        TECHNICAL_DRAWING = "technical_drawing", "Technical Drawing / Floor Plan"
        DEV_HANDOVER      = "dev_handover",      "Developer Handover"
        WARRANTY          = "warranty",          "Warranty / Guarantee"
        PAINT_SPEC        = "paint_spec",        "Paint Colours / Finishes"
        GENERATOR         = "generator",         "Generator / Inverter Info"
        SOLAR             = "solar",             "Solar / PV System Docs"
        # Bond, finance & insurance
        INSURANCE         = "insurance",         "Insurance Document"
        BOND_DOCS         = "bond_docs",         "Bond / Mortgage Documents"
        CAPITAL_UPGRADE   = "capital_upgrade",   "Capital Upgrade Invoice"
        SARS_DOCS         = "sars_docs",         "SARS Tax Certificate / IRP5"
        FINANCE_COSTS     = "finance_costs",     "Financing / Transfer Costs"
        # Estate & body corporate
        ESTATE_RULES      = "estate_rules",      "Estate / Complex Rules"
        BODY_CORPORATE    = "body_corporate",    "Body Corporate / HOA Minutes"
        HOA_LEVY          = "hoa_levy",          "HOA Levy Statement"
        # Tenant & FICA
        FICA_DOCS         = "fica_docs",         "FICA Documentation"
        TENANT_ID         = "tenant_id",         "Tenant ID Copy"
        TENANT_BANK       = "tenant_bank",       "Tenant Proof of Income / Bank"
        CREDIT_CHECK      = "credit_check",      "Credit Check Report"
        # Other
        HOUSE_RULES       = "house_rules",       "House Rules"
        OTHER             = "other",             "Other"

    property    = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="documents")
    unit        = models.ForeignKey("Unit", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents", help_text="Leave blank for property-level documents")
    document    = models.FileField(upload_to="properties/documents/")
    doc_type    = models.CharField(max_length=40, choices=DocType.choices, default=DocType.OTHER)
    name        = models.CharField(max_length=200, blank=True, help_text="Display name — auto-filled from filename if blank")
    notes       = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["doc_type", "-uploaded_at"]

    def save(self, *args, **kwargs):
        if not self.name and self.document:
            self.name = self.document.name.rsplit("/", 1)[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.name or self.property.name}"


# ── Compliance certificates ───────────────────────────────────────────────────

class ComplianceCertificate(models.Model):
    class CertType(models.TextChoices):
        ELECTRICAL = "electrical", "Electrical CoC"
        PEST       = "pest",       "Pest (Woodborer) Clearance"
        GAS        = "gas",        "Gas CoC"
        PLUMBING   = "plumbing",   "Plumbing CoC"
        FENCE      = "fence",      "Electric Fence CoC"
        SOLAR      = "solar",      "Solar Installation CoC"
        OTHER      = "other",      "Other"

    class Status(models.TextChoices):
        VALID   = "valid",   "Valid"
        EXPIRED = "expired", "Expired"
        PENDING = "pending", "Pending Renewal"

    property         = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="compliance_certs")
    cert_type        = models.CharField(max_length=20, choices=CertType.choices)
    certificate_number = models.CharField(max_length=50, blank=True)
    issued_date      = models.DateField()
    expiry_date      = models.DateField(null=True, blank=True, help_text="Leave blank if no fixed expiry (e.g. pest clearance)")
    contractor_name  = models.CharField(max_length=200, blank=True)
    contractor_phone = models.CharField(max_length=30, blank=True)
    contractor_email = models.EmailField(blank=True)
    registration_number = models.CharField(max_length=50, blank=True, help_text="Contractor's DoL/DoE registration number")
    document         = models.FileField(upload_to="properties/compliance/", null=True, blank=True)
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def get_status(self) -> str:
        if not self.expiry_date:
            return self.Status.VALID
        return self.Status.VALID if self.expiry_date >= timezone.now().date() else self.Status.EXPIRED

    class Meta:
        ordering = ["-issued_date"]

    def __str__(self):
        return f"{self.get_cert_type_display()} — {self.property.name} ({self.issued_date})"


# ── Municipal / utility accounts ──────────────────────────────────────────────

class MunicipalAccount(models.Model):
    class AccountType(models.TextChoices):
        RATES      = "rates",      "Property Rates"
        WATER      = "water",      "Water"
        ELECTRICITY = "electricity", "Electricity"
        REFUSE     = "refuse",     "Refuse"
        SEWERAGE   = "sewerage",   "Sewerage"
        COMBINED   = "combined",   "Combined Municipal Account"

    property       = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="municipal_accounts")
    account_type   = models.CharField(max_length=20, choices=AccountType.choices)
    account_number = models.CharField(max_length=50)
    municipality   = models.CharField(max_length=100, blank=True)
    reference      = models.CharField(max_length=100, blank=True, help_text="Payment reference e.g. ERF 3587 STELL CLR")
    meter_number   = models.CharField(max_length=50, blank=True)
    in_tenant_name = models.BooleanField(default=False, help_text="True if currently billed to tenant")
    monthly_levy   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Estimated monthly charge")
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["account_type"]

    def __str__(self):
        return f"{self.get_account_type_display()} — {self.account_number} ({self.property.name})"


# ── Property valuation history ────────────────────────────────────────────────

class PropertyValuation(models.Model):
    class ValuationType(models.TextChoices):
        PURCHASE  = "purchase",  "Purchase Price"
        MUNICIPAL = "municipal", "Municipal Valuation"
        BANK      = "bank",      "Bank Valuation"
        AGENT     = "agent",     "Agent Estimate"
        FORMAL    = "formal",    "Formal Appraisal"

    property         = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="valuations")
    valuation_type   = models.CharField(max_length=20, choices=ValuationType.choices)
    amount           = models.DecimalField(max_digits=14, decimal_places=2)
    valuation_date   = models.DateField()
    valuator         = models.CharField(max_length=200, blank=True, help_text="Bank, agent, or firm name")
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valuation_date"]

    def __str__(self):
        return f"{self.get_valuation_type_display()} R{self.amount:,.0f} — {self.property.name} ({self.valuation_date})"


# ── Insurance ─────────────────────────────────────────────────────────────────

class InsurancePolicy(models.Model):
    class PolicyType(models.TextChoices):
        BUILDING   = "building",   "Building / Structure"
        CONTENTS   = "contents",   "Contents"
        COMBINED   = "combined",   "Building + Contents"
        LIABILITY  = "liability",  "Public Liability"
        LANDLORD   = "landlord",   "Landlord Insurance"
        OTHER      = "other",      "Other"

    property       = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="insurance_policies")
    policy_type    = models.CharField(max_length=20, choices=PolicyType.choices)
    insurer        = models.CharField(max_length=200, help_text="e.g. Outsurance, Santam, Momentum")
    policy_number  = models.CharField(max_length=100)
    broker         = models.CharField(max_length=200, blank=True)
    broker_email   = models.EmailField(blank=True)
    broker_phone   = models.CharField(max_length=30, blank=True)
    sum_insured    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, help_text="Replacement value insured")
    monthly_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    excess         = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Standard excess per claim")
    start_date     = models.DateField()
    end_date       = models.DateField(null=True, blank=True, help_text="Null = ongoing")
    is_active      = models.BooleanField(default=True)
    document       = models.FileField(upload_to="properties/insurance/policies/", null=True, blank=True)
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "-start_date"]

    def __str__(self):
        return f"{self.insurer} — {self.get_policy_type_display()} ({self.policy_number})"


class InsuranceClaim(models.Model):
    class ClaimType(models.TextChoices):
        STORM      = "storm",      "Storm / Wind / Hail"
        FIRE       = "fire",       "Fire"
        FLOOD      = "flood",      "Flood / Water Damage"
        THEFT      = "theft",      "Theft / Burglary"
        GEYSER     = "geyser",     "Geyser Burst"
        SUBSIDENCE = "subsidence", "Subsidence / Settling"
        LIABILITY  = "liability",  "Third-Party Liability"
        OTHER      = "other",      "Other"

    class Status(models.TextChoices):
        DRAFT      = "draft",      "Draft / Not Yet Submitted"
        SUBMITTED  = "submitted",  "Submitted"
        ASSESSING  = "assessing",  "Under Assessment"
        APPROVED   = "approved",   "Approved"
        REJECTED   = "rejected",   "Rejected"
        SETTLED    = "settled",    "Settled / Paid Out"
        WITHDRAWN  = "withdrawn",  "Withdrawn"

    policy         = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True, related_name="claims")
    property       = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="insurance_claims")
    unit           = models.ForeignKey("Unit", on_delete=models.SET_NULL, null=True, blank=True, related_name="insurance_claims")
    claim_type     = models.CharField(max_length=20, choices=ClaimType.choices)
    claim_number   = models.CharField(max_length=100, blank=True, help_text="Insurer's claim reference number")
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    incident_date  = models.DateField()
    submitted_date = models.DateField(null=True, blank=True)
    settled_date   = models.DateField(null=True, blank=True)
    claimed_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    excess_paid    = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    settlement_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Amount actually paid by insurer")
    description    = models.TextField(help_text="What happened — used for claim submission and RAG context")
    document       = models.FileField(upload_to="properties/insurance/claims/", null=True, blank=True, help_text="Claim form or insurer correspondence")
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-incident_date"]

    def __str__(self):
        return f"{self.get_claim_type_display()} claim — {self.property.name} ({self.incident_date}) [{self.status}]"


# ── Municipal bills ───────────────────────────────────────────────────────────

class MunicipalBill(models.Model):
    class PaymentStatus(models.TextChoices):
        UNPAID  = "unpaid",  "Unpaid"
        PAID    = "paid",    "Paid"
        OVERDUE = "overdue", "Overdue"
        PARTIAL = "partial", "Partially Paid"
        DISPUTE = "dispute", "In Dispute"

    property        = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="municipal_bills")
    municipal_account = models.ForeignKey(MunicipalAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name="bills")
    account_number  = models.CharField(max_length=50, blank=True, help_text="Copied from account if blank")

    # Billing period
    billing_month   = models.PositiveSmallIntegerField(help_text="1–12")
    billing_year    = models.PositiveSmallIntegerField()

    # Amounts (line items — mirrors Stellenbosch municipality bill layout)
    rates_amount      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    water_amount      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    electricity_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    refuse_amount     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sewerage_amount   = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    other_amount      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_amount      = models.DecimalField(max_digits=10, decimal_places=2)

    # Payment
    payment_status  = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    due_date        = models.DateField(null=True, blank=True)
    paid_date       = models.DateField(null=True, blank=True)
    paid_amount     = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)

    # Storage
    document        = models.FileField(upload_to="properties/municipal_bills/", null=True, blank=True, help_text="Scanned/downloaded bill PDF")
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-billing_year", "-billing_month"]
        unique_together = [("property", "municipal_account", "billing_year", "billing_month")]

    def __str__(self):
        return f"Municipal bill {self.billing_year}-{self.billing_month:02d} — {self.property.name} (R{self.total_amount})"


# ── Property Viewings ─────────────────────────────────────────────────────────

class PropertyViewing(models.Model):
    """
    A scheduled property viewing appointment between an agent and a prospective tenant.
    Can be converted into a Lease once the prospect decides to proceed.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        CONVERTED = "converted", "Converted to Lease"

    property           = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="viewings")
    unit               = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True, related_name="viewings")
    prospect           = models.ForeignKey("accounts.Person", on_delete=models.PROTECT, related_name="viewings_as_prospect")
    agent              = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="viewings_as_agent")
    scheduled_at       = models.DateTimeField()
    duration_minutes   = models.PositiveSmallIntegerField(default=30)
    status             = models.CharField(max_length=15, choices=Status.choices, default=Status.SCHEDULED)
    notes              = models.TextField(blank=True)
    converted_to_lease = models.OneToOneField(
        "leases.Lease",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="source_viewing",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]

    def __str__(self):
        return f"Viewing: {self.prospect} @ {self.property.name} on {self.scheduled_at:%Y-%m-%d %H:%M}"


class PropertyAgentAssignment(models.Model):
    """
    Links an agent to a property with a specific role.
    Estate agents get transaction-only access that ends on completion.
    Managing agents get ongoing operational access.
    Replaces the flat Property.agent FK for fine-grained access control.
    """

    class AssignmentType(models.TextChoices):
        ESTATE = "estate", "Estate Agent (transaction)"
        MANAGING = "managing", "Managing Agent (ongoing)"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        INACTIVE = "inactive", "Inactive"

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="agent_assignments",
    )
    agent = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="property_assignments",
    )
    mandate = models.ForeignKey(
        "properties.RentalMandate", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="agent_assignments",
        help_text="Mandate under which this assignment was made",
    )
    assignment_type = models.CharField(max_length=20, choices=AssignmentType.choices)
    assigned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, related_name="+",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("property", "agent")
        indexes = [
            models.Index(fields=["agent", "status"]),
            models.Index(fields=["property", "status"]),
        ]

    def __str__(self):
        return f"{self.agent} → {self.property.name} ({self.assignment_type}/{self.status})"
