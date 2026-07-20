from campaign.campaign_sender import CampaignSender
from campaign.database import Database
from campaign.models import Campaign, CampaignStatus, Recipient, RecipientStatus
from services.gmail_service import GmailServiceError


class FakeGmailService:
    def __init__(self, fail_for: set[str] | None = None) -> None:
        self.fail_for = fail_for or set()
        self.sent: list[str] = []

    def send_email_with_attachments(self, to, subject, body, attachments, body_html=None):
        if to in self.fail_for:
            raise GmailServiceError("simulated failure")
        self.sent.append(to)
        return "fake-message-id"


def _make_campaign(db: Database) -> Campaign:
    campaign = Campaign(name="Test", subject="Hi {{Name}}", body="Welcome {{Name}}", status=CampaignStatus.DRAFT)
    campaign.id = db.create_campaign(campaign)
    return campaign


def test_send_records_success_and_failure(tmp_path):
    db = Database(tmp_path / "test.db")
    campaign = _make_campaign(db)
    recipients = [
        Recipient(campaign_id=campaign.id, email="ok@example.com", variables={"Name": "OK"}),
        Recipient(campaign_id=campaign.id, email="bad@example.com", variables={"Name": "Bad"}),
    ]
    db.add_recipients(recipients)
    recipients = db.list_recipients(campaign.id)

    gmail = FakeGmailService(fail_for={"bad@example.com"})
    sender = CampaignSender(db, gmail)

    progress = sender.send(campaign, recipients)

    assert progress.sent == 1
    assert progress.failed == 1
    assert gmail.sent == ["ok@example.com"]

    logs = db.list_logs(campaign.id)
    statuses = {log.recipient_email: log.status for log in logs}
    assert statuses["ok@example.com"] == RecipientStatus.SENT
    assert statuses["bad@example.com"] == RecipientStatus.FAILED

    updated = db.list_recipients(campaign.id)
    by_email = {r.email: r.status for r in updated}
    assert by_email["ok@example.com"] == RecipientStatus.SENT
    assert by_email["bad@example.com"] == RecipientStatus.FAILED


def test_send_skips_invalid_duplicate_and_missing_variable_recipients(tmp_path):
    db = Database(tmp_path / "test.db")
    campaign = _make_campaign(db)
    recipients = [
        Recipient(campaign_id=campaign.id, email="ok@example.com", variables={"Name": "OK"}),
        Recipient(campaign_id=campaign.id, email="ok@example.com", variables={"Name": "OK"}),  # duplicate
        Recipient(campaign_id=campaign.id, email="not-an-email", variables={"Name": "Bad"}),
        Recipient(campaign_id=campaign.id, email="missing@example.com", variables={}),  # missing {{Name}}
        Recipient(campaign_id=campaign.id, email="good2@example.com", variables={"Name": "Good2"}),
    ]
    db.add_recipients(recipients)
    recipients = db.list_recipients(campaign.id)

    gmail = FakeGmailService()
    sender = CampaignSender(db, gmail)

    progress = sender.send(campaign, recipients)

    assert progress.sent == 2
    assert progress.failed == 3
    assert set(gmail.sent) == {"ok@example.com", "good2@example.com"}

    logs = db.list_logs(campaign.id)
    reasons = {log.recipient_email: log.failure_reason for log in logs if log.status == RecipientStatus.FAILED}
    assert "Duplicate email" in reasons["ok@example.com"]
    assert "Invalid email format" in reasons["not-an-email"]
    assert "Missing variable" in reasons["missing@example.com"]
