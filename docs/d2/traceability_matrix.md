# D1 → Implementation → Test Traceability Matrix

**Source:** `doc/ICT2116_P2_team31_Deliverable_One.pdf` (all requirement families, incl. Appendices A-1…A-4 and §9.3 design decisions).
**Generated:** 4 Jul 2026, verified against code + test inventory on `main` (+ working tree). Companion docs: [milestone_audit_followups.md](milestone_audit_followups.md) (fix tasks), [owasp_mapping_table.md](owasp_mapping_table.md) (OWASP view of the same evidence).
**How to verify:** `pytest -q` runs every test cited here; test refs are `file::test_name`.

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
| FR-01 | Registration: name, email, phone, password | 🔧 M1.1 | `app/web/forms/auth_forms.py`, `app/services/auth_service.py::register_user` (email+password only today) | `tests/unit/test_auth.py::test_register_success`, `::test_register_duplicate_email`; **missing:** T-01, T-02 |
| FR-02 | Login / logout | ✅ | `auth_service.py::login_user/logout_user`, `app/web/routes/auth_routes.py` | `test_auth.py::test_login_success`, `::test_login_wrong_password`, `::test_logout_clears_session` |
| FR-03 | Profile management (own profile) | ✅ | `app/web/routes/profile_routes.py`, `app/services/profile_service.py`, `app/security/ownership.py` | `tests/integration/test_profile_idor.py::TestProfileIDOR` (own-edit + cross-user blocked) |
| FR-04 | Seller application | ⏸ M10 | `app/models/seller_application.py` (model only; routes/service stubs) | — (residual risk) |
| FR-05 | Public browsing + product detail page | 🔧 M3.1/M3.2 | `app/web/routes/listing_routes.py`, `app/services/listing_service.py` (index works; detail broken; approval filter missing) | **missing:** T-14, T-15 |
| FR-06 | Search & filter (category/brand/condition/price) | 🔧 M3.2 | not implemented yet | **missing:** T-16, T-17 |
| FR-07 | Listing create/edit + image upload (own only) | ✅ /🔧 M3.3 | `listing_routes.py`, `app/services/upload_service.py`, `app/security/file_validation.py` | `tests/unit/test_listing_routes.py::test_create_requires_login/-seller`, `::test_create_listing_success`, `::test_create_listing_with_image`, `::test_edit_requires_owner`, `::test_edit_owner_success` |
| FR-08 | Cart add/view/remove | 🔧 swap task ② | `app/services/cart_service.py` (complete), `cart_routes.py` (blocked by Flask-Login; templates missing) | `tests/unit/test_cart_service.py` (19 tests, service level); **missing:** T-22 (HTTP level) |
| FR-09 | Purchase commitment | ✅ (service) | `app/services/order_service.py::place_orders_from_cart` | `tests/unit/test_order_service.py` (7 tests incl. `::test_place_orders_server_price_enforcement`); **missing:** T-31 |
| FR-10 | Shipment status tracking by seller | 🔧 M4.1/M4.2 (workflow half); ⏸ M9 (Shipment entity) | `app/services/workflow_service.py` (awaiting_shipment/shipped edges) | `tests/unit/test_workflow_service.py::test_is_actor_allowed_seller_restricted`; **missing:** T-25 |
| FR-11 | Simulated checkout after workflow checks | 🔧 M4.3 | `PaymentStatus` enum only — checkout service not built | **missing:** T-26, T-27, T-28 |
| FR-12 | Admin dashboard | 🔧 M5.1 | `app/web/routes/admin_routes.py` (index + logs only) | `tests/test_admin_logs.py`, `tests/integration/test_admin_2fa_routes.py` (access control ✅ for existing pages) |
| FR-13 | User suspension by admin | 🔧 M5.1 + M1.4 + M2.2 | `AccountStatus.SUSPENDED` modelled; no action/enforcement yet | **missing:** T-07, T-10, T-32, T-33 |
| FR-14 | Listing monitoring (suspicious/reported) | 🔧 M5.1 + residual R2 | `ProductListing.approval_status` modelled; no admin action; no report mechanism | **missing:** T-34 |
| FR-15 | Admin order/workflow status update | 🔧 M4.1 + M5.1/M5.2 | `workflow_service.py` admin edges; admin UI missing | `test_workflow_service.py::test_is_actor_allowed_admin_always_allowed`, `::test_transition_order_authentication_path`; **missing:** T-35 |
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
| SDR-15 | Traffic filtering config reviewed/tested | 🏗 R1 | E-04 |
| SDR-16 | Secure code review before release | ✅ | PR-review working agreement + AI review workflows (`.github/workflows/ai-contextual-pr-review.yml`); evidence = PR history |
| SDR-17 | Dependency review | ✅ | `pip-audit` in CI, `image-scan.yml`; add `zxcvbn` to inventory (residual R7) |
| SDR-18 | Browser compatibility testing | ⏳ residual R4 | E-02 |
| SDR-19 | Controlled logging/error handling | ✅ | `test_error_routes.py` + `test_audit_service.py::test_record_does_not_store_sensitive_fields` |

## 7. Security Design Decisions (D1 §9.3) & Workflow States (§9.4 / H-3)

| Decision | Status | Trace |
|---|---|---|
| 9.3.1 Never trust frontend price/status/role values | 🔧 M4 | price ✅ `test_place_orders_server_price_enforcement`; payment/status tampering: T-27, T-30 |
| 9.3.2 Deny-by-default (login+role+ownership+state) | ✅ /🔧 | `test_rbac.py`, `test_ownership.py`; state checks complete with M4 |
| 9.3.3 Dedicated `/admin/*` routes, separated logic | ✅ pattern | `admin_routes.py` blueprint; new admin actions (M5.1) must stay in it |
| 9.3.4 Simulated payment, server-controlled transitions | 🔧 M4.3 | T-26, T-27, T-28 |
| 9.3.5 Authentication workflow (H-3 state machine) | 🔧 M4.1 + M5.2 | `test_workflow_service.py` (14 tests exist; **map itself contradicts H-3** — fix per CTRL-001 then T-23/T-24 lock it) |
| 9.3.6 Security event alerting | 🟡 R5 | NFSR-20 framing |
| 9.3.7 Security headers (CSP/XFO/nosniff/Referrer) | ✅ | FSR-20 tests |

## 8. Missing-test backlog (consolidated)

Every gap above, as one implementable list. IDs are referenced from the tables. **Bold = blocks an OWASP-mapping row.**

**M1 — BX**
- T-01 `test_register_captures_name_phone_and_creates_profile` (FR-01)
- T-02 `test_register_rejects_invalid_phone_and_overlong_name` (SFR-01)
- **T-03** `test_password_stored_as_hash_not_plaintext` (FSR-03; OWASP row 4)
- **T-04** `test_session_expires_after_inactivity` (+ activity refresh keeps alive) (FSR-04; OWASP row 13)
- **T-05** `test_session_marker_changes_after_login` (fixation; OWASP row 14)
- **T-06** `test_auth_events_write_audit_rows` (register/login-fail/login/logout; FSR-13; OWASP row 17)
- T-07 `test_suspended_user_cannot_login_and_event_recorded` (FR-13)
- T-08 `test_session_not_reusable_after_logout` (SDR-06)

**M2 — Bryan**
- T-09 `test_stale_session_for_deleted_user_is_401_not_500`
- T-10 `test_suspension_kills_active_session_on_next_request` (CONFLICT-002)
- T-11 `test_role_change_takes_effect_without_relogin`
- T-12 unit tests for `require_order_seller` / `require_order_buyer` helpers
- T-13 `test_dev_login_route_returns_403_in_production_config` (DOC-002)

**M3 — Tason**
- T-14 `test_public_index_hides_pending_and_rejected_listings` (TRACE-003)
- T-15 `test_detail_404_for_unapproved_listing` (FR-05/SFR-05)
- T-16 `test_search_filters_by_category_brand_condition_price` (FR-06)
- T-17 `test_search_hostile_input_treated_as_data` (SFR-06/SDR-03)
- T-18 `test_upload_rejects_spoofed_magic_bytes_via_route` (SDR-04; OWASP row 20)
- T-19 `test_upload_rejects_path_traversal_filename`
- **T-20** `test_stored_filename_is_randomised_not_original` (OWASP row 21)
- T-21 `test_image_serving_rejects_traversal_paths`

**M4 — Chun**
- T-22 `test_login_then_load_cart_page` (swap proving test — FR-08, FSR-08)
- **T-23** `test_transition_matrix_exactly_matches_d1_h3` (CTRL-001; OWASP row 9 upgrade)
- T-24 `test_shipped_to_sold_direct_is_rejected`
- T-25 `test_seller_cannot_transition_other_sellers_order` (CTRL-002/SFR-10)
- T-26 `test_checkout_happy_path_pending_to_paid_no_card_fields` (FR-11, FSR-17)
- T-27 `test_client_supplied_payment_status_ignored` (9.3.4)
- T-28 `test_checkout_blocked_before_authenticated_state` (SFR-11)
- T-29 `test_buyer_cannot_view_other_buyers_order_over_http` (FSR-08)
- T-30 `test_transition_rejects_invalid_status_strings` (SURFACE-001)
- T-31 `test_commit_to_unavailable_item_rejected` (SFR-09)

**M5 — Wayne**
- T-32 `test_admin_suspend_user_writes_audit_row` + non-admin 403 (T-33) (FR-13/SFR-13)
- T-34 `test_admin_approve_reject_listing_with_audit_row` (FR-14/SFR-14)
- T-35 `test_admin_authentication_review_flips_state_and_records` (THREAT-002/9.3.5)
- T-36 `test_seller_cannot_update_authentication_status` (SFR-15)
- **T-37** `test_workflow_transition_writes_audit_log_row` (CTRL-003; OWASP row 22)

**M6 — JR**
- T-39 `test_401_page_renders_with_login_link` (after template created)
- **T-40** `test_no_raw_sql_strings_in_app_code` (SDR-03; OWASP row 6)
- T-41 escaping tests for new cart/order/listing-detail templates as they land

**M7 — Yi Phang (evidence tasks, not pytest)**
- E-01 load-test pass: page/search/transaction timings, 50 concurrent, 1k listings (NFR-05…10, NFSR-10/13–16)
- E-02 browser matrix pass + screenshots (NFR-12/SDR-18)
- E-03 form data-minimisation review note (NFR-13/FSR-16/NFSR-03)
- E-04 nginx `limit_req` config + throttling demonstration (FSR-05/06/23/24, NFSR-12, SDR-15)
- E-05 TLS evidence: SSL Labs / `openssl s_client` output (FSR-18/NFSR-04)
- E-06 VM exposure checks: `.git`/`.env`/db/uploads/backups not web-reachable; SSH key-only (SDR-12–14, NFSR-05, FSR-19)
- (enabler) `login_as` fixture in `tests/conftest.py` so T-22/T-25/T-29… share one canonical login path

## 9. Coverage snapshot

| Family | Total | ✅ done+tested | 🟡 test gap | 🔧 in progress | 🏗/⏳ evidence | ⏸ descoped |
|---|---|---|---|---|---|---|
| FR | 17 | 4 | — | 10 | — | 3 |
| NFR | 16 | 1 | 4 | 2 | 8 | 1 |
| SFR | 17 | 5 | 2 | 7 | — | 3 |
| FSR | 26 | 7 | 4 | 7 | 6 | 2 |
| NFSR | 21 | 3 | 4 | 4 | 9 | 1 |
| SDR | 19 | 6 | 3 | 1 | 8 | 1 |

Current test suite: **~150 tests** across `tests/` (app: unit + integration + security; plus `tests/ai_review/` covering the AI tooling and `test_workflow_policies.py` guarding CI workflow policy). Missing-test backlog: **41 tests + 6 evidence tasks**, all assigned above.
