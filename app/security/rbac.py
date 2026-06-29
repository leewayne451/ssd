from functools import wraps
from flask import session, abort


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            abort(401)
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                abort(401)
            if session.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
