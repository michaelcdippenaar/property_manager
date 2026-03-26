import graphene
from graphene_django import DjangoObjectType

from apps.accounts.models import Person
from apps.esigning.models import ESigningSubmission
from apps.leases.models import (
    Lease, LeaseTemplate, LeaseBuilderSession,
    LeaseTenant, LeaseOccupant, LeaseEvent, OnboardingStep, LeaseDocument,
)
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
# Lifecycle types
# ---------------------------------------------------------------------------

class LeaseBuilderSessionType(DjangoObjectType):
    class Meta:
        model = LeaseBuilderSession
        fields = (
            "id", "template", "lease", "messages", "current_state",
            "rha_flags", "status", "created_at", "updated_at",
        )


class LeaseTenantType(DjangoObjectType):
    class Meta:
        model = LeaseTenant
        fields = ("id", "lease", "person")


class LeaseOccupantType(DjangoObjectType):
    class Meta:
        model = LeaseOccupant
        fields = ("id", "lease", "person", "relationship_to_tenant")


class LeaseEventType(DjangoObjectType):
    class Meta:
        model = LeaseEvent
        fields = (
            "id", "lease", "event_type", "title", "description", "date",
            "status", "is_recurring", "recurrence_day",
            "completed_at", "created_at",
        )


class OnboardingStepType(DjangoObjectType):
    class Meta:
        model = OnboardingStep
        fields = (
            "id", "lease", "step_type", "title", "is_completed",
            "completed_at", "notes", "order",
        )


class LeaseDocumentType(DjangoObjectType):
    class Meta:
        model = LeaseDocument
        fields = ("id", "lease", "document_type", "file", "description", "uploaded_at")


class ESigningSubmissionType(DjangoObjectType):
    class Meta:
        model = ESigningSubmission
        fields = (
            "id", "lease", "docuseal_submission_id", "docuseal_template_id",
            "status", "signing_mode", "signers", "signed_pdf_url",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class Query(graphene.ObjectType):
    # Templates
    lease_template = graphene.Field(LeaseTemplateType, id=graphene.ID(required=True))
    all_lease_templates = graphene.List(graphene.NonNull(LeaseTemplateType))

    # Leases
    lease = graphene.Field(LeaseType, id=graphene.ID(required=True))
    all_leases = graphene.List(graphene.NonNull(LeaseType), status=graphene.String())

    # Properties
    property = graphene.Field(PropertyType, id=graphene.ID(required=True))
    all_properties = graphene.List(graphene.NonNull(PropertyType))

    # Builder sessions
    builder_session = graphene.Field(LeaseBuilderSessionType, id=graphene.ID(required=True))
    all_builder_sessions = graphene.List(graphene.NonNull(LeaseBuilderSessionType), status=graphene.String())

    # E-signing
    signing_submission = graphene.Field(ESigningSubmissionType, id=graphene.ID(required=True))
    signing_submissions_for_lease = graphene.List(
        graphene.NonNull(ESigningSubmissionType), lease_id=graphene.ID(required=True)
    )

    # Lease lifecycle details
    lease_events = graphene.List(graphene.NonNull(LeaseEventType), lease_id=graphene.ID(required=True))
    onboarding_steps = graphene.List(graphene.NonNull(OnboardingStepType), lease_id=graphene.ID(required=True))
    lease_documents = graphene.List(graphene.NonNull(LeaseDocumentType), lease_id=graphene.ID(required=True))
    lease_co_tenants = graphene.List(graphene.NonNull(LeaseTenantType), lease_id=graphene.ID(required=True))
    lease_occupants = graphene.List(graphene.NonNull(LeaseOccupantType), lease_id=graphene.ID(required=True))

    # --- Resolvers ---

    def resolve_lease_template(self, info, id):
        return LeaseTemplate.objects.filter(pk=id).first()

    def resolve_all_lease_templates(self, info):
        return LeaseTemplate.objects.all()

    def resolve_lease(self, info, id):
        return Lease.objects.select_related("unit", "unit__property", "primary_tenant").filter(pk=id).first()

    def resolve_all_leases(self, info, status=None):
        qs = Lease.objects.select_related("unit", "primary_tenant")
        if status:
            qs = qs.filter(status=status)
        return qs.all()

    def resolve_property(self, info, id):
        return Property.objects.select_related("owner").prefetch_related("units").filter(pk=id).first()

    def resolve_all_properties(self, info):
        return Property.objects.select_related("owner").prefetch_related("units").all()

    def resolve_builder_session(self, info, id):
        return LeaseBuilderSession.objects.select_related("template", "lease").filter(pk=id).first()

    def resolve_all_builder_sessions(self, info, status=None):
        qs = LeaseBuilderSession.objects.select_related("template", "lease")
        if status:
            qs = qs.filter(status=status)
        return qs.all()

    def resolve_signing_submission(self, info, id):
        return ESigningSubmission.objects.select_related("lease").filter(pk=id).first()

    def resolve_signing_submissions_for_lease(self, info, lease_id):
        return ESigningSubmission.objects.filter(lease_id=lease_id).all()

    def resolve_lease_events(self, info, lease_id):
        return LeaseEvent.objects.filter(lease_id=lease_id).all()

    def resolve_onboarding_steps(self, info, lease_id):
        return OnboardingStep.objects.filter(lease_id=lease_id).order_by("order").all()

    def resolve_lease_documents(self, info, lease_id):
        return LeaseDocument.objects.filter(lease_id=lease_id).all()

    def resolve_lease_co_tenants(self, info, lease_id):
        return LeaseTenant.objects.select_related("person").filter(lease_id=lease_id).all()

    def resolve_lease_occupants(self, info, lease_id):
        return LeaseOccupant.objects.select_related("person").filter(lease_id=lease_id).all()


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


class UpdateBuilderSession(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        status = graphene.String()
        current_state = graphene.JSONString()
        rha_flags = graphene.JSONString()

    builder_session = graphene.Field(LeaseBuilderSessionType)

    def mutate(self, info, id, **kwargs):
        session = LeaseBuilderSession.objects.get(pk=id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(session, key, value)
        session.save()
        return UpdateBuilderSession(builder_session=session)


class UpdateLeaseStatus(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        status = graphene.String(required=True)

    lease = graphene.Field(LeaseType)

    def mutate(self, info, id, status):
        lease = Lease.objects.get(pk=id)
        lease.status = status
        lease.save(update_fields=["status"])
        return UpdateLeaseStatus(lease=lease)


class CompleteOnboardingStep(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        notes = graphene.String()

    step = graphene.Field(OnboardingStepType)

    def mutate(self, info, id, notes=None):
        from django.utils import timezone
        step = OnboardingStep.objects.get(pk=id)
        step.is_completed = True
        step.completed_at = timezone.now()
        if notes:
            step.notes = notes
        step.save()
        return CompleteOnboardingStep(step=step)


class Mutation(graphene.ObjectType):
    create_lease_template = CreateLeaseTemplate.Field()
    update_lease_template = UpdateLeaseTemplate.Field()
    update_builder_session = UpdateBuilderSession.Field()
    update_lease_status = UpdateLeaseStatus.Field()
    complete_onboarding_step = CompleteOnboardingStep.Field()
