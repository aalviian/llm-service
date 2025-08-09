from django.urls import path

from autoreply.views import views, views_classify, views_finetune

app_name = "autoreply"

urlpatterns = [
    path(
        "v1/autoreply/gmail-notification/",
        views.GmailNotificationWebhookView.as_view(),
        name="gmail_notification_webhook",
    ),
    path(
        "v1/autoreply/oauth2/start/",
        views.OAuth2StartView.as_view(),
        name="oauth2_start",
    ),
    path(
        "v1/autoreply/oauth2/callback/",
        views.OAuth2CallbackView.as_view(),
        name="oauth2_callback",
    ),
    path(
        "v1/autoreply/gmail/watch/",
        views.GmailWatchView.as_view(),
        name="gmail_watch",
    ),
    path(
        "v1/autoreply/gmail/stop-watch/",
        views.GmailStopWatchView.as_view(),
        name="gmail_stop_watch",
    ),
    path(
        "v1/autoreply/classify-email/",
        views_classify.ClassifyEmailView.as_view(),
        name="classify_email",
    ),
    path(
        "v1/autoreply/fine-tune/",
        views_finetune.FineTuneModelView.as_view(),
        name="fine_tune_model",
    ),
    path(
        "v1/autoreply/test-finetuned/",
        views_finetune.TestFineTunedModelView.as_view(),
        name="test_finetuned_model",
    ),
]
