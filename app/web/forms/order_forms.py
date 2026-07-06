"""Order forms (FR-09/FR-15) — kept for form-rendered flows; the routes
validate POST data server-side regardless.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


class PlaceOrderForm(FlaskForm):
    """Form for placing orders from cart."""
    submit = SubmitField("Place Orders")


class TransitionOrderForm(FlaskForm):
    """Form for transitioning an order to a new status."""
    new_status = StringField(
        "New Status",
        validators=[DataRequired()]
    )
    submit = SubmitField("Transition")
