"""Business logic for creating and managing campaigns (no UI, no Gmail calls)."""

from __future__ import annotations

from campaign.csv_parser import ParsedCsv
from campaign.database import Database
from campaign.models import Campaign, CampaignStatus, Recipient, RecipientStatus


class CampaignManager:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_campaign(self, name: str) -> Campaign:
        campaign = Campaign(name=name)
        campaign.id = self.database.create_campaign(campaign)
        return campaign

    def set_recipients(self, campaign_id: int, parsed_csv: ParsedCsv) -> list[Recipient]:
        if parsed_csv.email_column is None:
            raise ValueError("Email column must be resolved before setting recipients")

        recipients = [
            Recipient(
                campaign_id=campaign_id,
                email=row[parsed_csv.email_column].strip(),
                variables={k: row[k] for k in parsed_csv.variable_columns},
            )
            for row in parsed_csv.rows
        ]
        self.database.add_recipients(recipients)
        return recipients

    def update_content(self, campaign: Campaign, subject: str, body: str) -> None:
        campaign.subject = subject
        campaign.body = body
        self.database.update_campaign(campaign)

    def update_attachments(self, campaign: Campaign, attachments: list[str]) -> None:
        campaign.attachments = attachments
        self.database.update_campaign(campaign)

    def set_status(self, campaign: Campaign, status: CampaignStatus) -> None:
        campaign.status = status
        self.database.update_campaign(campaign)

    def delete_campaign(self, campaign_id: int) -> None:
        self.database.delete_campaign(campaign_id)

    def list_campaigns(self) -> list[Campaign]:
        return self.database.list_campaigns()

    def get_summary(self, campaign_id: int) -> dict[str, int]:
        recipients = self.database.list_recipients(campaign_id)
        return {
            "recipients": len(recipients),
            "sent": sum(1 for r in recipients if r.status == RecipientStatus.SENT),
            "failed": sum(1 for r in recipients if r.status == RecipientStatus.FAILED),
        }
