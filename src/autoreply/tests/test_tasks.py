from unittest.mock import Mock, patch

from django.test import TestCase

from autoreply.tasks import process_email_task, process_single_email, renewal_gmail_watch_task


class TasksTest(TestCase):
    @patch("autoreply.tasks.get_gmail_service_oauth")
    def test_process_email_task_no_messages(self, mock_service):
        mock_service_instance = Mock()
        mock_service_instance.users().messages().list().execute.return_value = {"messages": []}
        mock_service.return_value = mock_service_instance

        # Should not raise exception
        process_email_task("test@example.com", "12345")
        mock_service.assert_called_once()

    @patch("autoreply.tasks.get_gmail_service_oauth")
    @patch("autoreply.tasks.get_email_body")
    @patch("autoreply.tasks.process_single_email")
    def test_process_email_task_with_messages(
        self, mock_process_single, mock_get_body, mock_service
    ):
        mock_service_instance = Mock()
        mock_service_instance.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg123"}]
        }
        mock_service_instance.users().messages().get().execute.return_value = {"raw": "test_raw"}
        mock_service.return_value = mock_service_instance
        mock_get_body.return_value = "Test email body"

        process_email_task("test@example.com", "12345")
        mock_process_single.assert_called_once()

    @patch("autoreply.tasks.classify_email_text")
    def test_process_single_email_high_confidence(self, mock_classify):
        mock_classify.return_value = ("Test Category", 0.85)
        mock_service = Mock()

        process_single_email("test@example.com", "msg123", "Test email", mock_service)
        mock_service.users().messages().modify.assert_called_once()

    @patch("autoreply.tasks.classify_email_text")
    def test_process_single_email_low_confidence(self, mock_classify):
        mock_classify.return_value = ("Test Category", 0.5)
        mock_service = Mock()

        process_single_email("test@example.com", "msg123", "Test email", mock_service)
        # Should not call modify for low confidence
        mock_service.users().messages().modify.assert_not_called()

    @patch("autoreply.tasks.register_gmail_watch")
    @patch("django.conf.settings")
    def test_renewal_gmail_watch_task_success(self, mock_settings, mock_register):
        mock_settings.GMAIL_PUB_SUB_TOPIC_NAME = "test-topic"
        mock_register.return_value = {"expiration": "2024-01-01"}

        # Should not raise exception
        renewal_gmail_watch_task()
        mock_register.assert_called_once_with("test-topic")

    @patch("django.conf.settings")
    def test_renewal_gmail_watch_task_no_topic(self, mock_settings):
        delattr(mock_settings, "GMAIL_PUB_SUB_TOPIC_NAME")

        # Should not raise exception
        renewal_gmail_watch_task()

    @patch("autoreply.tasks.get_gmail_service_oauth")
    def test_process_email_task_list_error(self, mock_service):
        mock_service_instance = Mock()
        mock_service_instance.users().messages().list().execute.side_effect = Exception(
            "List error"
        )
        mock_service.return_value = mock_service_instance

        # Should handle exception and return
        process_email_task("test@example.com", "12345")
        mock_service.assert_called_once()

    @patch("autoreply.tasks.get_gmail_service_oauth")
    @patch("autoreply.tasks.get_email_body")
    def test_process_email_task_no_message_id(self, mock_get_body, mock_service):
        mock_service_instance = Mock()
        mock_service_instance.users().messages().list().execute.return_value = {
            "messages": [{}]  # No 'id' key
        }
        mock_service.return_value = mock_service_instance

        process_email_task("test@example.com", "12345")
        # Should continue without processing
        mock_get_body.assert_not_called()

    @patch("autoreply.tasks.classify_email_text")
    def test_process_single_email_classification_failed(self, mock_classify):
        mock_classify.return_value = (None, 0.0)
        mock_service = Mock()

        process_single_email("test@example.com", "msg123", "Test email", mock_service)
        # Should return early if classification fails
        mock_service.users().messages().modify.assert_not_called()

    @patch("autoreply.tasks.classify_email_text")
    def test_process_single_email_mark_as_read_error(self, mock_classify):
        mock_classify.return_value = ("Test Category", 0.85)
        mock_service = Mock()
        mock_service.users().messages().modify().execute.side_effect = Exception("Mark read error")

        # Should handle exception gracefully
        process_single_email("test@example.com", "msg123", "Test email", mock_service)
        mock_service.users().messages().modify.assert_called_once()

    @patch("django.conf.settings")
    def test_renewal_gmail_watch_task_no_topic_setting(self, mock_settings):
        # Remove the attribute to simulate missing setting
        if hasattr(mock_settings, "GMAIL_PUB_SUB_TOPIC_NAME"):
            delattr(mock_settings, "GMAIL_PUB_SUB_TOPIC_NAME")

        # Should handle missing setting gracefully
        renewal_gmail_watch_task()

    @patch("autoreply.tasks.register_gmail_watch")
    @patch("django.conf.settings")
    def test_renewal_gmail_watch_task_register_error(self, mock_settings, mock_register):
        mock_settings.GMAIL_PUB_SUB_TOPIC_NAME = "test-topic"
        mock_register.side_effect = Exception("Register error")

        # Should handle exception gracefully
        renewal_gmail_watch_task()
        mock_register.assert_called_once_with("test-topic")
