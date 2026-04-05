"""Unit tests for apps/leases/schema.py — GraphQL type and query definitions."""
import pytest


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# The schema.py file defines GraphQL types and resolvers (not a pure utility
# module with free functions).  These tests verify the structure is importable
# and the Query object exposes the expected fields.
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_schema_imports_without_error():
    """schema.py should import cleanly (no missing dependencies at import time)."""
    import apps.leases.schema  # noqa: F401


@pytest.mark.green
def test_query_has_all_leases():
    """Query object must expose an all_leases resolver field."""
    from apps.leases.schema import Query
    assert hasattr(Query, "resolve_all_leases")


@pytest.mark.green
def test_query_has_lease_templates():
    """Query object must expose lease template resolvers."""
    from apps.leases.schema import Query
    assert hasattr(Query, "resolve_all_lease_templates")
    assert hasattr(Query, "resolve_lease_template")


@pytest.mark.green
def test_query_has_builder_session():
    """Query object must expose builder session resolvers."""
    from apps.leases.schema import Query
    assert hasattr(Query, "resolve_builder_session")
    assert hasattr(Query, "resolve_all_builder_sessions")


@pytest.mark.green
def test_query_has_signing_submission():
    """Query object must expose e-signing submission resolvers."""
    from apps.leases.schema import Query
    assert hasattr(Query, "resolve_signing_submission")
    assert hasattr(Query, "resolve_signing_submissions_for_lease")


@pytest.mark.green
def test_query_has_lifecycle_resolvers():
    """Query object must expose lifecycle resolvers (events, steps, docs, tenants, occupants)."""
    from apps.leases.schema import Query
    assert hasattr(Query, "resolve_lease_events")
    assert hasattr(Query, "resolve_onboarding_steps")
    assert hasattr(Query, "resolve_lease_documents")
    assert hasattr(Query, "resolve_lease_co_tenants")
    assert hasattr(Query, "resolve_lease_occupants")


@pytest.mark.green
def test_mutation_has_lease_template_mutations():
    """Mutation object must expose create and update lease template mutations."""
    from apps.leases.schema import Mutation
    assert hasattr(Mutation, "create_lease_template")
    assert hasattr(Mutation, "update_lease_template")


@pytest.mark.green
def test_mutation_has_update_lease_status():
    """Mutation object must expose update_lease_status."""
    from apps.leases.schema import Mutation
    assert hasattr(Mutation, "update_lease_status")


@pytest.mark.green
def test_mutation_has_complete_onboarding_step():
    """Mutation object must expose complete_onboarding_step."""
    from apps.leases.schema import Mutation
    assert hasattr(Mutation, "complete_onboarding_step")


@pytest.mark.green
def test_property_type_has_owner_resolver():
    """PropertyType must expose a resolve_owner method for the union type."""
    from apps.leases.schema import PropertyType
    assert hasattr(PropertyType, "resolve_owner")


@pytest.mark.green
def test_owner_union_types():
    """Owner union must include both IndividualOwner and CompanyOwner."""
    from apps.leases.schema import Owner, IndividualOwner, CompanyOwner
    assert IndividualOwner in Owner._meta.types
    assert CompanyOwner in Owner._meta.types
