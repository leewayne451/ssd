# OWASP Mapping Table — Chateau Collective D2
**Owner: M6**  
Status (updated 5 Jul, post `harden/d1-conformance`): **all 25 rows now have passing tests.** The 4 Jul pending set (4, 6, 9, 13, 14, 17, 20, 21) was closed by the T-01…T-41 backlog — see [traceability_matrix.md](traceability_matrix.md) §8. Suite: 418 passing, 0 failures. Rows 5 and 15 additionally want a live-VM screenshot (TLS handshake / pip-audit artifact) for the report appendix.

| # | OWASP Category | Security Practice | File | Key Snippet | Test |
|---|---|---|---|---|---|
| 1 | A01 Broken Access Control | RBAC — role enforcement on protected routes | `app/security/rbac.py` | `role_required(*roles)` decorator aborts 403 if `session.get("role") not in roles` | `test_buyer_blocked_from_seller_route` — assert 403 |
| 2 | A01 Broken Access Control | RBAC — login gate on all protected routes | `app/security/rbac.py` | `login_required` checks `"user_id" not in session` → abort 401 | `test_anonymous_redirected_from_protected_route` — assert 401 |
| 3 | A01 Broken Access Control | Ownership / IDOR prevention on profile | `app/security/ownership.py` (enforced in `app/web/routes/profile_routes.py`) | `assert_owner(profile, current_user)` → 403 on owner mismatch | `tests/integration/test_profile_idor.py::TestProfileIDOR::test_user_cannot_edit_other_profile` (+ `::test_user_can_edit_own_profile`) |
| 4 | A02 Cryptographic Failures | Password hashing — no plaintext storage | `app/security/password_policy.py`, `app/services/auth_service.py` | `validate_password()` enforces strength; Werkzeug `generate_password_hash` at registration | `tests/integration/test_auth_sessions.py::test_password_stored_as_hash_not_plaintext` (T-03) |
| 5 | A02 Cryptographic Failures | HTTPS / HSTS — enforce encrypted transport | `app/security/headers.py` | `Strict-Transport-Security: max-age=31536000; includeSubDomains` injected on every response when `SESSION_COOKIE_SECURE=True` | `tests/security/test_headers.py::test_hsts_present_when_cookie_secure_is_true` (+ `::test_hsts_absent_over_plain_http_config`); M7 — SSL Labs / `openssl s_client` output |
| 6 | A03 Injection | Parameterised queries — no raw SQL | All routes via SQLAlchemy ORM | SQLAlchemy ORM used exclusively; no string-built queries anywhere in codebase | `tests/security/test_sql_and_pages.py::test_no_raw_sql_strings_in_app_code` (T-40) |
| 7 | A03 Injection | Input validation — length + format checks | `app/security/input_validation.py` | `validate_length()`, `validate_email()`, `validate_non_empty()`, `validate_integer_range()` | `tests/security/test_input_validation.py::test_validate_length_rejects_too_long`, `::test_validate_email_rejects_malformed_addresses` |
| 8 | A03 Injection | HTML stripping on free-text fields | `app/security/input_validation.py` | `strip_html()` uses stdlib `html.parser` to remove all tags before persistence | `tests/security/test_input_validation.py::test_strip_html_neutralizes_script_payload` (end-to-end: `tests/integration/test_profile_idor.py::...::test_user_can_edit_own_profile` asserts `<script>` not in saved bio) |
| 9 | A04 Insecure Design | Workflow state integrity — reject illegal transitions | `app/services/workflow_service.py` | Transition map matches D1 H-3 exactly (no shipped→sold bypass); role + ownership enforced; every accepted/rejected attempt audited | `tests/unit/test_workflow_d1.py::test_transition_matrix_exactly_matches_d1_h3` (T-23, 64 combos), `::test_shipped_to_sold_direct_is_rejected` (T-24) |
| 10 | A05 Security Misconfiguration | Secure response headers | `app/security/headers.py` | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`, `Referrer-Policy` set via `@app.after_request` | `tests/security/test_headers.py::test_security_headers_present_on_every_response` (+ `::test_csp_restricts_default_and_script_src`, `::test_headers_present_on_error_responses_too`) |
| 11 | A05 Security Misconfiguration | Safe error pages — no stack trace leakage | `app/web/routes/error_routes.py` | `@errors_bp.app_errorhandler(500)` returns generic `errors/500.html`; exception detail never passed to template | `tests/security/test_error_routes.py::test_500_returns_generic_page_with_no_leaked_detail` (+ `::test_404_returns_custom_page`) |
| 12 | A05 Security Misconfiguration | Session cookie flags | `app/security/session_policy.py` + `app/config.py` | `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_SECURE=True` (prod) | `tests/unit/test_auth.py::test_session_cookie_flags` |
| 13 | A05 Security Misconfiguration | Session inactivity timeout | `app/security/session_policy.py` + `app/__init__.py::check_session_timeout` | `before_request` hook clears the session past `SESSION_TIMEOUT_MINUTES` and redirects to login | `tests/integration/test_auth_sessions.py::test_session_expires_after_inactivity` (+ `_activity_within_limit_keeps_session_alive`) (T-04) |
| 14 | A05 Security Misconfiguration | Session fixation prevention | `app/security/session_policy.py` | `regenerate_session()` on login discards pre-login session content | `tests/integration/test_auth_sessions.py::test_login_discards_pre_login_session_content` (T-05) |
| 15 | A06 Vulnerable Components | Dependency vulnerability scanning | `requirements.txt` + CI | `pip-audit` runs on every PR via `.github/workflows/ci.yml`; findings reviewed before merge | M7 — pip-audit output screenshot |
| 16 | A07 Identification & Auth Failures | Brute-force / rate limiting on login | `app/security/rate_limit.py` | `should_lock_account()` triggers after 3 failures; `get_lockout_duration()` escalates: 5 min → 15 min → 60 min | `tests/unit/test_auth.py::test_account_lockout_after_failed_attempts`; IP-level throttling = nginx `limit_req` (M7, E-04) |
| 17 | A07 Identification & Auth Failures | Failed login audit logging | `app/services/auth_service.py` + `app/services/audit_service.py` | Register / login-failed (with reason) / login-success / logout each write an AuditLog row | `tests/integration/test_auth_sessions.py::test_auth_events_write_audit_rows` (T-06) |
| 18 | A07 Identification & Auth Failures | Admin 2FA gate | `app/security/admin_2fa.py` | TOTP gate on `/admin` — non-2FA-verified admin session redirected to verify | `tests/integration/test_admin_2fa_routes.py` (9 tests) + `tests/unit/security/test_admin_2fa.py` (7 tests, incl. RFC 6238 vector) |
| 19 | A08 Software & Data Integrity | CSRF token on every form | `app/security/csrf.py` + Flask-WTF | `CSRFProtect().init_app(app)` — every WTForm renders a hidden `csrf_token` field; POST without valid token → 400 | `tests/security/test_csrf.py::test_post_without_csrf_token_is_rejected` (+ `::test_post_with_garbage_csrf_token_is_rejected`, `::test_post_with_valid_csrf_token_is_accepted`) |
| 20 | A08 Software & Data Integrity | File upload — extension + MIME/magic byte validation | `app/security/file_validation.py` | `validate_upload()` checks extension against allowlist, reads first 12 bytes for magic signature, rejects mismatch | `tests/unit/test_file_validation.py` (3) + end-to-end `tests/integration/test_listing_discovery.py::test_spoofed_magic_bytes_rejected_via_route` (T-18) |
| 21 | A08 Software & Data Integrity | Randomised stored filenames + safe serving | `app/security/file_validation.py`, `listing_routes.py::media` | `generate_stored_filename()` → `uuid4().hex + ext`; media route resolves only uuid-shaped names inside the upload dir | `test_listing_discovery.py::test_traversal_filename_neutralised_and_stored_name_randomised` (T-20), `::test_media_route_rejects_traversal_and_unknown_names` (T-21) |
| 22 | A09 Security Logging & Monitoring | Audit trail for security events | `app/services/audit_service.py` + `app/models/audit_log.py` | `audit_service.record(...)` — service done; wiring into auth/workflow/admin flows in progress (CTRL-003) | `tests/test_audit_service.py::test_record_writes_a_row`; event wiring = T-06, T-37 |
| 23 | A09 Security Logging & Monitoring | No secrets in logs | `app/services/audit_service.py` | `meta` dict never includes `password`, `token`, or session keys | `tests/test_audit_service.py::test_record_does_not_store_sensitive_fields` (+ same for `test_security_event_service.py`) |
| 24 | A09 Security Logging & Monitoring | Admin log viewer — read-only, 2FA-gated | `app/web/routes/admin_routes.py` | Log page gated by admin role + 2FA; no edit/delete UI | `tests/test_admin_logs.py::test_non_admin_blocked_from_logs`, `::test_admin_with_2fa_can_access_logs`, `::test_audit_log_viewer_is_read_only` |
| 25 | A03 Injection (XSS) | Output encoding — XSS prevention | `app/security/output_encoding.py` + Jinja2 | Jinja2 autoescaping ON for all `.html` templates; `escape_html()` / `safe_display()` / `nl2br()` for non-template contexts; `|safe` filter never used on user data | `tests/security/test_output_encoding.py::test_escape_html_escapes_script_tag` (+ `::test_safe_display_escapes_xss_payload`) |

---

## Remaining for the report (code complete — evidence capture only)

All 25 code rows are tested and passing. What's left is screenshot/transcript
capture from the live VM + CI, not code:

| Row(s) | Outstanding evidence | Owner |
|---|---|---|
| 5 | TLS handshake proof (`openssl s_client` / SSL Labs) against the live domain | M7 (Yi Phang) |
| 15 | pip-audit artifact + dependency inventory (incl. `zxcvbn`) from a CI run | M7 (Yi Phang) |

See [traceability_matrix.md](traceability_matrix.md) §8b for the full list of
VM-only evidence items (E-01…E-06). The former M8–M12 descope is **implemented
as of 6 Jul** (seller applications, reviews, shipment tracking, disputes,
backup/recovery — §8b), which also strengthens the XSS row (stored-XSS escape
test on review comments) and the access-control rows (profile view/edit
locked to owner+admin; dev login backdoor removed; CSP now 'self'-only with
Bootstrap self-hosted).
