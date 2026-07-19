# EMAIL_CAMPAIGN_MVP.md

## Objective

Build a Mail Merge style Email Campaign feature using the authenticated Gmail account.

This is an MVP. Keep the implementation simple, clean, and production-ready.

---

## User Flow

Create Campaign → Upload CSV → Detect Email Column → Generate Variables → Write Subject → Write Body → Attach Files → Preview → Validate → Send → Show Progress → Generate Logs

---

## Campaign Dashboard

**Display**

- Campaign Name
- Created Time
- Recipients
- Sent
- Failed
- Status

**Actions**

- Create
- Open
- Delete
- View Logs

---

## CSV Upload

- Support CSV only.
- Automatically detect the email column. Possible column names:
  - Email
  - email
  - Email Address
  - Corporate Email
  - Work Email
  - Personal Email
- If multiple candidates exist, ask the user to choose.

---

## Variables

Every remaining column becomes a variable.

Example CSV columns: `Name`, `Company`, `Designation`, `Email`

Resulting variables: `{{Name}}`, `{{Company}}`, `{{Designation}}`

- Variables should be case insensitive.
- Unlimited variables.

---

## Email Composer

**Fields**

- Campaign Name
- Subject
- Body

Allow inserting variables into both Subject and Body.

Example:

- Subject: `Welcome {{Name}}`
- Body: `Hi {{Name}}, thank you for joining {{Company}}.`

---

## Attachments

- Support multiple static attachments.
- Every recipient receives the same files.

**Allow**

- Add Attachment
- Remove Attachment
- Preview Attachment Name
- Display File Size

**Validate**

- File exists
- Readable
- Within Gmail attachment limit

**Supported formats:** PDF, DOCX, XLSX, ZIP, PNG, JPEG, TXT, CSV

---

## Preview

- Select any recipient.
- Render the final email exactly as it will be sent (Subject, Body, Attachments).

Example:

- Subject: `Welcome John`
- Body: `Hi John, welcome to Google.`
- Attachments: `Brochure.pdf`, `Pricing.pdf`

---

## Validation

Before sending, check:

- Email format
- Duplicate emails
- Missing variables
- Missing attachments
- Blank subject
- Blank body
- Invalid CSV

Stop sending if validation fails.

---

## Sending

When the user clicks Send, for every row:

Replace variables → Prepare email → Attach static files → Call `GmailService.send_email_with_attachments()` → Record result → Continue

---

## Progress Screen

**Display**

- Progress bar
- Current recipient
- Sent / Failed / Remaining counts
- Current status

Allow the user to close the window while sending continues in the background.

---

## Logs

Store: campaign, recipient, timestamp, status, failure reason.

SQLite is sufficient.

---

## Database

**Tables:** `Campaign`, `Recipient`, `CampaignLog`

**Store:** campaign metadata, recipient status, failure messages, created timestamp.

---

## Folder Structure

```
campaign/
    campaign_manager.py
    campaign_sender.py
    csv_parser.py
    validators.py
    template_renderer.py
    database.py
    models.py
ui/
    CampaignPage.py
    CampaignEditor.py
    CampaignProgress.py
```

---

## Out of Scope

The following MUST NOT be implemented:

- AI generated emails
- Groq integration
- Scheduling, Pause, Resume, Retry
- Campaign Templates
- Campaign Analytics
- Dynamic Attachments
- HTML Email Builder
- Open Tracking, Click Tracking, Reply Tracking
- Multiple Gmail Accounts
- Per-recipient Attachments
- Rate Limiting Dashboard

---

## Acceptance Criteria

The feature is complete when the user can:

- Upload a CSV
- Automatically detect the email column
- Use CSV fields as variables
- Write subject and body
- Attach one or more static files
- Preview the final email
- Send personalized emails through Gmail
- View progress
- View logs

All emails must be sent through `GmailService` without directly calling Gmail APIs from the campaign module.
