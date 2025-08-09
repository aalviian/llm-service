from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient


class ClassifyViewExtendedTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("autoreply.llm.classify.classify_email_text")
    def test_classify_email_view_success(self, mock_classify):
        mock_classify.return_value = ("Test Category", 0.85)

        data = {"email_body": "Test email content"}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/classify-email/", data, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["predicted_category"], "Test Category")
        self.assertEqual(response.data["confidence"], 0.85)
        mock_classify.assert_called_once_with("Test email content")

    def test_classify_email_view_empty_request(self):
        response = self.client.post("/autoreply/api/v1/autoreply/classify-email/", {})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Request body is required")

    def test_classify_email_view_missing_email_body(self):
        data = {"other_field": "value"}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/classify-email/", data, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "email_body is required")

    @patch("autoreply.llm.classify.classify_email_text")
    def test_classify_email_view_exception(self, mock_classify):
        mock_classify.side_effect = Exception("Classification error")

        data = {"email_body": "Test email content"}
        response = self.client.post(
            "/autoreply/api/v1/autoreply/classify-email/", data, format="json"
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.data)
