"""Cart forms (FR-08). The cart routes currently validate POST fields
directly server-side; these classes remain for form-rendered flows.
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class AddToCartForm(FlaskForm):
    """Form for adding an item to cart."""
    listing_id = IntegerField("Listing ID", validators=[DataRequired()])
    quantity = IntegerField(
        "Quantity",
        validators=[DataRequired(), NumberRange(min=1, message="Quantity must be >= 1")],
        default=1
    )
    submit = SubmitField("Add to Cart")


class UpdateCartItemForm(FlaskForm):
    """Form for updating quantity of a cart item."""
    listing_id = IntegerField("Listing ID", validators=[DataRequired()])
    quantity = IntegerField(
        "Quantity",
        validators=[DataRequired(), NumberRange(min=1, message="Quantity must be >= 1")]
    )
    submit = SubmitField("Update")


class RemoveFromCartForm(FlaskForm):
    """Form for removing an item from cart."""
    listing_id = IntegerField("Listing ID", validators=[DataRequired()])
    submit = SubmitField("Remove")
