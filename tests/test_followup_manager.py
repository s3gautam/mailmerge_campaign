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


def _msg(sender, to, message_id="<m@mail>", subject="Application") -> Message:
    return Message(
        id="id",
        thread_id="t",
        sender=sender,
        to=to,
        subject=subject,
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


def test_find_candidates_recovers_recipient_and_subject_from_later_messages(tmp_path):
    # Mirrors a real thread where the first message's To/Subject headers
    # weren't usable but later replies in the thread carry the info.
    db = FollowUpDatabase(tmp_path / "test.db")
    threads = {
        "t1": _thread(
            "t1",
            "",  # thread-level subject missing
            [
                _msg("me@example.com", "", message_id="<first@mail>", subject=""),
                _msg("Sankalp Shangari <sankalp@brexy.ai>", "me@example.com", message_id="<second@mail>", subject=""),
                _msg(
                    "Samarth Ahuja <sam@brexy.ai>",
                    "sankalp@brexy.ai, me@example.com",
                    message_id="<third@mail>",
                    subject="Application for Product Manager Role at Brexy",
                ),
            ],
        ),
    }
    gmail = FakeGmailService(threads)
    manager = FollowUpManager(db, gmail)

    candidates = manager.find_candidates(date_from=date(2024, 1, 1), date_to=date(2024, 1, 31))

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.recipient_email == "sankalp@brexy.ai"
    assert candidate.company == "Brexy"
    assert candidate.subject == "Application for Product Manager Role at Brexy"
    assert candidate.replied is True
    assert candidate.message_count == 3


def test_find_candidates_builds_gmail_search_query_with_date_range_and_keyword(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    gmail = FakeGmailService({})
    manager = FollowUpManager(db, gmail)

    manager.find_candidates(date_from=date(2024, 3, 1), date_to=date(2024, 3, 5), keyword="product manager")

    assert gmail.queries == ["in:sent after:2024/03/01 before:2024/03/06 product manager"]


def test_find_candidates_builds_or_clause_for_comma_separated_companies(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    gmail = FakeGmailService({})
    manager = FollowUpManager(db, gmail)

    manager.find_candidates(
        date_from=date(2024, 3, 1), date_to=date(2024, 3, 5), keyword="antilease, brexy, seedflex"
    )

    assert gmail.queries == [
        "in:sent after:2024/03/01 before:2024/03/06 (antilease OR brexy OR seedflex)"
    ]


def test_find_candidates_ands_subject_keyword_with_company_clause(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    gmail = FakeGmailService({})
    manager = FollowUpManager(db, gmail)

    manager.find_candidates(
        date_from=date(2024, 3, 1),
        date_to=date(2024, 3, 5),
        keyword="antilease, brexy",
        subject_keyword="Application for role of",
    )

    assert gmail.queries == [
        'in:sent after:2024/03/01 before:2024/03/06 (antilease OR brexy) subject:"Application for role of"'
    ]


def test_find_candidates_subject_keyword_alone(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    gmail = FakeGmailService({})
    manager = FollowUpManager(db, gmail)

    manager.find_candidates(
        date_from=date(2024, 3, 1), date_to=date(2024, 3, 5), subject_keyword="Application for role of"
    )

    assert gmail.queries == [
        'in:sent after:2024/03/01 before:2024/03/06 subject:"Application for role of"'
    ]


def test_find_candidates_keyword_list_tolerates_semicolons_and_stray_whitespace(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    gmail = FakeGmailService({})
    manager = FollowUpManager(db, gmail)

    manager.find_candidates(
        date_from=date(2024, 3, 1), date_to=date(2024, 3, 5), keyword=" antilease ;brexy,  seedflex "
    )

    assert gmail.queries == [
        "in:sent after:2024/03/01 before:2024/03/06 (antilease OR brexy OR seedflex)"
    ]


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
