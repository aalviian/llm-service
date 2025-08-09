from unittest.mock import patch, Mock
from django.test import TestCase
from rest_framework.test import APIClient


class FineTuneViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch('autoreply.llm.fine_tune.fine_tune_model')
    @patch('autoreply.models.FineTunedModel.objects')
    def test_fine_tune_model_view_success(self, mock_objects, mock_fine_tune):
        mock_fine_tune.return_value = "/path/to/model"
        mock_objects.create.return_value = Mock()
        
        data = {
            "training_data": [
                {"text": "Test email 1", "label": "Category1"},
                {"text": "Test email 2", "label": "Category2"}
            ]
        }
        response = self.client.post('/autoreply/api/v1/autoreply/fine-tune/', data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], "Model fine-tuned successfully")
        self.assertEqual(response.data['model_path'], "/path/to/model")
        mock_fine_tune.assert_called_once()
        mock_objects.create.assert_called_once()
    
    def test_fine_tune_model_view_empty_request(self):
        response = self.client.post('/autoreply/api/v1/autoreply/fine-tune/', {})
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], "Request body is required")
    
    def test_fine_tune_model_view_missing_training_data(self):
        data = {"model_name": "test-model"}
        response = self.client.post('/autoreply/api/v1/autoreply/fine-tune/', data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], "training_data is required")
    
    def test_fine_tune_model_view_empty_training_data(self):
        data = {"training_data": []}
        response = self.client.post('/autoreply/api/v1/autoreply/fine-tune/', data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], "training_data must be a non-empty list")
    
    def test_fine_tune_model_view_invalid_training_data_format(self):
        data = {"training_data": [{"invalid": "format"}]}
        response = self.client.post('/autoreply/api/v1/autoreply/fine-tune/', data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid training data format", response.data['error'])
    
    @patch('autoreply.llm.fine_tune.fine_tune_model')
    def test_fine_tune_model_view_exception(self, mock_fine_tune):
        mock_fine_tune.side_effect = Exception("Fine-tuning error")
        
        data = {
            "training_data": [
                {"text": "Test email", "label": "Category"}
            ]
        }
        response = self.client.post('/autoreply/api/v1/autoreply/fine-tune/', data, format='json')
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.data)
    
    @patch('autoreply.llm.classify.classify_email_text')
    def test_test_finetuned_model_view_success(self, mock_classify):
        mock_classify.return_value = ("Test Category", 0.85)
        
        data = {"email_body": "Test email content"}
        response = self.client.post('/autoreply/api/v1/autoreply/test-finetuned/', data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['predicted_category'], "Test Category")
        self.assertEqual(response.data['confidence'], 0.85)
        self.assertEqual(response.data['model_used'], "fine-tuned")
    
    def test_test_finetuned_model_view_empty_request(self):
        response = self.client.post('/autoreply/api/v1/autoreply/test-finetuned/', {})
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], "Request body is required")
    
    def test_test_finetuned_model_view_missing_email_body(self):
        data = {"other_field": "value"}
        response = self.client.post('/autoreply/api/v1/autoreply/test-finetuned/', data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], "email_body is required")
    
    @patch('autoreply.llm.classify.classify_email_text')
    def test_test_finetuned_model_view_exception(self, mock_classify):
        mock_classify.side_effect = Exception("Classification error")
        
        data = {"email_body": "Test email content"}
        response = self.client.post('/autoreply/api/v1/autoreply/test-finetuned/', data, format='json')
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("error", response.data)