from django.db import models
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
    bathrooms = models.PositiveSmallIntegerField(default=1)
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AVAILABLE)
    floor = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.property.name} — Unit {self.unit_number}"


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


class PropertyOwnership(models.Model):
    """
    Tracks ownership of a property over time.
    A property can change owners (e.g. sold), and existing leases
    remain linked to the ownership record that was active when signed.
    """
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="ownerships")

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


class PropertyGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    properties = models.ManyToManyField(Property, related_name="groups", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
