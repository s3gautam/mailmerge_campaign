"""Pre-send validation for a campaign and its recipients."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from campaign.template_renderer import missing_variables

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Gmail's hard cap on a full outgoing message (including attachments) is 25 MB.
GMAIL_ATTACHMENT_LIMIT_BYTES = 25 * 1024 * 1024


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_PATTERN.match(email.strip()))


def validate_attachments(attachments: list[str]) -> list[str]:
    errors = []
    total_size = 0
    for path_str in attachments:
        path = Path(path_str)
        if not path.exists():
            errors.append(f"Attachment not found: {path_str}")
            continue
        if not path.is_file() or not _is_readable(path):
            errors.append(f"Attachment not readable: {path_str}")
            continue
        total_size += path.stat().st_size

    if total_size > GMAIL_ATTACHMENT_LIMIT_BYTES:
        errors.append(
            f"Attachments exceed Gmail's {GMAIL_ATTACHMENT_LIMIT_BYTES // (1024 * 1024)}MB limit"
        )
    return errors


def _is_readable(path: Path) -> bool:
    try:
        with path.open("rb"):
            return True
    except OSError:
        return False


def validate_campaign(
    subject: str,
    body: str,
    attachments: list[str],
    recipients: list[dict[str, str]],
    email_field: str = "email",
) -> ValidationResult:
    """Validate a campaign before sending. ``recipients`` is a list of dicts with
    an ``email_field`` key plus arbitrary variable keys."""
    result = ValidationResult()

    if not subject.strip():
        result.add("Subject cannot be blank")
    if not body.strip():
        result.add("Body cannot be blank")

    if not recipients:
        result.add("CSV has no recipients")

    seen_emails: set[str] = set()
    for row in recipients:
        email = row.get(email_field, "").strip()
        if not is_valid_email(email):
            result.add(f"Invalid email format: {email or '(blank)'}")
            continue
        normalized = email.lower()
        if normalized in seen_emails:
            result.add(f"Duplicate email: {email}")
        seen_emails.add(normalized)

        variables = {k: v for k, v in row.items() if k != email_field}
        for missing in {*missing_variables(subject, variables), *missing_variables(body, variables)}:
            result.add(f"Missing variable '{{{{{missing}}}}}' for recipient {email}")

    for error in validate_attachments(attachments):
        result.add(error)

    return result
