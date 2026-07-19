"""CSV parsing and email-column detection for the campaign feature."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

EMAIL_COLUMN_CANDIDATES = {
    "email",
    "email address",
    "corporate email",
    "work email",
    "personal email",
}


@dataclass
class ParsedCsv:
    rows: list[dict[str, str]]
    email_column: str | None
    email_column_candidates: list[str]
    variable_columns: list[str]


def _find_email_column_candidates(columns: list[str]) -> list[str]:
    return [c for c in columns if c.strip().lower() in EMAIL_COLUMN_CANDIDATES]


def parse_csv(file_path: str | Path) -> ParsedCsv:
    """Parse a CSV file and detect the email column plus variable columns.

    If exactly one email-column candidate is found, it is selected automatically.
    If multiple candidates are found, ``email_column`` is left ``None`` and the
    caller (UI layer) must ask the user to pick one from ``email_column_candidates``.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row")
        columns = [c.strip() for c in reader.fieldnames]
        rows = [dict(zip(columns, row.values())) for row in reader]

    candidates = _find_email_column_candidates(columns)
    email_column = candidates[0] if len(candidates) == 1 else None
    variable_columns = [c for c in columns if c != email_column]

    return ParsedCsv(
        rows=rows,
        email_column=email_column,
        email_column_candidates=candidates,
        variable_columns=variable_columns,
    )


def resolve_email_column(parsed: ParsedCsv, chosen_column: str) -> ParsedCsv:
    """Apply a user-chosen email column when auto-detection was ambiguous."""
    if chosen_column not in parsed.rows[0]:
        raise ValueError(f"Column '{chosen_column}' not present in CSV")
    variable_columns = [c for c in parsed.rows[0] if c != chosen_column]
    return ParsedCsv(
        rows=parsed.rows,
        email_column=chosen_column,
        email_column_candidates=parsed.email_column_candidates,
        variable_columns=variable_columns,
    )
