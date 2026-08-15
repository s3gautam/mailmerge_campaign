import base64

from services.gmail_service import GmailService, _sanitize_header


def test_sanitize_header_collapses_embedded_newlines():
    assert _sanitize_header("Application for Product Manager Role\nat ABC") == (
        "Application for Product Manager Role at ABC"
    )


def test_sanitize_header_collapses_crlf_and_trims():
    assert _sanitize_header("  Hi\r\nThere  \n") == "Hi There"


def test_sanitize_header_leaves_normal_text_untouched():
    assert _sanitize_header("Welcome to Acme") == "Welcome to Acme"


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode()


def test_extract_plain_text_from_simple_payload():
    payload = {"mimeType": "text/plain", "body": {"data": _b64("Hello there")}}
    assert GmailService._extract_plain_text(payload) == "Hello there"


def test_extract_plain_text_finds_nested_plain_part():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<p>Hi</p>")}},
            {"mimeType": "text/plain", "body": {"data": _b64("Hi")}},
        ],
    }
    assert GmailService._extract_plain_text(payload) == "Hi"


def test_extract_plain_text_returns_empty_when_no_plain_part():
    payload = {"mimeType": "text/html", "body": {"data": _b64("<p>Hi</p>")}}
    assert GmailService._extract_plain_text(payload) == ""


def test_parse_message_reads_headers_and_body():
    raw_message = {
        "id": "msg1",
        "threadId": "thread1",
        "payload": {
            "headers": [
                {"name": "From", "value": "alice@example.com"},
                {"name": "To", "value": "bob@example.com"},
                {"name": "Subject", "value": "Hello"},
                {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"},
                {"name": "Message-ID", "value": "<abc@mail.gmail.com>"},
            ],
            "mimeType": "text/plain",
            "body": {"data": _b64("Body text")},
        },
    }
    message = GmailService._parse_message(raw_message)
    assert message.id == "msg1"
    assert message.thread_id == "thread1"
    assert message.sender == "alice@example.com"
    assert message.to == "bob@example.com"
    assert message.subject == "Hello"
    assert message.body == "Body text"
    assert message.message_id_header == "<abc@mail.gmail.com>"
