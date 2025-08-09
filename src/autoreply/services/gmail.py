import base64
import email
import json
import os
import re

from bs4 import BeautifulSoup
from django.conf import settings
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Define the necessary scopes for the Gmail API
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/pubsub",
]
# The user email to impersonate with domain-wide delegation
DELEGATED_USER_EMAIL = "cs@julo.co.id"


def get_delegated_credentials():
    """
    Creates and returns credentials for a service account with domain-wide delegation.
    This allows the service account to act on behalf of the DELEGATED_USER_EMAIL.
    """
    # Parse JSON string from settings
    if isinstance(settings.CX_GOOGLE_CREDENTIALS_FILE, str):
        creds_dict = json.loads(settings.CX_GOOGLE_CREDENTIALS_FILE)
    else:
        creds_dict = settings.CX_GOOGLE_CREDENTIALS_FILE

    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    delegated_creds = creds.with_subject(DELEGATED_USER_EMAIL)
    return delegated_creds


def get_gmail_service():
    """
    Builds and returns an authenticated Gmail service object using
    service account credentials with domain-wide delegation.
    """
    credentials = get_delegated_credentials()
    return build("gmail", "v1", credentials=credentials)


def register_gmail_watch(topic_name: str):
    """
    Sets up a watch on the delegated user's Gmail account to receive push
    notifications for new, unread emails.

    Args:
        topic_name: The full name of the Google Cloud Pub/Sub topic to send
                    notifications to (e.g., 'projects/your-project-id/topics/your-topic-name').

    Returns:
        The response from the Gmail API's watch request, which includes
        the historyId and expiration timestamp.
    """
    service = get_gmail_service()
    request = {"labelIds": ["INBOX", "UNREAD"], "topicName": topic_name}
    response = service.users().watch(userId="me", body=request).execute()
    print(
        f"Successfully registered watch for {DELEGATED_USER_EMAIL}. Expiration: {response.get('expiration')}"
    )
    return response


def stop_gmail_watch():
    """
    Stops push notifications for the delegated user's account.
    """
    service = get_gmail_service()
    response = service.users().stop(userId="me").execute()
    print(f"Successfully stopped watch for {DELEGATED_USER_EMAIL}.")
    return response


def get_gmail_service_oauth():
    """
    Creates Gmail service using service account from CX_GOOGLE_CREDENTIALS_FILE.
    Uses domain-wide delegation with the provided tokens.

    Args:
        access_token: OAuth2 access token (for reference)
        refresh_token: OAuth2 refresh token (for reference)

    Returns:
        Authenticated Gmail service object using service account
    """
    try:
        credentials_json = os.getenv("CX_GOOGLE_OAUTH2_CREDENTIALS")
        if not credentials_json:
            raise ValueError("CX_GOOGLE_OAUTH2_CREDENTIALS not found")

        creds_dict = json.loads(credentials_json)
        web_config = creds_dict["web"]

        access_token = web_config.get("access_token")
        refresh_token = web_config.get("refresh_token")

        if not access_token or not refresh_token:
            raise ValueError(
                "access_token and refresh_token must be provided in CX_GOOGLE_OAUTH2_CREDENTIALS"
            )

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=web_config["token_uri"],
            client_id=web_config["client_id"],
            client_secret=web_config["client_secret"],
            scopes=[
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.modify",
            ],
        )

        return build("gmail", "v1", credentials=credentials)

    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in CX_GOOGLE_CREDENTIALS_FILE: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to create Gmail service: {str(e)}")


def get_email_body(raw_email: str) -> str:
    """
    Parses the raw email content and extracts the plain text body.

    Args:
        raw_email: The raw, base64-encoded email data from the Gmail API.

    Returns:
        The plain text body of the email as a string.
    """
    cleaned_body = ""
    try:
        msg_str = base64.urlsafe_b64decode(raw_email.encode("ASCII"))
        mime_msg = email.message_from_bytes(msg_str)
        body = ""
        if mime_msg.is_multipart():
            for part in mime_msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")
                        break
        else:
            payload = mime_msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="ignore")
        # Clean the email body
        cleaned_body = clean_email_body(body) if body else ""
    except Exception as e:
        print("Error parsing email body")
        print(str(e))
    return cleaned_body


def get_gmail_service_account_from_env():
    """
    Creates Gmail service using service account credentials from environment variable.
    Uses domain-wide delegation to impersonate the delegated user.

    Returns:
        Authenticated Gmail service object
    """
    try:
        # Get service account JSON from environment
        service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not service_account_json:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not found")

        service_account_info = json.loads(service_account_json)

        # Create service account credentials
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES
        )

        # Delegate to the user email
        delegated_credentials = credentials.with_subject(DELEGATED_USER_EMAIL)

        return build("gmail", "v1", credentials=delegated_credentials)

    except Exception as e:
        raise Exception(f"Failed to create Gmail service account from env: {str(e)}")


def get_oauth2_credentials():
    """
    Get OAuth2 credentials from environment variable.

    Returns:
        dict: Parsed OAuth2 credentials
    """
    credentials_json = os.getenv("CX_GOOGLE_OAUTH2_CREDENTIALS")
    if not credentials_json:
        raise ValueError("CX_GOOGLE_OAUTH2_CREDENTIALS not found")

    creds_dict = json.loads(credentials_json)

    if "web" not in creds_dict:
        raise ValueError('Credentials missing "web" key')

    web_config = creds_dict["web"]
    required_keys = ["client_id", "client_secret", "redirect_uris"]
    for key in required_keys:
        if key not in web_config:
            raise ValueError(f'Credentials missing "{key}" in web config')

    if not web_config["redirect_uris"]:
        raise ValueError("No redirect URIs configured")

    return creds_dict


def create_oauth2_flow(creds_dict, state=None):
    """
    Create OAuth2 flow from credentials.

    Args:
        creds_dict: OAuth2 credentials dictionary
        state: OAuth2 state parameter (optional)

    Returns:
        Flow: Configured OAuth2 flow
    """
    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    redirect_uri = creds_dict["web"]["redirect_uris"][0]

    flow = Flow.from_client_config(creds_dict, scopes=scopes, redirect_uri=redirect_uri)

    if state:
        flow.state = state

    return flow


def create_gmail_service_with_tokens(access_token, refresh_token):
    """
    Create Gmail service using access and refresh tokens.

    Args:
        access_token: OAuth2 access token
        refresh_token: OAuth2 refresh token

    Returns:
        Gmail service object
    """
    creds_dict = get_oauth2_credentials()

    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=creds_dict["web"]["token_uri"],
        client_id=creds_dict["web"]["client_id"],
        client_secret=creds_dict["web"]["client_secret"],
        scopes=scopes,
    )

    return build("gmail", "v1", credentials=creds)


def clean_email_body(email_body: str) -> str:
    """
    Clean email body by removing HTML tags, signatures, and unnecessary content.

    Args:
        email_body: Raw email body text

    Returns:
        str: Cleaned email body
    """
    if not email_body:
        return ""

    # Remove HTML tags using BeautifulSoup
    soup = BeautifulSoup(email_body, "html.parser")
    text = soup.get_text()

    # Remove common signature patterns
    signature_patterns = [
        r"--\s*\n.*",  # Standard signature delimiter
        r"Best regards.*",
        r"Regards.*",
        r"Sincerely.*",
        r"Thanks.*",
        r"Terima kasih.*",
        r"Salam.*",
        r"Sent from.*",
        r"Dikirim dari.*",
        r"On .* wrote:.*",  # Reply chain
        r"Pada .* menulis:.*",  # Indonesian reply chain
        r"From:.*To:.*Subject:.*",  # Email headers
        r"\*\*\*.*\*\*\*",  # Asterisk separators
        r"_{3,}",  # Underscore separators
        r"-{3,}",  # Dash separators
    ]

    for pattern in signature_patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)

    # Remove excessive whitespace and newlines
    text = re.sub(r"\n{3,}", "\n\n", text)  # Max 2 consecutive newlines
    text = re.sub(r"[ \t]+", " ", text)  # Multiple spaces to single space
    text = text.strip()

    # Remove email addresses and URLs for privacy
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text)
    text = re.sub(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        "[URL]",
        text,
    )

    return text
