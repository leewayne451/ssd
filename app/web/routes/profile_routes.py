from flask import Blueprint, render_template, redirect, url_for, flash, request, abort

from app.security.rbac import login_required
from app.security.ownership import assert_owner
from app.services.auth_service import get_current_user
from app.services.profile_service import get_profile_by_user_id, update_profile
from app.web.forms.profile_forms import ProfileForm

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/<int:user_id>")
@login_required
def view_profile(user_id: int):
    """Own-profile view (SFR-03) — plus admins for account management.

    Profiles hold personal data (name, phone, address), so they are never
    public: the ownership check runs BEFORE any lookup, and a non-owner gets
    403 without learning whether the profile even exists (NFSR-01/02).
    """
    current_user = get_current_user()
    if current_user.id != user_id and current_user.role.value != "admin":
        abort(403)

    profile = get_profile_by_user_id(user_id)
    if not profile:
        abort(404)
    return render_template("profile/view.html", profile=profile)


@profile_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_profile(user_id: int):
    """
    Edit own profile only. If the profile doesn't exist, create it.
    """
    # 1. Get the current user
    current_user = get_current_user()

    # 2. Ownership FIRST — before this check ran, a request for another
    #    user's missing profile would auto-create a row for THAT user
    #    (IDOR-driven data pollution). Only the owner ever reaches the
    #    load/create step.
    if current_user.id != user_id:
        abort(403)

    # 3. Load or create the (own) profile
    profile = get_profile_by_user_id(user_id)
    if profile is None:
        # Auto-create a profile with default values
        from app.services.profile_service import create_profile
        profile = create_profile(user_id, "First", "Last")
        # This will flush/commit the new profile

    # 4. Enforce ownership (M2's helper) — defence in depth after the load
    assert_owner(profile, current_user)

    form = ProfileForm(obj=profile)

    if form.validate_on_submit():
        update_profile(user_id, form.data)
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile.view_profile", user_id=user_id))

    return render_template("profile/edit.html", form=form, profile=profile)