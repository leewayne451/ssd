"""Authentication forms (FR-01/FR-02) — WTForms with CSRF via FlaskForm."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, ValidationError
from app.services.user_service import get_user_by_email

class RegistrationForm(FlaskForm):
    # FR-01: registration collects name, email, phone number and password.
    """Registration fields (FR-01): name, email, phone, password +
    confirmation. The server-side password policy runs in auth_service on
    top of these validators.
    """
    name = StringField('Full name', validators=[
        DataRequired(),
        Length(min=2, max=100),
    ])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField('Phone number', validators=[
        DataRequired(),
        # digits with optional leading + and common separators; 7-20 chars
        Regexp(r'^\+?[0-9][0-9\s\-]{6,19}$', message='Enter a valid phone number.'),
    ])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, field):
        """WTForms hook: reject duplicate registrations (SFR-01)."""
        if get_user_by_email(field.data):
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    # No "remember me": the backend never honoured it, and doing so would
    # conflict with the 30-minute inactivity timeout (FSR-04) — a dead
    # security control on the form is worse than none.
    """Email + password only (see class comment on the removed remember-me)."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
