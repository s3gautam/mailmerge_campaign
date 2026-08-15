"""Read a thread's messages and send a reply."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from inbox.inbox_manager import InboxManager
from services.gmail_service import GmailServiceError, ThreadDetail


class ThreadView(QWidget):
    def __init__(
        self,
        manager: InboxManager,
        thread_id: str,
        on_back: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.thread_id = thread_id
        self.on_back = on_back
        self._thread: ThreadDetail | None = None

        self.back_button = QPushButton("Back to Inbox")
        self.subject_label = QLabel("")
        self.messages_view = QTextEdit()
        self.messages_view.setReadOnly(True)

        self.reply_input = QTextEdit()
        self.reply_input.setPlaceholderText("Type your reply...")
        self.send_reply_button = QPushButton("Send Reply")

        self.back_button.clicked.connect(self.on_back)
        self.send_reply_button.clicked.connect(self._on_send_reply)

        header_row = QHBoxLayout()
        header_row.addWidget(self.back_button)
        header_row.addWidget(self.subject_label)

        layout = QVBoxLayout(self)
        layout.addLayout(header_row)
        layout.addWidget(self.messages_view)
        layout.addWidget(QLabel("Reply:"))
        layout.addWidget(self.reply_input)
        layout.addWidget(self.send_reply_button)

        self._load_thread()

    def _load_thread(self) -> None:
        try:
            self._thread = self.manager.get_thread(self.thread_id)
        except GmailServiceError as exc:
            QMessageBox.critical(self, "Could not load thread", str(exc))
            return

        self.subject_label.setText(self._thread.subject)
        self.messages_view.setPlainText(
            "\n\n---\n\n".join(
                f"From: {m.sender}\nTo: {m.to}\nDate: {m.date}\n\n{m.body}" for m in self._thread.messages
            )
        )

    def _on_send_reply(self) -> None:
        if self._thread is None:
            return
        body = self.reply_input.toPlainText().strip()
        if not body:
            QMessageBox.warning(self, "Empty reply", "Type a reply before sending.")
            return

        try:
            self.manager.reply(self._thread, body)
        except GmailServiceError as exc:
            QMessageBox.critical(self, "Reply failed", str(exc))
            return

        QMessageBox.information(self, "Reply sent", "Your reply was sent.")
        self.reply_input.clear()
        self._load_thread()
