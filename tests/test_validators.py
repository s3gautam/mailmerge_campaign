from campaign.validators import is_valid_email, validate_attachments, validate_campaign


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


def test_validate_campaign_detects_duplicates_and_missing_variables():
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
    assert not result.is_valid
    assert any("Duplicate email" in e for e in result.errors)
    assert any("Invalid email format" in e for e in result.errors)
    assert any("Missing variable '{{Company}}'" in e for e in result.errors)


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
