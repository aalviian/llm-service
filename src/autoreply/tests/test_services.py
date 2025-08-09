from unittest.mock import Mock, patch

from django.test import TestCase

from autoreply.services.gmail import (
    clean_email_body,
    create_gmail_service_with_tokens,
    create_oauth2_flow,
    get_delegated_credentials,
    get_gmail_service,
    get_gmail_service_oauth,
    register_gmail_watch,
    stop_gmail_watch,
)


class GmailServiceTest(TestCase):
    def test_clean_email_body_html_removal(self):
        html_email = "<html><body><p>Test email content</p></body></html>"
        cleaned = clean_email_body(html_email)
        self.assertEqual(cleaned, "Test email content")

    def test_clean_email_body_signature_removal(self):
        email_with_signature = "Test content\n\n--\nBest regards\nJohn Doe"
        cleaned = clean_email_body(email_with_signature)
        self.assertNotIn("Best regards", cleaned)
        self.assertIn("Test content", cleaned)

    def test_clean_email_body_empty_input(self):
        cleaned = clean_email_body("")
        self.assertEqual(cleaned, "")

    def test_clean_email_body_email_replacement(self):
        email_content = "Contact me at john@example.com for details"
        cleaned = clean_email_body(email_content)
        self.assertIn("[EMAIL]", cleaned)
        self.assertNotIn("john@example.com", cleaned)

    @patch("os.getenv")
    def test_get_oauth2_credentials_missing(self, mock_getenv):
        mock_getenv.return_value = None
        with self.assertRaises(ValueError):
            get_oauth2_credentials()

    @patch("os.getenv")
    def test_get_oauth2_credentials_valid(self, mock_getenv):
        mock_getenv.return_value = '{"web":{"client_id":"test","client_secret":"secret","redirect_uris":["http://test.com"]}}'
        creds = get_oauth2_credentials()
        self.assertIn("web", creds)
        self.assertEqual(creds["web"]["client_id"], "test")

    @patch("django.conf.settings")
    @patch("autoreply.services.gmail.service_account")
    def test_get_delegated_credentials(self, mock_service_account, mock_settings):
        mock_settings.CX_GOOGLE_CREDENTIALS_FILE = "test_file"
        mock_creds = Mock()
        mock_delegated = Mock()
        mock_creds.with_subject.return_value = mock_delegated
        mock_service_account.Credentials.from_service_account_file.return_value = mock_creds

        result = get_delegated_credentials()
        self.assertEqual(result, mock_delegated)
        mock_creds.with_subject.assert_called_once()

    @patch("autoreply.services.gmail.get_delegated_credentials")
    @patch("autoreply.services.gmail.build")
    def test_get_gmail_service(self, mock_build, mock_get_creds):
        mock_creds = Mock()
        mock_get_creds.return_value = mock_creds
        mock_service = Mock()
        mock_build.return_value = mock_service

        result = get_gmail_service()
        self.assertEqual(result, mock_service)
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_creds)

    @patch("autoreply.services.gmail.get_gmail_service")
    def test_register_gmail_watch(self, mock_service):
        mock_service_instance = Mock()
        mock_service_instance.users().watch().execute.return_value = {"expiration": "123"}
        mock_service.return_value = mock_service_instance

        result = register_gmail_watch("test-topic")
        self.assertEqual(result["expiration"], "123")

    @patch("autoreply.services.gmail.get_gmail_service")
    def test_stop_gmail_watch(self, mock_service):
        mock_service_instance = Mock()
        mock_service_instance.users().stop().execute.return_value = {}
        mock_service.return_value = mock_service_instance

        result = stop_gmail_watch()
        mock_service_instance.users().stop.assert_called_once()

    @patch("os.getenv")
    def test_get_gmail_service_oauth_missing_env(self, mock_getenv):
        mock_getenv.return_value = None

        with self.assertRaises(Exception):
            get_gmail_service_oauth()
    
    @patch("os.getenv")
    @patch("autoreply.services.gmail.service_account")
    @patch("autoreply.services.gmail.build")
    def test_get_gmail_service_oauth_success(self, mock_build, mock_service_account, mock_getenv):
        mock_getenv.return_value = '{"type":"service_account","client_email":"test@test.com"}'
        mock_creds = Mock()
        mock_delegated = Mock()
        mock_creds.with_subject.return_value = mock_delegated
        mock_service_account.Credentials.from_service_account_info.return_value = mock_creds
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        result = get_gmail_service_oauth()
        self.assertEqual(result, mock_service)
        mock_build.assert_called_once_with("gmail", "v1", credentials=mock_delegated)
    
    @patch("os.getenv")
    def test_get_gmail_service_oauth_invalid_json(self, mock_getenv):
        mock_getenv.return_value = "invalid json"
        
        with self.assertRaises(Exception):
            get_gmail_service_oauth()

    @patch("os.getenv")
    def test_get_oauth2_credentials_missing_web_key(self, mock_getenv):
        mock_getenv.return_value = '{"invalid": "data"}'

        from autoreply.services.gmail import get_oauth2_credentials

        with self.assertRaises(ValueError):
            get_oauth2_credentials()

    @patch("autoreply.services.gmail.get_oauth2_credentials")
    @patch("autoreply.services.gmail.Flow")
    def test_create_oauth2_flow(self, mock_flow, mock_get_creds):
        mock_get_creds.return_value = {"web": {"redirect_uris": ["http://test.com"]}}
        mock_flow_instance = Mock()
        mock_flow.from_client_config.return_value = mock_flow_instance

        result = create_oauth2_flow({"web": {"redirect_uris": ["http://test.com"]}}, "state123")
        self.assertEqual(result.state, "state123")

    def test_clean_email_body_signature_patterns(self):
        email_with_signature = "Content\n--\nBest regards\nJohn"
        cleaned = clean_email_body(email_with_signature)
        self.assertNotIn("Best regards", cleaned)

        email_with_sent_from = "Content\nSent from my iPhone"
        cleaned = clean_email_body(email_with_sent_from)
        self.assertNotIn("Sent from", cleaned)

    @patch("autoreply.services.gmail.get_oauth2_credentials")
    @patch("autoreply.services.gmail.build")
    def test_create_gmail_service_with_tokens(self, mock_build, mock_get_creds):
        mock_get_creds.return_value = {
            "web": {
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test_id",
                "client_secret": "test_secret",
            }
        }
        mock_service = Mock()
        mock_build.return_value = mock_service

        result = create_gmail_service_with_tokens("access_token", "refresh_token")
        self.assertEqual(result, mock_service)
        mock_build.assert_called_once()

    def test_clean_email_body_privacy_protection(self):
        email_with_personal_info = "Contact john@example.com or visit http://example.com"
        cleaned = clean_email_body(email_with_personal_info)
        self.assertIn("[EMAIL]", cleaned)
        self.assertIn("[URL]", cleaned)
        self.assertNotIn("john@example.com", cleaned)
        self.assertNotIn("http://example.com", cleaned)
