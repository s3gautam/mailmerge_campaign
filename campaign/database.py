"""SQLite persistence for campaigns, recipients, and logs.

No SQL lives outside this module.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from campaign.models import Campaign, CampaignLog, CampaignStatus, Recipient, RecipientStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaign (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    attachments TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipient (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaign(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    variables TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS campaign_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaign(id) ON DELETE CASCADE,
    recipient_email TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    failure_reason TEXT
);
"""


class Database:
    def __init__(self, db_path: str | Path = "campaign.db") -> None:
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- Campaign -----------------------------------------------------

    def create_campaign(self, campaign: Campaign) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO campaign (name, subject, body, attachments, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    campaign.name,
                    campaign.subject,
                    campaign.body,
                    json.dumps(campaign.attachments),
                    campaign.status.value,
                    campaign.created_at.isoformat(),
                ),
            )
            return int(cursor.lastrowid)

    def update_campaign(self, campaign: Campaign) -> None:
        if campaign.id is None:
            raise ValueError("Campaign must have an id to be updated")
        with self._connect() as conn:
            conn.execute(
                "UPDATE campaign SET name=?, subject=?, body=?, attachments=?, status=? WHERE id=?",
                (
                    campaign.name,
                    campaign.subject,
                    campaign.body,
                    json.dumps(campaign.attachments),
                    campaign.status.value,
                    campaign.id,
                ),
            )

    def delete_campaign(self, campaign_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM campaign WHERE id=?", (campaign_id,))

    def get_campaign(self, campaign_id: int) -> Campaign | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM campaign WHERE id=?", (campaign_id,)).fetchone()
            return self._row_to_campaign(row) if row else None

    def list_campaigns(self) -> list[Campaign]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM campaign ORDER BY created_at DESC").fetchall()
            return [self._row_to_campaign(row) for row in rows]

    @staticmethod
    def _row_to_campaign(row: sqlite3.Row) -> Campaign:
        return Campaign(
            id=row["id"],
            name=row["name"],
            subject=row["subject"],
            body=row["body"],
            attachments=json.loads(row["attachments"]),
            status=CampaignStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # -- Recipient ------------------------------------------------------

    def add_recipients(self, recipients: list[Recipient]) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO recipient (campaign_id, email, variables, status) VALUES (?, ?, ?, ?)",
                [
                    (r.campaign_id, r.email, json.dumps(r.variables), r.status.value)
                    for r in recipients
                ],
            )

    def update_recipient_status(self, recipient_id: int, status: RecipientStatus) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE recipient SET status=? WHERE id=?", (status.value, recipient_id)
            )

    def list_recipients(self, campaign_id: int) -> list[Recipient]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM recipient WHERE campaign_id=?", (campaign_id,)
            ).fetchall()
            return [
                Recipient(
                    id=row["id"],
                    campaign_id=row["campaign_id"],
                    email=row["email"],
                    variables=json.loads(row["variables"]),
                    status=RecipientStatus(row["status"]),
                )
                for row in rows
            ]

    # -- CampaignLog ------------------------------------------------------

    def add_log(self, log: CampaignLog) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO campaign_log (campaign_id, recipient_email, status, timestamp, failure_reason) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    log.campaign_id,
                    log.recipient_email,
                    log.status.value,
                    log.timestamp.isoformat(),
                    log.failure_reason,
                ),
            )

    def list_logs(self, campaign_id: int) -> list[CampaignLog]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM campaign_log WHERE campaign_id=? ORDER BY timestamp", (campaign_id,)
            ).fetchall()
            return [
                CampaignLog(
                    id=row["id"],
                    campaign_id=row["campaign_id"],
                    recipient_email=row["recipient_email"],
                    status=RecipientStatus(row["status"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    failure_reason=row["failure_reason"],
                )
                for row in rows
            ]
