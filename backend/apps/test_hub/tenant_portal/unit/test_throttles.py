"""Unit tests for TenantChatThrottle and TenantDraftThrottle rate limiters."""
import pytest


pytestmark = pytest.mark.unit


@pytest.mark.green
def test_tenant_chat_throttle_rate():
    """TenantChatThrottle must enforce 10 requests per minute."""
    from apps.tenant_portal.views import TenantChatThrottle
    assert TenantChatThrottle.rate == "10/min"


@pytest.mark.green
def test_tenant_chat_throttle_scope():
    """TenantChatThrottle must use scope 'tenant_chat'."""
    from apps.tenant_portal.views import TenantChatThrottle
    assert TenantChatThrottle.scope == "tenant_chat"


@pytest.mark.green
def test_tenant_draft_throttle_rate():
    """TenantDraftThrottle must enforce 5 requests per minute."""
    from apps.tenant_portal.views import TenantDraftThrottle
    assert TenantDraftThrottle.rate == "5/min"


@pytest.mark.green
def test_tenant_draft_throttle_scope():
    """TenantDraftThrottle must use scope 'tenant_draft'."""
    from apps.tenant_portal.views import TenantDraftThrottle
    assert TenantDraftThrottle.scope == "tenant_draft"


@pytest.mark.green
def test_tenant_chat_throttle_is_user_rate_throttle():
    """TenantChatThrottle must be a subclass of UserRateThrottle."""
    from rest_framework.throttling import UserRateThrottle
    from apps.tenant_portal.views import TenantChatThrottle
    assert issubclass(TenantChatThrottle, UserRateThrottle)


@pytest.mark.green
def test_tenant_draft_throttle_is_user_rate_throttle():
    """TenantDraftThrottle must be a subclass of UserRateThrottle."""
    from rest_framework.throttling import UserRateThrottle
    from apps.tenant_portal.views import TenantDraftThrottle
    assert issubclass(TenantDraftThrottle, UserRateThrottle)


@pytest.mark.green
def test_tenant_chat_throttle_lower_than_draft():
    """
    RED: This test documents a design question — should chat (10/min) be
    higher than draft (5/min)?  Currently chat > draft which is intentional
    (drafts are expensive AI calls).  If the rates are reversed this test
    will catch the regression.

    Marked red because the 'correct' rate is an opinion, not a hard fact.
    """
    from apps.tenant_portal.views import TenantChatThrottle, TenantDraftThrottle

    def _rate_num(rate_str: str) -> int:
        return int(rate_str.split("/")[0])

    chat_rate = _rate_num(TenantChatThrottle.rate)
    draft_rate = _rate_num(TenantDraftThrottle.rate)
    assert chat_rate > draft_rate, (
        f"Expected chat rate ({chat_rate}) > draft rate ({draft_rate}); "
        "drafts are expensive so draft throttle should be tighter"
    )


@pytest.mark.green
def test_max_chat_window_constant():
    """MAX_CHAT_WINDOW must be defined and be a positive integer."""
    from apps.tenant_portal.views import MAX_CHAT_WINDOW
    assert isinstance(MAX_CHAT_WINDOW, int)
    assert MAX_CHAT_WINDOW > 0
