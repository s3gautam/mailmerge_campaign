"""Dataclasses for the Email Campaign MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"


class RecipientStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class Campaign:
    name: str
    subject: str = ""
    body: str = ""
    attachments: list[str] = field(default_factory=list)
    status: CampaignStatus = CampaignStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None


@dataclass
class Recipient:
    campaign_id: int
    email: str
    variables: dict[str, str] = field(default_factory=dict)
    status: RecipientStatus = RecipientStatus.PENDING
    id: int | None = None


@dataclass
class CampaignLog:
    campaign_id: int
    recipient_email: str
    status: RecipientStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    failure_reason: str | None = None
    id: int | None = None
