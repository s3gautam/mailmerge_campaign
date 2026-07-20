"""Background thread that runs a campaign send without blocking the UI."""

from __future__ import annotations

import logging

from PySide6.QtCore import QThread, Signal

from campaign.campaign_sender import CampaignSender, SendProgress
from campaign.models import Campaign, Recipient

logger = logging.getLogger("campaign_sender")


class SendWorker(QThread):
    progress = Signal(object)
    finished_sending = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        sender: CampaignSender,
        campaign: Campaign,
        recipients: list[Recipient],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.sender = sender
        self.campaign = campaign
        self.recipients = recipients

    def run(self) -> None:
        try:
            result: SendProgress = self.sender.send(
                self.campaign, self.recipients, on_progress=self.progress.emit
            )
        except Exception as exc:  # last-resort guard so the UI never hangs silently
            logger.error("Campaign send crashed: %s", exc)
            self.failed.emit(str(exc))
            return
        self.finished_sending.emit(result)
