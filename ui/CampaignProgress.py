"""Progress screen shown while a campaign is sending."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from campaign.campaign_sender import SendProgress


class CampaignProgress(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sending Campaign")

        self.progress_bar = QProgressBar()
        self.current_label = QLabel("")
        self.sent_label = QLabel("Sent: 0")
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

    def update_progress(self, progress: SendProgress) -> None:
        self.progress_bar.setMaximum(progress.total)
        self.progress_bar.setValue(progress.sent + progress.failed)
        self.current_label.setText(f"Sending to: {progress.current_email}")
        self.sent_label.setText(f"Sent: {progress.sent}")
        self.failed_label.setText(f"Failed: {progress.failed}")
        self.remaining_label.setText(f"Remaining: {progress.remaining}")
        self.status_label.setText(
            "Completed" if progress.remaining == 0 else "Sending..."
        )
