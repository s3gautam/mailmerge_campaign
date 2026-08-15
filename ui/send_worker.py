"""Background thread that runs a campaign send/draft operation without blocking the UI."""

from __future__ import annotations

import logging
from typing import Literal

from PySide6.QtCore import QThread, Signal

from campaign.campaign_sender import CampaignSender, SendProgress
from campaign.models import Campaign, Recipient

logger = logging.getLogger("campaign_sender")

Mode = Literal["send", "draft"]


class SendWorker(QThread):
    progress = Signal(object)
    finished_sending = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        sender: CampaignSender,
        campaign: Campaign,
        recipients: list[Recipient],
        mode: Mode = "send",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sender = sender
        self.campaign = campaign
        self.recipients = recipients
        self.mode = mode

    def run(self) -> None:
        operation = self.sender.send if self.mode == "send" else self.sender.create_drafts
        try:
            result: SendProgress = operation(
                self.campaign, self.recipients, on_progress=self.progress.emit
            )
        except Exception as exc:  # last-resort guard so the UI never hangs silently
            logger.error("Campaign %s crashed: %s", self.mode, exc)
            self.failed.emit(str(exc))
            return
        self.finished_sending.emit(result)
