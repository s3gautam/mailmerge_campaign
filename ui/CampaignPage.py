"""Campaign dashboard: list, create, open, delete campaigns; view logs."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from campaign.campaign_manager import CampaignManager
from campaign.models import Campaign

COLUMNS = ["Campaign Name", "Created Time", "Recipients", "Sent", "Failed", "Status"]


class CampaignPage(QWidget):
    def __init__(self, manager: CampaignManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._campaigns: list[Campaign] = []

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.create_button = QPushButton("Create")
        self.open_button = QPushButton("Open")
        self.delete_button = QPushButton("Delete")
        self.logs_button = QPushButton("View Logs")

        self.create_button.clicked.connect(self._on_create)
        self.open_button.clicked.connect(self._on_open)
        self.delete_button.clicked.connect(self._on_delete)
        self.logs_button.clicked.connect(self._on_view_logs)

        actions = QHBoxLayout()
        for button in (self.create_button, self.open_button, self.delete_button, self.logs_button):
            actions.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(actions)

        self.refresh()

    def refresh(self) -> None:
        self._campaigns = self.manager.list_campaigns()
        self.table.setRowCount(len(self._campaigns))
        for row, campaign in enumerate(self._campaigns):
            summary = self.manager.get_summary(campaign.id) if campaign.id else {
                "recipients": 0,
                "sent": 0,
                "failed": 0,
            }
            values = [
                campaign.name,
                campaign.created_at.strftime("%Y-%m-%d %H:%M"),
                str(summary["recipients"]),
                str(summary["sent"]),
                str(summary["failed"]),
                campaign.status.value,
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def _selected_campaign(self) -> Campaign | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._campaigns):
            return None
        return self._campaigns[row]

    def _on_create(self) -> None:
        # Wiring to CampaignEditor happens at the application composition layer.
        pass

    def _on_open(self) -> None:
        if self._selected_campaign() is None:
            QMessageBox.warning(self, "No selection", "Select a campaign to open.")

    def _on_delete(self) -> None:
        campaign = self._selected_campaign()
        if campaign is None or campaign.id is None:
            QMessageBox.warning(self, "No selection", "Select a campaign to delete.")
            return
        confirm = QMessageBox.question(
            self, "Delete campaign", f"Delete '{campaign.name}'? This cannot be undone."
        )
        if confirm == QMessageBox.Yes:
            self.manager.delete_campaign(campaign.id)
            self.refresh()

    def _on_view_logs(self) -> None:
        if self._selected_campaign() is None:
            QMessageBox.warning(self, "No selection", "Select a campaign to view logs.")
