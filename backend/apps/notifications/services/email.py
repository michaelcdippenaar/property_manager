"""
Branded transactional email renderer for Klikk.

Usage::

    from apps.notifications.services.email import send_template_email

    send_template_email(
        template_id="welcome_agent",
        to_emails="agent@example.com",
        context={
            "recipient_name": "Sipho",
            "dashboard_url": "https://app.klikk.co.za/dashboard",
        },
    )

Template content (subject, heading, body copy) lives in ``content/emails/<template_id>.md``.
HTML layout is ``backend/apps/notifications/email_templates/compiled/base.html``,
pre-compiled from MJML.

Context variables available in all templates:
  - ``recipient_name`` (str) — used in greeting line
  - ``current_year`` (int) — auto-injected
  - ``unsubscribe_url`` (str, optional) — renders unsubscribe link in footer
  - Any template-specific variables (e.g. ``property_address``, ``cta_url``)

Content .md frontmatter keys:
  - ``subject`` — email subject line (supports ``{{ var }}`` placeholders)
  - ``heading`` — large heading in card (supports ``{{ var }}`` placeholders)
  - ``cta_label`` — button label (optional, omit or empty string to hide button)
  - ``cta_url_key`` — name of the context key whose value becomes the button href
  - ``note`` — small text below button (optional)
"""
from __future__ import annotations

import logging
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from django.template import Context, Engine
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_CONTENT_EMAIL_DIR = Path(__file__).resolve().parents[4] / "content" / "emails"
_COMPILED_HTML = (
    Path(__file__).resolve().parents[1]
    / "email_templates"
    / "compiled"
    / "base.html"
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_base_html() -> str:
    """Load the pre-compiled MJML base HTML (cached at module level after first read)."""
    if not hasattr(_load_base_html, "_cache"):
        _load_base_html._cache = _COMPILED_HTML.read_text(encoding="utf-8")
    return _load_base_html._cache  # type: ignore[attr-defined]


def _parse_md(template_id: str) -> dict[str, str]:
    """
    Parse ``content/emails/<template_id>.md`` and return a dict with keys:
    ``subject``, ``heading``, ``cta_label``, ``cta_url_key``, ``note``, ``body``.
    """
    path = _CONTENT_EMAIL_DIR / f"{template_id}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Email content file not found: {path}. "
            f"Create content/emails/{template_id}.md to define this template."
        )

    raw = path.read_text(encoding="utf-8")
    # Split YAML frontmatter from body
    fm: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].splitlines():
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    fm[key.strip()] = val.strip().strip('"')
            body = parts[2].strip()

    return {
        "subject": fm.get("subject", f"Notification from Klikk"),
        "heading": fm.get("heading", ""),
        "cta_label": fm.get("cta_label", ""),
        "cta_url_key": fm.get("cta_url_key", ""),
        "note": fm.get("note", ""),
        "body": body,
    }


def _simple_md_to_html(text: str) -> str:
    """
    Minimal markdown-to-HTML converter for email body text.
    Supports: **bold**, paragraphs separated by blank lines.
    """
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Split into paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paragraphs)


def _render_string(template_str: str, context: dict[str, Any]) -> str:
    """Render a Django template string with the given context."""
    engine = Engine.get_default()
    from django.template import Template
    t = Template(template_str)
    return t.render(Context(context))


def _build_plaintext(
    heading: str,
    recipient_name: str,
    body: str,
    cta_label: str,
    cta_url: str,
    note: str,
) -> str:
    """Generate a plaintext alternative from the template fields."""
    lines = [
        f"Klikk",
        "=" * 40,
        "",
        heading,
        "",
        f"Hi {recipient_name},",
        "",
        body,
        "",
    ]
    if cta_url:
        lines += [f"{cta_label}: {cta_url}", ""]
    if note:
        lines += [note, ""]
    lines += [
        "-" * 40,
        "POPIA Information Officer: privacy@klikk.co.za",
        "Klikk (Pty) Ltd, South Africa",
        "https://klikk.co.za/privacy | https://klikk.co.za/terms",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_template_email(
    template_id: str,
    context: dict[str, Any],
) -> tuple[str, str, str]:
    """
    Render a transactional email.

    Returns ``(subject, plaintext_body, html_body)``.

    :param template_id: matches ``content/emails/<template_id>.md``
    :param context: dict of variables merged into the template
    """
    md = _parse_md(template_id)

    recipient_name = context.get("recipient_name", "there")
    current_year = context.get("current_year", date.today().year)
    unsubscribe_url = context.get("unsubscribe_url", "")

    # Resolve CTA URL from context via cta_url_key
    cta_url = ""
    cta_url_key = md.get("cta_url_key", "")
    if cta_url_key:
        cta_url = context.get(cta_url_key, "")
    # Allow caller to override directly
    if not cta_url:
        cta_url = context.get("cta_url", "")

    # Build the full render context
    render_ctx: dict[str, Any] = {
        **context,
        "recipient_name": recipient_name,
        "current_year": current_year,
        "unsubscribe_url": unsubscribe_url,
        "heading": md["heading"],
        "body_text": _simple_md_to_html(md["body"]),
        "cta_label": md["cta_label"],
        "cta_url": cta_url,
        "note": md["note"],
    }

    # Subject and heading support {{ var }} placeholders from context
    subject = _render_string(md["subject"], render_ctx)
    render_ctx["heading"] = _render_string(md["heading"], render_ctx)

    # Render note and body with placeholders
    render_ctx["note"] = _render_string(md["note"], render_ctx)
    raw_body_rendered = _render_string(md["body"], render_ctx)
    render_ctx["body_text"] = mark_safe(_simple_md_to_html(raw_body_rendered))

    # Render full HTML
    base_html = _load_base_html()
    html_body = _render_string(base_html, render_ctx)

    # Plaintext fallback
    plaintext = _build_plaintext(
        heading=render_ctx["heading"],
        recipient_name=str(recipient_name),
        body=raw_body_rendered,
        cta_label=str(md["cta_label"]),
        cta_url=str(cta_url),
        note=str(render_ctx["note"]),
    )

    return subject, plaintext, html_body


def send_template_email(
    template_id: str,
    to_emails: str | Sequence[str],
    context: dict[str, Any] | None = None,
    *,
    from_email: str | None = None,
) -> bool:
    """
    Render and send a transactional email using a Klikk branded template.

    :param template_id: matches ``content/emails/<template_id>.md``
    :param to_emails: recipient email address(es)
    :param context: template variables
    :param from_email: override sender (defaults to ``DEFAULT_FROM_EMAIL``)
    :returns: ``True`` if the email was handed to the mail backend without error
    """
    from apps.notifications.services import send_email  # noqa: PLC0415 (avoids circular)

    ctx = context or {}
    try:
        subject, plaintext, html_body = render_template_email(template_id, ctx)
    except FileNotFoundError:
        logger.exception("Email template not found: %s", template_id)
        return False
    except Exception:
        logger.exception("Failed to render email template: %s", template_id)
        return False

    return send_email(
        subject=subject,
        body=plaintext,
        to_emails=to_emails,
        html_body=html_body,
        from_email=from_email,
    )
