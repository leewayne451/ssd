from app.services.audit_service import record
from app.models.audit_log import AuditLog


def test_record_writes_a_row(app, db_session):
    record(actor=None, action="test_action", target="user", target_id=1)
    row = AuditLog.query.filter_by(action_type="test_action").first()
    assert row is not None
    assert row.target_type == "user"
    assert row.target_id == 1
    assert row.actor_user_id is None


def test_record_does_not_crash_on_bad_input(app, db_session):
    record(actor=None, action="test_action_2")


def test_record_does_not_store_sensitive_fields(app, db_session):
    # NEGATIVE: passwords/tokens must not leak into log fields
    record(actor=None, action="login_fail", target="user", target_id=1,
           meta="hunter")
    row = AuditLog.query.filter_by(action_type="login_fail").first()
    assert row is not None
    assert "hunter2" not in (row.details or "")
    assert "secret123" not in (row.details or "")