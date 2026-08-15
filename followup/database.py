"""SQLite persistence for follow-up history.

Additive to the existing schema — a new table only, no changes to the
campaign/recipient tables. No SQL lives outside this module.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from followup.models import FollowUpLog, FollowUpStatus

SCHEMA = """
CREATE TABLE IF NOT EXISTS follow_up_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    failure_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_follow_up_log_thread ON follow_up_log(thread_id);
"""


class FollowUpDatabase:
    def __init__(self, db_path: str | Path = "campaign.db") -> None:
        self.db_path = str(db_path)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add_log(self, log: FollowUpLog) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO follow_up_log "
                "(thread_id, recipient_email, subject, status, timestamp, failure_reason) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    log.thread_id,
                    log.recipient_email,
                    log.subject,
                    log.status.value,
                    log.timestamp.isoformat(),
                    log.failure_reason,
                ),
            )

    def last_followup_dates(self, thread_ids: list[str]) -> dict[str, datetime]:
        """Most recent successful follow-up timestamp per thread id."""
        if not thread_ids:
            return {}
        placeholders = ",".join("?" for _ in thread_ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT thread_id, MAX(timestamp) AS last_ts FROM follow_up_log "
                f"WHERE thread_id IN ({placeholders}) AND status = ? "
                f"GROUP BY thread_id",
                (*thread_ids, FollowUpStatus.SENT.value),
            ).fetchall()
        return {row["thread_id"]: datetime.fromisoformat(row["last_ts"]) for row in rows}
