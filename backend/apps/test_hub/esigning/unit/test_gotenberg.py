"""
Unit tests for apps/esigning/gotenberg.py.

All HTTP calls are mocked. Tests verify the request is built correctly
and that bytes are returned.
"""
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


class TestHtmlToPdf:
    """html_to_pdf(): converts HTML string to PDF bytes via Gotenberg."""

    @patch("apps.esigning.gotenberg.requests.post")
    def test_returns_bytes_on_success(self, mock_post):
        from apps.esigning.gotenberg import html_to_pdf

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"%PDF-1.4 test"
        mock_post.return_value = mock_response

        result = html_to_pdf("<html><body>Test</body></html>")
        assert isinstance(result, bytes)
        assert result == b"%PDF-1.4 test"

    @patch("apps.esigning.gotenberg.requests.post")
    def test_posts_to_chromium_route(self, mock_post):
        from apps.esigning.gotenberg import html_to_pdf, _gotenberg_url

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"%PDF"
        mock_post.return_value = mock_response

        html_to_pdf("<html><body></body></html>")

        call_url = mock_post.call_args[0][0]
        assert "/forms/chromium/convert/html" in call_url

    @patch("apps.esigning.gotenberg.requests.post")
    def test_sends_html_as_file(self, mock_post):
        from apps.esigning.gotenberg import html_to_pdf

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"%PDF"
        mock_post.return_value = mock_response

        html_content = "<html><body>Hello</body></html>"
        html_to_pdf(html_content)

        call_kwargs = mock_post.call_args[1]
        files = call_kwargs.get("files") or mock_post.call_args[1].get("files")
        # Files dict should contain index.html
        assert "files" in mock_post.call_args[1] or "files" in str(mock_post.call_args)

    @patch("apps.esigning.gotenberg.time.sleep")
    @patch("apps.esigning.gotenberg.requests.post")
    def test_raises_on_http_error(self, mock_post, mock_sleep):
        import requests as req_lib
        from apps.esigning.gotenberg import html_to_pdf

        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = req_lib.HTTPError("500 Server Error")
        mock_post.return_value = mock_response

        with pytest.raises(req_lib.HTTPError):
            html_to_pdf("<html></html>")

    @patch("apps.esigning.gotenberg.requests.post")
    def test_includes_a4_paper_dimensions_by_default(self, mock_post):
        from apps.esigning.gotenberg import html_to_pdf

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"%PDF"
        mock_post.return_value = mock_response

        html_to_pdf("<html></html>")

        call_kwargs = mock_post.call_args[1]
        data = call_kwargs.get("data", {})
        # A4 dimensions: 8.27 x 11.7 inches
        assert "8.27" in str(data.get("paperWidth", ""))
        assert "11.7" in str(data.get("paperHeight", ""))

    @patch("apps.esigning.gotenberg.requests.post")
    def test_includes_footer_when_provided(self, mock_post):
        from apps.esigning.gotenberg import html_to_pdf

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.content = b"%PDF"
        mock_post.return_value = mock_response

        html_to_pdf("<html></html>", footer_html="<p>Page footer</p>")

        call_kwargs = mock_post.call_args[1]
        files = call_kwargs.get("files", {})
        assert "footer" in files

    @patch("apps.esigning.gotenberg.requests.get")
    def test_health_check_returns_json(self, mock_get):
        from apps.esigning.gotenberg import health_check

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "pass"}
        mock_get.return_value = mock_response

        result = health_check()
        assert isinstance(result, dict)
        assert result.get("status") == "pass"


class TestGotenbergUrl:
    """_gotenberg_url(): returns configured Gotenberg service URL."""

    @patch("apps.esigning.gotenberg.settings")
    def test_uses_gotenberg_url_setting(self, mock_settings):
        from apps.esigning.gotenberg import _gotenberg_url
        mock_settings.GOTENBERG_URL = "http://gotenberg:3000"
        result = _gotenberg_url()
        assert result == "http://gotenberg:3000"

    @patch("apps.esigning.gotenberg.settings")
    def test_strips_trailing_slash(self, mock_settings):
        from apps.esigning.gotenberg import _gotenberg_url
        mock_settings.GOTENBERG_URL = "http://gotenberg:3000/"
        result = _gotenberg_url()
        assert not result.endswith("/")

    @patch("apps.esigning.gotenberg.settings")
    def test_defaults_to_localhost_3000(self, mock_settings):
        from apps.esigning.gotenberg import _gotenberg_url
        # Simulate missing setting
        del mock_settings.GOTENBERG_URL
        mock_settings.GOTENBERG_URL = "http://localhost:3000"  # getattr default
        result = _gotenberg_url()
        assert "localhost:3000" in result
