# profile_forms — WTForms validation.
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from app.security.input_validation import MAX_SHORT, MAX_LONG


class ProfileForm(FlaskForm):
    """Form for editing a user's profile."""
    first_name = StringField(
        "First Name",
        validators=[DataRequired(message="First name is required."), Length(max=MAX_SHORT)]
    )
    last_name = StringField(
        "Last Name",
        validators=[DataRequired(message="Last name is required."), Length(max=MAX_SHORT)]
    )
    phone_number = StringField(
        "Phone Number",
        validators=[Optional(), Length(max=20)]
    )
    address = TextAreaField(
        "Address",
        validators=[Optional(), Length(max=MAX_LONG)]
    )
    bio = TextAreaField(
        "Bio",
        validators=[Optional(), Length(max=MAX_LONG)],
        description="Tell buyers a bit about yourself."
    )
    submit = SubmitField("Save Profile")