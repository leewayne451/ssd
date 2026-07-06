"""`flask seed-admin` — bootstrap administrator provisioning.

There is deliberately no in-app path to the admin role, so the first admin is
seeded out-of-band by this idempotent CLI command (run automatically by the
Docker entrypoint). Credentials come from env/options, the password faces the
same zxcvbn policy as registration (FSR-02), and seeding never bypasses the
admin TOTP requirement (FSR-01).
"""

from app.extensions import db
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.models.profile import Profile
from app.models.user import User

STRONG = "Correct-Horse-Battery-Staple-31!"


def _run(app, args=None, env=None):
    runner = app.test_cli_runner()
    return runner.invoke(args=["seed-admin"] + (args or []), env=env)


def test_creates_admin_with_profile_and_audit(app, db_session):
    result = _run(app, ["--email", "root@example.com", "--password", STRONG])
    assert result.exit_code == 0, result.output

    admin = User.query.filter_by(email="root@example.com").one()
    assert admin.role == UserRole.ADMIN
    assert admin.password_hash != STRONG  # stored hashed, never plaintext
    assert Profile.query.filter_by(user_id=admin.id).count() == 1
    assert AuditLog.query.filter_by(
        action_type="admin_seeded", target_id=admin.id
    ).count() == 1
    # 2FA still unenrolled — the /admin gate remains fully in force.
    assert admin.totp_enabled is False


def test_idempotent_second_run_changes_nothing(app, db_session):
    _run(app, ["--email", "root@example.com", "--password", STRONG])
    admin = User.query.filter_by(email="root@example.com").one()
    original_hash = admin.password_hash

    result = _run(app, ["--email", "root@example.com", "--password", "different-pass-entirely-9?"])
    assert result.exit_code == 0
    assert "already an administrator" in result.output

    db.session.refresh(admin)
    assert admin.password_hash == original_hash  # never resets credentials
    assert User.query.filter_by(email="root@example.com").count() == 1


def test_noop_when_env_not_configured(app, db_session):
    result = _run(app, env={"ADMIN_EMAIL": "", "ADMIN_PASSWORD": ""})
    assert result.exit_code == 0
    assert "skipping" in result.output
    assert User.query.count() == 0


def test_email_only_enters_generate_mode(app, db_session):
    """Email without a password is the RECOMMENDED mode since the rotation
    pattern landed: a single-use credential is generated and force-rotated
    (full coverage in test_password_rotation.py)."""
    result = _run(app, ["--email", "root@example.com"])
    assert result.exit_code == 0, result.output
    assert "SINGLE-USE bootstrap password:" in result.output
    admin = User.query.filter_by(email="root@example.com").one()
    assert admin.must_change_password is True


def test_password_without_email_fails_loudly(app, db_session):
    result = _run(app, ["--password", STRONG])
    assert result.exit_code != 0
    assert User.query.count() == 0


def test_weak_password_rejected_by_policy(app, db_session):
    result = _run(app, ["--email", "root@example.com", "--password", "password123"])
    assert result.exit_code != 0
    assert User.query.count() == 0


def test_reads_credentials_from_environment(app, db_session):
    result = _run(app, env={"ADMIN_EMAIL": "envadmin@example.com",
                            "ADMIN_PASSWORD": STRONG})
    assert result.exit_code == 0, result.output
    assert User.query.filter_by(email="envadmin@example.com").one().role == UserRole.ADMIN


def test_existing_non_admin_needs_explicit_promote(app, db_session, make_user):
    make_user("citizen@example.com", role=UserRole.BUYER)
    db.session.commit()

    refused = _run(app, ["--email", "citizen@example.com", "--password", STRONG])
    assert refused.exit_code != 0
    assert User.query.filter_by(email="citizen@example.com").one().role == UserRole.BUYER

    promoted = _run(app, ["--email", "citizen@example.com", "--password", STRONG, "--promote"])
    assert promoted.exit_code == 0
    assert User.query.filter_by(email="citizen@example.com").one().role == UserRole.ADMIN
    assert AuditLog.query.filter_by(action_type="admin_seeded").count() == 1
