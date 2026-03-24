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


class PropertyGroup(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    properties = models.ManyToManyField(Property, related_name="groups", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
