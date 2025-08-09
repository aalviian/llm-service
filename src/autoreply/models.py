import json

from django.conf import settings
from django.db import models


class AutoReplyResponseTemplate(models.Model):
    """Stores the predefined email templates for each category."""

    id = models.BigAutoField(primary_key=True)
    category = models.CharField(max_length=100, unique=True)
    subject_email = models.CharField(max_length=255)
    content_email = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "autoreply_response_template"
        verbose_name = "Auto Reply Response Template"
        verbose_name_plural = "Auto Reply Response Templates"

    def __str__(self):
        return self.category


class AutoReplyEmailLog(models.Model):
    """Logs every incoming email, its prediction, and the final outcome."""

    id = models.BigAutoField(primary_key=True)
    body = models.TextField(help_text="The content of the email.")
    email_from = models.CharField(max_length=255, help_text="Customer's email address.")
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Confidence score from the model.",
    )
    predicted_category = models.CharField(
        max_length=100, null=True, blank=True, help_text="Category predicted by the LLM."
    )
    actual_category = models.CharField(
        max_length=100, null=True, blank=True, help_text="Category verified by a human agent."
    )
    template_response = models.ForeignKey(
        AutoReplyResponseTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The template response sent, if any.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "autoreply_email_log"
        verbose_name = "Auto Reply Email Log"
        verbose_name_plural = "Auto Reply Email Log"

    def __str__(self):
        return f"Log for {self.email_from} - Predicted: {self.predicted_category}, Actual: {self.actual_category}"


class FineTunedModel(models.Model):
    """Tracks versions of fine-tuned models."""

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="A unique name for the model version (e.g., 'v2.1-with-new-data').",
    )
    model_path = models.CharField(max_length=255, help_text="Path to the saved model directory.")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=False, help_text="Is this the currently active model for predictions?"
    )
    notes = models.TextField(blank=True, help_text="Notes about the training data or performance.")

    class Meta:
        verbose_name = "Fine-Tuned Model"
        verbose_name_plural = "Fine-Tuned Models"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensures only one model can be active at a time.
        if self.is_active:
            FineTunedModel.objects.filter(is_active=True).update(is_active=False)
        super(FineTunedModel, self).save(*args, **kwargs)
