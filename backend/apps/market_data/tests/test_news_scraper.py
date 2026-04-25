"""
Unit tests for the news feed scraper.
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest


def _make_entry(title: str, link: str, published_parsed=None) -> MagicMock:
    """Return a minimal feedparser-style entry mock."""
    entry = MagicMock()
    entry.title = title
    entry.summary = "property rental development cape town"
    entry.description = ""
    entry.link = link
    entry.published_parsed = published_parsed
    return entry


@pytest.mark.django_db
class TestNewsScraper:
    """Tests for apps.market_data.scrapers.news.scrape_news_feeds."""

    def _run_with_entries(self, entries: list) -> list:
        """Patch feedparser.parse for every configured feed and return results."""
        from apps.market_data.scrapers import news as news_mod  # noqa: PLC0415

        feed_mock = MagicMock()
        feed_mock.entries = entries

        with patch.object(news_mod, "feedparser") as mock_fp:
            mock_fp.parse.return_value = feed_mock
            return news_mod.scrape_news_feeds()

    def test_healthy_entries_return_results(self):
        """All well-formed entries are included in the output."""
        entries = [
            _make_entry("Cape Town property boom", "https://example.com/1", (2026, 4, 24, 10, 0, 0, 4, 114, 0)),
            _make_entry("Stellenbosch rental demand", "https://example.com/2", (2026, 4, 23, 9, 0, 0, 3, 113, 0)),
        ]
        results = self._run_with_entries(entries)
        assert len(results) >= 2

    def test_bad_date_entry_logs_warning_and_continues(self, caplog):
        """
        When published_parsed is a tuple that datetime() cannot unpack,
        a WARNING is logged and remaining entries are still processed.
        """
        from apps.market_data.scrapers import news as news_mod  # noqa: PLC0415

        bad_entry = _make_entry("Cape Town zoning change", "https://example.com/bad", published_parsed=(99999,))
        good_entry = _make_entry("Paarl housing development", "https://example.com/good", published_parsed=(2026, 4, 24, 10, 0, 0, 4, 114, 0))

        feed_mock = MagicMock()
        feed_mock.entries = [bad_entry, good_entry]

        with patch.object(news_mod, "feedparser") as mock_fp:
            mock_fp.parse.return_value = feed_mock
            with caplog.at_level(logging.WARNING, logger="apps.market_data.scrapers.news"):
                results = news_mod.scrape_news_feeds()

        # Warning must be emitted for the bad entry
        assert any("Skipping news entry date parse" in r.message for r in caplog.records), (
            "Expected a WARNING for the bad date entry but none was found."
        )

        # Good entry must still appear in results
        good_links = [r["url"] for r in results]
        assert "https://example.com/good" in good_links, (
            "Good entry after the bad one was dropped — scraper did not continue iterating."
        )

    def test_no_log_noise_on_clean_run(self, caplog):
        """No WARNING is emitted when all entries parse cleanly."""
        entries = [
            _make_entry("Cape Town property news", "https://example.com/clean", (2026, 4, 24, 8, 0, 0, 4, 114, 0)),
        ]
        with caplog.at_level(logging.WARNING, logger="apps.market_data.scrapers.news"):
            self._run_with_entries(entries)

        date_warnings = [r for r in caplog.records if "Skipping news entry date parse" in r.message]
        assert not date_warnings, "Unexpected WARNING logged for a healthy run."
