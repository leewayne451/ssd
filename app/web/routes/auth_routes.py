"""Authentication routes (FR-01/FR-02): register, login, logout.
All policy — password strength, lockout, generic errors, session
regeneration, audit — lives in auth_service; these views translate HTTP.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session

from app.security.rbac import login_required
from app.web.forms.auth_forms import RegistrationForm, LoginForm, ChangePasswordForm
from app.services.auth_service import (
    register_user,
    login_user,
    logout_user,
    get_current_user,
    change_password,
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Create an account + profile; validation errors re-render the form."""
    form = RegistrationForm()
    if form.validate_on_submit():
        user, error = register_user(
            form.email.data,
            form.password.data,
            name=form.name.data,
            phone=form.phone.data,
        )
        if user:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'danger')
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate and establish the session; every failure shows one generic message (no account enumeration).
    """
    form = LoginForm()
    if form.validate_on_submit():
        user, error = login_user(form.email.data, form.password.data)
        if user:
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('public.index'))
        else:
            flash(error, 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password_view():
    """Rotate the caller's own password (FR-02).

    Requires the current password and runs the new one through the full
    zxcvbn policy in auth_service. Accounts flagged must_change_password
    (bootstrap admins) are quarantined here by the app-factory hook until
    they rotate.
    """
    form = ChangePasswordForm()
    forced = getattr(get_current_user(), 'must_change_password', False)
    if form.validate_on_submit():
        ok, error = change_password(
            get_current_user(),
            form.current_password.data,
            form.new_password.data,
        )
        if ok:
            flash('Password changed successfully.', 'success')
            return redirect(url_for('public.index'))
        flash(error, 'danger')
    return render_template('auth/change_password.html', form=form, forced=forced)


@auth_bp.route('/logout')
def logout():
    """Clear the session and audit the logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))