from followup.database import FollowUpDatabase
from followup.models import FollowUpLog, FollowUpStatus


def test_last_followup_dates_only_counts_sent_status(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    db.add_log(FollowUpLog(thread_id="t1", recipient_email="a@x.com", subject="Hi", status=FollowUpStatus.SENT))
    db.add_log(
        FollowUpLog(
            thread_id="t2",
            recipient_email="b@x.com",
            subject="Hi",
            status=FollowUpStatus.FAILED,
            failure_reason="boom",
        )
    )

    dates = db.last_followup_dates(["t1", "t2", "t3"])

    assert "t1" in dates
    assert "t2" not in dates
    assert "t3" not in dates


def test_last_followup_dates_returns_most_recent(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    first = FollowUpLog(thread_id="t1", recipient_email="a@x.com", subject="Hi", status=FollowUpStatus.SENT)
    db.add_log(first)

    from datetime import datetime, timedelta

    second = FollowUpLog(
        thread_id="t1",
        recipient_email="a@x.com",
        subject="Hi",
        status=FollowUpStatus.SENT,
        timestamp=first.timestamp + timedelta(days=1),
    )
    db.add_log(second)

    dates = db.last_followup_dates(["t1"])
    assert dates["t1"] == second.timestamp


def test_last_followup_dates_empty_input_returns_empty_dict(tmp_path):
    db = FollowUpDatabase(tmp_path / "test.db")
    assert db.last_followup_dates([]) == {}
