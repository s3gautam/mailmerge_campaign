"""Follow Up tab: find sent job-application threads and send follow-ups."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from followup.followup_manager import FollowUpCandidate, FollowUpManager
from services.gmail_service import GmailServiceError

COLUMNS = ["Include", "Company", "Email", "Subject", "Replied", "Messages", "Last followed up"]

REPLY_FILTER_VALUES = {"All": "all", "Replied": "replied", "Not replied": "not_replied"}


class FollowUpPage(QWidget):
    def __init__(
        self,
        manager: FollowUpManager,
        on_send: Callable[[list[FollowUpCandidate], str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.on_send = on_send
        self._candidates: list[FollowUpCandidate] = []

        today = QDate.currentDate()
        self.from_date = QDateEdit(today.addMonths(-1))
        self.from_date.setCalendarPopup(True)
        self.to_date = QDateEdit(today)
        self.to_date.setCalendarPopup(True)

        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText(
            "Keyword(s), comma-separated (optional), e.g. antilease, brexy, seedflex"
        )

        self.reply_filter = QComboBox()
        self.reply_filter.addItems(list(REPLY_FILTER_VALUES.keys()))
        self.reply_filter.setCurrentText("Not replied")

        self.find_button = QPushButton("Find Candidates")
        self.find_button.clicked.connect(self._on_find)

        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 260)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_row_selected)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setPlaceholderText("Select a row to see its full details here.")
        self.detail_view.setMaximumHeight(90)

        self.select_all_button = QPushButton("Select All")
        self.select_none_button = QPushButton("Select None")
        self.select_all_button.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_button.clicked.connect(lambda: self._set_all_checked(False))

        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText(
            "Write your follow-up message (sent as-is into every selected thread)..."
        )

        self.preview_button = QPushButton("Preview Follow-ups")
        self.send_button = QPushButton("Send Follow-ups")
        self.preview_button.clicked.connect(self._on_preview)
        self.send_button.clicked.connect(self._on_send)

        filter_row = QHBoxLayout()
        for widget in (
            QLabel("From"),
            self.from_date,
            QLabel("To"),
            self.to_date,
            self.keyword_input,
            self.reply_filter,
            self.find_button,
        ):
            filter_row.addWidget(widget)

        select_row = QHBoxLayout()
        select_row.addWidget(self.select_all_button)
        select_row.addWidget(self.select_none_button)
        select_row.addStretch()

        footer_row = QHBoxLayout()
        footer_row.addWidget(self.preview_button)
        footer_row.addWidget(self.send_button)

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Selected row"))
        layout.addWidget(self.detail_view)
        layout.addLayout(select_row)
        layout.addWidget(QLabel("Follow-up message"))
        layout.addWidget(self.body_input)
        layout.addLayout(footer_row)

    def _on_find(self) -> None:
        date_from = self.from_date.date().toPython()
        date_to = self.to_date.date().toPython()
        reply_filter = REPLY_FILTER_VALUES[self.reply_filter.currentText()]

        try:
            self._candidates = self.manager.find_candidates(
                date_from=date_from,
                date_to=date_to,
                keyword=self.keyword_input.text(),
                reply_filter=reply_filter,
            )
        except GmailServiceError as exc:
            QMessageBox.critical(self, "Could not search mail", str(exc))
            return

        self._render_table()

    def _render_table(self) -> None:
        self.table.setRowCount(len(self._candidates))
        for row, candidate in enumerate(self._candidates):
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            self.table.setCellWidget(row, 0, checkbox)
            self.table.setItem(row, 1, QTableWidgetItem(candidate.company))
            self.table.setItem(row, 2, QTableWidgetItem(candidate.recipient_email))
            self.table.setItem(row, 3, QTableWidgetItem(candidate.subject))
            self.table.setItem(row, 4, QTableWidgetItem("Replied" if candidate.replied else "Not replied"))
            self.table.setItem(row, 5, QTableWidgetItem(str(candidate.message_count)))
            last = (
                candidate.last_followup_at.strftime("%Y-%m-%d")
                if candidate.last_followup_at
                else "Never"
            )
            self.table.setItem(row, 6, QTableWidgetItem(last))

    def _on_row_selected(self) -> None:
        rows = {index.row() for index in self.table.selectedIndexes()}
        if not rows or not self._candidates:
            self.detail_view.clear()
            return
        row = min(rows)
        if row >= len(self._candidates):
            return
        candidate = self._candidates[row]
        last = (
            candidate.last_followup_at.strftime("%Y-%m-%d")
            if candidate.last_followup_at
            else "Never"
        )
        self.detail_view.setPlainText(
            f"Company: {candidate.company}\n"
            f"Email: {candidate.recipient_email}\n"
            f"Subject: {candidate.subject}\n"
            f"Replied: {'Yes' if candidate.replied else 'No'}  |  "
            f"Messages in thread: {candidate.message_count}  |  "
            f"Last followed up: {last}"
        )

    def _set_all_checked(self, checked: bool) -> None:
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(checked)

    def _selected_candidates(self) -> list[FollowUpCandidate]:
        selected = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox) and widget.isChecked():
                selected.append(self._candidates[row])
        return selected

    def _on_preview(self) -> None:
        selected = self._selected_candidates()
        if not selected:
            QMessageBox.warning(self, "No selection", "Select at least one company to follow up with.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Confirm {len(selected)} follow-up(s)")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Each reply lands inside the original thread shown below."))
        for candidate in selected:
            layout.addWidget(
                QLabel(
                    f"• {candidate.company} — {candidate.subject} "
                    f"({candidate.message_count} message(s) in thread)"
                )
            )
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Confirm && Send")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.Accepted:
            self._start_send(selected)

    def _on_send(self) -> None:
        selected = self._selected_candidates()
        if not selected:
            QMessageBox.warning(self, "No selection", "Select at least one company to follow up with.")
            return
        self._start_send(selected)

    def _start_send(self, selected: list[FollowUpCandidate]) -> None:
        body = self.body_input.toPlainText().strip()
        if not body:
            QMessageBox.warning(self, "Empty message", "Write a follow-up message before sending.")
            return
        self.on_send(selected, body)
