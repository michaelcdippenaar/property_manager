"""
Unit tests for apps/maintenance/chat_history.py.

Tests the persist_chat_history_to_request function.
"""
import pytest
from unittest.mock import MagicMock, patch, call

pytestmark = pytest.mark.unit


class TestPersistChatHistoryToRequest:
    """persist_chat_history_to_request: saves messages as MaintenanceActivity rows."""

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_returns_count_of_created_activities(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = []
        mock_activity_qs.create.return_value = MagicMock()

        request_obj = MagicMock()
        messages = [
            {"role": "user", "content": "My tap is leaking"},
            {"role": "assistant", "content": "I can log that for you"},
        ]

        count = persist_chat_history_to_request(request_obj, messages)
        assert count == 2

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_empty_messages_returns_zero(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = []

        request_obj = MagicMock()
        count = persist_chat_history_to_request(request_obj, [])
        assert count == 0

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_none_messages_returns_zero(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = []

        request_obj = MagicMock()
        count = persist_chat_history_to_request(request_obj, None)
        assert count == 0

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_assistant_messages_stored_with_no_created_by(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = []
        created_activities = []
        mock_activity_qs.create.side_effect = lambda **kwargs: created_activities.append(kwargs)

        request_obj = MagicMock()
        messages = [{"role": "assistant", "content": "I will log this"}]
        persist_chat_history_to_request(request_obj, messages, created_by=MagicMock())

        assert len(created_activities) == 1
        assert created_activities[0]["created_by"] is None  # AI message — no user

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_user_messages_stored_with_created_by(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = []
        created_activities = []
        mock_activity_qs.create.side_effect = lambda **kwargs: created_activities.append(kwargs)

        user = MagicMock()
        request_obj = MagicMock()
        messages = [{"role": "user", "content": "My tap is leaking"}]
        persist_chat_history_to_request(request_obj, messages, created_by=user)

        assert len(created_activities) == 1
        assert created_activities[0]["created_by"] is user

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_skips_messages_with_empty_content(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = []

        request_obj = MagicMock()
        messages = [
            {"role": "user", "content": ""},
            {"role": "user", "content": "  "},
        ]
        count = persist_chat_history_to_request(request_obj, messages)
        assert count == 0

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_skips_special_message_types(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = []

        request_obj = MagicMock()
        messages = [
            {"role": "user", "content": "something", "type": "skills"},   # skipped
            {"role": "user", "content": "something", "type": "confirm"},  # skipped
            {"role": "user", "content": "valid message"},                  # kept
        ]
        count = persist_chat_history_to_request(request_obj, messages)
        assert count == 1

    @patch("apps.maintenance.chat_history.MaintenanceActivity.objects")
    def test_deduplication_by_chat_message_id(self, mock_activity_qs):
        from apps.maintenance.chat_history import persist_chat_history_to_request

        # Simulate that message id=1 already exists
        mock_activity_qs.filter.return_value.exclude.return_value.values_list.return_value = [1]

        created_activities = []
        mock_activity_qs.create.side_effect = lambda **kwargs: created_activities.append(kwargs)

        request_obj = MagicMock()
        messages = [
            {"id": 1, "role": "user", "content": "Already persisted"},  # should be skipped
            {"id": 2, "role": "user", "content": "New message"},         # should be created
        ]
        count = persist_chat_history_to_request(request_obj, messages)

        assert count == 1
        assert len(created_activities) == 1

    @pytest.mark.red
    def test_metadata_source_set_correctly(self):
        """RED: Verify metadata.source is 'ai_agent' for assistant, 'user' for human.

        This test is marked red pending verification of exact metadata key structure.
        """
        raise NotImplementedError(
            "Verify metadata structure: source='ai_agent' vs source='user', "
            "chat_source=source_param, chat_role=role"
        )
