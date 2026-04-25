"""
Unit tests for storage-error logging in lease document delete paths.

Covers:
  - LeaseViewSet.perform_destroy: logs when doc.file.delete() raises; DB deletion proceeds.
  - LeaseViewSet.delete_document: logs when doc.file.delete() raises; DB deletion proceeds
    and API returns 204.
"""
import logging
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


pytestmark = [pytest.mark.unit, pytest.mark.green]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_doc(pk, raise_on_storage=False):
    """Return a mock LeaseDocument whose file.delete() may raise."""
    doc = MagicMock()
    doc.pk = pk
    if raise_on_storage:
        doc.file.delete.side_effect = Exception("S3 connection refused")
    return doc


# ---------------------------------------------------------------------------
# perform_destroy — storage error is logged; DB row is deleted
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_perform_destroy_logs_storage_error(caplog):
    """
    When doc.file.delete() raises, logger.exception fires and instance.delete() is
    still called (DB row removed).
    """
    from apps.leases.views import LeaseViewSet

    doc = _make_doc(pk=42, raise_on_storage=True)
    instance = MagicMock()
    instance.documents.all.return_value = [doc]

    view = LeaseViewSet()

    with caplog.at_level(logging.ERROR, logger="apps.leases.views"):
        view.perform_destroy(instance)

    # Storage error must be logged
    assert any("42" in record.message for record in caplog.records), (
        "Expected a log message containing the document pk"
    )
    assert any(record.exc_info is not None for record in caplog.records), (
        "Expected exc_info to be captured (logger.exception)"
    )
    # DB row must still be deleted
    instance.delete.assert_called_once()


@pytest.mark.green
def test_perform_destroy_no_log_when_storage_succeeds(caplog):
    """No log emitted when storage delete succeeds."""
    from apps.leases.views import LeaseViewSet

    doc = _make_doc(pk=7, raise_on_storage=False)
    instance = MagicMock()
    instance.documents.all.return_value = [doc]

    view = LeaseViewSet()

    with caplog.at_level(logging.ERROR, logger="apps.leases.views"):
        view.perform_destroy(instance)

    assert caplog.records == []
    instance.delete.assert_called_once()


# ---------------------------------------------------------------------------
# delete_document — storage error is logged; DB row and 204 response intact
# ---------------------------------------------------------------------------

@pytest.mark.green
def test_delete_document_logs_storage_error_and_returns_204(caplog):
    """
    When doc.file.delete() raises in delete_document, logger.exception fires,
    doc.delete() is still called, and the action returns 204.
    """
    from apps.leases.views import LeaseViewSet
    from rest_framework.test import APIRequestFactory

    doc = _make_doc(pk=99, raise_on_storage=True)

    factory = APIRequestFactory()
    request = factory.delete("/fake/")

    view = LeaseViewSet()
    view.kwargs = {"pk": "1", "doc_id": "99"}
    view.request = request
    view.format_kwarg = None

    with (
        patch("apps.leases.views.get_object_or_404", return_value=doc),
        patch.object(LeaseViewSet, "get_object", return_value=MagicMock()),
        caplog.at_level(logging.ERROR, logger="apps.leases.views"),
    ):
        response = view.delete_document(request, pk="1", doc_id="99")

    assert response.status_code == 204
    doc.delete.assert_called_once()

    assert any("99" in record.message for record in caplog.records), (
        "Expected a log message containing the document pk"
    )
    assert any(record.exc_info is not None for record in caplog.records), (
        "Expected exc_info to be captured (logger.exception)"
    )


@pytest.mark.green
def test_delete_document_no_log_when_storage_succeeds(caplog):
    """No log emitted when storage delete succeeds in delete_document."""
    from apps.leases.views import LeaseViewSet
    from rest_framework.test import APIRequestFactory

    doc = _make_doc(pk=55, raise_on_storage=False)

    factory = APIRequestFactory()
    request = factory.delete("/fake/")

    view = LeaseViewSet()
    view.kwargs = {"pk": "1", "doc_id": "55"}
    view.request = request
    view.format_kwarg = None

    with (
        patch("apps.leases.views.get_object_or_404", return_value=doc),
        patch.object(LeaseViewSet, "get_object", return_value=MagicMock()),
        caplog.at_level(logging.ERROR, logger="apps.leases.views"),
    ):
        response = view.delete_document(request, pk="1", doc_id="55")

    assert response.status_code == 204
    doc.delete.assert_called_once()
    assert caplog.records == []
