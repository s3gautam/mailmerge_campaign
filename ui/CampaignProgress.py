"""Progress screen shown while a campaign is sending or being drafted."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from campaign.campaign_sender import SendProgress


class CampaignProgress(QWidget):
    def __init__(self, mode: str = "send", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.verb = "Sending" if mode == "send" else "Creating drafts"
        self.setWindowTitle(f"{self.verb} — Campaign")

        self.progress_bar = QProgressBar()
        self.current_label = QLabel("")
        self.sent_label = QLabel("Sent: 0" if mode == "send" else "Drafted: 0")
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
        self.current_label.setText(f"{self.verb}: {progress.current_email}")
        label = "Sent" if self.verb == "Sending" else "Drafted"
        self.sent_label.setText(f"{label}: {progress.sent}")
        self.failed_label.setText(f"Failed: {progress.failed}")
        self.remaining_label.setText(f"Remaining: {progress.remaining}")
        self.status_label.setText(
            "Completed" if progress.remaining == 0 else f"{self.verb}..."
        )
