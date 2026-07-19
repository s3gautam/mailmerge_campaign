"""Application entrypoint: wires database, services, and UI pages together."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget

from campaign.campaign_manager import CampaignManager
from campaign.campaign_sender import CampaignSender
from campaign.database import Database
from campaign.logging_config import configure_logging
from campaign.models import Campaign, CampaignStatus, Recipient
from services.gmail_service import GmailService
from ui.CampaignEditor import CampaignEditor
from ui.CampaignLogs import CampaignLogs
from ui.CampaignPage import CampaignPage
from ui.CampaignProgress import CampaignProgress
from ui.send_worker import SendWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Gmail Campaign")
        self.resize(900, 600)

        self.database = Database("campaign.db")
        self.manager = CampaignManager(self.database)
        self.gmail_service = GmailService()
        self.sender = CampaignSender(self.database, self.gmail_service)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.dashboard = CampaignPage(
            self.manager,
            on_open_campaign=self.open_campaign,
            on_view_logs=self.view_logs,
        )
        self.stack.addWidget(self.dashboard)
        self.stack.setCurrentWidget(self.dashboard)

        self._active_worker: SendWorker | None = None
        self._active_progress_screen: CampaignProgress | None = None

    def open_campaign(self, campaign: Campaign) -> None:
        editor = CampaignEditor(self.manager, campaign, on_send=self.start_send)
        self.stack.addWidget(editor)
        self.stack.setCurrentWidget(editor)

    def view_logs(self, campaign: Campaign) -> None:
        if campaign.id is None:
            return
        logs_view = CampaignLogs(self.database, campaign.id)
        self.stack.addWidget(logs_view)
        self.stack.setCurrentWidget(logs_view)

    def start_send(self, campaign: Campaign, recipients: list[Recipient]) -> None:
        progress_screen = CampaignProgress()
        self.stack.addWidget(progress_screen)
        self.stack.setCurrentWidget(progress_screen)
        self._active_progress_screen = progress_screen

        worker = SendWorker(self.sender, campaign, recipients)
        worker.progress.connect(progress_screen.update_progress)
        worker.finished_sending.connect(lambda result: self._on_send_finished(campaign, result))
        self._active_worker = worker
        worker.start()

    def _on_send_finished(self, campaign: Campaign, result) -> None:
        status = CampaignStatus.COMPLETED if result.failed == 0 else CampaignStatus.FAILED
        self.manager.set_status(campaign, status)
        self.dashboard.refresh()
        self._active_worker = None
        QMessageBox.information(
            self,
            "Campaign finished",
            f"Sent: {result.sent}, Failed: {result.failed}",
        )
        self.stack.setCurrentWidget(self.dashboard)


def main() -> None:
    configure_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
