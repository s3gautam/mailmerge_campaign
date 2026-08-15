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

# gmail.compose covers both sending and draft management (a superset of
# gmail.send), so a single scope supports send_email_with_attachments() and
# create_draft_with_attachments().
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


class GmailServiceError(Exception):
    """Raised when a Gmail send operation fails."""


def _sanitize_header(value: str) -> str:
    """Collapse embedded newlines so header values can't break RFC 5322 folding.

    A variable containing a literal newline (e.g. pasted multi-line text) would
    otherwise raise ``HeaderParseError: folded header contains newline`` deep
    inside the email library when the message is serialized.
    """
    return " ".join(value.splitlines()).strip()


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

    @staticmethod
    def _build_raw_message(
        to: str,
        subject: str,
        body: str,
        attachments: list[str],
        body_html: str | None,
    ) -> str:
        """Build a base64url-encoded RFC 5322 message.

        ``body`` is the plain-text fallback. If ``body_html`` is provided, the
        message is built as ``multipart/alternative`` so HTML-capable clients
        render the rich version while others fall back to plain text.
        """
        message = MIMEMultipart()
        message["to"] = _sanitize_header(to)
        message["subject"] = _sanitize_header(subject)

        if body_html is not None:
            alternative = MIMEMultipart("alternative")
            alternative.attach(MIMEText(body, "plain"))
            alternative.attach(MIMEText(body_html, "html"))
            message.attach(alternative)
        else:
            message.attach(MIMEText(body, "plain"))

        for attachment_path in attachments:
            path = Path(attachment_path)
            mime_type, _ = mimetypes.guess_type(path.name)
            mime_type = mime_type or "application/octet-stream"
            with path.open("rb") as f:
                part = MIMEApplication(f.read(), _subtype=mime_type.split("/")[-1])
            part.add_header("Content-Disposition", "attachment", filename=path.name)
            message.attach(part)

        return base64.urlsafe_b64encode(message.as_bytes()).decode()

    def send_email(self, to: str, subject: str, body: str) -> str:
        """Send a plain-text email. Returns the Gmail message id."""
        return self.send_email_with_attachments(to, subject, body, attachments=[])

    def send_email_with_attachments(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[str],
        body_html: str | None = None,
    ) -> str:
        """Send an email with zero or more file attachments. Returns the Gmail message id."""
        raw = self._build_raw_message(to, subject, body, attachments, body_html)

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

    def create_draft_with_attachments(
        self,
        to: str,
        subject: str,
        body: str,
        attachments: list[str],
        body_html: str | None = None,
    ) -> str:
        """Create a Gmail draft (not sent). Returns the draft id."""
        raw = self._build_raw_message(to, subject, body, attachments, body_html)

        try:
            draft = (
                self._get_service()
                .users()
                .drafts()
                .create(userId="me", body={"message": {"raw": raw}})
                .execute()
            )
        except GmailServiceError:
            raise
        except (HttpError, GoogleAuthError, OSError) as exc:
            logger.error("Gmail draft creation failed for %s: %s", to, exc)
            raise GmailServiceError(str(exc)) from exc

        return draft["id"]
