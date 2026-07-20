"""Centralized Gmail API access.

Every module that needs to send mail must go through this service. No other
module should import ``googleapiclient`` or perform OAuth directly.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("gmail_service")

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailServiceError(Exception):
    """Raised when a Gmail send operation fails."""


class GmailService:
    """Thin, authenticated wrapper around the Gmail API."""

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
    ) -> None:
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._service = None

    def _get_credentials(self) -> Credentials:
        creds: Credentials | None = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not creds or not creds.valid:
            if not os.path.exists(self.credentials_path):
                raise GmailServiceError(
                    f"Gmail credentials file not found at '{self.credentials_path}'. "
                    "Download a Desktop-app OAuth client from Google Cloud Console."
                )
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
            except Exception as exc:
                # A stale/revoked token or malformed credentials file must not keep
                # failing the same way forever; drop the token so the next attempt
                # falls through to a fresh interactive OAuth flow.
                if os.path.exists(self.token_path):
                    os.remove(self.token_path)
                logger.error("Gmail authentication failed: %s", exc)
                raise GmailServiceError(f"Gmail authentication failed: {exc}") from exc
            with open(self.token_path, "w") as token_file:
                token_file.write(creds.to_json())

        return creds

    def _get_service(self):
        if self._service is None:
            self._service = build("gmail", "v1", credentials=self._get_credentials())
        return self._service

    def reauthenticate(self) -> None:
        """Discard any cached token and re-run the interactive OAuth flow.

        Call this from the UI (e.g. a "Reauthenticate Gmail" button) when sending
        fails due to an expired, revoked, or otherwise broken token.
        """
        if os.path.exists(self.token_path):
            os.remove(self.token_path)
        self._service = None
        self._get_credentials()

    def send_email(self, to: str, subject: str, body: str) -> str:
        """Send a plain-text email. Returns the Gmail message id."""
        return self.send_email_with_attachments(to, subject, body, attachments=[])

    def send_email_with_attachments(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[str],
    ) -> str:
        """Send an email with zero or more file attachments. Returns the Gmail message id."""
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        for attachment_path in attachments:
            path = Path(attachment_path)
            mime_type, _ = mimetypes.guess_type(path.name)
            mime_type = mime_type or "application/octet-stream"
            with path.open("rb") as f:
                part = MIMEApplication(f.read(), _subtype=mime_type.split("/")[-1])
            part.add_header("Content-Disposition", "attachment", filename=path.name)
            message.attach(part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        try:
            sent = (
                self._get_service()
                .users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
        except GmailServiceError:
            raise
        except (HttpError, GoogleAuthError, OSError) as exc:
            logger.error("Gmail send failed for %s: %s", to, exc)
            raise GmailServiceError(str(exc)) from exc

        return sent["id"]
