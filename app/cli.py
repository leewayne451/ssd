"""
Château Collective — operational CLI commands.

`flask seed-admin` provisions the bootstrap administrator account. There is
deliberately NO in-app path to the admin role (registration always creates a
buyer, and only an existing admin could promote anyone), so the first admin
must be seeded out-of-band:

  * credentials come from the environment (ADMIN_EMAIL / ADMIN_PASSWORD) or
    CLI options — never from the repository;
  * the password must satisfy the same zxcvbn policy as every user (FSR-02);
  * the command is idempotent, so the container entrypoint runs it on every
    start: with the env vars unset it is a no-op, with them set it converges
    to "this admin exists" without ever resetting an existing password;
  * the seeded admin still has to enrol TOTP on first login — /admin stays
    2FA-gated (FSR-01), seeding grants no bypass.
"""
import click
from flask.cli import with_appcontext


@click.command("seed-admin")
@click.option("--email", envvar="ADMIN_EMAIL", default="",
              help="Admin email (or set ADMIN_EMAIL).")
@click.option("--password", envvar="ADMIN_PASSWORD", default="",
              help="Admin password (or set ADMIN_PASSWORD). Must satisfy the password policy.")
@click.option("--promote", is_flag=True, default=False,
              help="Allow promoting an EXISTING non-admin account with this email.")
@with_appcontext
def seed_admin(email: str, password: str, promote: bool):
    """Ensure the bootstrap administrator account exists (idempotent)."""
    from werkzeug.security import generate_password_hash

    from app.extensions import db
    from app.models.enums import AccountStatus, UserRole
    from app.models.profile import Profile
    from app.models.user import User
    from app.security.password_policy import validate_password
    from app.services.audit_service import record as audit_record

    email = (email or "").strip()
    password = password or ""

    # No credentials configured: explicit no-op so the container entrypoint
    # can call this unconditionally on every start.
    if not email and not password:
        click.echo("seed-admin: ADMIN_EMAIL/ADMIN_PASSWORD not set - skipping.")
        return

    # Half-configured is a deployment mistake — fail the start loudly.
    if not email or not password:
        raise click.ClickException(
            "seed-admin: set BOTH ADMIN_EMAIL and ADMIN_PASSWORD (or neither)."
        )

    if "@" not in email or len(email) > 255:
        raise click.ClickException("seed-admin: ADMIN_EMAIL is not a valid email address.")

    existing = User.query.filter_by(email=email).first()
    if existing is not None:
        role = getattr(existing.role, "value", existing.role)
        if role == UserRole.ADMIN.value:
            click.echo(f"seed-admin: '{email}' is already an administrator - nothing to do.")
            return
        if not promote:
            raise click.ClickException(
                f"seed-admin: '{email}' exists with role '{role}'. "
                "Refusing to promote an existing account without --promote."
            )
        existing.role = UserRole.ADMIN
        db.session.commit()
        audit_record(None, "admin_seeded", "user", existing.id,
                     {"mode": "promoted_existing"})
        click.echo(f"seed-admin: promoted existing account '{email}' to administrator.")
        click.echo("seed-admin: TOTP 2FA enrolment is still required on first /admin visit.")
        return

    # New account: same password bar as interactive registration (FSR-02).
    ok, error = validate_password(password)
    if not ok:
        raise click.ClickException(f"seed-admin: ADMIN_PASSWORD rejected - {error}")

    admin = User(
        email=email,
        password_hash=generate_password_hash(password),
        role=UserRole.ADMIN,
        status=AccountStatus.ACTIVE,
        email_confirmed=True,
    )
    db.session.add(admin)
    db.session.flush()
    db.session.add(Profile(user_id=admin.id, first_name="Platform",
                           last_name="Administrator"))
    db.session.commit()

    audit_record(None, "admin_seeded", "user", admin.id, {"mode": "created"})
    click.echo(f"seed-admin: administrator '{email}' created.")
    click.echo("seed-admin: log in and enrol TOTP 2FA at /admin (required before any admin action).")


def register_cli(app):
    app.cli.add_command(seed_admin)
