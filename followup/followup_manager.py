"""Finds job-application threads to follow up on and sends the follow-ups.

Never calls the Gmail API directly — always goes through GmailService,
same pattern as campaign/campaign_manager.py.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from email.utils import parseaddr

from followup.database import FollowUpDatabase
from followup.models import FollowUpCandidate, FollowUpLog, FollowUpStatus
from services.gmail_service import GmailService, ThreadDetail


def _bare_address(header_value: str) -> str:
    return parseaddr(header_value)[1] or header_value.strip()


def _company_label(email: str) -> str:
    domain = email.split("@")[-1] if "@" in email else email
    domain = domain.split(".")[0]
    words = [w for w in re.split(r"[-_]", domain) if w]
    return " ".join(w.capitalize() for w in words) or domain


def _build_keyword_clause(keyword: str) -> str:
    """Turn a comma/semicolon-separated keyword list into a Gmail OR clause.

    "antilease, brexy, seedflex" -> "(antilease OR brexy OR seedflex)" so a
    thread matching any one of the companies is found. A single term is
    passed through unwrapped.
    """
    terms = [term.strip() for term in re.split(r"[,;]", keyword) if term.strip()]
    if not terms:
        return ""
    if len(terms) == 1:
        return terms[0]
    return "(" + " OR ".join(terms) + ")"


@dataclass
class FollowUpProgress:
    total: int
    sent: int = 0
    failed: int = 0
    current_email: str = ""

    @property
    def remaining(self) -> int:
        return self.total - self.sent - self.failed


ProgressCallback = Callable[[FollowUpProgress], None]


class FollowUpManager:
    def __init__(self, database: FollowUpDatabase, gmail_service: GmailService) -> None:
        self.database = database
        self.gmail_service = gmail_service

    def find_candidates(
        self,
        date_from: date,
        date_to: date,
        keyword: str = "",
        subject_keyword: str = "",
        reply_filter: str = "all",
        max_results: int = 50,
    ) -> list[FollowUpCandidate]:
        """Search Sent mail for a date range and classify each thread.

        ``keyword`` is a comma/semicolon-separated list of companies (OR'd
        together). ``subject_keyword`` is an exact phrase required in the
        subject line (e.g. "Application for role of") -- ANDed with the
        company list and date range, narrowing the results.
        ``reply_filter`` is one of "all", "replied", "not_replied".
        """
        query_parts = [
            "in:sent",
            f"after:{date_from.strftime('%Y/%m/%d')}",
            f"before:{(date_to + timedelta(days=1)).strftime('%Y/%m/%d')}",
        ]
        keyword_clause = _build_keyword_clause(keyword)
        if keyword_clause:
            query_parts.append(keyword_clause)
        if subject_keyword.strip():
            escaped = subject_keyword.strip().replace('"', '\\"')
            query_parts.append(f'subject:"{escaped}"')

        thread_ids = self.gmail_service.list_thread_ids(
            query=" ".join(query_parts), max_results=max_results
        )
        my_email = self.gmail_service.get_profile_email()
        last_followups = self.database.last_followup_dates(thread_ids)

        candidates = []
        for thread_id in thread_ids:
            thread = self.gmail_service.get_thread(thread_id)
            candidate = self._build_candidate(thread, my_email, last_followups.get(thread_id))
            if candidate is None:
                continue
            if reply_filter == "replied" and not candidate.replied:
                continue
            if reply_filter == "not_replied" and candidate.replied:
                continue
            candidates.append(candidate)
        return candidates

    @staticmethod
    def _build_candidate(
        thread: ThreadDetail, my_email: str, last_followup_at
    ) -> FollowUpCandidate | None:
        if not thread.messages:
            return None

        my_email_lower = my_email.lower()

        # Recipient: the first address anywhere in the thread that isn't me,
        # checking each message's To then From in order. Scanning every
        # message (not just assuming the first message's To header is
        # populated/well-formed) makes this resilient to messages sent to
        # multiple people, missing headers, or CC-only addressing.
        recipient_email = ""
        for message in thread.messages:
            for header_value in (message.to, message.sender):
                addr = _bare_address(header_value)
                if addr and addr.lower() != my_email_lower:
                    recipient_email = addr
                    break
            if recipient_email:
                break

        if not recipient_email:
            return None

        # Subject: prefer the thread-level subject, but fall back to
        # scanning every message in case the first one's header was blank.
        subject = thread.subject.strip() if thread.subject else ""
        if not subject:
            subject = next((m.subject.strip() for m in thread.messages if m.subject.strip()), "")
        subject = subject or "(no subject)"

        last_message = thread.messages[-1]
        replied = (
            len(thread.messages) > 1
            and _bare_address(last_message.sender).lower() != my_email_lower
        )

        return FollowUpCandidate(
            thread_id=thread.id,
            recipient_email=recipient_email,
            company=_company_label(recipient_email),
            subject=subject,
            message_count=len(thread.messages),
            replied=replied,
            last_message_id_header=last_message.message_id_header,
            last_followup_at=last_followup_at,
        )

    def send_followups(
        self,
        candidates: list[FollowUpCandidate],
        body: str,
        on_progress: ProgressCallback | None = None,
    ) -> FollowUpProgress:
        progress = FollowUpProgress(total=len(candidates))

        for candidate in candidates:
            progress.current_email = candidate.recipient_email
            if on_progress:
                on_progress(progress)

            try:
                self.gmail_service.reply_to_thread(
                    thread_id=candidate.thread_id,
                    to=candidate.recipient_email,
                    subject=candidate.subject,
                    body=body,
                    in_reply_to=candidate.last_message_id_header,
                )
            except Exception as exc:  # never let one thread's failure kill the whole batch
                self._record(candidate, FollowUpStatus.FAILED, str(exc))
                progress.failed += 1
            else:
                self._record(candidate, FollowUpStatus.SENT, None)
                progress.sent += 1

            if on_progress:
                on_progress(progress)

        return progress

    def _record(
        self, candidate: FollowUpCandidate, status: FollowUpStatus, failure_reason: str | None
    ) -> None:
        self.database.add_log(
            FollowUpLog(
                thread_id=candidate.thread_id,
                recipient_email=candidate.recipient_email,
                subject=candidate.subject,
                status=status,
                failure_reason=failure_reason,
            )
        )
