from flask import Blueprint, render_template, redirect, url_for, flash, request, abort

from app.security.rbac import login_required
from app.security.ownership import assert_owner
from app.services.auth_service import get_current_user
from app.services.profile_service import get_profile_by_user_id, update_profile
from app.web.forms.profile_forms import ProfileForm

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/<int:user_id>")
def view_profile(user_id: int):
    """Public profile view (anyone can view)."""
    profile = get_profile_by_user_id(user_id)
    if not profile:
        abort(404)
    # No ownership check here — profiles are public read.
    return render_template("profile/view.html", profile=profile)


@profile_bp.route("/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
def edit_profile(user_id: int):
    """
    Edit own profile only. If the profile doesn't exist, create it.
    """
    # 1. Get the current user
    current_user = get_current_user()
    
    # 2. Load or create the profile
    profile = get_profile_by_user_id(user_id)
    if profile is None:
        # Auto-create a profile with default values
        from app.services.profile_service import create_profile
        profile = create_profile(user_id, "First", "Last")
        # This will flush/commit the new profile

    # 3. Enforce ownership (M2's helper)
    assert_owner(profile, current_user)

    form = ProfileForm(obj=profile)

    if form.validate_on_submit():
        update_profile(user_id, form.data)
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile.view_profile", user_id=user_id))

    return render_template("profile/edit.html", form=form, profile=profile)