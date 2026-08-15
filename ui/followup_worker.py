"""Background thread that sends follow-ups without blocking the UI."""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

from followup.followup_manager import FollowUpCandidate, FollowUpManager, FollowUpProgress

logger = logging.getLogger("followup_manager")


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
