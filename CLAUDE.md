# CLAUDE.md

## Project Overview

This repository contains a Python desktop application that acts as a Gmail Agent.

The current task is to build ONLY the Email Campaign MVP.

Do not implement unrelated Gmail functionality unless required by the campaign module.

---

# Technology Stack

Language

- Python 3.12+

UI

- PySide6

Database

- SQLite

Mail Provider

- Gmail API

Authentication

- OAuth2

Scheduler

- None (not required for MVP)

LLM

- Groq

Groq is used elsewhere in the application.

Do NOT use Groq for this module.

Everything in this campaign feature should be deterministic Python.

---

# Architecture Principles

Follow clean architecture.

Separate

UI

Business Logic

Persistence

Services

Utilities

Do not mix them.

---

# Folder Structure

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

---

# Gmail Access

The Campaign module must NEVER directly call Gmail APIs.

Always use

GmailService.send_email()

or

GmailService.send_email_with_attachments()

This ensures Gmail logic remains centralized.

---

# Code Quality

Use

- Type hints
- Dataclasses or Pydantic models
- Small reusable classes
- SOLID principles
- Dependency injection where appropriate

No duplicated code.

---

# Performance

Avoid unnecessary memory usage.

Load CSV efficiently.

Do not repeatedly open attachments.

Cache parsed CSV data.

---

# Logging

Implement

Application Logs

Campaign Logs

Error Logs

Use rotating log files.

---

# Error Handling

Gracefully handle

Invalid CSV

Missing files

Invalid emails

OAuth failures

Network failures

Gmail API errors

Display user-friendly messages.

---

# Database

Use SQLite.

Create normalized tables.

Do not hardcode SQL inside UI code.

---

# Testing

Implement

Unit Tests

CSV Parsing Tests

Validation Tests

Template Rendering Tests

Campaign Sending Tests

---

# Security

Never expose OAuth tokens.

Never expose Gmail credentials.

Never log sensitive information.

---

# SSL

Support corporate Windows laptops.

The setup should install

python-certifi-win32

Do not disable SSL verification globally.

---

# Deliverables

Produce production-ready code.

No placeholders.

No TODOs.

No pseudo-code.

Every module should be complete and executable.
