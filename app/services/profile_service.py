from datetime import datetime, timezone
from app.extensions import db
from app.models.profile import Profile
from app.security.input_validation import sanitize_text, strip_html


def get_profile_by_user_id(user_id: int) -> Profile | None:
    """Fetch a user's profile, or None if not found."""
    return Profile.query.filter_by(user_id=user_id).first()


def create_profile(user_id: int, first_name: str, last_name: str) -> Profile:
    """Create a profile for a new user (called from M1 on registration)."""
    profile = Profile(
        user_id=user_id,
        first_name=sanitize_text(first_name),
        last_name=sanitize_text(last_name),
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def update_profile(user_id: int, data: dict) -> Profile:
    """
    Update a user's profile with sanitized data.
    Uses strip_html() on free-text fields to prevent stored XSS.
    """
    profile = get_profile_by_user_id(user_id)
    if not profile:
        # Safety fallback — create if missing (shouldn't happen)
        profile = create_profile(
            user_id,
            data.get("first_name", ""),
            data.get("last_name", "")
        )

    # Strip HTML and trim whitespace on all text fields
    profile.first_name = sanitize_text(data.get("first_name", profile.first_name))
    profile.last_name = sanitize_text(data.get("last_name", profile.last_name))

    if "phone_number" in data:
        profile.phone_number = sanitize_text(data.get("phone_number", "")) or None

    if "address" in data:
        # strip_html() removes all HTML tags using stdlib parser
        profile.address = strip_html(data.get("address", profile.address or ""))

    if "bio" in data:
        # Bio is the IDOR + XSS demo field: strips tags before saving
        profile.bio = strip_html(data.get("bio", profile.bio or ""))

    profile.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return profile