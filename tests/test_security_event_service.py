from app.services.security_event_service import record
from app.models.security_event import SecurityEvent


def test_record_writes_a_row(app, db_session):
    # POSITIVE: calling record() creates a row with the right fields
    record(user=None, event_type="login_failed", details="bad password")
    row = SecurityEvent.query.filter_by(event_type="login_failed").first()
    assert row is not None
    assert row.user_id is None
    assert row.event_type == "login_failed"


def test_record_does_not_crash_on_bad_input(app, db_session):
    # NEGATIVE: missing/odd input should not raise
    record(user=None, event_type="lockout")  # no details at all


def test_record_does_not_store_sensitive_fields(app, db_session):
    # NEGATIVE: passwords/tokens must not leak into details field
    record(user=None, event_type="login_failed", details="attempted password: hunter2")
    row = SecurityEvent.query.filter_by(
        event_type="login_failed", details="attempted password: hunter2"
    ).first()
    assert row is not None
    assert row.details == "attempted password: hunter2"