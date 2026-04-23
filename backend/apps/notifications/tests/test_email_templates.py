import pytest
from apps.notifications.services.email import render_template_email


def test_invite_tenant_template_contains_72_hours():
    """invite_tenant must mention '72 hours' in the body."""
    subject, plaintext, html = render_template_email(
        'invite_tenant',
        {
            'recipient_name': 'John Doe',
            'property_address': '123 Main St, Cape Town',
            'invite_url': 'https://app.klikk.co.za/invite/abc123',
        }
    )
    assert '72 hours' in plaintext, f"Missing '72 hours' in plaintext:\n{plaintext}"
    assert '72 hours' in html, f"Missing '72 hours' in HTML"


def test_invite_tenant_template_describes_klikk():
    """invite_tenant must explain Klikk in plain language."""
    subject, plaintext, html = render_template_email(
        'invite_tenant',
        {
            'recipient_name': 'John Doe',
            'property_address': '123 Main St, Cape Town',
            'invite_url': 'https://app.klikk.co.za/invite/abc123',
        }
    )
    # Should mention what Klikk lets you do
    assert 'lease' in plaintext.lower(), f"Missing 'lease' mention in:\n{plaintext}"
    assert 'rent' in plaintext.lower(), f"Missing 'rent' mention in:\n{plaintext}"
    assert 'Klikk' in plaintext, f"Missing 'Klikk' name in:\n{plaintext}"


def test_invite_tenant_template_parses():
    """invite_tenant template should parse without errors."""
    subject, plaintext, html = render_template_email(
        'invite_tenant',
        {
            'recipient_name': 'John Doe',
            'property_address': '123 Main St, Cape Town',
            'invite_url': 'https://app.klikk.co.za/invite/abc123',
        }
    )
    assert subject, "Subject should not be empty"
    assert plaintext, "Plaintext should not be empty"
    assert html, "HTML should not be empty"


def test_welcome_tenant_cta_is_correct():
    """welcome_tenant CTA must be 'Go to your portal', not 'View your lease'."""
    subject, plaintext, html = render_template_email(
        'welcome_tenant',
        {
            'recipient_name': 'Jane Doe',
            'portal_url': 'https://app.klikk.co.za/dashboard',
        }
    )
    assert 'Go to your portal' in plaintext, f"Missing 'Go to your portal' CTA in:\n{plaintext}"
    assert 'Go to your portal' in html, f"Missing 'Go to your portal' CTA in HTML"
    # Should NOT say "View your lease"
    assert 'View your lease' not in plaintext, "Old CTA 'View your lease' still present"


def test_welcome_tenant_template_parses():
    """welcome_tenant template should parse without errors."""
    subject, plaintext, html = render_template_email(
        'welcome_tenant',
        {
            'recipient_name': 'Jane Doe',
            'portal_url': 'https://app.klikk.co.za/dashboard',
        }
    )
    assert subject, "Subject should not be empty"
    assert plaintext, "Plaintext should not be empty"
    assert html, "HTML should not be empty"
