# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a Python desktop application that acts as a Gmail Agent.

The current task is to build **only** the Email Campaign MVP (see `instructions.md` for the full feature spec). Do not implement unrelated Gmail functionality unless required by the campaign module.

## Technology Stack

- **Language:** Python 3.12+
- **UI:** PySide6
- **Database:** SQLite
- **Mail Provider:** Gmail API
- **Authentication:** OAuth2
- **Scheduler:** None (not required for MVP)
- **LLM:** Groq is used elsewhere in the application, but **do not use Groq for this module**. Everything in the campaign feature should be deterministic Python.

## Architecture Principles

Follow clean architecture — keep these layers separate and do not mix them:

- UI
- Business logic
- Persistence
- Services
- Utilities

## Folder Structure

```
campaign/
    campaign_manager.py
    campaign_sender.py
    csv_parser.py
    template_renderer.py
    validators.py
    database.py
    models.py
services/
    gmail_service.py
ui/
    CampaignPage.py
    CampaignEditor.py
    CampaignProgress.py
```

## Gmail Access

The campaign module must **never** directly call Gmail APIs. Always go through:

- `GmailService.send_email()`
- `GmailService.send_email_with_attachments()`

This ensures Gmail logic remains centralized.

## Code Quality

- Type hints throughout
- Dataclasses or Pydantic models
- Small, reusable classes
- SOLID principles
- Dependency injection where appropriate
- No duplicated code

## Performance

- Avoid unnecessary memory usage
- Load CSV efficiently
- Do not repeatedly open attachments
- Cache parsed CSV data

## Logging

Implement application logs, campaign logs, and error logs, using rotating log files.

## Error Handling

Gracefully handle: invalid CSV, missing files, invalid emails, OAuth failures, network failures, and Gmail API errors. Display user-friendly messages.

## Database

- Use SQLite with normalized tables
- Do not hardcode SQL inside UI code

## Testing

Implement unit tests for:

- CSV parsing
- Validation
- Template rendering
- Campaign sending

## Security

- Never expose OAuth tokens
- Never expose Gmail credentials
- Never log sensitive information

## SSL

Support corporate Windows laptops — the setup should install `python-certifi-win32`. Do not disable SSL verification globally.

## Deliverables

Produce production-ready code: no placeholders, no TODOs, no pseudo-code. Every module should be complete and executable.
