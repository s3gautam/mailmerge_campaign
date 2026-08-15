"""Background threads for the Follow Up tab (searching and sending) so
Gmail API calls never block the UI thread.
"""

from __future__ import annotations

import logging
from datetime import date

from PySide6.QtCore import QThread, Signal

from followup.followup_manager import FollowUpCandidate, FollowUpManager, FollowUpProgress
from services.gmail_service import GmailServiceError

logger = logging.getLogger("followup_manager")


class FindCandidatesWorker(QThread):
    finished_search = Signal(list)
    failed = Signal(str)

    def __init__(
        self,
        manager: FollowUpManager,
        date_from: date,
        date_to: date,
        keyword: str,
        subject_keyword: str,
        reply_filter: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.date_from = date_from
        self.date_to = date_to
        self.keyword = keyword
        self.subject_keyword = subject_keyword
        self.reply_filter = reply_filter

    def run(self) -> None:
        try:
            candidates: list[FollowUpCandidate] = self.manager.find_candidates(
                date_from=self.date_from,
                date_to=self.date_to,
                keyword=self.keyword,
                subject_keyword=self.subject_keyword,
                reply_filter=self.reply_filter,
            )
        except GmailServiceError as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:  # last-resort guard so the UI never hangs silently
            logger.error("Follow-up search crashed: %s", exc)
            self.failed.emit(str(exc))
            return
        self.finished_search.emit(candidates)


class FollowUpWorker(QThread):
    progress = Signal(object)
    finished_sending = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        manager: FollowUpManager,
        candidates: list[FollowUpCandidate],
        body: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.candidates = candidates
        self.body = body

    def run(self) -> None:
        try:
            result: FollowUpProgress = self.manager.send_followups(
                self.candidates, self.body, on_progress=self.progress.emit
            )
        except Exception as exc:  # last-resort guard so the UI never hangs silently
            logger.error("Follow-up send crashed: %s", exc)
            self.failed.emit(str(exc))
            return
        self.finished_sending.emit(result)
