# OWASP Mapping Table — Chateau Collective D2
**Owner: M6**  
Status: M6 rows (3, 5, 7, 8, 10, 11, 19, 25) implemented with passing tests. Rows still marked ⏳ are pending other members (M1/M2/M4/M5/M7).

| # | OWASP Category | Security Practice | File | Key Snippet | Test |
|---|---|---|---|---|---|
| 1 | A01 Broken Access Control | RBAC — role enforcement on protected routes | `app/security/rbac.py` | `role_required(*roles)` decorator aborts 403 if `session.get("role") not in roles` | `test_buyer_blocked_from_seller_route` — assert 403 |
| 2 | A01 Broken Access Control | RBAC — login gate on all protected routes | `app/security/rbac.py` | `login_required` checks `"user_id" not in session` → abort 401 | `test_anonymous_redirected_from_protected_route` — assert 401 |
| 3 | A01 Broken Access Control | Ownership / IDOR prevention on profile | `app/security/ownership.py` (enforced in `app/web/routes/profile_routes.py`) | `assert_owner(profile, current_user)` → 403 on owner mismatch | `tests/integration/test_profile_idor.py::TestProfileIDOR::test_user_cannot_edit_other_profile` (+ `::test_user_can_edit_own_profile`) |
| 4 | A02 Cryptographic Failures | Password hashing — no plaintext storage | `app/security/password_policy.py` | `validate_password()` enforces min 8 chars, upper/lower/digit/special; Werkzeug `generate_password_hash` used at registration *(wired in M1 auth service)* | ⏳ `test_password_stored_as_hash` — assert DB value not equal to plaintext |
| 5 | A02 Cryptographic Failures | HTTPS / HSTS — enforce encrypted transport | `app/security/headers.py` | `Strict-Transport-Security: max-age=31536000; includeSubDomains` injected on every response when `SESSION_COOKIE_SECURE=True` | `tests/security/test_headers.py::test_hsts_present_when_cookie_secure_is_true` (+ `::test_hsts_absent_over_plain_http_config`); M7 — SSL Labs / `openssl s_client` output |
| 6 | A03 Injection | Parameterised queries — no raw SQL | All routes via SQLAlchemy ORM | SQLAlchemy ORM used exclusively; no string-built queries anywhere in codebase | ⏳ negative test — assert raw SQL string not present in any route file |
| 7 | A03 Injection | Input validation — length + format checks | `app/security/input_validation.py` | `validate_length()`, `validate_email()`, `validate_non_empty()`, `validate_integer_range()` | `tests/security/test_input_validation.py::test_validate_length_rejects_too_long`, `::test_validate_email_rejects_malformed_addresses` |
| 8 | A03 Injection | HTML stripping on free-text fields | `app/security/input_validation.py` | `strip_html()` uses stdlib `html.parser` to remove all tags before persistence | `tests/security/test_input_validation.py::test_strip_html_neutralizes_script_payload` (end-to-end: `tests/integration/test_profile_idor.py::...::test_user_can_edit_own_profile` asserts `<script>` not in saved bio) |
| 9 | A04 Insecure Design | Workflow state integrity — reject illegal transitions | `app/services/workflow_service.py` | Legal transition map enforced server-side; illegal jump raises error *(M4)* | ⏳ `test_illegal_order_status_transition_rejected` |
| 10 | A05 Security Misconfiguration | Secure response headers | `app/security/headers.py` | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy` set via `@app.after_request` | `tests/security/test_headers.py::test_security_headers_present_on_every_response` (+ `::test_csp_restricts_default_and_script_src`, `::test_headers_present_on_error_responses_too`) |
| 11 | A05 Security Misconfiguration | Safe error pages — no stack trace leakage | `app/web/routes/error_routes.py` | `@errors_bp.app_errorhandler(500)` returns generic `errors/500.html`; exception detail never passed to template | `tests/security/test_error_routes.py::test_500_returns_generic_page_with_no_leaked_detail` (+ `::test_404_returns_custom_page`) |
| 12 | A05 Security Misconfiguration | Session cookie flags | `app/security/session_policy.py` + `app/config.py` | `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_SECURE=True` (prod) | `test_session_cookie_has_httponly_and_samesite` — inspect response `Set-Cookie` header |
| 13 | A05 Security Misconfiguration | Session inactivity timeout | `app/security/session_policy.py` | `check_inactivity_timeout()` clears session if `now - last_activity > SESSION_TIMEOUT_MINUTES` (default 30 min) | ⏳ `test_session_expires_after_inactivity` — mock time delta > 30 min |
| 14 | A05 Security Misconfiguration | Session fixation prevention | `app/security/session_policy.py` | `regenerate_session()` called on login to issue a new session ID | ⏳ `test_session_id_changes_after_login` |
| 15 | A06 Vulnerable Components | Dependency vulnerability scanning | `requirements.txt` + CI | `pip-audit` runs on every PR via `.github/workflows/ci.yml`; findings reviewed before merge | M7 — pip-audit output screenshot |
| 16 | A07 Identification & Auth Failures | Brute-force / rate limiting on login | `app/security/rate_limit.py` | `should_lock_account()` triggers after 3 failures; `get_lockout_duration()` escalates: 5 min → 15 min → 60 min | ⏳ `test_account_locked_after_n_failed_logins` |
| 17 | A07 Identification & Auth Failures | Failed login audit logging | `app/services/auth_service.py` + `app/services/audit_service.py` | Failed attempt writes a security event via `audit_service.record(actor, "login_failed", ...)` *(M1 + M5)* | ⏳ `test_failed_login_writes_security_event` |
| 18 | A07 Identification & Auth Failures | Admin 2FA gate | `app/security/admin_2fa.py` | TOTP gate on `/admin` — non-2FA-verified admin session aborts 403 *(M2)* | ⏳ `test_admin_route_requires_2fa` |
| 19 | A08 Software & Data Integrity | CSRF token on every form | `app/security/csrf.py` + Flask-WTF | `CSRFProtect().init_app(app)` — every WTForm renders a hidden `csrf_token` field; POST without valid token → 400 | `tests/security/test_csrf.py::test_post_without_csrf_token_is_rejected` (+ `::test_post_with_garbage_csrf_token_is_rejected`, `::test_post_with_valid_csrf_token_is_accepted`) |
| 20 | A08 Software & Data Integrity | File upload — extension + MIME/magic byte validation | `app/security/file_validation.py` | `validate_upload()` checks extension against allowlist, reads first 12 bytes for magic signature, rejects mismatch | `test_php_upload_rejected`, `test_spoofed_mime_rejected`, `test_oversize_upload_rejected` |
| 21 | A08 Software & Data Integrity | Randomised stored filenames | `app/security/file_validation.py` | `generate_stored_filename()` replaces original name with `uuid4().hex + ext` — prevents path traversal / enumeration | `test_stored_filename_is_uuid_not_original` |
| 22 | A09 Security Logging & Monitoring | Audit trail for security events | `app/services/audit_service.py` + `app/models/audit_log.py` | `audit_service.record(actor, action, target, meta)` called on login, access denied, state change, admin actions *(M5)* | ⏳ `test_action_writes_audit_row` |
| 23 | A09 Security Logging & Monitoring | No secrets in logs | `app/services/audit_service.py` | `meta` dict never includes `password`, `token`, or session keys; enforced by audit service *(M5)* | ⏳ `test_no_plaintext_secrets_in_audit_log` |
| 24 | A09 Security Logging & Monitoring | Admin log viewer — read-only, 2FA-gated | `app/web/routes/admin_routes.py` | Dashboard lists audit + security events, paginated, no edit/delete UI *(M5)* | ⏳ `test_non_admin_cannot_access_log_viewer` |
| 25 | A03 Injection (XSS) | Output encoding — XSS prevention | `app/security/output_encoding.py` + Jinja2 | Jinja2 autoescaping ON for all `.html` templates; `escape_html()` / `safe_display()` / `nl2br()` for non-template contexts; `|safe` filter never used on user data | `tests/security/test_output_encoding.py::test_escape_html_escapes_script_tag` (+ `::test_safe_display_escapes_xss_payload`) |

---

## Summary of pending rows (fill in once teammates merge)

| Row | Waiting on | Expected by |
|---|---|---|
| 4 — Password hash wired | M1 (auth service) | Wed 1 Jul |
| 13, 14 — Session timeout / fixation | M1 (auth routes wired) | Wed 1 Jul |
| 16, 17 — Rate limit / failed login audit | M1 + M5 | Wed 1 Jul |
| 18 — Admin 2FA | M2 | Wed 1 Jul |
| 22, 23, 24 — Audit logging | M5 | Sun 5 Jul |
| 9 — Workflow integrity | M4 | Sun 5 Jul |
