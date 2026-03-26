import graphene
from graphene_django import DjangoObjectType

from apps.accounts.models import Person
from apps.leases.models import Lease, LeaseTemplate
from apps.properties.models import Property, Unit


# ---------------------------------------------------------------------------
# Object types
# ---------------------------------------------------------------------------

class PersonType(DjangoObjectType):
    """A natural person or company involved in property transactions."""

    class Meta:
        model = Person
        fields = (
            "id", "person_type", "full_name", "id_number", "phone", "email",
            "company_reg", "vat_number", "created_at",
        )


class IndividualOwner(graphene.ObjectType):
    """Owner who is a natural person."""
    id = graphene.ID(required=True)
    full_name = graphene.String(required=True)
    id_number = graphene.String()
    phone = graphene.String()
    email = graphene.String()


class CompanyOwner(graphene.ObjectType):
    """Owner who is a registered company."""
    id = graphene.ID(required=True)
    full_name = graphene.String(required=True)
    company_reg = graphene.String()
    vat_number = graphene.String()
    phone = graphene.String()
    email = graphene.String()


class Owner(graphene.Union):
    """
    Property ownership can be either an individual person or a company.
    Both are stored in the Person model, distinguished by person_type.
    """

    class Meta:
        types = (IndividualOwner, CompanyOwner)


class UnitType(DjangoObjectType):
    class Meta:
        model = Unit
        fields = (
            "id", "unit_number", "bedrooms", "bathrooms",
            "rent_amount", "status", "floor", "leases",
        )


class PropertyType(DjangoObjectType):
    owner = graphene.Field(Owner)

    class Meta:
        model = Property
        fields = (
            "id", "name", "property_type", "address", "city",
            "province", "postal_code", "description", "image",
            "units", "created_at",
        )

    def resolve_owner(self, info):
        owner = self.owner
        if owner is None:
            return None
        if owner.person_type == Person.PersonType.COMPANY:
            return CompanyOwner(
                id=owner.id,
                full_name=owner.full_name,
                company_reg=owner.company_reg,
                vat_number=owner.vat_number,
                phone=owner.phone,
                email=owner.email,
            )
        return IndividualOwner(
            id=owner.id,
            full_name=owner.full_name,
            id_number=owner.id_number,
            phone=owner.phone,
            email=owner.email,
        )


class LeaseType(DjangoObjectType):
    primary_tenant = graphene.Field(PersonType)

    class Meta:
        model = Lease
        fields = (
            "id", "unit", "primary_tenant", "start_date", "end_date",
            "monthly_rent", "deposit", "status", "max_occupants",
            "water_included", "water_limit_litres", "electricity_prepaid",
            "notice_period_days", "early_termination_penalty_months",
            "lease_number", "payment_reference", "created_at",
        )


class LeaseTemplateType(DjangoObjectType):
    class Meta:
        model = LeaseTemplate
        fields = (
            "id", "name", "version", "province", "docx_file",
            "fields_schema", "content_html", "header_html", "footer_html",
            "is_active", "created_at",
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class Query(graphene.ObjectType):
    lease_template = graphene.Field(LeaseTemplateType, id=graphene.ID(required=True))
    all_lease_templates = graphene.List(graphene.NonNull(LeaseTemplateType))

    lease = graphene.Field(LeaseType, id=graphene.ID(required=True))
    all_leases = graphene.List(graphene.NonNull(LeaseType))

    property = graphene.Field(PropertyType, id=graphene.ID(required=True))
    all_properties = graphene.List(graphene.NonNull(PropertyType))

    def resolve_lease_template(self, info, id):
        return LeaseTemplate.objects.filter(pk=id).first()

    def resolve_all_lease_templates(self, info):
        return LeaseTemplate.objects.all()

    def resolve_lease(self, info, id):
        return Lease.objects.select_related("unit", "primary_tenant").filter(pk=id).first()

    def resolve_all_leases(self, info):
        return Lease.objects.select_related("unit", "primary_tenant").all()

    def resolve_property(self, info, id):
        return Property.objects.select_related("owner").prefetch_related("units").filter(pk=id).first()

    def resolve_all_properties(self, info):
        return Property.objects.select_related("owner").prefetch_related("units").all()


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

class LeaseTemplateInput(graphene.InputObjectType):
    name = graphene.String()
    version = graphene.String()
    province = graphene.String()
    fields_schema = graphene.JSONString()
    content_html = graphene.String()
    header_html = graphene.String()
    footer_html = graphene.String()
    is_active = graphene.Boolean()


class CreateLeaseTemplate(graphene.Mutation):
    class Arguments:
        input = LeaseTemplateInput(required=True)

    lease_template = graphene.Field(LeaseTemplateType)

    def mutate(self, info, input):
        data = {k: v for k, v in input.items() if v is not None}
        template = LeaseTemplate.objects.create(**data)
        return CreateLeaseTemplate(lease_template=template)


class UpdateLeaseTemplate(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        input = LeaseTemplateInput(required=True)

    lease_template = graphene.Field(LeaseTemplateType)

    def mutate(self, info, id, input):
        template = LeaseTemplate.objects.get(pk=id)
        for key, value in input.items():
            if value is not None:
                setattr(template, key, value)
        template.save()
        return UpdateLeaseTemplate(lease_template=template)


class Mutation(graphene.ObjectType):
    create_lease_template = CreateLeaseTemplate.Field()
    update_lease_template = UpdateLeaseTemplate.Field()
