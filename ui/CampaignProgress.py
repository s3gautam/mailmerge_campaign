"""Progress screen shown while a batch Gmail operation runs (send, draft, or follow-up)."""

from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

_MODE_LABELS = {
    "send": ("Sending", "Sent"),
    "draft": ("Creating drafts", "Drafted"),
    "followup": ("Following up", "Followed up"),
}


class _BatchProgress(Protocol):
    total: int
    sent: int
    failed: int
    current_email: str
    remaining: int


class CampaignProgress(QWidget):
    def __init__(self, mode: str = "send", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.verb, self.count_label_text = _MODE_LABELS[mode]
        self.setWindowTitle(f"{self.verb}...")

        self.progress_bar = QProgressBar()
        self.current_label = QLabel("")
        self.sent_label = QLabel(f"{self.count_label_text}: 0")
        self.failed_label = QLabel("Failed: 0")
        self.remaining_label = QLabel("Remaining: 0")
        self.status_label = QLabel("Starting...")

        layout = QVBoxLayout(self)
        for widget in (
            self.progress_bar,
            self.current_label,
            self.sent_label,
            self.failed_label,
            self.remaining_label,
            self.status_label,
        ):
            layout.addWidget(widget)

    def update_progress(self, progress: _BatchProgress) -> None:
        self.progress_bar.setMaximum(progress.total)
        self.progress_bar.setValue(progress.sent + progress.failed)
        self.current_label.setText(f"{self.verb}: {progress.current_email}")
        self.sent_label.setText(f"{self.count_label_text}: {progress.sent}")
        self.failed_label.setText(f"Failed: {progress.failed}")
        self.remaining_label.setText(f"Remaining: {progress.remaining}")
        self.status_label.setText(
            "Completed" if progress.remaining == 0 else f"{self.verb}..."
        )
