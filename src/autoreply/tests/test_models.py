from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from autoreply.models import AutoReplyEmailLog, AutoReplyResponseTemplate, FineTunedModel


class AutoReplyResponseTemplateTest(TestCase):
    def test_str_method(self):
        template = AutoReplyResponseTemplate(category="test_category")
        self.assertEqual(str(template), "test_category")


class AutoReplyEmailLogTest(TestCase):
    def test_str_method(self):
        log = AutoReplyEmailLog(
            email_from="test@example.com",
            predicted_category="pred_cat",
            actual_category="actual_cat",
        )
        expected = "Log for test@example.com - Predicted: pred_cat, Actual: actual_cat"
        self.assertEqual(str(log), expected)


class FineTunedModelTest(TestCase):
    def test_str_method(self):
        model = FineTunedModel(name="test_model")
        self.assertEqual(str(model), "test_model")

    @patch("autoreply.models.FineTunedModel.objects")
    def test_save_deactivate_others(self, mock_objects):
        mock_objects.exclude().update.return_value = None

        model = FineTunedModel(name="test", is_active=True)
        model.pk = 1

        with patch("django.db.models.Model.save"):
            model.save()
            mock_objects.exclude.assert_called_once_with(pk=1)
            mock_objects.exclude().update.assert_called_once_with(is_active=False)
