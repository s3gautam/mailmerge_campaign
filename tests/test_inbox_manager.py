import pytest

from inbox.inbox_manager import InboxManager
from services.gmail_service import Message, ThreadDetail


class FakeGmailService:
    def __init__(self) -> None:
        self.replies: list[dict] = []

    def reply_to_thread(self, thread_id, to, subject, body, in_reply_to=""):
        self.replies.append(
            {"thread_id": thread_id, "to": to, "subject": subject, "body": body, "in_reply_to": in_reply_to}
        )
        return "sent-id"


def test_reply_targets_last_message_sender_and_thread_subject():
    gmail = FakeGmailService()
    manager = InboxManager(gmail)
    thread = ThreadDetail(
        id="thread1",
        subject="Job Opening",
        messages=[
            Message(
                id="m1",
                thread_id="thread1",
                sender="me@example.com",
                to="alice@example.com",
                subject="Job Opening",
                date="",
                body="",
                message_id_header="<first@mail>",
            ),
            Message(
                id="m2",
                thread_id="thread1",
                sender="alice@example.com",
                to="me@example.com",
                subject="Re: Job Opening",
                date="",
                body="",
                message_id_header="<second@mail>",
            ),
        ],
    )

    manager.reply(thread, "Thanks for reaching out!")

    assert gmail.replies == [
        {
            "thread_id": "thread1",
            "to": "alice@example.com",
            "subject": "Job Opening",
            "body": "Thanks for reaching out!",
            "in_reply_to": "<second@mail>",
        }
    ]


def test_reply_raises_for_empty_thread():
    manager = InboxManager(FakeGmailService())
    thread = ThreadDetail(id="thread1", subject="Empty", messages=[])
    with pytest.raises(ValueError):
        manager.reply(thread, "Hi")
