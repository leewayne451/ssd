# order_forms — WTForms validation.
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
