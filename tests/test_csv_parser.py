from pathlib import Path

import pytest

from campaign.csv_parser import parse_csv, resolve_email_column


def _write_csv(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "recipients.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_detects_single_email_column(tmp_path):
    path = _write_csv(tmp_path, "Name,Email,Company\nJohn,john@example.com,Google\n")
    parsed = parse_csv(path)
    assert parsed.email_column == "Email"
    assert parsed.variable_columns == ["Name", "Company"]
    assert parsed.rows == [{"Name": "John", "Email": "john@example.com", "Company": "Google"}]


def test_ambiguous_email_column_requires_resolution(tmp_path):
    path = _write_csv(tmp_path, "Name,Work Email,Personal Email\nJohn,a@b.com,c@d.com\n")
    parsed = parse_csv(path)
    assert parsed.email_column is None
    assert set(parsed.email_column_candidates) == {"Work Email", "Personal Email"}

    resolved = resolve_email_column(parsed, "Work Email")
    assert resolved.email_column == "Work Email"
    assert resolved.variable_columns == ["Name", "Personal Email"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_csv(tmp_path / "missing.csv")
