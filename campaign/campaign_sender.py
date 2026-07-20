"""Drives sending a validated campaign, one recipient at a time.

All Gmail traffic goes through the injected GmailService instance — this
module never calls the Gmail API directly.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from campaign.database import Database
from campaign.models import Campaign, CampaignLog, Recipient, RecipientStatus
from campaign.template_renderer import (
    missing_variables,
    render_body_html,
    render_template,
    strip_bold_markers,
)
from campaign.validators import is_valid_email
from services.gmail_service import GmailService

logger = logging.getLogger("campaign_sender")


@dataclass
class SendProgress:
    total: int
    sent: int = 0
    failed: int = 0
    current_email: str = ""

    @property
    def remaining(self) -> int:
        return self.total - self.sent - self.failed


ProgressCallback = Callable[[SendProgress], None]


class CampaignSender:
    def __init__(self, database: Database, gmail_service: GmailService) -> None:
        self.database = database
        self.gmail_service = gmail_service

    def send(
        self,
        campaign: Campaign,
        recipients: list[Recipient],
        on_progress: ProgressCallback | None = None,
    ) -> SendProgress:
        progress = SendProgress(total=len(recipients))
        seen_emails: set[str] = set()

        for recipient in recipients:
            progress.current_email = recipient.email
            if on_progress:
                on_progress(progress)

            skip_reason = self._skip_reason(campaign, recipient, seen_emails)
            if skip_reason is not None:
                self._record(campaign, recipient, RecipientStatus.FAILED, skip_reason)
                progress.failed += 1
                logger.warning("Skipped %s: %s", recipient.email, skip_reason)
                if on_progress:
                    on_progress(progress)
                continue

            seen_emails.add(recipient.email.strip().lower())

            try:
                subject = render_template(campaign.subject, recipient.variables)
                body = render_template(campaign.body, recipient.variables)
                self.gmail_service.send_email_with_attachments(
                    to=recipient.email,
                    subject=subject,
                    body=strip_bold_markers(body),
                    body_html=render_body_html(body),
                    attachments=campaign.attachments,
                )
            except Exception as exc:  # never let one recipient's failure kill the whole send loop
                self._record(campaign, recipient, RecipientStatus.FAILED, str(exc))
                progress.failed += 1
                logger.warning("Failed to send to %s: %s", recipient.email, exc)
            else:
                self._record(campaign, recipient, RecipientStatus.SENT, None)
                progress.sent += 1

            if on_progress:
                on_progress(progress)

        return progress

    @staticmethod
    def _skip_reason(campaign: Campaign, recipient: Recipient, seen_emails: set[str]) -> str | None:
        email = recipient.email.strip()
        if not is_valid_email(email):
            return f"Invalid email format: {email or '(blank)'}"
        if email.lower() in seen_emails:
            return f"Duplicate email: {email}"
        missing = {
            *missing_variables(campaign.subject, recipient.variables),
            *missing_variables(campaign.body, recipient.variables),
        }
        if missing:
            return f"Missing variable(s): {', '.join(sorted(missing))}"
        return None

    def _record(
        self,
        campaign: Campaign,
        recipient: Recipient,
        status: RecipientStatus,
        failure_reason: str | None,
    ) -> None:
        if recipient.id is not None:
            self.database.update_recipient_status(recipient.id, status)
        self.database.add_log(
            CampaignLog(
                campaign_id=campaign.id,
                recipient_email=recipient.email,
                status=status,
                failure_reason=failure_reason,
            )
        )
