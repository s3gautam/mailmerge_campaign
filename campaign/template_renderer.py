"""Renders `{{Variable}}` placeholders in the subject/body, case insensitively."""

from __future__ import annotations

import re

VARIABLE_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def extract_variables(template: str) -> list[str]:
    return [match.group(1) for match in VARIABLE_PATTERN.finditer(template)]


def render_template(template: str, variables: dict[str, str]) -> str:
    """Replace ``{{Name}}`` style placeholders using a case-insensitive lookup."""
    lookup = {key.lower(): value for key, value in variables.items()}

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1).lower()
        return lookup.get(key, match.group(0))

    return VARIABLE_PATTERN.sub(_replace, template)


def missing_variables(template: str, variables: dict[str, str]) -> list[str]:
    lookup = {key.lower() for key in variables}
    return [
        name
        for name in extract_variables(template)
        if name.lower() not in lookup
    ]
