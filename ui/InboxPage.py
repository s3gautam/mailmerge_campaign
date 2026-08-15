"""Inbox tab: list threads and open one for reading/replying."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from inbox.inbox_manager import InboxManager
from services.gmail_service import GmailServiceError, ThreadSummary

COLUMNS = ["From", "Subject", "Snippet", "Date"]


class InboxPage(QWidget):
    def __init__(
        self,
        manager: InboxManager,
        on_open_thread: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.on_open_thread = on_open_thread
        self._threads: list[ThreadSummary] = []

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search mail (Gmail search syntax, e.g. from:someone@x.com)")
        self.refresh_button = QPushButton("Refresh")
        self.open_button = QPushButton("Open")

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_open)

        self.refresh_button.clicked.connect(self.refresh)
        self.open_button.clicked.connect(self._on_open)

        search_row = QHBoxLayout()
        search_row.addWidget(self.search_input)
        search_row.addWidget(self.refresh_button)

        layout = QVBoxLayout(self)
        layout.addLayout(search_row)
        layout.addWidget(self.table)
        layout.addWidget(self.open_button)

    def refresh(self) -> None:
        try:
            self._threads = self.manager.list_threads(query=self.search_input.text().strip())
        except GmailServiceError as exc:
            QMessageBox.critical(self, "Could not load inbox", str(exc))
            return

        self.table.setRowCount(len(self._threads))
        for row, thread in enumerate(self._threads):
            values = [thread.sender, thread.subject, thread.snippet, thread.date]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def _selected_thread(self) -> ThreadSummary | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._threads):
            return None
        return self._threads[row]

    def _on_open(self) -> None:
        thread = self._selected_thread()
        if thread is None:
            QMessageBox.warning(self, "No selection", "Select a thread to open.")
            return
        self.on_open_thread(thread.id)
