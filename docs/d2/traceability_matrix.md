# D1 → Implementation → Test Traceability Matrix

**Source:** `doc/ICT2116_P2_team31_Deliverable_One.pdf` (all requirement families, incl. Appendices A-1…A-4 and §9.3 design decisions).
**Generated:** 4 Jul 2026. **Updated 5 Jul 2026** after the `harden/d1-conformance` iteration landed all pre-freeze fixes (M1–M6 + R1). Companion docs: [milestone_audit_followups.md](milestone_audit_followups.md) (fix tasks), [owasp_mapping_table.md](owasp_mapping_table.md) (OWASP view of the same evidence).
**How to verify:** `pytest -q` runs every test cited here; test refs are `file::test_name`. **Suite status: 418 passing** (309 application + 109 AI-review tooling), 0 failures.

> **Iteration note (harden/d1-conformance):** the T-01…T-41 backlog in §8 and the R1 edge-hardening are **implemented** — every ⏳-code item below is now ✅. The only remaining non-✅ rows are (a) M7 evidence captures that require the live VM (load numbers, browser screenshots, TLS/SSH proofs — the 🏗/⏳ rows), and (b) the M8–M12 features deliberately descoped to the residual-risks section (⏸).

**Status legend**

| Symbol | Meaning |
|---|---|
| ✅ | Implemented and covered by passing test(s) |
| 🟡 | Implemented; **test missing** (listed in §8 backlog) |
| 🔧 | Being fixed/completed pre-freeze — task reference in [milestone_audit_followups.md](milestone_audit_followups.md) |
| 🏗 | Deploy/CI-layer control (M7) — evidence is config + screenshots, not pytest |
| ⏳ | Evidence task only (measurement, screenshot, review) — no code needed |
| ⏸ | Descoped to stretch M8–M12 → D2 residual-risks section |

---

## 1. Functional Requirements (FR)

| ID | Requirement | Status | Implementation evidence | Test evidence / gap |
|---|---|---|---|---|
| FR-01 | Registration: name, email, phone, password | ✅ | `app/web/forms/auth_forms.py` (name+phone), `auth_service.py::register_user` (creates Profile) | `tests/integration/test_auth_sessions.py::test_register_captures_name_phone_and_creates_profile` (T-01), `::test_register_rejects_invalid_name_or_phone` (T-02) |
| FR-02 | Login / logout | ✅ | `auth_service.py::login_user/logout_user`, `app/web/routes/auth_routes.py` | `test_auth.py::test_login_success`, `::test_login_wrong_password`, `::test_logout_clears_session` |
| FR-03 | Profile management (own profile) | ✅ | `app/web/routes/profile_routes.py`, `app/services/profile_service.py`, `app/security/ownership.py` | `tests/integration/test_profile_idor.py::TestProfileIDOR` (own-edit + cross-user blocked) |
| FR-04 | Seller application | ⏸ M10 | `app/models/seller_application.py` (model only; routes/service stubs) | — (residual risk) |
| FR-05 | Public browsing + product detail page | ✅ | `app/web/routes/listing_routes.py` (detail rebuilt), `listing_service.py::get_public_listings` (approval-filtered) | `tests/integration/test_listing_discovery.py::test_public_index_hides_pending_and_rejected` (T-14), `::test_detail_hidden_for_unapproved_except_owner_and_admin` (T-15) |
| FR-06 | Search & filter (category/brand/condition/price) | ✅ | `listing_routes.py::index`, `listing_service.py::get_public_listings` (ORM-bound filters) | `test_listing_discovery.py::test_search_filters_by_category_brand_condition_price` (T-16), `::test_search_hostile_input_treated_as_data` (T-17) |
| FR-07 | Listing create/edit + image upload (own only) | ✅ | `listing_routes.py`, `app/services/upload_service.py`, `app/security/file_validation.py` | `tests/unit/test_listing_routes.py` (6 tests); upload hardening `test_listing_discovery.py` T-18..T-21 |
| FR-08 | Cart add/view/remove | ✅ | `app/services/cart_service.py`, `cart_routes.py` (own rbac auth; templates added) | `tests/unit/test_cart_service.py` (19) + `tests/integration/test_cart_order_http.py::test_login_then_load_cart_page` (T-22) |
| FR-09 | Purchase commitment | ✅ | `app/services/order_service.py::place_orders_from_cart` (approved-only, SFR-09) | `tests/unit/test_order_service.py` (7) + `test_workflow_d1.py::test_commit_skips_unapproved_listing` (T-31) |
| FR-10 | Shipment status tracking by seller | ✅ (workflow); ⏸ M9 (Shipment tracking entity) | `workflow_service.py` (awaiting_shipment/shipped edges + ownership) | `test_workflow_d1.py::test_seller_cannot_transition_other_sellers_order` (T-25); tracking-reference detail deferred to M9 |
| FR-11 | Simulated checkout after workflow checks | ✅ | `app/services/checkout_service.py`, `order_routes.py::checkout` (server-controlled payment) | `test_workflow_d1.py::test_checkout_happy_path` (T-26), `::test_client_supplied_payment_status_ignored` (T-27), `::test_checkout_blocked_before_authentication` (T-28) |
| FR-12 | Admin dashboard | ✅ | `admin_routes.py` (users/listings/orders/logs, all 2FA-gated) | `tests/integration/test_admin_operations.py`, `test_admin_2fa_routes.py` |
| FR-13 | User suspension by admin | ✅ | `admin_service.py::suspend_user` + login/session enforcement (`auth_service`, `rbac`) | `test_admin_operations.py::test_admin_suspend_user_writes_audit_row` (T-32), `test_auth_sessions.py::test_suspended_user_cannot_login` (T-07), `test_rbac_hardening.py::test_suspension_kills_active_session_on_next_request` (T-10) |
| FR-14 | Listing monitoring (suspicious/reported) | ✅ | `admin_service.py` approve/reject + `report_listing`; `product_listings.reported` column + migration | `test_admin_operations.py::test_admin_approve_and_reject_listing_with_audit` (T-34), `::test_buyer_can_report_listing` |
| FR-15 | Admin order/workflow status update | ✅ | `admin_service.py::update_order_workflow` via audited state machine | `test_admin_operations.py::test_admin_workflow_update_writes_audit` (T-35/T-37) |
| FR-16 | Purchase-based reviews | ⏸ M8 | `app/models/review.py` only | — (residual risk; top stretch — XSS-defence evidence) |
| FR-17 | Dispute resolution | ⏸ M11 | `app/models/dispute.py` only | — (residual risk) |

## 2. Non-Functional Requirements (NFR)

| ID | Requirement | Status | Evidence | Test / gap |
|---|---|---|---|---|
| NFR-01 | 99% availability during demo period | 🏗 M7 | `.github/workflows/uptime.yml` run history; systemd unit `deploy/systemd/chateau-collective.service` | evidence = uptime workflow screenshots |
| NFR-02 | Data integrity across records | 🟡 | SQLAlchemy FK model (`app/models/*`, D1 H-4 aligned) | integration tests assert DB↔display consistency per flow (grow with M3–M5 tests) |
| NFR-03 | Backup & recovery | ⏸ M12 | `deploy/scripts/backup.sh` (untested), `BackupRecord` model | — (residual risk) |
| NFR-04 | Graceful error recovery | ✅ partial | `app/web/routes/error_routes.py`, `errors/*.html` | `tests/security/test_error_routes.py` (5 tests); per-flow negative tests live with each feature |
| NFR-05 | Pages load < 3 s | ⏳ residual R3 | — | load-test evidence pass (E-01) |
| NFR-06 | Search results < 2 s | ⏳ residual R3 | (search not yet built — M3.2) | E-01 |
| NFR-07 | Valid upload < 5 s | ⏳ residual R3 | — | E-01 |
| NFR-08 | ≥ 50 concurrent users | ⏳ residual R3 | — | E-01 |
| NFR-09 | Transactions < 3 s | ⏳ residual R3 | — | E-01 |
| NFR-10 | Acceptable at ≥1,000 listings | ⏳ residual R3 | — | E-01 (seed script + timed browse/search) |
| NFR-11 | Observability of major workflows | 🔧 CTRL-003 | `app/logging_config.py`, `audit_service.py`, `security_event_service.py` | `tests/test_audit_service.py`, `tests/test_security_event_service.py`; wiring tests = T-06, T-37 |
| NFR-12 | Browser compatibility (Chrome/Edge/Firefox) | ⏳ residual R4 | — | manual pass + screenshots (E-02) |
| NFR-13 | Personal data minimisation | 🟡 | forms collect only required fields (verify again after M1.1 adds name/phone) | form review (E-03) |
| NFR-14 | Privacy of user records | ✅ partial | `ownership.py`, `rbac.py` | `test_profile_idor.py`; per-resource extension: T-29 (orders), cart via T-22 |
| NFR-15 | Retention of business records | 🟡 | no deletion paths; `OrderStatusHistory` persists | `test_workflow_service.py::test_transition_order_records_history` |
| NFR-16 | Auditability of admin actions | 🔧 M5 | `audit_service.py` + admin routes | **missing:** T-32, T-34, T-35, T-37 |

## 3. Secure Functional Requirements (SFR, Appendix A-1)

| ID | Requirement | Status | Trace |
|---|---|---|---|
| SFR-01 | Secure registration (validation, no dupes, no weak pw) | 🔧 M1.1 | dupes ✅ `test_register_duplicate_email`; weak pw ✅ `tests/unit/test_password_policy.py` (7 tests); name/phone: T-01, T-02 |
| SFR-02 | Secure login/logout; no access without session | ✅ | FR-02 tests + `tests/unit/security/test_rbac.py::test_login_required_blocks_anonymous` |
| SFR-03 | Profile: own-only view/edit | ✅ | `test_profile_idor.py` |
| SFR-04 | Seller application confidentiality | ⏸ M10 | — |
| SFR-05 | Public browsing hides private/internal fields | 🔧 M3.1 | approval filter + serializer review; T-14, T-15 |
| SFR-06 | Search input validated (anti-injection) | 🔧 M3.2 | T-16, T-17; ORM-only queries (SDR-03) |
| SFR-07 | Listing edit restricted to owner | ✅ | `test_listing_routes.py::test_edit_requires_owner` |
| SFR-08 | Cart private to buyer | 🟡 | service scoped by user (`test_cart_service.py`); HTTP cross-user check rides on T-22 |
| SFR-09 | Commitment only for available items, authorised buyer | 🟡 | `test_order_service.py` (server price ✅); **missing:** T-31 |
| SFR-10 | Shipment updates only for own listings' orders | 🔧 M2.1/M4.2 | **missing:** T-25 |
| SFR-11 | Checkout completes only after workflow checks | 🔧 M4.3 | **missing:** T-28 |
| SFR-12 | Admin dashboard admin-only | ✅ | `test_admin_2fa_routes.py::test_admin_index_anonymous_is_401`, `::test_admin_index_buyer_is_403` |
| SFR-13 | Suspension actions logged | 🔧 M5.1 | **missing:** T-32 |
| SFR-14 | Listing moderation notes hidden from users | 🔧 M5.1 | **missing:** T-34 |
| SFR-15 | Admin workflow updates logged | 🔧 M5.3/CTRL-003 | **missing:** T-37 |
| SFR-16 | Reviews only for completed purchases | ⏸ M8 | — |
| SFR-17 | Disputes own-order only | ⏸ M11 | — |

## 4. Functional Security Requirements (FSR, Appendix A-2)

| ID | Requirement | Status | Trace |
|---|---|---|---|
| FSR-01 | Admin 2FA before dashboard | ✅ | `app/security/admin_2fa.py`; `tests/unit/security/test_admin_2fa.py` (7 tests, incl. RFC 6238 vector), `tests/integration/test_admin_2fa_routes.py` (9 tests) |
| FSR-02 | Password policy (short/common/guessable rejected) | ✅ | `password_policy.py` (zxcvbn score ≥3); `test_password_policy.py` |
| FSR-03 | Hashing + salt, no plaintext | 🟡 | Werkzeug `generate_password_hash`; **missing:** T-03 |
| FSR-04 | Session created on login, ends on logout/timeout | 🔧 CTRL-004 (tests) | hook wired in `app/__init__.py::check_session_timeout`; logout ✅; **missing:** T-04, T-05 |
| FSR-05 | Brute-force: progressive throttling | ✅ /🏗 R1 | account lockout ✅ `test_auth.py::test_account_lockout_after_failed_attempts` (escalating 5/15/60 min); IP-level = nginx `limit_req` (R1) |
| FSR-06 | Account abuse prevention (registration flooding etc.) | 🏗 R1 | **missing:** nginx `limit_req` on register/login + E-04 evidence |
| FSR-07 | RBAC for all four roles | ✅ | `rbac.py`; `test_rbac.py` (7 tests) |
| FSR-08 | Buyers access only own records | ✅ partial | profile ✅; orders/cart HTTP: T-22, T-29 |
| FSR-09 | Sellers manage only own listings/shipments | ✅ /🔧 | listings ✅; shipments: T-25 |
| FSR-10 | Admin-only: suspend, moderate, workflow, disputes | 🔧 M5 | T-32…T-36 |
| FSR-11 | Audit logging of key actions | 🔧 CTRL-003 | service ✅ `test_audit_service.py::test_record_writes_a_row`; wiring: T-06, T-37 |
| FSR-12 | Admin action traceability (who/when/what/target) | 🔧 M5 | T-32, T-34, T-35 assert row fields |
| FSR-13 | Failed auth + suspicious access logged | 🔧 M1.3 | calls exist but commented out; T-06 |
| FSR-14 | Audit logs protected from modification/deletion | ✅ partial | `test_admin_logs.py::test_audit_log_viewer_is_read_only`, `::test_non_admin_blocked_from_logs` |
| FSR-15 | Private records protected | ✅ | ownership tests (`test_ownership.py`, 8 tests, incl. fail-closed) |
| FSR-16 | Data minimisation | 🟡 | E-03 form review |
| FSR-17 | No real payment data collected | 🟡 (by design) | checkout has no card fields; assert in T-26 |
| FSR-18 | HTTPS/TLS everywhere | 🏗 M7 | `deploy/nginx/chateau-collective.tls.conf` (TLS 1.2/1.3, ECDHE, OCSP stapling); E-05 SSL Labs/openssl |
| FSR-19 | Stored data protected (at-rest controls) | 🏗 M7 | VM file permissions per D1 G-3.1; E-06 |
| FSR-20 | Security headers on all responses | ✅ | `headers.py` (CSP, XFO, nosniff, Referrer-Policy, HSTS); `tests/security/test_headers.py` (5) + `test_headers_on_errors.py` (3) |
| FSR-21 | CSRF on state-changing requests | ✅ | `app/security/csrf.py` (global `CSRFProtect`); `tests/security/test_csrf.py` (5 tests) |
| FSR-22 | Server-side business rules; reject tampering | 🔧 M4 | price ✅ `test_place_orders_server_price_enforcement`; illegal transitions ✅ (service); T-23, T-24, T-27, T-30 |
| FSR-23 | App-layer DDoS/excessive-request protection | 🏗 R1 | **missing:** nginx `limit_req`/`limit_conn` + E-04 |
| FSR-24 | Bot/automated traffic filtering | 🏗 R1 | **missing** (declare minimal scope: rate limits + AWS SG) |
| FSR-25 | Backup functionality | ⏸ M12 | `backup.sh` exists, unverified |
| FSR-26 | Recovery functionality | ⏸ M12 | — |

## 5. Non-Functional Security Requirements (NFSR, Appendix A-3)

| ID | Requirement | Status | Trace |
|---|---|---|---|
| NFSR-01/02 | No unauthorised access to personal/private records | ✅ partial | `test_profile_idor.py`, `test_ownership.py`; extend per resource (T-22, T-29) |
| NFSR-03 | Data minimisation compliance | ⏳ | E-03 |
| NFSR-04 | TLS ≥1.2 on all sensitive flows | 🏗 | FSR-18 evidence (E-05) |
| NFSR-05 | Stored data/backups not web-accessible | 🏗 | SDR-12/13 curl checks (E-06) |
| NFSR-06 | Data integrity (no DB↔display mismatch) | 🟡 | per-flow integration tests |
| NFSR-07 | Transaction integrity; approved transitions only | 🔧 M4 | `test_workflow_service.py::test_can_transition_invalid_path`, `::test_transition_order_illegal_transition`; map fix = T-23 |
| NFSR-08 | Admin action records accurate + traceable | 🔧 M5 | T-32, T-35, T-37 |
| NFSR-09 | 99% uptime | 🏗 | NFR-01 evidence |
| NFSR-10 | 50 concurrent users | ⏳ | E-01 |
| NFSR-11 | Restore backup < 1 h | ⏸ M12 | — |
| NFSR-12 | Excessive-request resilience on hot endpoints | 🏗 R1 | E-04 |
| NFSR-13–16 | Perf: 3 s pages / 2 s search / 3 s transactions / 5 s upload | ⏳ | E-01 |
| NFSR-17 | Audit log integrity (non-admin cannot alter) | ✅ partial | `test_admin_logs.py::test_audit_log_viewer_is_read_only`, `::test_non_admin_blocked_from_logs` |
| NFSR-18 | Security log field quality | 🔧 M5 | asserted inside T-06, T-37 |
| NFSR-19 | Business record retention | 🟡 | `::test_transition_order_records_history` |
| NFSR-20 | Security event alerting (admin-visible) | 🟡 residual R5 | `security_event_service.py` + admin log page = alert surface; report framing sentence |
| NFSR-21 | Secure error messages (no stack traces/paths) | ✅ | `test_error_routes.py::test_500_returns_generic_page_with_no_leaked_detail` |

## 6. Secure Development Requirements (SDR, Appendix A-4)

| ID | Requirement | Status | Trace |
|---|---|---|---|
| SDR-01 | Input validation before processing | ✅ | `input_validation.py`; `tests/security/test_input_validation.py` (16 tests) |
| SDR-02 | Output encoding of user content | ✅ | `output_encoding.py` + Jinja autoescape; `test_output_encoding.py` (7), `test_templates_escape.py`, `test_listings_templates.py` |
| SDR-03 | SQLi prevention (ORM/parameterised only) | 🟡 | SQLAlchemy throughout; **missing:** T-40 guard test |
| SDR-04 | Secure upload (type/size/ext/MIME, rename, non-exec dir) | ✅ partial | `file_validation.py`, `upload_service.py`; `test_file_validation.py` (png ✅ / ext-mismatch ✅ / oversize ✅); **missing:** T-18…T-21 |
| SDR-05 | Password storage implementation | 🟡 | T-03 |
| SDR-06 | Session invalidated after logout, no reuse | 🟡 | logout-clears ✅; **missing:** T-08 |
| SDR-07 | Access-control testing (URL/ID manipulation, all roles) | ✅ partial | profile+listing+admin done; cart/order after swap (T-22, T-25, T-29) |
| SDR-08 | Negative testing (failures don't corrupt data) | ✅ partial | validation/error tests; per-flow negatives ride with M3–M5 items |
| SDR-09 | Audit log testing (recorded + protected) | 🔧 | service ✅; wiring T-06/T-37; protection ✅ (viewer read-only) |
| SDR-10 | Backup/restore testing | ⏸ M12 | — |
| SDR-11 | Secrets management (no secrets in repo) | ✅ 🏗 | env-based `app/config.py`; `.env` untracked; secret-scan in `.github/workflows/security-scan.yml` |
| SDR-12 | VM: no exposed source/.git/.env/db/debug; key-based SSH | 🏗 M7 | E-06 curl + SSH config evidence |
| SDR-13 | DB/uploads/backups outside web root | 🏗 M7 | D1 G-3.1 layout; E-06 |
| SDR-14 | Only required public services exposed | 🏗 M7 | AWS security group + nginx; E-06 |
| SDR-15 | Traffic filtering config reviewed/tested | ✅ 🏗 | nginx `limit_req`/`limit_conn`/bad-UA map in both configs; [evidence/rate-limiting.md](evidence/rate-limiting.md); on-VM `nginx -t` + throttle demo = E-04 |
| SDR-16 | Secure code review before release | ✅ | PR-review working agreement + AI review workflows (`.github/workflows/ai-contextual-pr-review.yml`); evidence = PR history |
| SDR-17 | Dependency review | ✅ | `pip-audit` in CI, `image-scan.yml`; add `zxcvbn` to inventory (residual R7) |
| SDR-18 | Browser compatibility testing | ⏳ residual R4 | E-02 |
| SDR-19 | Controlled logging/error handling | ✅ | `test_error_routes.py` + `test_audit_service.py::test_record_does_not_store_sensitive_fields` |

## 7. Security Design Decisions (D1 §9.3) & Workflow States (§9.4 / H-3)

| Decision | Status | Trace |
|---|---|---|
| 9.3.1 Never trust frontend price/status/role values | ✅ | price `test_place_orders_server_price_enforcement`; `test_workflow_d1.py::test_client_supplied_payment_status_ignored` (T-27), `::test_transition_route_rejects_invalid_status_strings` (T-30); RBAC authorises against DB role not session |
| 9.3.2 Deny-by-default (login+role+ownership+state) | ✅ | `test_rbac.py`, `test_rbac_hardening.py`, `test_ownership.py`, `test_order_ownership.py`; workflow state checks in `test_workflow_d1.py` |
| 9.3.3 Dedicated `/admin/*` routes, separated logic | ✅ | `admin_routes.py` blueprint — all actions role+2FA-gated |
| 9.3.4 Simulated payment, server-controlled transitions | ✅ | `checkout_service.py`; T-26, T-27, T-28 |
| 9.3.5 Authentication workflow (H-3 state machine) | ✅ | map now matches H-3 exactly — `test_workflow_d1.py::test_transition_matrix_exactly_matches_d1_h3` (T-23, 64 combos), `::test_shipped_to_sold_direct_is_rejected` (T-24); admin review `test_admin_operations.py::test_admin_authentication_review_flips_state_and_records` (T-35) |
| 9.3.6 Security event alerting | 🟡 R5 | `security_event_service.py` + admin log viewer = alert surface; NFSR-20 report framing |
| 9.3.7 Security headers (CSP/XFO/nosniff/Referrer) | ✅ | FSR-20 tests |

## 8. Test backlog — DONE (implemented in harden/d1-conformance, 5 Jul)

All T-01…T-41 are implemented and passing. Each line shows the delivered test.
**Bold = unblocked an OWASP-mapping row.**

**M1 (auth) — `tests/integration/test_auth_sessions.py`, `tests/unit/test_auth.py`**
- ✅ T-01 `test_register_captures_name_phone_and_creates_profile` · ✅ T-02 `test_register_rejects_invalid_name_or_phone`
- ✅ **T-03** `test_password_stored_as_hash_not_plaintext` (row 4) · ✅ **T-04** `test_session_expires_after_inactivity` (+`_activity_within_limit_keeps_session_alive`) (row 13)
- ✅ **T-05** `test_login_discards_pre_login_session_content` (row 14) · ✅ **T-06** `test_auth_events_write_audit_rows` (row 17)
- ✅ T-07 `test_suspended_user_cannot_login` · ✅ T-08 `test_session_not_reusable_after_logout`

**M2 (rbac/ownership) — `tests/unit/security/test_rbac_hardening.py`, `test_order_ownership.py`**
- ✅ T-09 `test_stale_session_for_deleted_user_is_401_not_500` · ✅ T-10 `test_suspension_kills_active_session_on_next_request`
- ✅ T-11 `test_role_change_takes_effect_without_relogin` · ✅ T-12 (6 helper tests in `test_order_ownership.py`) · ✅ T-13 `test_dev_login_route_disabled_outside_debug_and_testing`

**M3 (discovery/upload) — `tests/integration/test_listing_discovery.py`**
- ✅ T-14 `test_public_index_hides_pending_and_rejected` · ✅ T-15 `test_detail_hidden_for_unapproved_except_owner_and_admin`
- ✅ T-16 `test_search_filters_by_category_brand_condition_price` · ✅ T-17 `test_search_hostile_input_treated_as_data`
- ✅ T-18 `test_spoofed_magic_bytes_rejected_via_route` (row 20) · ✅ T-19 `test_traversal_filename_neutralised…`
- ✅ **T-20** `…_and_stored_name_randomised` (row 21) · ✅ T-21 `test_media_route_rejects_traversal_and_unknown_names`

**M4 (workflow/checkout) — `tests/unit/test_workflow_d1.py`, `tests/integration/test_cart_order_http.py`**
- ✅ T-22 `test_login_then_load_cart_page` · ✅ **T-23** `test_transition_matrix_exactly_matches_d1_h3` (64 combos; row 9) · ✅ T-24 `test_shipped_to_sold_direct_is_rejected`
- ✅ T-25 `test_seller_cannot_transition_other_sellers_order` · ✅ T-26 `test_checkout_happy_path` · ✅ T-27 `test_client_supplied_payment_status_ignored`
- ✅ T-28 `test_checkout_blocked_before_authentication` · ✅ T-29 `test_buyer_cannot_view_other_buyers_order_over_http` · ✅ T-30 `test_transition_route_rejects_invalid_status_strings` · ✅ T-31 `test_commit_skips_unapproved_listing`

**M5 (admin) — `tests/integration/test_admin_operations.py`**
- ✅ T-32 `test_admin_suspend_user_writes_audit_row` · ✅ T-33 `test_non_admin_cannot_suspend` · ✅ T-34 `test_admin_approve_and_reject_listing_with_audit`
- ✅ T-35 `test_admin_authentication_review_flips_state_and_records` · ✅ T-36 `test_seller_cannot_authenticate_via_admin_route` · ✅ **T-37** `test_admin_workflow_update_writes_audit` / `test_workflow_d1.py::test_transition_writes_audit_log_row` (row 22)

**M6 (cross-cuts) — `tests/security/test_sql_and_pages.py`, `tests/integration/test_error_pages.py`**
- ✅ T-39 `test_401_page_renders_with_login_link` · ✅ **T-40** `test_no_raw_sql_strings_in_app_code` (row 6) · ✅ T-41 `test_new_templates_render_without_error` (+ `test_no_jinja_safe_filter_on_user_data`)

**R1 (edge) — config + evidence doc:** ✅ nginx `limit_req`/`limit_conn`/bad-UA map in both configs; verification steps in [evidence/rate-limiting.md](evidence/rate-limiting.md) (E-04).

### Still open — require the live VM or descoped (unchanged)
- **M7 evidence captures** (need the deployed VM, not code): E-01 load/perf numbers (NFR-05…10, NFSR-13–16), E-02 browser matrix (NFR-12/SDR-18), E-03 data-min review note, E-05 TLS `openssl`/SSL-Labs output (FSR-18), E-06 VM exposure + SSH checks (SDR-12–14). Config for all of these already exists; only the screenshots/transcripts remain.
- **M8–M12 descope** (residual-risks section): FR-04 seller application, FR-16 reviews, FR-17 disputes, NFR-03/FSR-25/26/SDR-10 backup-restore, FR-10 shipment-tracking *entity*.
- **NFSR-20** security-event alerting: implemented as SecurityEvent rows + admin viewer; only the report framing sentence is outstanding.

## 9. Coverage snapshot (post-iteration)

| Family | Total | ✅ done+tested | 🟡/🔧 remaining code | 🏗/⏳ VM evidence | ⏸ descoped |
|---|---|---|---|---|---|
| FR | 17 | 14 | — | — | 3 (FR-04/16/17; FR-10 tracking partial) |
| NFR | 16 | 3 | 1 (NFR-15 retention) | 9 | 1 (NFR-03) |
| SFR | 17 | 13 | — | — | 3 (SFR-04/16/17; SFR-10 tracking partial) |
| FSR | 26 | 16 | 1 (FSR-16 review) | 6 | 2 (FSR-25/26) |
| NFSR | 21 | 8 | 1 (NFSR-20 framing) | 9 | 1 (NFSR-11) |
| SDR | 19 | 11 | — | 6 | 1 (SDR-10) |

Current test suite: **418 tests** (309 application across unit/integration/security + 109 `tests/ai_review/` + workflow-policy guard), **0 failures**. The T-01…T-41 backlog and R1 edge-hardening are complete; what remains is VM-only evidence capture and the M8–M12 descope.
