"""Application entrypoint: wires database, services, and UI pages together."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStackedWidget, QToolBar

from campaign.campaign_manager import CampaignManager
from campaign.campaign_sender import CampaignSender
from campaign.database import Database
from campaign.logging_config import configure_logging
from campaign.models import Campaign, CampaignStatus, Recipient
from services.gmail_service import GmailService, GmailServiceError
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

        toolbar = QToolBar("Gmail")
        toolbar.addAction("Reauthenticate Gmail", self._on_reauthenticate)
        self.addToolBar(toolbar)

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

    def start_send(self, campaign: Campaign, recipients: list[Recipient], mode: str = "send") -> None:
        progress_screen = CampaignProgress(mode=mode)
        self.stack.addWidget(progress_screen)
        self.stack.setCurrentWidget(progress_screen)
        self._active_progress_screen = progress_screen

        worker = SendWorker(self.sender, campaign, recipients, mode=mode)
        worker.progress.connect(progress_screen.update_progress)
        worker.finished_sending.connect(lambda result: self._on_send_finished(campaign, result, mode))
        worker.failed.connect(lambda message: self._on_send_failed(campaign, message, mode))
        self._active_worker = worker
        worker.start()

    def _on_send_finished(self, campaign: Campaign, result, mode: str) -> None:
        if mode == "send":
            status = CampaignStatus.COMPLETED if result.failed == 0 else CampaignStatus.FAILED
            label = "Sent"
        else:
            status = CampaignStatus.DRAFTS_CREATED if result.failed == 0 else CampaignStatus.FAILED
            label = "Drafted"
        self.manager.set_status(campaign, status)
        self.dashboard.refresh()
        self._active_worker = None
        QMessageBox.information(
            self,
            "Campaign finished",
            f"{label}: {result.sent}, Failed: {result.failed}",
        )
        self.stack.setCurrentWidget(self.dashboard)

    def _on_send_failed(self, campaign: Campaign, message: str, mode: str) -> None:
        self.manager.set_status(campaign, CampaignStatus.FAILED)
        self.dashboard.refresh()
        self._active_worker = None
        title = "Campaign send failed" if mode == "send" else "Draft creation failed"
        QMessageBox.critical(self, title, message)
        self.stack.setCurrentWidget(self.dashboard)

    def _on_reauthenticate(self) -> None:
        QMessageBox.information(
            self,
            "Reauthenticate Gmail",
            "Your browser will open so you can sign in to Gmail. "
            "Complete the sign-in there, then return to this window.",
        )
        try:
            self.gmail_service.reauthenticate()
        except GmailServiceError as exc:
            QMessageBox.critical(self, "Reauthentication failed", str(exc))
            return
        QMessageBox.information(self, "Reauthenticate Gmail", "Gmail authentication succeeded.")


def main() -> None:
    configure_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
