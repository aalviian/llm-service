from unittest.mock import MagicMock, Mock, patch

from django.test import TestCase

from autoreply.llm.classify import classify_email_text, get_latest_finetuned_model_path
from autoreply.llm.fine_tune import fine_tune_model


class ClassifyTest(TestCase):
    @patch("autoreply.models.FineTunedModel.objects")
    @patch("os.path.exists")
    def test_get_latest_finetuned_model_path_exists(self, mock_exists, mock_objects):
        mock_model = Mock()
        mock_model.model_path = "/test/path"
        mock_objects.filter().order_by().first.return_value = mock_model
        mock_exists.return_value = True

        result = get_latest_finetuned_model_path()
        self.assertEqual(result, "/test/path")

    @patch("autoreply.models.FineTunedModel.objects")
    def test_get_latest_finetuned_model_path_none(self, mock_objects):
        mock_objects.filter().order_by().first.return_value = None
        result = get_latest_finetuned_model_path()
        self.assertIsNone(result)

    @patch("autoreply.llm.classify.get_latest_finetuned_model_path")
    @patch("autoreply.llm.classify.pipeline")
    def test_classify_email_text_zero_shot_fallback(self, mock_pipeline, mock_model_path):
        mock_model_path.return_value = None
        mock_classifier = Mock()
        mock_classifier.return_value = {"labels": ["Loan/Payment:Disbursement"], "scores": [0.85]}
        mock_pipeline.return_value = mock_classifier

        category, confidence = classify_email_text("Test email content")
        self.assertEqual(category, "Loan/Payment:Disbursement")
        self.assertEqual(confidence, 0.85)
        mock_pipeline.assert_called_once()
    
    @patch("autoreply.llm.classify.get_latest_finetuned_model_path")
    def test_classify_email_text_no_labels_error(self, mock_model_path):
        mock_model_path.return_value = None
        
        with patch("autoreply.llm.classify.pipeline") as mock_pipeline:
            mock_pipeline.side_effect = Exception("No labels")
            category, confidence = classify_email_text("test")
            self.assertIsNone(category)
            self.assertEqual(confidence, 0.0)


class FineTuneTest(TestCase):
    @patch("autoreply.llm.fine_tune.AutoTokenizer")
    @patch("autoreply.llm.fine_tune.AutoModelForSequenceClassification")
    @patch("autoreply.llm.fine_tune.Trainer")
    @patch("os.makedirs")
    def test_fine_tune_model_basic(self, mock_makedirs, mock_trainer, mock_model, mock_tokenizer):
        training_data = [
            {"text": "Test email 1", "label": "Category1"},
            {"text": "Test email 2", "label": "Category2"},
        ]

        mock_tokenizer_instance = Mock()
        mock_tokenizer_instance.pad_token = None
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance

        mock_model_instance = Mock()
        mock_model.from_pretrained.return_value = mock_model_instance

        mock_trainer_instance = Mock()
        mock_trainer.return_value = mock_trainer_instance

        result = fine_tune_model(training_data)
        self.assertIn("fine_tuned_models", result)
        mock_trainer_instance.train.assert_called_once()

    @patch("autoreply.llm.fine_tune.AutoTokenizer")
    @patch("autoreply.llm.fine_tune.AutoModelForSequenceClassification")
    @patch("autoreply.llm.fine_tune.Trainer")
    @patch("autoreply.llm.fine_tune.Dataset")
    @patch("os.makedirs")
    @patch("torch.backends.mps.is_available")
    @patch("torch.mps.empty_cache")
    def test_fine_tune_model_data_balancing(self, mock_cache, mock_mps, mock_makedirs, mock_dataset, mock_trainer, mock_model, mock_tokenizer):
        training_data = [
            {"text": "Test 1", "label": "Cat1"},
            {"text": "Test 2", "label": "Cat1"},
            {"text": "Test 3", "label": "Cat2"}
        ]
        
        mock_tokenizer_instance = Mock()
        mock_tokenizer_instance.pad_token = None
        mock_tokenizer_instance.eos_token = "<eos>"
        mock_tokenizer.from_pretrained.return_value = mock_tokenizer_instance
        
        mock_model_instance = Mock()
        mock_model.from_pretrained.return_value = mock_model_instance
        
        mock_trainer_instance = Mock()
        mock_trainer.return_value = mock_trainer_instance
        
        mock_dataset_instance = Mock()
        mock_dataset.from_list.return_value = mock_dataset_instance
        mock_dataset_instance.map.return_value = mock_dataset_instance
        
        mock_mps.return_value = True
        
        result = fine_tune_model(training_data)
        self.assertIn("fine_tuned_models", result)
        self.assertEqual(mock_tokenizer_instance.pad_token, "<eos>")
        mock_trainer_instance.train.assert_called_once()
        mock_cache.assert_called()
    
    def test_fine_tune_model_empty_data(self):
        with self.assertRaises(ValueError):
            fine_tune_model([])
