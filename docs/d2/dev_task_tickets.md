# Chateau Collective — Deliverable 2 Development Task Tickets

**Prepared:** Week 9 (Mon 29 Jun 2026) · **Team 31** · 7 members
**Scope decision:** Focused secure vertical slice — `auth → listings → cart/order → admin/audit`, every control hardened and tested. Other domains stay minimal/stubbed.
**Code freeze:** EOD **Tue 7 Jul** · **Report finalize:** Wed 8 Jul · **Submit:** Thu 9 Jul 09:00
**Repo:** https://github.com/leewayne451/ssd.git

> D2 is graded on *evidence that security controls actually run* — working code + tests + screenshots + CI/deploy history. Build thin but real and fully hardened. Breadth without working security earns nothing on a security deliverable.

---

## 1. Shared working agreements (everyone)

**Branching / PR — this is also our contribution evidence.**
- One branch per ticket: `m<n>/<short-topic>` (e.g. `m1/auth-login`). Never push straight to `main`.
- Open a PR for every chunk of work. **Another member reviews and merges** — not the author. This produces the PR-review + merge screenshots D2 requires.
- Keep PRs small and frequent. Many small commits from *every* member across the window = the GitHub Actions run history and contributor-graph evidence D2 needs. Do **not** let one person land everything at the end.

**Definition of Done (DoD) — a ticket is not done until all five hold:**
1. Code implemented and runs locally (`flask run` / `pytest` green).
2. Security control(s) for the ticket are wired into a real route, not just a helper.
3. Tests added — at least one **positive** and one **negative/abuse** test per control.
4. PR reviewed + merged by another member; CI green on the PR.
5. Evidence captured into `docs/d2/evidence/` (screenshot/snippet/test log) per the ticket's Evidence row.

**Cross-cutting rules baked into every route (no exceptions):**
- All DB access via SQLAlchemy ORM / parameterized queries — never string-built SQL.
- All forms render and validate a CSRF token.
- All user input validated server-side; all output auto-escaped by Jinja (no `|safe` on user data).
- Protected routes carry the RBAC decorator; owner-scoped resources carry an ownership check.
- Security-relevant events (login success/fail, access denied, admin actions, state changes) write an audit/security-event record.

---

## 2. Phase timeline (work backward from 9 Jul 09:00)

| Phase | Dates | Milestone |
|---|---|---|
| **0 — Spine** | Mon 29 Jun → Wed 1 Jul | Models + migrations finalized; app-factory wired; base layout; **auth + session + RBAC + CSRF + headers + audit logging backbone running**. Unblocks everyone. |
| **1 — Breadth (parallel)** | Thu 2 Jul → Sun 5 Jul | Each member's domain slice on the spine: routes + forms + service + templates + ownership + tests. M7 gets CI green + AWS deploy live. |
| **2 — Harden + deploy + evidence** | Mon 6 Jul → Tue 7 Jul | Security/negative tests, pip-audit/Bandit/Semgrep/ZAP green, HTTPS/TLS deploy, evidence pack. **Freeze EOD Tue 7 Jul.** |
| **3 — Report + freeze** | Sat 5 Jul (start) → Wed 8 Jul | 30-page report, traceability matrix, appendix. Submit Thu 9 Jul. |

**Critical-path rule:** Phase 0 (M1 + M2) must land by Wed 1 Jul or the whole team is blocked. M1/M2 get priority review turnaround.

---

## 3. Member tickets

> Members are labelled M1–M7 by workstream. Leader: map names onto these. The original 7-way split has been re-balanced so everyone sits on the focused slice's critical path (the previous Reviews/Disputes + Shipment streams are descoped to stubs).

### M1 — Authentication & Session core  *(Phase 0 spine owner)*
**Goal:** Secure register / login / logout with hashing, rate limiting, failed-login logging, and full session lifecycle.
**Files:** `app/web/routes/auth_routes.py`, `app/services/auth_service.py`, `app/services/user_service.py`, `app/security/session_policy.py`, `app/security/rate_limit.py`, `app/security/password_policy.py`, `app/web/forms/auth_forms.py`, `app/web/templates/auth/*`, `app/models/user.py`.
**Tasks:**
- Register: enforce password policy, hash with Werkzeug (`generate_password_hash`), reject duplicate email.
- Login: `check_password_hash`; on failure increment counter + log a security event; lock/throttle after N failures (rate_limit).
- Logout: clear session + invalidate.
- Session policy: regenerate session ID on login (fixation defence), inactivity timeout, secure/HttpOnly/SameSite cookie flags confirmed in prod config.
**Controls demonstrated:** FSR-02/03, SDR-05 (password hashing/storage), FSR-04/SDR-06 (sessions), brute-force protection, abuse logging.
**Depends on:** User model fields (own), audit/security-event service from M5 (coordinate interface day 1).
**Tests:** login success; wrong-password rejected + logged; lockout after N attempts; session cookie has Secure/HttpOnly/SameSite; logout clears session; protected route 302→login when anonymous.
**Evidence:** login/register/logout snippets; failed-login log line; cookie-flags devtools screenshot; login **sequence diagram**.

### M2 — Access control & RBAC  *(Phase 0 spine owner)*
**Goal:** Role + ownership enforcement applied across real routes; admin 2FA.
**Files:** `app/security/rbac.py`, `app/security/ownership.py`, `app/security/admin_2fa.py`, decorator wiring in all protected route files, `app/utils/decorators.py` (retire stub).
**Tasks:**
- Finalize `login_required` / `role_required(role)` decorators; apply to every protected endpoint as routes land.
- Ownership/IDOR helper: `assert_owner(resource, current_user)` → 403; apply to profile/cart/order/listing edit routes.
- Admin 2FA gate on `/admin` (TOTP or email-OTP — pick one, keep simple).
**Controls demonstrated:** RBAC, IDOR prevention, least privilege, admin 2FA.
**Depends on:** Auth/session from M1 (current_user). Coordinate decorator signatures with all domain owners.
**Tests:** buyer blocked from seller route (403); user A cannot open user B's order (403); admin route requires 2FA; **negative tests** per role.
**Evidence:** decorator-on-route snippets; buyer-vs-seller-vs-admin denied-access screenshots; IDOR negative-test output.

### M3 — Listings & Upload
**Goal:** Seller creates a listing with image upload; buyers browse/view. Hardened file handling.
**Files:** `app/web/routes/listing_routes.py`, `app/web/routes/seller_routes.py`, `app/services/listing_service.py`, `app/services/seller_service.py`, `app/services/upload_service.py`, `app/security/file_validation.py`, `app/web/forms/listing_forms.py`, `app/web/forms/seller_forms.py`, `app/web/templates/listings/*`, `app/web/templates/seller/*`, `app/models/product_listing.py`, `app/models/uploaded_file.py`.
**Tasks:**
- Public listing index + detail (buyer). Seller-only create/edit (RBAC + ownership).
- Upload: validate extension **and** MIME/signature (magic bytes), size cap, randomized stored filename, store outside web root / served safely.
**Controls demonstrated:** upload validation, input validation, output encoding, RBAC + ownership on seller resources.
**Depends on:** M1 (auth), M2 (decorators/ownership), M5 (audit on create).
**Tests:** create listing as seller (ok); as buyer (403); reject `.php`/oversize/spoofed-MIME upload; XSS payload in title is escaped on render.
**Evidence:** `file_validation.py` snippet; rejected-upload screenshots; listing create→view flow screenshots.

### M4 — Cart & Order workflow
**Goal:** Buyer adds to cart and places an order; order state machine with valid transitions only.
**Files:** `app/web/routes/cart_routes.py`, `app/web/routes/order_routes.py`, `app/services/cart_service.py`, `app/services/order_service.py`, `app/services/workflow_service.py`, `app/web/forms/cart_forms.py`, `app/web/forms/order_forms.py`, templates `cart/*` + `orders/*`, models `cart.py`, `cart_item.py`, `order.py`, `order_status_history.py`.
**Tasks:**
- Cart scoped to current user (ownership). Add/update/remove with server-side qty/price validation.
- Place order → create order + status history row. `workflow_service` enforces legal state transitions (reject illegal jumps) per D1 workflow rules.
**Controls demonstrated:** ownership/IDOR on cart & orders, server-side validation (no client-trusted prices), workflow state integrity, audit on state change.
**Depends on:** M3 (listings to buy), M1/M2 (auth/ownership), M5 (audit).
**Tests:** add-to-cart updates total server-side; user A can't see user B's cart/order (403); illegal status transition rejected; price tamper rejected.
**Evidence:** workflow_service transition snippet; IDOR negative test; order placement flow screenshots; state-history DB screenshot.

### M5 — Admin, Audit & Security Events
**Goal:** Audit/security-event persistence used by everyone, plus an admin log-viewer screen.
**Files:** `app/web/routes/admin_routes.py`, `app/services/admin_service.py`, `app/services/audit_service.py`, `app/services/security_event_service.py`, `app/models/audit_log.py`, `app/models/security_event.py`, `app/web/templates/admin/*`, `app/web/forms/admin_forms.py`.
**Tasks:**
- **Day 1:** publish the audit/security-event service interface (`audit_service.record(actor, action, target, meta)`) so M1/M3/M4 can call it. This is on the critical path.
- Admin-only dashboard: list audit log + security events (paginated, read-only). Admin 2FA gated (M2).
- Ensure no sensitive data (passwords, tokens) ever written to logs.
**Controls demonstrated:** audit logging, security monitoring, admin RBAC + 2FA, tamper-evident trail.
**Depends on:** M1/M2 (admin auth + 2FA). Interface consumers: M1, M3, M4.
**Tests:** action writes an audit row; non-admin blocked from `/admin` (403); log view requires 2FA; no secret leaks into log fields.
**Evidence:** audit_service snippet; admin log-viewer screenshot; DB rows showing recorded events; "no plaintext secrets in logs" snippet.

### M6 — Secure-coding cross-cuts & Profile
**Goal:** Own the secure-coding evidence surface end-to-end, plus Profile as a clean ownership/IDOR demo.
**Files:** `app/security/input_validation.py`, `app/security/output_encoding.py`, `app/security/csrf.py`, `app/security/headers.py`, `app/web/routes/error_routes.py`, `app/web/routes/profile_routes.py`, `app/services/profile`/`user_service` profile bits, `app/web/forms/profile_forms.py`, `app/web/templates/profile/*`, `app/models/profile.py`.
**Tasks:**
- Finalize CSRF integration (token in every form + verification), secure headers (CSP, X-Frame-Options, X-Content-Type-Options, HSTS in prod), and central input-validation/output-encoding helpers.
- Custom 400/403/404/500 handlers that don't leak stack traces.
- Profile view/edit scoped to owner (ownership check) — the canonical IDOR demo route.
- **Build the OWASP mapping table** (practice → file → snippet → test) for the report.
**Controls demonstrated:** CSRF, secure headers, input validation, output encoding, safe error handling, IDOR on profile.
**Depends on:** M1/M2 (auth/ownership). Coordinates with all (CSRF/headers are global).
**Tests:** POST without CSRF token rejected; response carries security headers; 500 shows friendly page (no trace); user A can't edit user B's profile (403).
**Evidence:** headers devtools screenshot; CSRF-rejected screenshot; OWASP mapping table; error-page screenshots.

### M7 — DevSecOps, CI/CD, Deploy & Test harness
**Goal:** Green pipelines with repeated run history, AWS deploy over HTTPS, and the test/evidence infrastructure.
**Files:** `.github/workflows/*` (ci, security-scan, zap-baseline, deploy-aws), `security/bandit.yaml`, `security/semgrep.yaml`, `security/zap/*`, `deploy/nginx/*`, `deploy/gunicorn/*`, `deploy/systemd/*`, `tests/conftest.py` + fixtures, `requirements*.txt`.
**Tasks:**
- Keep CI green as code lands; ensure pytest + pip-audit + Bandit + Semgrep run on every PR; ZAP baseline on main.
- Stand up the test harness/fixtures so every member can write tests easily.
- Deploy to AWS VM via `deploy-aws.yml` (verify GitHub secrets), Nginx + Gunicorn + systemd, **HTTPS/TLS** with valid cert; document key path/permissions (no secrets committed).
- Run `pip-audit`, save output, remediate/note findings.
**Controls demonstrated:** DevSecOps pipeline, SAST/DAST/dependency scanning, secure deployment, TLS, secret management.
**Depends on:** Nothing to start; deploy needs a runnable app (~Phase 1).
**Tests:** ensure CI fails on a deliberately broken test (gate works), then green.
**Evidence:** Actions run-history screenshots (multiple dates/authors); pip-audit/Bandit/Semgrep/ZAP outputs; `systemctl status` + browser HTTPS padlock + SSL Labs/`openssl s_client`; CI/CD sequence diagram; **Repository Access & Freeze appendix** (repo URL, branch, final commit SHA, collaborators screenshot).

---

## 4. Descoped for this slice (keep as minimal stubs)

Reviews, Disputes, Shipment, detailed Seller-application review, Backup. Leave routes returning a simple "coming soon" page or 404 so the app stays clean. Mention them in the report as *designed in D1, scoped out of the D2 evidence slice* — do not claim them as implemented.

These are available as **stretch tickets M8–M12** (§6) for any member who finishes their core ticket early. They are pulled *in* if completed to full DoD, and stay in the descope-as-stub category if not.

---

## 5. D2 evidence ownership (collect into `docs/d2/evidence/` as you go — not at the end)

| Evidence | Owner |
|---|---|
| Login/session/cookie + sequence diagram | M1 |
| RBAC/IDOR denied-access screenshots + negative tests | M2 |
| Upload validation + listing flow | M3 |
| Cart/order IDOR + workflow integrity | M4 |
| Audit log viewer + recorded-events DB rows | M5 |
| Secure headers, CSRF, OWASP mapping table, error pages | M6 |
| Actions history, scans, pip-audit, AWS HTTPS deploy, freeze appendix | M7 |
| Traceability matrix (control → file → snippet → test) | Leader + M6 |

**Leader checkpoints:** daily 15-min standup; hard gate Wed 1 Jul (spine merged?), Sun 5 Jul (all slices working end-to-end?), Tue 7 Jul EOD (freeze).

---

## 6. Stretch tickets M8–M12 (descoped features — pull in only if capacity frees up)

These re-add the descoped features **as a prioritized backlog**, not as committed work. They exist so a member who finishes their core ticket to full DoD can add value instead of idling. They must never compromise the core slice or the freeze.

**Stretch rules (read before claiming one):**
1. **Eligibility:** start a stretch ticket *only* after your own M1–M7 ticket meets the full 5-point DoD (code + control wired + tests + reviewed-merged + evidence). Helping the critical path (reviews, tests, evidence on a teammate's core slice) always outranks starting a stretch ticket.
2. **Claim, don't pre-assign:** announce at standup and claim the highest-priority open stretch ticket. Realistically M1/M2 free up first (post-spine) and are fastest here, since auth/RBAC/ownership are already in their hands.
3. **Same DoD, same branch/PR/review discipline** as core tickets. A stretch feature with no tests does **not** count and should not merge.
4. **The freeze is immovable.** If a stretch ticket is not at full DoD by **EOD Tue 7 Jul**, pull the cord: revert its branch to a clean "coming soon"/404 stub and do **not** merge half-built security code. A partial, untested feature lowers a security grade more than an honest stub.
5. **Stretch PRs are reviewed after critical-path PRs.** Never let stretch review bandwidth delay a core or spine merge.

**Priority order:** M8 → M9 → M10 → M11 → M12. Reorder M8 only if a *different* feature was a headline of your D1 report (an implementation that traces to your design narrative beats one that just adds breadth).

### M8 — Reviews  *(highest value — adds security evidence)*
**Goal:** Buyers who purchased a product can post a review; reviews render safely.
**Files:** `app/web/routes/review_routes.py`, `app/services/review_service.py`, `app/web/forms/review_forms.py`, `app/web/templates/reviews/*`, `app/models/review.py`.
**Tasks:** post/list reviews on a product; restrict posting to buyers with a completed order for that product (ownership); validate + length-cap input; rely on Jinja auto-escaping for output.
**Controls / evidence:** ownership/authorization, input validation, **XSS-defence demo** — submit a `<script>` payload and screenshot it rendered inert. This is the reason M8 is first: it produces *new* evidence, not duplicate.
**Prereq:** M4 (orders exist to gate on), M2 (ownership), M6 (output encoding).

### M9 — Shipment
**Goal:** Seller marks an order shipped; buyer sees shipment status.
**Files:** `app/web/routes/shipment_routes.py`, `app/services/shipment_service.py`, `app/models/shipment.py`, templates `shipments/*`.
**Tasks:** create shipment tied to an order; status transitions via `workflow_service`; ownership (only the order's seller updates, only its buyer views).
**Controls / evidence:** ownership/IDOR on shipment, workflow state integrity (mostly re-proves M4's controls).
**Prereq:** M4 (order workflow).

### M10 — Seller-application review
**Goal:** Admin approves/rejects seller applications.
**Files:** `app/services/seller_service.py` (review path), `app/web/routes/admin_routes.py` (admin section), `app/models/seller_application.py`, admin templates.
**Tasks:** list pending applications; approve/reject promotes user role; 2FA-gated; writes an audit record.
**Controls / evidence:** admin RBAC + 2FA, role transition, audit (re-proves M2/M5 controls on a new surface).
**Prereq:** M5 (admin/audit), M2 (2FA).

### M11 — Disputes
**Goal:** Buyer opens a dispute on an order; admin resolves it.
**Files:** `app/web/routes/dispute_routes.py`, `app/services/dispute_service.py`, `app/web/forms/dispute_forms.py`, `app/models/dispute.py`, templates `disputes/*`.
**Tasks:** open dispute (buyer, ownership); dispute state machine; admin resolution view; audit on state change.
**Controls / evidence:** ownership, dispute workflow integrity, audit. Heaviest of the five; lowest new-evidence-per-effort.
**Prereq:** M4 (orders), M5 (admin/audit).

### M12 — Backup
**Goal:** Record/trigger a DB backup with an integrity record.
**Files:** `app/services/backup_service.py`, `app/models/backup_record.py`, optional admin trigger route, optional `deploy/scripts/`.
**Tasks:** create backup record (path, timestamp, checksum); admin-only trigger; restore-verification note.
**Controls / evidence:** data-protection / recoverability, integrity hash. Hardest to *demo* live — lowest priority; consider documenting the design + a scripted backup over a full UI.
**Prereq:** M5 (admin), M7 (deploy/scripts if scripted).

