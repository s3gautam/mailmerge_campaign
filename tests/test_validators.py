from campaign.validators import (
    is_valid_email,
    partition_recipients,
    validate_attachments,
    validate_campaign,
)


def test_is_valid_email():
    assert is_valid_email("john@example.com")
    assert not is_valid_email("not-an-email")


def test_validate_attachments_missing_file(tmp_path):
    errors = validate_attachments([str(tmp_path / "missing.pdf")])
    assert any("not found" in e for e in errors)


def test_validate_campaign_flags_blank_subject_and_body():
    result = validate_campaign(subject="", body="", attachments=[], recipients=[])
    assert not result.is_valid
    assert any("Subject" in e for e in result.errors)
    assert any("Body" in e for e in result.errors)
    assert any("no recipients" in e for e in result.errors)


def test_validate_campaign_passes_for_clean_input():
    recipients = [{"email": "a@example.com", "Name": "A", "Company": "Acme"}]
    result = validate_campaign(
        subject="Hi {{Name}}",
        body="Welcome to {{Company}}",
        attachments=[],
        recipients=recipients,
        email_field="email",
    )
    assert result.is_valid


def test_validate_campaign_does_not_block_on_per_recipient_issues():
    # Bad emails, duplicates, and missing variables are per-recipient concerns
    # handled by partition_recipients; validate_campaign must not block on them.
    recipients = [
        {"email": "a@example.com", "Name": "A"},
        {"email": "a@example.com", "Name": "A"},
        {"email": "bad-email", "Name": "B"},
    ]
    result = validate_campaign(
        subject="Hi {{Name}}",
        body="Welcome {{Company}}",
        attachments=[],
        recipients=recipients,
        email_field="email",
    )
    assert result.is_valid


def test_partition_recipients_skips_invalid_duplicate_and_missing_variable_rows():
    recipients = [
        {"email": "a@example.com", "Name": "A", "Company": "Acme"},
        {"email": "a@example.com", "Name": "A", "Company": "Acme"},
        {"email": "bad-email", "Name": "B", "Company": "Acme"},
        {"email": "c@example.com", "Name": "C"},
        {"email": "d@example.com", "Name": "D", "Company": "Acme"},
    ]
    valid, skipped = partition_recipients(
        subject="Hi {{Name}}",
        body="Welcome to {{Company}}",
        recipients=recipients,
        email_field="email",
    )

    assert [row["email"] for row in valid] == ["a@example.com", "d@example.com"]
    assert len(skipped) == 3
    reasons = {s.row["email"]: s.reason for s in skipped}
    assert "Duplicate email" in reasons["a@example.com"]
    assert "Invalid email format" in reasons["bad-email"]
    assert "Missing variable" in reasons["c@example.com"]
