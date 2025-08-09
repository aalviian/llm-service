import logging
import os
import warnings

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

logging.getLogger("transformers").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

from autoreply.models import AutoReplyResponseTemplate, FineTunedModel


def get_latest_finetuned_model_path():
    """Retrieves the file path of the currently active fine-tuned model."""
    active_model = FineTunedModel.objects.filter(is_active=True).order_by("-created_at").first()
    if active_model and os.path.exists(active_model.model_path):
        return active_model.model_path
    return None


def classify_email_text(email_body: str) -> (str, float):
    """
    Classifies the given email text using the best available model.

    It first checks for a fine-tuned model and falls back to a zero-shot
    classifier if none is found.

    Args:
        email_body: The text content of the email.

    Returns:
        A tuple containing the predicted category (str) and the confidence score (float).
        Returns (None, 0.0) if classification is not possible.
    """
    predicted_category = None
    confidence = 0.0

    # model_path = get_latest_finetuned_model_path()
    model_path = "./fine_tuned_models/model_20250801_222301"

    if model_path and os.path.exists(model_path):
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)

        inputs = tokenizer(
            email_body, return_tensors="pt", truncation=True, padding=True, max_length=512
        )

        # Ensure tensors are on the same device and materialized
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = model(**inputs).logits

        # Ensure logits are materialized (not meta tensors)
        if logits.is_meta:
            logits = logits.to("cpu")

        probabilities = torch.softmax(logits, dim=1)
        confidence_tensor, predicted_class_id = torch.max(probabilities, dim=1)

        predicted_category = model.config.id2label[predicted_class_id.item()]
        confidence = confidence_tensor.item()
    else:
        classifier = pipeline("zero-shot-classification", model="joeddav/xlm-roberta-large-xnli")
        labels = [
            "Loan/Payment:Disbursement",
            "GRAB permintaan notifikasi",
            "GRAB perubahan data",
            "GRAB pengajuan error - lainnya",
            "Application:Error",
            "GRAB lainnya",
            "Loan/Payment:SKL Request",
            "Loan/Payment:Permohonan keringanan",
        ]
        # candidate_labels = list(
        #     AutoReplyResponseTemplate.objects.filter(is_active=True).values_list(
        #         "category", flat=True
        #     )
        # )

        if not labels:
            return None, 0.0

        result = classifier(email_body, candidate_labels=labels)
        predicted_category = result["labels"][0]
        confidence = result["scores"][0]

    return predicted_category, confidence
