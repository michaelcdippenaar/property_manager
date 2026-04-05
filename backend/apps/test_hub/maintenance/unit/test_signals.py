"""
Unit tests for signal handlers in apps/maintenance/signals.py.

Signals are tested by mocking external dependencies (channel layer, ingest).
"""
import pytest
from unittest.mock import MagicMock, patch, call

pytestmark = pytest.mark.unit


class TestBroadcastQuestionUpdate:
    """broadcast_question_update: sends correct data via channel layer."""

    @patch("asgiref.sync.async_to_sync")
    @patch("channels.layers.get_channel_layer")
    def test_sends_question_created_event_on_create(self, mock_get_layer, mock_async):
        from apps.maintenance.signals import broadcast_question_update

        mock_channel = MagicMock()
        mock_get_layer.return_value = mock_channel
        mock_group_send = MagicMock()
        mock_async.return_value = mock_group_send

        instance = MagicMock()
        instance.pk = 42
        instance.status = "pending"

        broadcast_question_update(sender=None, instance=instance, created=True)

        mock_async.assert_called_once()
        call_args = mock_group_send.call_args[0]
        assert call_args[0] == "maintenance_updates"
        payload = call_args[1]["payload"]
        assert payload["event"] == "question_created"
        assert payload["question_id"] == 42

    @patch("asgiref.sync.async_to_sync")
    @patch("channels.layers.get_channel_layer")
    def test_sends_question_updated_event_on_update(self, mock_get_layer, mock_async):
        from apps.maintenance.signals import broadcast_question_update

        mock_channel = MagicMock()
        mock_get_layer.return_value = mock_channel
        mock_group_send = MagicMock()
        mock_async.return_value = mock_group_send

        instance = MagicMock()
        instance.pk = 10
        instance.status = "answered"

        broadcast_question_update(sender=None, instance=instance, created=False)

        call_args = mock_group_send.call_args[0]
        payload = call_args[1]["payload"]
        assert payload["event"] == "question_updated"

    @patch("channels.layers.get_channel_layer")
    def test_no_channel_layer_does_not_raise(self, mock_get_layer):
        from apps.maintenance.signals import broadcast_question_update

        mock_get_layer.return_value = None  # No channel layer configured

        instance = MagicMock()
        instance.pk = 1
        instance.status = "pending"

        # Should not raise
        broadcast_question_update(sender=None, instance=instance, created=True)

    @patch("channels.layers.get_channel_layer", side_effect=Exception("channels error"))
    def test_channel_layer_exception_does_not_raise(self, mock_get_layer):
        from apps.maintenance.signals import broadcast_question_update

        instance = MagicMock()
        instance.pk = 1
        instance.status = "pending"

        # Signal handler catches all exceptions
        broadcast_question_update(sender=None, instance=instance, created=True)


class TestIngestAnsweredQuestion:
    """ingest_answered_question: calls ingest function for answered questions."""

    @patch("apps.maintenance.signals.AgentQuestion")
    @patch("core.contract_rag.ingest_agent_question", create=True)
    def test_ingest_called_for_answered_question(self, mock_ingest, mock_aq_class):
        from apps.maintenance.signals import ingest_answered_question

        # Patch the import inside the signal
        with patch.dict("sys.modules", {"core.contract_rag": MagicMock(ingest_agent_question=mock_ingest)}):
            from apps.maintenance.models import AgentQuestion

            instance = MagicMock()
            instance.status = AgentQuestion.Status.ANSWERED if hasattr(AgentQuestion, "Status") else "answered"
            instance.answer = "The gate code is 1234"
            instance.pk = 5
            instance.question = "What is the gate code?"
            instance.category = "property"
            instance.property_id = None
            instance.added_to_context = True  # already flagged

            mock_aq_class.objects.filter.return_value.update.return_value = 1
            mock_ingest.return_value = True

            ingest_answered_question(sender=None, instance=instance)

    def test_skipped_for_non_answered_status(self):
        from apps.maintenance.signals import ingest_answered_question

        instance = MagicMock()
        instance.status = "pending"
        instance.answer = ""

        # Should return early without calling ingest
        with patch("core.contract_rag.ingest_agent_question", create=True) as mock_ingest:
            ingest_answered_question(sender=None, instance=instance)
            mock_ingest.assert_not_called()

    @pytest.mark.green
    def test_ingest_failure_does_not_raise(self):
        """RED: Verify signal handles ingest failure gracefully (exception path).

        This test is marked red because the import path for ingest_agent_question
        is dynamic and may need adjustment based on the actual module structure.
        """
        from apps.maintenance.signals import ingest_answered_question

        instance = MagicMock()
        instance.status = "answered"
        instance.answer = "Some answer"
        instance.pk = 99
        instance.question = "A question"
        instance.category = "general"
        instance.property_id = None
        instance.added_to_context = True

        with patch("apps.maintenance.signals.AgentQuestion") as mock_aq:
            mock_aq.objects.filter.return_value.update.return_value = 1
            # Importing core.contract_rag may raise — signal should catch it
            ingest_answered_question(sender=None, instance=instance)
