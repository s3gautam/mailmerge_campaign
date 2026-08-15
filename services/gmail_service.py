"""Centralized Gmail API access.

Every module that needs to talk to Gmail must go through this service. No
other module should import ``googleapiclient`` or perform OAuth directly.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
from dataclasses import dataclass, field
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

# gmail.modify covers reading, composing, sending, and draft management in
# one scope, so it supports every method on this service.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailServiceError(Exception):
    """Raised when a Gmail operation fails."""


@dataclass
class ThreadSummary:
    """One row in an inbox thread listing."""

    id: str
    subject: str
    sender: str
    date: str
    snippet: str


@dataclass
class Message:
    """A single message within a thread."""

    id: str
    thread_id: str
    sender: str
    to: str
    subject: str
    date: str
    body: str
    message_id_header: str = ""


@dataclass
class ThreadDetail:
    """A full thread with all of its messages, oldest first."""

    id: str
    subject: str
    messages: list[Message] = field(default_factory=list)


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

    def list_threads(self, query: str = "", max_results: int = 20) -> list[ThreadSummary]:
        """List inbox threads, most recent first, as lightweight summaries."""
        try:
            response = (
                self._get_service()
                .users()
                .threads()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
        except (HttpError, GoogleAuthError, OSError) as exc:
            logger.error("Gmail thread listing failed: %s", exc)
            raise GmailServiceError(str(exc)) from exc

        summaries = []
        for thread_ref in response.get("threads", []):
            summaries.append(self._get_thread_summary(thread_ref["id"]))
        return summaries

    def _get_thread_summary(self, thread_id: str) -> ThreadSummary:
        try:
            thread = (
                self._get_service()
                .users()
                .threads()
                .get(
                    userId="me",
                    id=thread_id,
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                .execute()
            )
        except (HttpError, GoogleAuthError, OSError) as exc:
            logger.error("Gmail thread metadata fetch failed for %s: %s", thread_id, exc)
            raise GmailServiceError(str(exc)) from exc

        last_message = thread["messages"][-1]
        headers = {h["name"]: h["value"] for h in last_message["payload"].get("headers", [])}
        return ThreadSummary(
            id=thread_id,
            subject=headers.get("Subject", "(no subject)"),
            sender=headers.get("From", ""),
            date=headers.get("Date", ""),
            snippet=last_message.get("snippet", ""),
        )

    def get_thread(self, thread_id: str) -> ThreadDetail:
        """Fetch a full thread with all messages and decoded plain-text bodies."""
        try:
            thread = (
                self._get_service()
                .users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )
        except (HttpError, GoogleAuthError, OSError) as exc:
            logger.error("Gmail thread fetch failed for %s: %s", thread_id, exc)
            raise GmailServiceError(str(exc)) from exc

        messages = [self._parse_message(m) for m in thread.get("messages", [])]
        subject = messages[0].subject if messages else "(no subject)"
        return ThreadDetail(id=thread_id, subject=subject, messages=messages)

    @staticmethod
    def _parse_message(raw_message: dict) -> Message:
        headers = {h["name"]: h["value"] for h in raw_message["payload"].get("headers", [])}
        return Message(
            id=raw_message["id"],
            thread_id=raw_message["threadId"],
            sender=headers.get("From", ""),
            to=headers.get("To", ""),
            subject=headers.get("Subject", "(no subject)"),
            date=headers.get("Date", ""),
            body=GmailService._extract_plain_text(raw_message["payload"]),
            message_id_header=headers.get("Message-ID", headers.get("Message-Id", "")),
        )

    @staticmethod
    def _extract_plain_text(payload: dict) -> str:
        if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            text = GmailService._extract_plain_text(part)
            if text:
                return text
        return ""

    def reply_to_thread(
        self,
        thread_id: str,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str = "",
    ) -> str:
        """Send a reply within an existing thread. Returns the sent message id."""
        message = MIMEMultipart()
        message["to"] = _sanitize_header(to)
        clean_subject = _sanitize_header(subject)
        message["subject"] = clean_subject if clean_subject.lower().startswith("re:") else f"Re: {clean_subject}"
        message.attach(MIMEText(body, "plain"))
        if in_reply_to:
            message["In-Reply-To"] = in_reply_to
            message["References"] = in_reply_to

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        try:
            sent = (
                self._get_service()
                .users()
                .messages()
                .send(userId="me", body={"raw": raw, "threadId": thread_id})
                .execute()
            )
        except (HttpError, GoogleAuthError, OSError) as exc:
            logger.error("Gmail reply failed for thread %s: %s", thread_id, exc)
            raise GmailServiceError(str(exc)) from exc

        return sent["id"]
