"""Read-only view of a campaign's send logs."""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from campaign.database import Database

COLUMNS = ["Recipient", "Status", "Timestamp", "Failure Reason"]


class CampaignLogs(QWidget):
    def __init__(self, database: Database, campaign_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.database = database
        self.campaign_id = campaign_id

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

        self.refresh()

    def refresh(self) -> None:
        logs = self.database.list_logs(self.campaign_id)
        self.table.setRowCount(len(logs))
        for row, log in enumerate(logs):
            values = [
                log.recipient_email,
                log.status.value,
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                log.failure_reason or "",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
