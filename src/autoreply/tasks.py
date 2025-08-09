import base64

from celery import shared_task
from django.conf import settings

from autoreply.llm.classify import classify_email_text
from autoreply.models import AutoReplyEmailLog, AutoReplyResponseTemplate

# Local imports
from autoreply.services.gmail import (
    get_email_body,
    get_gmail_service,
    get_gmail_service_oauth,
    register_gmail_watch,
)

# Global set to track processed messages
processed_messages = set()


@shared_task
def process_email_task(user_email, history_id):
    try:
        service = get_gmail_service_oauth()
        messages = (
            service.users().messages().list(userId="me", labelIds=["INBOX"], maxResults=1).execute()
        )

        latest_messages = messages.get("messages", [])

        if not latest_messages:
            return

        # Get the latest (first) message since Gmail returns newest first
        latest_msg = latest_messages[0]

        for msg in [latest_msg]:
            print(msg)
            print(msg.get("id"))
            message_id = msg.get("id")
            if not message_id:
                continue

            # Skip if already processed
            if message_id in processed_messages:
                print(f"Message {message_id} already processed, skipping")
                return

            # Add to processed set
            processed_messages.add(message_id)

            msg_raw = (
                service.users().messages().get(userId="me", id=message_id, format="raw").execute()
            )
            email_body = get_email_body(msg_raw["raw"])

            # Get sender email, subject, and message ID from message headers
            msg_full = service.users().messages().get(userId="me", id=message_id).execute()
            sender_email = None
            subject = None
            original_message_id = None
            for header in msg_full.get("payload", {}).get("headers", []):
                if header["name"] == "From":
                    sender_email = header["value"]
                    # Extract email from "Name <email@domain.com>" format
                    if "<" in sender_email and ">" in sender_email:
                        sender_email = sender_email.split("<")[1].split(">")[0]
                elif header["name"] == "Subject":
                    subject = header["value"]
                    print("subject: " + subject)
                elif header["name"] == "Message-ID":
                    print("message ID: " + header["value"])
                    original_message_id = header["value"]

            if email_body and sender_email:
                predicted_category, confidence = process_single_email(
                    sender_email, message_id, email_body, service
                )
                print("body: " + email_body[:100])
                print("score: " + str(confidence))
                print("predicted_category: " + predicted_category)
                print("sender_email: " + sender_email)

                # Get thread ID for reply
                thread_id = msg_raw.get("threadId")
                create_auto_reply(
                    sender_email,
                    message_id,
                    thread_id,
                    email_body,
                    predicted_category,
                    confidence,
                    service,
                    subject,
                    original_message_id,
                )

                # Mark all processed emails as read (remove bold)
                service.users().messages().modify(
                    userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
                ).execute()
                print(f"Marked message {message_id} as read")

            return

    except Exception as e:
        print(f"Error processing email: {e}")
        raise e


def process_single_email(user_email, message_id, email_body, service):
    """
    Process a single email message
    """

    predicted_category = ""
    confidence = 0.0
    try:
        predicted_category, confidence = classify_email_text(email_body)
        # print(f"Processing emai: {email_body[:100]}...")
    except Exception as classify_error:
        error_msg = str(classify_error)
        if "meta tensors" in error_msg or "item()" in error_msg:
            raise classify_error

    return predicted_category, confidence


def create_auto_reply(
    user_email,
    message_id,
    thread_id,
    email_body,
    predicted_category,
    confidence,
    service,
    subject,
    original_message_id,
):
    """
    Create auto reply with thread ID support.
    Auto reply sent if confidence > 80% and predefined response matches predicted_category.
    If confidence below 80%, agent will review manually and reply manually.
    """
    # Log email to database
    # log_entry = AutoReplyEmailLog.objects.create(
    #     body=email_body,
    #     email_from=user_email,
    #     predicted_category=predicted_category,
    #     confidence_score=confidence,
    # )
    print("masuk create auto reply")
    if confidence > 0.80:
        print("threshold 0.8")
        try:
            # Find matching template
            # template = AutoReplyResponseTemplate.objects.get(
            #     category=predicted_category, is_active=True
            # )

            # Send auto reply in same thread
            reply_subject = (
                f"Re: {subject}" if subject and not subject.startswith("Re:") else subject
            )
            raw_message = f"From: cs@julo.co.id\nTo: {user_email}\nSubject: {reply_subject}\nIn-Reply-To: {original_message_id}\nReferences: {original_message_id}\nContent-Type: text/plain; charset=utf-8\n\nHalo"
            encoded_message = base64.urlsafe_b64encode(raw_message.encode()).decode()

            reply_message = {
                "threadId": thread_id,
                "raw": encoded_message,
            }

            service.users().messages().send(userId="me", body=reply_message).execute()

            # Update log with template used
            # log_entry.template_response = template
            # log_entry.save(update_fields=["template_response"])

            print(f"Auto reply sent for message {message_id}")

        except Exception as e:
            print(f"Failed to send auto reply: {e}")
    else:
        print(f"Confidence {confidence:.2f} below 80%. Flagged for manual review")
        reply_subject = f"Re: {subject}" if subject and not subject.startswith("Re:") else subject
        raw_message = f"From: cs@julo.co.id\nTo: {user_email}\nSubject: {reply_subject}\nIn-Reply-To: {original_message_id}\nReferences: {original_message_id}\nContent-Type: text/plain; charset=utf-8\n\nHalo terima kasih atas laporannya."
        encoded_message = base64.urlsafe_b64encode(raw_message.encode()).decode()

        reply_message = {
            "threadId": thread_id,
            "raw": encoded_message,
        }

        try:
            service.users().messages().send(userId="me", body=reply_message).execute()
        except Exception as e:
            print("gagal: " + str(e))


@shared_task(name="tasks.renewal_gmail_watch")
def renewal_gmail_watch_task():
    """
    Periodically renews the Gmail watch subscription.
    The watch expires every 7 days, so this task should run every 6 days
    as a safety measure to prevent monitoring gaps.
    """
    print("Executing periodic Gmail watch renewal...")
    try:
        if not hasattr(settings, "GMAIL_PUB_SUB_TOPIC_NAME"):
            print("Error: GMAIL_PUB_SUB_TOPIC_NAME is not configured in Django settings.")
            return

        topic_name = settings.GMAIL_PUB_SUB_TOPIC_NAME
        response = register_gmail_watch(topic_name)
        print(f"Successfully renewed Gmail watch. New expiration: {response.get('expiration')}")
    except Exception as e:
        print(f"An error occurred during Gmail watch renewal: {e}")
        # In a production environment, consider adding more robust error handling,
        # like sending an alert to an admin.
        raise e
