"""
Château Collective — operational CLI commands.

`flask seed-admin` provisions the bootstrap administrator account. There is
deliberately NO in-app path to the admin role (registration always creates a
buyer, and only an existing admin could promote anyone), so the first admin
must be seeded out-of-band:

  * the recommended mode sets ONLY ADMIN_EMAIL: a strong random single-use
    password is generated, printed once to stdout (docker compose logs), and
    the account is quarantined behind forced first-login rotation — the
    logged value is dead the moment the real admin rotates it, and no secret
    ever sits in .env, the shell history or the container environment;
  * an explicit ADMIN_PASSWORD (env or --password) is still accepted for
    local development and must satisfy the same zxcvbn policy as every user
    (FSR-02); explicitly chosen passwords are not force-rotated;
  * the command is idempotent, so the container entrypoint runs it on every
    start: with the env vars unset it is a no-op, with them set it converges
    to "this admin exists" without ever resetting an existing password;
  * the seeded admin still has to enrol TOTP — /admin stays 2FA-gated
    (FSR-01), and the rotation quarantine runs first, so enrolment can only
    happen after the bootstrap credential has been retired.
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

    # Nothing configured: explicit no-op so the container entrypoint can
    # call this unconditionally on every start.
    if not email and not password:
        click.echo("seed-admin: ADMIN_EMAIL not set - skipping.")
        return

    # A password without an email is a deployment mistake — fail loudly.
    if not email:
        raise click.ClickException(
            "seed-admin: ADMIN_PASSWORD is set but ADMIN_EMAIL is not."
        )

    if "@" not in email or len(email) > 255:
        raise click.ClickException("seed-admin: ADMIN_EMAIL is not a valid email address.")

    # Email only (recommended): generate a strong single-use bootstrap
    # password and force rotation on first login. The one-time echo below is
    # the only place it ever exists outside the password hash.
    generated = not password
    if generated:
        import secrets

        password = secrets.token_urlsafe(18)

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

    # Explicitly chosen passwords face the same bar as interactive
    # registration (FSR-02). Generated ones are 144-bit random tokens —
    # strength is guaranteed by construction, not by composition rules.
    if not generated:
        ok, error = validate_password(password)
        if not ok:
            raise click.ClickException(f"seed-admin: ADMIN_PASSWORD rejected - {error}")

    admin = User(
        email=email,
        password_hash=generate_password_hash(password),
        role=UserRole.ADMIN,
        status=AccountStatus.ACTIVE,
        email_confirmed=True,
        must_change_password=generated,
    )
    db.session.add(admin)
    db.session.flush()
    db.session.add(Profile(user_id=admin.id, first_name="Platform",
                           last_name="Administrator"))
    db.session.commit()

    audit_record(None, "admin_seeded", "user", admin.id,
                 {"mode": "created", "bootstrap_password": generated})
    click.echo(f"seed-admin: administrator '{email}' created.")
    if generated:
        click.echo("seed-admin: ------------------------------------------------------------")
        click.echo(f"seed-admin: SINGLE-USE bootstrap password: {password}")
        click.echo("seed-admin: The first login forces a password change; this value is")
        click.echo("seed-admin: dead the moment the new password is set.")
        click.echo("seed-admin: ------------------------------------------------------------")
    click.echo("seed-admin: after rotating, enrol TOTP 2FA at /admin (required before any admin action).")


def register_cli(app):
    """Attach the operational commands to the Flask CLI."""
    app.cli.add_command(seed_admin)
