"""Campaign editor: CSV upload, subject/body composer, attachments, preview."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from campaign.campaign_manager import CampaignManager
from campaign.csv_parser import ParsedCsv, parse_csv, resolve_email_column
from campaign.models import Campaign, CampaignStatus, Recipient
from campaign.template_renderer import render_body_html, render_template
from campaign.validators import validate_campaign


class CampaignEditor(QWidget):
    def __init__(
        self,
        manager: CampaignManager,
        campaign: Campaign,
        on_send: Callable[[Campaign, list[Recipient]], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.manager = manager
        self.campaign = campaign
        self.on_send = on_send
        self._parsed_csv: ParsedCsv | None = None

        self.name_label = QLabel(f"Campaign: {campaign.name}")
        self.upload_button = QPushButton("Upload CSV")
        self.csv_status_label = QLabel("No CSV uploaded")
        self.email_column_combo = QComboBox()

        self.subject_input = QLineEdit(campaign.subject)
        self.body_input = QTextEdit(campaign.body)

        self.attachments_list = QListWidget()
        self.add_attachment_button = QPushButton("Add Attachment")
        self.remove_attachment_button = QPushButton("Remove Attachment")

        self.preview_button = QPushButton("Preview")
        self.validate_button = QPushButton("Validate")
        self.send_button = QPushButton("Send")

        self.upload_button.clicked.connect(self._on_upload_csv)
        self.email_column_combo.currentTextChanged.connect(self._on_email_column_chosen)
        self.add_attachment_button.clicked.connect(self._on_add_attachment)
        self.remove_attachment_button.clicked.connect(self._on_remove_attachment)
        self.preview_button.clicked.connect(self._on_preview)
        self.validate_button.clicked.connect(self._on_validate)
        self.send_button.clicked.connect(self._on_send)

        for attachment in campaign.attachments:
            self.attachments_list.addItem(attachment)

        layout = QVBoxLayout(self)
        for widget in (
            self.name_label,
            self.upload_button,
            self.csv_status_label,
            self.email_column_combo,
            QLabel("Subject"),
            self.subject_input,
            QLabel("Body (wrap text in ** ** for bold, e.g. **important**)"),
            self.body_input,
            QLabel("Attachments"),
            self.attachments_list,
            self.add_attachment_button,
            self.remove_attachment_button,
            self.preview_button,
            self.validate_button,
            self.send_button,
        ):
            layout.addWidget(widget)

        self.email_column_combo.setVisible(False)

    def _on_upload_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Upload CSV", filter="CSV Files (*.csv)")
        if not file_path:
            return
        try:
            self._parsed_csv = parse_csv(file_path)
        except (FileNotFoundError, ValueError) as exc:
            self.csv_status_label.setText("Upload failed")
            QMessageBox.critical(self, "Invalid CSV", str(exc))
            return

        if self._parsed_csv.email_column is None and self._parsed_csv.email_column_candidates:
            self.csv_status_label.setText("Multiple possible email columns found — choose one below")
            self.email_column_combo.clear()
            self.email_column_combo.addItems(self._parsed_csv.email_column_candidates)
            self.email_column_combo.setVisible(True)
        elif self._parsed_csv.email_column is None:
            self.csv_status_label.setText("Upload failed")
            QMessageBox.critical(self, "No email column", "No email column could be detected in this CSV.")
        else:
            self.email_column_combo.setVisible(False)
            self._apply_recipients()

    def _on_email_column_chosen(self, column: str) -> None:
        if not column or self._parsed_csv is None:
            return
        self._parsed_csv = resolve_email_column(self._parsed_csv, column)
        self._apply_recipients()

    def _apply_recipients(self) -> None:
        if self._parsed_csv is None or self.campaign.id is None:
            return
        self.manager.set_recipients(self.campaign.id, self._parsed_csv)
        self.csv_status_label.setText(
            f"Loaded {len(self._parsed_csv.rows)} recipients "
            f"(email column: {self._parsed_csv.email_column}; "
            f"variables: {', '.join(self._parsed_csv.variable_columns) or 'none'})"
        )

    def _on_add_attachment(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Add Attachment")
        if file_path:
            self.attachments_list.addItem(file_path)
            self._save_attachments()

    def _on_remove_attachment(self) -> None:
        row = self.attachments_list.currentRow()
        if row >= 0:
            self.attachments_list.takeItem(row)
            self._save_attachments()

    def _save_attachments(self) -> None:
        attachments = [
            self.attachments_list.item(i).text() for i in range(self.attachments_list.count())
        ]
        self.manager.update_attachments(self.campaign, attachments)

    def _current_recipients_as_dicts(self) -> list[dict[str, str]]:
        if self._parsed_csv is None or self._parsed_csv.email_column is None:
            return []
        return self._parsed_csv.rows

    def _run_validation(self):
        self.manager.update_content(self.campaign, self.subject_input.text(), self.body_input.toPlainText())
        return validate_campaign(
            subject=self.campaign.subject,
            body=self.campaign.body,
            attachments=self.campaign.attachments,
            recipients=self._current_recipients_as_dicts(),
            email_field=self._parsed_csv.email_column if self._parsed_csv else "email",
        )

    def _on_validate(self) -> None:
        result = self._run_validation()
        if result.is_valid:
            QMessageBox.information(self, "Validation passed", "Campaign is ready to send.")
        else:
            QMessageBox.warning(self, "Validation failed", "\n".join(result.errors))

    def render_preview(self, variables: dict[str, str]) -> tuple[str, str]:
        subject = render_template(self.subject_input.text(), variables)
        body = render_template(self.body_input.toPlainText(), variables)
        return subject, body

    def _on_preview(self) -> None:
        recipients = self._current_recipients_as_dicts()
        if not recipients or self._parsed_csv is None or self._parsed_csv.email_column is None:
            QMessageBox.warning(self, "No recipients", "Upload a CSV before previewing.")
            return

        variables = {k: v for k, v in recipients[0].items() if k != self._parsed_csv.email_column}
        subject, body = self.render_preview(variables)
        attachments = "\n".join(self.campaign.attachments) or "(none)"

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Preview: {recipients[0][self._parsed_csv.email_column]}")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(f"Subject: {subject}"))
        layout.addWidget(QLabel("Body:"))
        body_view = QTextEdit()
        body_view.setReadOnly(True)
        body_view.setHtml(render_body_html(body))
        layout.addWidget(body_view)
        layout.addWidget(QLabel(f"Attachments:\n{attachments}"))
        dialog.exec()

    def _on_send(self) -> None:
        result = self._run_validation()
        if not result.is_valid:
            QMessageBox.warning(self, "Cannot send", "Fix validation errors first:\n" + "\n".join(result.errors))
            return
        if self.campaign.id is None:
            return

        recipients = self.manager.database.list_recipients(self.campaign.id)
        self.manager.set_status(self.campaign, CampaignStatus.SENDING)
        self.on_send(self.campaign, recipients)
