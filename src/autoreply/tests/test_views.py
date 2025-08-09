import base64
import json
from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient


class GmailNotificationWebhookViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_invalid_message_format(self):
        response = self.client.post("/autoreply/api/webhook/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("autoreply.views.process_email_task")
    def test_valid_webhook_message(self, mock_task):
        data = {
            "message": {
                "data": "eyJlbWFpbEFkZHJlc3MiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaGlzdG9yeUlkIjoiMTIzNDUifQ=="
            }
        }
        response = self.client.post("/autoreply/api/webhook/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class OAuth2StartViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("autoreply.services.gmail.get_oauth2_credentials")
    @patch("autoreply.services.gmail.create_oauth2_flow")
    def test_oauth2_start(self, mock_flow, mock_creds):
        mock_creds.return_value = {"web": {"client_id": "test"}}
        mock_flow_instance = Mock()
        mock_flow_instance.authorization_url.return_value = ("http://test.com", "state123")
        mock_flow.return_value = mock_flow_instance

        response = self.client.get("/autoreply/api/v1/autoreply/oauth2/start/")
        self.assertEqual(response.status_code, 302)


class ClassifyEmailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_missing_email_body(self):
        response = self.client.post("/autoreply/api/v1/autoreply/classify-email/", {})
        self.assertEqual(response.status_code, 400)

    @patch("autoreply.llm.classify.classify_email_text")
    def test_classify_email(self, mock_classify):
        mock_classify.return_value = ("Test Category", 0.85)
        data = {"email_body": "Test email content"}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/classify-email/", data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["predicted_category"], "Test Category")
    
    def test_classify_email_empty_request(self):
        response = self.client.post("/autoreply/api/v1/autoreply/classify-email/", {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Request body is required")
    
    def test_classify_email_missing_email_body(self):
        data = {"other_field": "value"}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/classify-email/", data, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "email_body is required")
    
    @patch("autoreply.llm.classify.classify_email_text")
    def test_classify_email_exception(self, mock_classify):
        mock_classify.side_effect = Exception("Classification error")
        data = {"email_body": "Test email content"}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/classify-email/", data, format="json"
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.data)

    @patch("autoreply.views.process_email_task")
    def test_gmail_webhook_valid_message(self, mock_task):
        message_data = {"emailAddress": "test@example.com", "historyId": "12345"}
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

        data = {"message": {"data": encoded_data}}
        response = self.client.post("/autoreply/api/webhook/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_task.assert_called_once_with("test@example.com", "12345")

    def test_gmail_webhook_missing_email_address(self):
        message_data = {"historyId": "12345"}
        encoded_data = base64.b64encode(json.dumps(message_data).encode()).decode()

        data = {"message": {"data": encoded_data}}
        response = self.client.post("/autoreply/api/webhook/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_gmail_webhook_json_decode_error(self):
        encoded_data = base64.b64encode(b"invalid json").decode()

        data = {"message": {"data": encoded_data}}
        response = self.client.post("/autoreply/api/webhook/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("autoreply.services.gmail.get_oauth2_credentials")
    def test_oauth2_start_credentials_error(self, mock_get_creds):
        mock_get_creds.side_effect = ValueError("Credentials error")

        response = self.client.get("/autoreply/api/v1/autoreply/oauth2/start/")
        self.assertEqual(response.status_code, 500)

    @patch("autoreply.services.gmail.get_oauth2_credentials")
    @patch("autoreply.services.gmail.create_oauth2_flow")
    def test_oauth2_callback_success(self, mock_flow, mock_get_creds):
        mock_get_creds.return_value = {"web": {"redirect_uris": ["http://test.com"]}}
        mock_flow_instance = Mock()
        mock_creds = Mock()
        mock_creds.token = "access_token"
        mock_creds.refresh_token = "refresh_token"
        mock_creds.id_token = {"email": "test@example.com"}
        mock_flow_instance.credentials = mock_creds
        mock_flow_instance.fetch_token = Mock()
        mock_flow.return_value = mock_flow_instance

        response = self.client.get("/autoreply/api/v1/autoreply/oauth2/callback/?state=test_state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["access_token"], "access_token")

    @patch("autoreply.services.gmail.create_gmail_service_with_tokens")
    def test_gmail_watch_success(self, mock_service):
        mock_service_instance = Mock()
        mock_service_instance.users().watch().execute.return_value = {
            "expiration": "123456",
            "historyId": "789",
        }
        mock_service.return_value = mock_service_instance

        data = {"access_token": "test_token", "refresh_token": "test_refresh"}
        response = self.client.post("/autoreply/api/v1/autoreply/gmail/watch/", data, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Gmail Watch registered")

    def test_gmail_watch_missing_tokens(self):
        data = {}
        response = self.client.post("/autoreply/api/v1/autoreply/gmail/watch/", data, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Missing token")

    @patch("autoreply.services.gmail.create_gmail_service_with_tokens")
    def test_gmail_stop_watch_success(self, mock_service):
        mock_service_instance = Mock()
        mock_service_instance.users().stop().execute.return_value = {}
        mock_service.return_value = mock_service_instance

        data = {"access_token": "test_token", "refresh_token": "test_refresh"}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/gmail/stop-watch/", data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Gmail Watch stopped successfully")

    def test_gmail_stop_watch_missing_tokens(self):
        data = {}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/gmail/stop-watch/", data, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Missing token")
