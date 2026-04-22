"""
Gotenberg PDF generation client.

Converts HTML to PDF via the Gotenberg Docker service (Chromium-based).
Produces pixel-perfect PDFs that match TipTap editor rendering since both
use the same Chromium engine.

Usage:
    from apps.esigning.gotenberg import html_to_pdf
    pdf_bytes = html_to_pdf(html_string)

Requires GOTENBERG_URL in settings (defaults to http://localhost:3000).

Resilience: 3 automatic retries with exponential backoff (1s → 2s → 4s)
on 5xx responses or connection timeouts.  After all retries are exhausted
the underlying exception is re-raised so callers can decide whether to
enqueue an async fallback.
"""

import logging
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _gotenberg_url():
    return getattr(settings, 'GOTENBERG_URL', 'http://localhost:3000').rstrip('/')


# ---------------------------------------------------------------------------
# Metrics helpers — thin wrappers around Sentry so the rest of the code
# doesn't need to guard against sentry_sdk being absent.
# ---------------------------------------------------------------------------

def _emit_metric(name: str, value: float, unit: str = "none", tags: dict | None = None) -> None:
    """Emit a Sentry custom metric (counter or distribution).

    Silently swallows any import / SDK errors so missing Sentry never breaks
    the happy path.
    """
    try:
        import sentry_sdk
        sentry_sdk.metrics.distribution(
            key=name,
            value=value,
            unit=unit,
            tags=tags or {},
        )
    except Exception:
        pass  # metrics are best-effort


def _increment_counter(name: str, tags: dict | None = None) -> None:
    try:
        import sentry_sdk
        sentry_sdk.metrics.incr(key=name, tags=tags or {})
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core conversion
# ---------------------------------------------------------------------------

#: Number of retry attempts after the first try (total = 1 + MAX_RETRIES)
MAX_RETRIES = 3
#: Initial back-off delay in seconds (doubles each attempt)
RETRY_BACKOFF_BASE = 1


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

    Retries up to MAX_RETRIES times with exponential backoff on 5xx / timeout.
    Raises requests.HTTPError or requests.Timeout on final failure.

    Emits Sentry metrics:
      - gotenberg.pdf.latency_ms  (distribution, milliseconds)
      - gotenberg.pdf.success     (counter)
      - gotenberg.pdf.failure     (counter, tags: attempt=N, reason=<class>)
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

    last_exc: Exception | None = None
    total_start = time.monotonic()

    for attempt in range(1, MAX_RETRIES + 2):  # attempts 1..4
        attempt_start = time.monotonic()
        try:
            resp = requests.post(url, files=files, data=data, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            elapsed = (time.monotonic() - attempt_start) * 1000
            logger.warning(
                'Gotenberg request failed (attempt %d/%d, %.0f ms): %s',
                attempt, MAX_RETRIES + 1, elapsed, exc,
            )
            _increment_counter(
                'gotenberg.pdf.failure',
                tags={'attempt': str(attempt), 'reason': type(exc).__name__},
            )
            last_exc = exc
        else:
            if resp.ok:
                elapsed_ms = (time.monotonic() - total_start) * 1000
                _emit_metric('gotenberg.pdf.latency_ms', elapsed_ms, unit='millisecond')
                _increment_counter('gotenberg.pdf.success')
                return resp.content

            body = (resp.text or '')[:500]
            logger.warning(
                'Gotenberg HTTP %s on attempt %d/%d: %s',
                resp.status_code, attempt, MAX_RETRIES + 1, body,
            )
            _increment_counter(
                'gotenberg.pdf.failure',
                tags={'attempt': str(attempt), 'reason': f'http_{resp.status_code}'},
            )
            last_exc = requests.HTTPError(
                f'Gotenberg {resp.status_code}', response=resp
            )

        # Do not sleep after the final attempt
        if attempt <= MAX_RETRIES:
            delay = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))  # 1, 2, 4 seconds
            logger.info('Gotenberg retry in %ds (attempt %d of %d)', delay, attempt, MAX_RETRIES)
            time.sleep(delay)

    # All attempts exhausted
    logger.error(
        'Gotenberg PDF generation failed after %d attempts: %s',
        MAX_RETRIES + 1, last_exc,
    )
    raise last_exc  # type: ignore[misc]


def health_check() -> dict:
    """Check Gotenberg service health. Returns the JSON health payload."""
    url = f'{_gotenberg_url()}/health'
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()
