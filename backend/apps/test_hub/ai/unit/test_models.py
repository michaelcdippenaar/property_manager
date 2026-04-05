"""Unit tests for apps/ai/models.py — TenantChatSession and TenantIntelligence."""
import pytest


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# TenantChatSession
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_tenant_chat_session_str():
    """TenantChatSession.__str__ returns title and user_id."""
    from apps.ai.models import TenantChatSession
    from django.db.models.base import ModelState
    session = TenantChatSession.__new__(TenantChatSession)
    session._state = ModelState()
    session.title = "Kitchen Leak"
    session.user_id = 7
    result = str(session)
    assert "Kitchen Leak" in result
    assert "7" in result


@pytest.mark.green
def test_tenant_chat_session_title_default():
    """TenantChatSession.title should default to 'AI Assistant'."""
    from apps.ai.models import TenantChatSession
    field = TenantChatSession._meta.get_field("title")
    assert field.default == "AI Assistant"


@pytest.mark.green
def test_tenant_chat_session_messages_default_is_list():
    """TenantChatSession.messages should default to list."""
    from apps.ai.models import TenantChatSession
    field = TenantChatSession._meta.get_field("messages")
    assert field.default is list


@pytest.mark.green
def test_tenant_chat_session_maintenance_report_suggested_default():
    """TenantChatSession.maintenance_report_suggested should default to False."""
    from apps.ai.models import TenantChatSession
    field = TenantChatSession._meta.get_field("maintenance_report_suggested")
    assert field.default is False


@pytest.mark.green
def test_tenant_chat_session_maintenance_request_nullable():
    """TenantChatSession.maintenance_request FK must be nullable."""
    from apps.ai.models import TenantChatSession
    field = TenantChatSession._meta.get_field("maintenance_request")
    assert field.null is True


@pytest.mark.green
def test_tenant_chat_session_agent_question_nullable():
    """TenantChatSession.agent_question FK must be nullable."""
    from apps.ai.models import TenantChatSession
    field = TenantChatSession._meta.get_field("agent_question")
    assert field.null is True


# ---------------------------------------------------------------------------
# TenantIntelligence
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_tenant_intelligence_str():
    """TenantIntelligence.__str__ returns TenantIntel(user_id)."""
    from apps.ai.models import TenantIntelligence
    from django.db.models.base import ModelState
    intel = TenantIntelligence.__new__(TenantIntelligence)
    intel._state = ModelState()
    intel.user_id = 99
    result = str(intel)
    assert "99" in result
    assert "TenantIntel" in result


@pytest.mark.green
def test_tenant_intelligence_total_chats_default():
    """TenantIntelligence.total_chats should default to 0."""
    from apps.ai.models import TenantIntelligence
    field = TenantIntelligence._meta.get_field("total_chats")
    assert field.default == 0


@pytest.mark.green
def test_tenant_intelligence_total_messages_default():
    """TenantIntelligence.total_messages should default to 0."""
    from apps.ai.models import TenantIntelligence
    field = TenantIntelligence._meta.get_field("total_messages")
    assert field.default == 0


@pytest.mark.green
def test_tenant_intelligence_complaint_score_default():
    """TenantIntelligence.complaint_score should default to 0.0."""
    from apps.ai.models import TenantIntelligence
    field = TenantIntelligence._meta.get_field("complaint_score")
    assert field.default == 0.0


@pytest.mark.green
def test_tenant_intelligence_facts_default():
    """TenantIntelligence.facts should default to dict."""
    from apps.ai.models import TenantIntelligence
    field = TenantIntelligence._meta.get_field("facts")
    assert field.default is dict


@pytest.mark.green
def test_tenant_intelligence_question_categories_default():
    """TenantIntelligence.question_categories should default to dict."""
    from apps.ai.models import TenantIntelligence
    field = TenantIntelligence._meta.get_field("question_categories")
    assert field.default is dict


@pytest.mark.green
def test_tenant_intelligence_property_ref_nullable():
    """TenantIntelligence.property_ref FK must be nullable."""
    from apps.ai.models import TenantIntelligence
    field = TenantIntelligence._meta.get_field("property_ref")
    assert field.null is True


@pytest.mark.green
def test_tenant_intelligence_unit_ref_nullable():
    """TenantIntelligence.unit_ref FK must be nullable."""
    from apps.ai.models import TenantIntelligence
    field = TenantIntelligence._meta.get_field("unit_ref")
    assert field.null is True
