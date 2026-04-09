"""
Unit tests for the shared AI document-extraction utilities.

Source file under test: apps/properties/extraction_utils.py

Covers the pure-Python helpers that don't need a real Claude client:
  - encode_file   — image / PDF / text / unknown fallback behaviour
  - extract_pdf_text — pypdf integration with truncation and failure modes
  - validate_classification — SA registration number regex + entity-type mismatch
  - SA_REG_NUMBER_PATTERNS — real-world SA company / CC / Trust numbers
  - Tool schemas — shape invariants that the downstream views depend on

The heavier ``call_claude_with_tools`` helper is covered via a small mock
suite so we can assert the retry / backoff behaviour without hitting the
Anthropic API.
"""
import base64
import io
from unittest import mock

import anthropic
import pytest

from apps.properties.extraction_utils import (
    CLASSIFY_TOOL,
    MAX_FILE_SIZE_BYTES,
    MUNICIPAL_BILL_TOOL,
    SA_REG_NUMBER_PATTERNS,
    call_claude_with_tools,
    encode_file,
    extract_pdf_text,
    validate_classification,
)

pytestmark = [pytest.mark.unit, pytest.mark.green]


# ─────────────────────────────────────────────────────────────────────────────
# encode_file — images
# ─────────────────────────────────────────────────────────────────────────────
class TestEncodeFileImages:
    def test_png_is_encoded_as_image_block(self):
        data = b"\x89PNG\r\n\x1a\nfakepayload"
        block = encode_file(data=data, filename="bill.png")

        assert block is not None
        assert block["type"] == "image"
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "image/png"
        # Payload must round-trip through base64
        assert base64.b64decode(block["source"]["data"]) == data

    def test_jpeg_is_encoded_as_image_block(self):
        data = b"\xff\xd8\xff\xe0fake-jpeg"
        block = encode_file(data=data, filename="bill.jpg")

        assert block["type"] == "image"
        assert block["source"]["media_type"] == "image/jpeg"

    def test_explicit_mime_overrides_filename_guess(self):
        """Callers can force a mime type even if the filename has no extension."""
        data = b"\x89PNG\r\n\x1a\n"
        block = encode_file(data=data, filename="blob", mime="image/png")
        assert block["type"] == "image"
        assert block["source"]["media_type"] == "image/png"


# ─────────────────────────────────────────────────────────────────────────────
# encode_file — PDFs
# ─────────────────────────────────────────────────────────────────────────────
class TestEncodeFilePdfs:
    def test_pdf_is_encoded_as_document_block(self):
        data = b"%PDF-1.4\nfake pdf bytes"
        block = encode_file(data=data, filename="rates.pdf")

        assert block is not None
        assert block["type"] == "document"
        assert block["source"]["type"] == "base64"
        assert block["source"]["media_type"] == "application/pdf"
        assert base64.b64decode(block["source"]["data"]) == data


# ─────────────────────────────────────────────────────────────────────────────
# encode_file — text + fallback
# ─────────────────────────────────────────────────────────────────────────────
class TestEncodeFileText:
    def test_plain_text_falls_back_to_text_block(self):
        data = b"Dear landlord,\nYour rates are due."
        block = encode_file(data=data, filename="notice.txt")

        assert block is not None
        assert block["type"] == "text"
        assert "notice.txt" in block["text"]
        assert "Dear landlord" in block["text"]

    def test_text_is_truncated_at_8000_chars(self):
        """Massive text inputs must be clipped so we don't blow the context."""
        big = b"a" * 20_000
        block = encode_file(data=big, filename="huge.log")
        assert block["type"] == "text"
        # 8000 chars of payload + the "[File: huge.log]\n" prefix
        assert len(block["text"]) <= 8000 + 20

    def test_unknown_mime_still_decoded_as_text(self):
        """octet-stream falls through to the text branch so callers still
        get *something* rather than a silent drop."""
        data = b"some binary-ish content"
        block = encode_file(data=data, filename="weird.bin")
        # octet-stream → text fallback
        assert block is not None
        assert block["type"] == "text"

    def test_invalid_utf8_is_handled_with_replacement(self):
        """Invalid UTF-8 bytes should not raise — decode uses errors='replace'."""
        data = b"\xff\xfe\xfdnot utf-8"
        block = encode_file(data=data, filename="garbled.txt")
        assert block is not None
        assert block["type"] == "text"


# ─────────────────────────────────────────────────────────────────────────────
# extract_pdf_text
# ─────────────────────────────────────────────────────────────────────────────
class TestExtractPdfText:
    def test_invalid_pdf_returns_empty_string(self):
        """Must never raise — best-effort extraction only."""
        result = extract_pdf_text(b"not a pdf")
        assert result == ""

    def test_empty_bytes_returns_empty_string(self):
        assert extract_pdf_text(b"") == ""

    def test_respects_max_chars_truncation(self):
        """Patch the reader so we can assert the slice[:max_chars] behaviour."""
        fake_page = mock.MagicMock()
        fake_page.extract_text.return_value = "x" * 20_000

        fake_reader = mock.MagicMock()
        fake_reader.pages = [fake_page]

        with mock.patch("pypdf.PdfReader", return_value=fake_reader):
            result = extract_pdf_text(b"%PDF-1.4 stub", max_pages=5, max_chars=500)

        assert len(result) == 500
        assert result == "x" * 500

    def test_respects_max_pages(self):
        """Only the first ``max_pages`` pages are extracted."""
        pages = []
        for i in range(20):
            p = mock.MagicMock()
            p.extract_text.return_value = f"page{i}"
            pages.append(p)

        fake_reader = mock.MagicMock()
        fake_reader.pages = pages

        with mock.patch("pypdf.PdfReader", return_value=fake_reader):
            result = extract_pdf_text(b"%PDF", max_pages=3, max_chars=9999)

        assert "page0" in result
        assert "page1" in result
        assert "page2" in result
        assert "page3" not in result  # would be 4th page

    def test_pages_returning_none_are_skipped(self):
        """pypdf returns ``None`` for empty pages — we must not crash."""
        blank = mock.MagicMock()
        blank.extract_text.return_value = None
        good = mock.MagicMock()
        good.extract_text.return_value = "real content"

        fake_reader = mock.MagicMock()
        fake_reader.pages = [blank, good]

        with mock.patch("pypdf.PdfReader", return_value=fake_reader):
            result = extract_pdf_text(b"%PDF")

        assert "real content" in result


# ─────────────────────────────────────────────────────────────────────────────
# SA registration number regex
# ─────────────────────────────────────────────────────────────────────────────
class TestSARegNumberPatterns:
    @pytest.mark.parametrize("reg_num", [
        "2021/123456/07",      # Pty Ltd
        "2015/000001/06",      # Public company
        "1999/999999/21",      # NPC (21 suffix still matches the YYYY/XXXXXX/NN pattern)
    ])
    def test_standard_company_numbers_match(self, reg_num):
        assert any(p.match(reg_num) for p in SA_REG_NUMBER_PATTERNS), (
            f"{reg_num} did not match any SA reg number pattern"
        )

    @pytest.mark.parametrize("reg_num", [
        "CK2005/12345",
        "CK1999/01",
        "ck2010/123456",  # case-insensitive
    ])
    def test_close_corporation_numbers_match(self, reg_num):
        assert any(p.match(reg_num) for p in SA_REG_NUMBER_PATTERNS)

    @pytest.mark.parametrize("reg_num", [
        "IT2020/1234",
        "it1999/9999",
    ])
    def test_trust_numbers_match(self, reg_num):
        assert any(p.match(reg_num) for p in SA_REG_NUMBER_PATTERNS)

    @pytest.mark.parametrize("reg_num", [
        "",
        "12345",
        "2021/123/07",         # too-short middle segment
        "2021/1234567/07",     # middle segment too long
        "ABC2021/123456/07",   # leading letters not allowed on the standard pattern
        "random garbage",
    ])
    def test_invalid_numbers_do_not_match(self, reg_num):
        assert not any(p.match(reg_num) for p in SA_REG_NUMBER_PATTERNS)


# ─────────────────────────────────────────────────────────────────────────────
# validate_classification
# ─────────────────────────────────────────────────────────────────────────────
class TestValidateClassification:
    def test_valid_pty_ltd_returns_no_warnings(self):
        c = {
            "entity_type": "Company",
            "extracted_data": {
                "registration_number": "2021/123456/07",
                "directors": [{"full_name": "Jane Doe"}],
            },
        }
        assert validate_classification(c) == []

    def test_bad_reg_number_format_is_flagged(self):
        c = {
            "entity_type": "Company",
            "extracted_data": {
                "registration_number": "NOT-A-REG-NUMBER",
                "directors": [{"full_name": "Jane"}],
            },
        }
        warnings = validate_classification(c)
        assert any("does not match expected SA format" in w for w in warnings)

    def test_entity_type_vs_suffix_mismatch_is_flagged(self):
        """Suffix /08 is a CC, but the classifier returned Company."""
        c = {
            "entity_type": "Company",
            "extracted_data": {
                "registration_number": "2005/00123/08",
                "directors": [{"full_name": "Jane"}],
            },
        }
        warnings = validate_classification(c)
        assert any("suggests CC" in w for w in warnings)

    def test_empty_directors_flagged_for_company(self):
        c = {
            "entity_type": "Company",
            "extracted_data": {
                "registration_number": "2021/123456/07",
                "directors": [],
            },
        }
        warnings = validate_classification(c)
        assert any("No directors/members extracted" in w for w in warnings)

    def test_empty_directors_flagged_for_cc(self):
        c = {
            "entity_type": "CC",
            "extracted_data": {
                "registration_number": "CK2001/12345",
                "directors": [],
            },
        }
        warnings = validate_classification(c)
        assert any("No directors/members extracted" in w for w in warnings)

    def test_empty_directors_not_flagged_for_trust(self):
        """Trusts have trustees, not directors — don't nag about missing directors."""
        c = {
            "entity_type": "Trust",
            "extracted_data": {
                "registration_number": "IT2020/1234",
                "directors": [],
            },
        }
        warnings = validate_classification(c)
        assert not any("directors/members" in w for w in warnings)

    def test_missing_registration_number_is_not_flagged(self):
        """No reg number → can't validate format, no warning."""
        c = {
            "entity_type": "Individual",
            "extracted_data": {},
        }
        assert validate_classification(c) == []

    def test_handles_missing_extracted_data(self):
        """Defensive: classification dict without ``extracted_data`` should not crash."""
        c = {"entity_type": "Individual"}
        assert validate_classification(c) == []


# ─────────────────────────────────────────────────────────────────────────────
# Tool schema shape invariants
# ─────────────────────────────────────────────────────────────────────────────
class TestMunicipalBillToolSchema:
    def test_has_tool_name(self):
        assert MUNICIPAL_BILL_TOOL["name"] == "submit_municipal_bill_data"

    def test_required_fields_are_present(self):
        schema = MUNICIPAL_BILL_TOOL["input_schema"]
        assert "property_name" in schema["required"]
        assert "total_due" in schema["required"]
        assert "municipality" in schema["required"]
        assert "confidence_scores" in schema["required"]

    def test_every_required_field_is_declared_in_properties(self):
        schema = MUNICIPAL_BILL_TOOL["input_schema"]
        for field in schema["required"]:
            assert field in schema["properties"], (
                f"required field {field!r} is not declared in properties"
            )

    def test_monetary_fields_allow_null(self):
        """Null-safe — Claude must be able to signal 'field not present'."""
        schema = MUNICIPAL_BILL_TOOL["input_schema"]["properties"]
        for field in ("rates_amount", "refuse_amount", "water_amount", "total_due"):
            assert "null" in schema[field]["type"], f"{field} must allow null"


class TestClassifyToolSchema:
    def test_has_tool_name(self):
        assert CLASSIFY_TOOL["name"] == "submit_classification"

    def test_required_fields_are_present(self):
        schema = CLASSIFY_TOOL["input_schema"]
        for field in ("entity_type", "fica", "cipc", "extracted_data", "classified_at"):
            assert field in schema["required"]

    def test_entity_type_enum(self):
        enum = CLASSIFY_TOOL["input_schema"]["properties"]["entity_type"]["enum"]
        assert enum == ["Individual", "Company", "Trust", "CC", "Partnership"]

    def test_fica_status_enum(self):
        enum = (
            CLASSIFY_TOOL["input_schema"]["properties"]["fica"]
            ["properties"]["status"]["enum"]
        )
        assert enum == ["complete", "incomplete", "needs_review"]


# ─────────────────────────────────────────────────────────────────────────────
# call_claude_with_tools (mocked client)
# ─────────────────────────────────────────────────────────────────────────────
def _mock_response_with_tool_use(payload: dict):
    """Build a fake Anthropic response containing a single tool_use block."""
    block = mock.MagicMock()
    block.type = "tool_use"
    block.input = payload

    response = mock.MagicMock()
    response.content = [block]
    return response


def _mock_response_without_tool_use():
    block = mock.MagicMock()
    block.type = "text"
    response = mock.MagicMock()
    response.content = [block]
    return response


class TestCallClaudeWithTools:
    def test_happy_path_returns_tool_input(self):
        client = mock.MagicMock()
        client.messages.create.return_value = _mock_response_with_tool_use(
            {"entity_type": "Company"}
        )

        result, err = call_claude_with_tools(
            client=client,
            system="you are a classifier",
            content=[{"type": "text", "text": "hi"}],
            tool=CLASSIFY_TOOL,
        )

        assert err is None
        assert result == {"entity_type": "Company"}
        client.messages.create.assert_called_once()
        # And we must have forced the specific tool
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["tool_choice"] == {"type": "tool", "name": "submit_classification"}

    def test_response_without_tool_use_block_returns_error(self):
        client = mock.MagicMock()
        client.messages.create.return_value = _mock_response_without_tool_use()

        result, err = call_claude_with_tools(
            client=client,
            system="s",
            content=[],
            tool=CLASSIFY_TOOL,
        )

        assert result is None
        assert "tool_use" in err

    def test_rate_limit_triggers_retry_with_backoff(self):
        """First call raises RateLimitError, second call succeeds."""
        client = mock.MagicMock()
        # anthropic.RateLimitError() takes (message, response, body) in newer SDKs;
        # use a base Exception subclass that the helper will catch.
        rate_limit = anthropic.RateLimitError(
            "rate limited",
            response=mock.MagicMock(status_code=429),
            body=None,
        )
        client.messages.create.side_effect = [
            rate_limit,
            _mock_response_with_tool_use({"ok": True}),
        ]

        with mock.patch("apps.properties.extraction_utils.time.sleep") as sleep_mock:
            result, err = call_claude_with_tools(
                client=client,
                system="s",
                content=[],
                tool=CLASSIFY_TOOL,
                max_retries=2,
            )

        assert err is None
        assert result == {"ok": True}
        assert client.messages.create.call_count == 2
        # First retry should sleep 1s (1 * 2**0)
        sleep_mock.assert_called_with(1)

    def test_unexpected_exception_is_not_retried(self):
        client = mock.MagicMock()
        client.messages.create.side_effect = ValueError("boom")

        result, err = call_claude_with_tools(
            client=client,
            system="s",
            content=[],
            tool=CLASSIFY_TOOL,
            max_retries=5,
        )

        assert result is None
        assert "Unexpected error" in err
        # Called exactly once — no retry on generic exceptions
        assert client.messages.create.call_count == 1

    def test_exhausted_retries_return_final_error(self):
        """All attempts rate-limited → final error with attempt count."""
        client = mock.MagicMock()
        rate_limit = anthropic.RateLimitError(
            "rate limited",
            response=mock.MagicMock(status_code=429),
            body=None,
        )
        client.messages.create.side_effect = rate_limit

        with mock.patch("apps.properties.extraction_utils.time.sleep"):
            result, err = call_claude_with_tools(
                client=client,
                system="s",
                content=[],
                tool=CLASSIFY_TOOL,
                max_retries=2,
            )

        assert result is None
        assert "failed after 3 attempts" in err
        assert client.messages.create.call_count == 3


# ─────────────────────────────────────────────────────────────────────────────
# Size limit constant
# ─────────────────────────────────────────────────────────────────────────────
class TestSizeLimit:
    def test_max_file_size_is_10_mb(self):
        """Pinned so we notice if anyone bumps it silently — bumping the cap
        has cost implications on the Anthropic side and must be a conscious
        decision."""
        assert MAX_FILE_SIZE_BYTES == 10 * 1024 * 1024
