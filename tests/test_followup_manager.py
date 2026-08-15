from datetime import date

from followup.database import FollowUpDatabase
from followup.followup_manager import FollowUpManager, _company_label
from services.gmail_service import Message, ThreadDetail


class FakeGmailService:
    def __init__(self, threads: dict[str, ThreadDetail], my_email: str = "me@example.com") -> None:
        self.threads = threads
        self.my_email = my_email
        self.queries: list[str] = []
        self.replies: list[dict] = []

    def list_thread_ids(self, query, max_results=50):
        self.queries.append(query)
        return list(self.threads.keys())

    def get_profile_email(self):
        return self.my_email

    def get_thread(self, thread_id):
        return self.threads[thread_id]

    def reply_to_thread(self, thread_id, to, subject, body, in_reply_to=""):
        self.replies.append({"thread_id": thread_id, "to": to, "subject": subject, "body": body})
        return "sent-id"


def _thread(thread_id, subject, messages) -> ThreadDetail:
    return ThreadDetail(id=thread_id, subject=subject, messages=messages)


def _msg(sender, to, message_id="<m@mail>") -> Message:
    return Message(
        id="id",
        thread_id="t",
        sender=sender,
        to=to,
        subject="Application",
        date="",
        body="",
        message_id_header=message_id,
    )


def test_company_label_derives_readable_name_from_domain():
    assert _company_label("careers@northwind-labs.io") == "Northwind Labs"
    assert _company_label("jobs@cobaltco.com") == "Cobaltco"


def test_find_candidates_detects_replied_vs_not_replied(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    threads = {
        "not-replied": _thread(
            "not-replied", "Application for PM", [_msg("me@example.com", "Alice <alice@acme.com>")]
        ),
        "replied": _thread(
            "replied",
            "Application for Eng",
            [
                _msg("me@example.com", "Bob <bob@zenith.com>", message_id="<first@mail>"),
                _msg("bob@zenith.com", "me@example.com", message_id="<second@mail>"),
            ],
        ),
    }
    gmail = FakeGmailService(threads)
    manager = FollowUpManager(db, gmail)

    all_candidates = manager.find_candidates(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))
    by_id = {c.thread_id: c for c in all_candidates}
    assert by_id["not-replied"].replied is False
    assert by_id["not-replied"].recipient_email == "alice@acme.com"
    assert by_id["replied"].replied is True
    assert by_id["replied"].message_count == 2

    replied_only = manager.find_candidates(
        date_from=date(2024, 1, 1), date_to=date(2024, 1, 31), reply_filter="replied"
    )
    assert [c.thread_id for c in replied_only] == ["replied"]

    not_replied_only = manager.find_candidates(
        date_from=date(2024, 1, 1), date_to=date(2024, 1, 31), reply_filter="not_replied"
    )
    assert [c.thread_id for c in not_replied_only] == ["not-replied"]


def test_find_candidates_builds_gmail_search_query_with_date_range_and_keyword(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    gmail = FakeGmailService({})
    manager = FollowUpManager(db, gmail)

    manager.find_candidates(date_from=date(2024, 3, 1), date_to=date(2024, 3, 5), keyword="product manager")

    assert gmail.queries == ["in:sent after:2024/03/01 before:2024/03/06 product manager"]


def test_send_followups_records_success_and_failure(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    threads = {
        "ok": _thread("ok", "Application for PM", [_msg("me@example.com", "alice@acme.com")]),
    }
    gmail = FakeGmailService(threads)
    manager = FollowUpManager(db, gmail)
    candidates = manager.find_candidates(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))

    progress = manager.send_followups(candidates, "Just following up!")

    assert progress.sent == 1
    assert progress.failed == 0
    assert gmail.replies == [
        {"thread_id": "ok", "to": "alice@acme.com", "subject": "Application for PM", "body": "Just following up!"}
    ]

    last = db.last_followup_dates(["ok"])
    assert "ok" in last
