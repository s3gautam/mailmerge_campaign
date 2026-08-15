"""Dataclasses for the job-application follow-up feature."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class FollowUpStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"


@dataclass
class FollowUpCandidate:
    """A sent-mail thread that could receive a follow-up."""

    thread_id: str
    recipient_email: str
    company: str
    subject: str
    message_count: int
    replied: bool
    last_message_id_header: str = ""
    last_followup_at: datetime | None = None


@dataclass
class FollowUpLog:
    thread_id: str
    recipient_email: str
    subject: str
    status: FollowUpStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    failure_reason: str | None = None
    id: int | None = None
