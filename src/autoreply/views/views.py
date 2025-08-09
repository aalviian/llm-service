import base64
import json
import logging
import os
from datetime import datetime
from urllib.parse import urlencode

from celery import current_app
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django_redis import get_redis_connection
from drf_spectacular.utils import OpenApiExample, extend_schema
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from autoreply.services.gmail import get_gmail_service, get_gmail_service_oauth
from autoreply.tasks import process_email_task

logger = logging.getLogger(__name__)


class GmailNotificationWebhookView(APIView):
    """
    Handles incoming push notifications from Google Pub/Sub for new emails.
    This endpoint is triggered by the Gmail watch subscription.
    """

    permission_classes = []  # Allow unauthenticated access from Google Pub/Sub

    @extend_schema(
        summary="Gmail Webhook",
        description="Handle Gmail push notifications from Google Pub/Sub",
        request={
            "type": "object",
            "properties": {
                "message": {
                    "type": "object",
                    "properties": {"data": {"type": "string"}, "messageId": {"type": "string"}},
                }
            },
        },
        responses={204: {"description": "Notification processed"}},
        tags=["Gmail"],
    )
    def post(self, request, *args, **kwargs):
        """
        Receives and processes notifications from Google Pub/Sub.
        """
        envelope = request.data
        if not envelope or "message" not in envelope:
            print("Webhook received invalid Pub/Sub message format.")
            return Response(
                {"error": "Invalid Pub/Sub message format"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Decode the base64-encoded data from the Pub/Sub message
            message = envelope["message"]
            data_str = base64.b64decode(message["data"]).decode("utf-8")
            message_data = json.loads(data_str)

            email_address = message_data.get("emailAddress")
            history_id = message_data.get("historyId")

            print("--------------------- email masuk " + str(history_id) + " ---------------------")
            if not email_address or not history_id:
                print(f"Webhook missing emailAddress or historyId in message: {message_data}")
                return Response(
                    {"error": "Missing emailAddress or historyId in message data"},
                    status=status.HTTP_204_NO_CONTENT,
                )
            process_email_task.delay(email_address, history_id)
            print(
                "--------------------- stop email masuk "
                + str(history_id)
                + " ---------------------"
            )
            return Response(
                {"success": True},
                status=status.HTTP_200_OK,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # print(f"Error processing Pub/Sub message payload: {e}")
            return Response(
                {"error": f"Failed to process message payload: {e}"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            # print(f"An unexpected error occurred in the webhook: {e}")
            return Response(
                {"error": "An unexpected server error occurred"},
                status=status.HTTP_200_OK,
            )


class OAuth2StartView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Start OAuth2 Flow",
        description="Initiate Google OAuth2 flow for Gmail access",
        responses={302: {"description": "Redirect to Google OAuth2"}},
        tags=["OAuth2"],
    )
    def get(self, request):
        try:
            from autoreply.services.gmail import create_oauth2_flow, get_oauth2_credentials

            creds_dict = get_oauth2_credentials()
            flow = create_oauth2_flow(creds_dict)

            authorization_url, state = flow.authorization_url(
                access_type="offline", include_granted_scopes="true", prompt="consent"
            )

            request.session["oauth_state"] = state
            return redirect(authorization_url)

        except Exception as e:
            return Response({"error": f"OAuth2 configuration error: {str(e)}"}, status=500)


class OAuth2CallbackView(APIView):
    """
    Handles Gmail OAuth2 callback
    GET /api/gmail/auth/callback/
    """

    authentication_classes = []
    permission_classes = []
    http_method_names = ["get"]

    @extend_schema(
        summary="OAuth2 Callback",
        description="Handle OAuth2 callback and return tokens",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "refresh_token": {"type": "string"},
                    "email": {"type": "string"},
                },
            }
        },
        tags=["OAuth2"],
    )
    def get(self, request):
        try:
            from autoreply.services.gmail import create_oauth2_flow, get_oauth2_credentials

            state = request.query_params.get("state")
            creds_dict = get_oauth2_credentials()
            flow = create_oauth2_flow(creds_dict, state)

            flow.fetch_token(authorization_response=request.build_absolute_uri())

            creds = flow.credentials
            email = creds.id_token.get("email") if creds.id_token else None

            expires_in = 3600  # Google access tokens typically expire in 1 hour
            expires_at = None
            if creds.expiry:
                expires_at = creds.expiry.isoformat()

            return Response(
                {
                    "access_token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "email": email,
                    "expires_in": expires_in,
                    "expires_at": expires_at,
                    "token_type": "Bearer",
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class GmailWatchView(APIView):
    """
    Register Gmail Watch for an authenticated user
    POST /api/gmail/watch/
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Register Gmail Watch",
        description="Register Gmail watch for push notifications",
        request={
            "type": "object",
            "properties": {
                "access_token": {"type": "string"},
                "refresh_token": {"type": "string"},
                "use_domain_delegation": {"type": "boolean", "default": False},
            },
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "result": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"},
                            "watch_response": {"type": "object"},
                            "expiration": {"type": "string"},
                            "history_id": {"type": "string"},
                        },
                    },
                },
            }
        },
        tags=["Gmail"],
    )
    def post(self, request):
        access_token = request.data.get("access_token")
        refresh_token = request.data.get("refresh_token")
        use_domain_delegation = request.data.get("use_domain_delegation", False)
        print(use_domain_delegation)
        if not use_domain_delegation and (not access_token or not refresh_token):
            return Response({"error": "Missing token"}, status=400)

        try:
            if use_domain_delegation:
                # Use domain-wide delegation with service account
                from autoreply.services.gmail import get_gmail_service

                service = get_gmail_service()
                message = "Gmail Watch registered using domain-wide delegation"
            else:
                # Use OAuth2 tokens
                from autoreply.services.gmail import create_gmail_service_with_tokens

                service = create_gmail_service_with_tokens(access_token, refresh_token)
                message = "Gmail Watch registered using OAuth2"

            watch_body = {
                "labelIds": ["INBOX"],
                "topicName": "projects/firstllm-466410/topics/gmail-notification-topic",
            }

            response = service.users().watch(userId="me", body=watch_body).execute()
            return Response(
                {
                    "message": message,
                    "result": {
                        "success": True,
                        "watch_response": response,
                        "expiration": response.get("expiration"),
                        "history_id": response.get("historyId"),
                    },
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class GmailStopWatchView(APIView):
    """
    Stop Gmail Watch for an authenticated user
    POST /api/gmail/stop-watch/
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Stop Gmail Watch",
        description="Stop Gmail watch notifications",
        request={
            "type": "object",
            "properties": {
                "access_token": {"type": "string"},
                "refresh_token": {"type": "string"},
                "use_domain_delegation": {"type": "boolean", "default": False},
            },
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "success": {"type": "boolean"},
                },
            }
        },
        tags=["Gmail"],
    )
    def post(self, request):
        access_token = request.data.get("access_token")
        refresh_token = request.data.get("refresh_token")
        use_domain_delegation = request.data.get("use_domain_delegation", False)

        if not use_domain_delegation and (not access_token or not refresh_token):
            return Response({"error": "Missing token"}, status=400)

        try:
            stopped_methods = []
            errors = []

            if use_domain_delegation:
                # Stop domain-wide delegation watch
                try:
                    from autoreply.services.gmail import get_gmail_service

                    service = get_gmail_service()
                    service.users().stop(userId="me").execute()
                    stopped_methods.append("domain-wide delegation")
                    print("Stopped domain-wide delegation watch")
                except Exception as e:
                    errors.append(f"Domain delegation stop failed: {str(e)}")
                    print(f"Failed to stop domain delegation watch: {e}")
            else:
                # Stop both OAuth2 and domain delegation watches to be sure
                # Try OAuth2 first
                if access_token and refresh_token:
                    try:
                        from autoreply.services.gmail import create_gmail_service_with_tokens

                        service = create_gmail_service_with_tokens(access_token, refresh_token)
                        service.users().stop(userId="me").execute()
                        stopped_methods.append("OAuth2")
                        print("Stopped OAuth2 watch")
                    except Exception as e:
                        errors.append(f"OAuth2 stop failed: {str(e)}")
                        print(f"Failed to stop OAuth2 watch: {e}")

                # Also try domain delegation as fallback
                try:
                    from autoreply.services.gmail import get_gmail_service

                    service = get_gmail_service()
                    service.users().stop(userId="me").execute()
                    stopped_methods.append("domain-wide delegation (fallback)")
                    print("Stopped domain delegation watch as fallback")
                except Exception as e:
                    errors.append(f"Domain delegation fallback failed: {str(e)}")
                    print(f"Failed to stop domain delegation fallback: {e}")

            if stopped_methods:
                message = f"Gmail Watch stopped using: {', '.join(stopped_methods)}"
                return Response({"message": message, "success": True, "errors": errors})
            else:
                return Response(
                    {"error": "Failed to stop any watches", "details": errors}, status=500
                )

        except Exception as e:
            return Response({"error": str(e)}, status=500)
