"""
Gotenberg PDF generation client.

Converts HTML to PDF via the Gotenberg Docker service (Chromium-based).
Produces pixel-perfect PDFs that match TipTap editor rendering since both
use the same Chromium engine.

Usage:
    from apps.esigning.gotenberg import html_to_pdf
    pdf_bytes = html_to_pdf(html_string)

Requires GOTENBERG_URL in settings (defaults to http://localhost:3000).
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _gotenberg_url():
    return getattr(settings, 'GOTENBERG_URL', 'http://localhost:3000').rstrip('/')


def html_to_pdf(
    html: str,
    *,
    footer_html: str | None = None,
    paper_width: float = 8.27,     # A4 inches
    paper_height: float = 11.7,    # A4 inches
    margin_top: float = 0.0,       # 0 — CSS @page margin controls layout
    margin_bottom: float = 0.0,
    margin_left: float = 0.0,
    margin_right: float = 0.0,
    prefer_css_page_size: bool = True,
    print_background: bool = True,
    timeout: int = 60,
) -> bytes:
    """
    Convert an HTML string to PDF bytes via Gotenberg's Chromium route.

    Margins default to 0 so that CSS @page rules have full control over the
    page layout.  When preferCssPageSize is true (default), Chromium honours
    the @page { size: A4; margin: ... } declarations in the HTML stylesheet.

    If footer_html is provided, it is rendered as a separate HTML document
    at the bottom of every page.  The footer is isolated from the main page
    CSS — everything must be inline.  Gotenberg injects .pageNumber and
    .totalPages CSS classes automatically.

    Raises requests.HTTPError on failure.
    """
    url = f'{_gotenberg_url()}/forms/chromium/convert/html'

    files = {
        'files': ('index.html', html.encode('utf-8'), 'text/html'),
    }
    if footer_html:
        files['footer'] = ('footer.html', footer_html.encode('utf-8'), 'text/html')

    data = {
        'paperWidth': str(paper_width),
        'paperHeight': str(paper_height),
        'marginTop': str(margin_top),
        'marginBottom': str(margin_bottom),
        'marginLeft': str(margin_left),
        'marginRight': str(margin_right),
        'preferCssPageSize': str(prefer_css_page_size).lower(),
        'printBackground': str(print_background).lower(),
    }

    resp = requests.post(url, files=files, data=data, timeout=timeout)

    if not resp.ok:
        body = (resp.text or '')[:500]
        logger.error('Gotenberg error %s: %s', resp.status_code, body)
        resp.raise_for_status()

    return resp.content


def health_check() -> dict:
    """Check Gotenberg service health. Returns the JSON health payload."""
    url = f'{_gotenberg_url()}/health'
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()
