# admin_forms — WTForms validation.
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


class TOTPCodeForm(FlaskForm):
    """A single 6-digit TOTP code, used for both enrolment and verification."""

    code = StringField(
        "Authentication code",
        validators=[
            DataRequired(),
            Length(min=6, max=6, message="Enter the 6-digit code."),
            Regexp(r"^\d{6}$", message="The code must be 6 digits."),
        ],
    )
    submit = SubmitField("Verify")
