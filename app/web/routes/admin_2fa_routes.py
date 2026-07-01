"""
Château Collective — Admin 2FA enrolment & verification routes (M2)

These live in their own blueprint (still under the /admin prefix) so they stay
reachable while the rest of the /admin area is gated by ``admin_2fa_required``:
an admin must be able to reach the setup/verify pages *before* they hold a
verified second factor. Both pages still require an authenticated admin via
``role_required("admin")``.
"""

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
)

from app.extensions import db
from app.security.rbac import role_required
from app.security import admin_2fa
from app.services.auth_service import get_current_user
from app.services.audit_service import record as audit_record
from app.services.security_event_service import record as security_record
from app.web.forms.admin_forms import TOTPCodeForm

admin_2fa_bp = Blueprint("admin_2fa", __name__, url_prefix="/admin/2fa")

# Session dict key name (not a credential) holding the not-yet-confirmed secret during enrolment.
_PENDING_SECRET = "pending_totp_secret"  # nosec B105


def _safe_next(default_endpoint="admin.index"):
    """Return a safe local redirect target from ?next=, else the admin home."""
    target = request.args.get("next") or request.form.get("next")
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for(default_endpoint)


@admin_2fa_bp.route("/setup", methods=("GET", "POST"))
@role_required("admin")
def setup():
    """Enrol a TOTP secret for the current admin and confirm it with a code."""
    user = get_current_user()

    # Already enrolled — nothing to set up; send them to verify instead.
    if user.totp_enabled and user.totp_secret:
        return redirect(url_for("admin_2fa.verify", next=_safe_next()))

    # Reuse a pending secret across the GET->POST round trip so the QR/secret
    # the admin scanned stays valid; generate one on first view.
    secret = session.get(_PENDING_SECRET)
    if not secret:
        secret = admin_2fa.generate_secret()
        session[_PENDING_SECRET] = secret

    form = TOTPCodeForm()
    if form.validate_on_submit():
        if admin_2fa.verify(secret, form.code.data):
            user.totp_secret = secret
            user.totp_enabled = True
            db.session.commit()
            session.pop(_PENDING_SECRET, None)
            admin_2fa.mark_verified()
            audit_record(user, "admin_2fa_enrolled", target="user", target_id=user.id)
            flash("Two-factor authentication is now enabled.", "success")
            return redirect(_safe_next())
        security_record(user, "admin_2fa_failed", "invalid code during enrolment")
        flash("That code was not valid. Try again.", "danger")

    uri = admin_2fa.provisioning_uri(secret, account_name=user.email)
    return render_template(
        "admin/2fa_setup.html",
        form=form,
        secret=secret,
        provisioning_uri=uri,
        next=_safe_next(),
    )


@admin_2fa_bp.route("/verify", methods=("GET", "POST"))
@role_required("admin")
def verify():
    """Challenge an enrolled admin for a current TOTP code (once per session)."""
    user = get_current_user()

    # Not enrolled yet — they must set up first.
    if not user.totp_enabled or not user.totp_secret:
        return redirect(url_for("admin_2fa.setup", next=_safe_next()))

    form = TOTPCodeForm()
    if form.validate_on_submit():
        if admin_2fa.verify(user.totp_secret, form.code.data):
            admin_2fa.mark_verified()
            audit_record(user, "admin_2fa_verified", target="user", target_id=user.id)
            return redirect(_safe_next())
        security_record(user, "admin_2fa_failed", "invalid code at verification")
        flash("That code was not valid. Try again.", "danger")

    return render_template("admin/2fa_verify.html", form=form, next=_safe_next())
