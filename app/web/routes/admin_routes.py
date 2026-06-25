from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# TODO: admin dashboard, manage users, suspend accounts,
#       approve/reject listings, authentication review workflow,
#       order status updates, resolve disputes, audit logs
