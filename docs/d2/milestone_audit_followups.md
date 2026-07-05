# Audit follow-ups by milestone (M1–M7)

**Source:** AI Milestone Audit run on `main`, 4 Jul 2026 (scope `full`, advisory).
**Deadline:** code freeze **EOD Tue 7 Jul**. Criticals should land by **Sun 6 Jul** so Monday is buffer + test day.
**How to read this:** each item = the problem the audit found → why it matters → what to do → the test that proves it. Finding IDs (e.g. `CTRL-001`) reference the audit report so you can read the full evidence yourself (Actions → AI Milestone Audit → latest `main` run → job summary or artifact).

**Definition of done for every item:** code merged via reviewed PR **+** a passing test **+** the matching row in `docs/d2/owasp_mapping_table.md` updated if one exists. A control that exists but isn't wired in or isn't tested counts as *not done* — that is exactly what the audit dinged us for, and it is exactly what D2 grades.

---

## DECIDED — single auth mechanism: Flask session + our own RBAC (tasks ①–③, do these first)

**Finding:** `CONFLICT-001` (high). **This is not open for debate** — the decision is made and required by module rules (rationale below, kept so everyone understands *why*). What remains is executing tasks ①–③.

**Problem:** We currently have *two* authentication systems half-in-place. `auth_service` logs users in by writing `user_id` and `role` into the Flask session, and our RBAC decorators (`app/security/rbac.py`) read from that session. But the cart and order routes use `flask_login.login_required` and `flask_login.current_user` — a different mechanism that we never initialise properly. Depending on wiring, either cart/order routes reject genuinely logged-in users, or they trust a different login state than every other protected route.

**Why it matters:** Access control is only as strong as its weakest, most confused boundary. Mixed mechanisms are how "logged in for route A but anonymous for route B" bugs happen — and on top of that, keeping Flask-Login is a **module-rule compliance problem**, not a style choice:

1. `doc/project_description.pdf` (proposal deliverable note): *"Some of third-party libraries (e.g., OAuth) are NOT allowed to be used in the project. Please discuss with lab instructors on your libraries."* Third-party authentication layers are the named banned example. Flask-Login is a third-party auth/session layer that is not in our declared stack and was never cleared with the lab instructor.
2. Our proposal's declared stack is **Werkzeug password hashing + Flask session management**. Deviating from it would have to be justified in D2's Design Review section — for zero benefit.
3. Lecture 5.5 (D2 details §2.3–2.4) grades us on explaining, with our own code snippets and filenames, *how user authentication is implemented*, *how session tokens/cookies are generated and protected from modification*, and *how session hijacking/replay are prevented*. That evidence must point at code **we wrote**. A library black box earns none of those marks.

**Decision (leader):** we standardise on **Flask session + our own RBAC decorators** and remove Flask-Login entirely. This is required by the module rules above — not negotiable, and definitely not three days before freeze. (Werkzeug hashing and Flask's signed session cookie are fine: both are in the declared, approved stack — the rule targets undeclared third-party auth layers, not the framework primitives.)

**Code check confirms this is a live outage, not just a design smell:** nothing in the app ever calls `flask_login.login_user()` — our real login only sets `session['user_id']` — so `flask_login.current_user` is always anonymous and **every cart/order route currently rejects even correctly logged-in users**. Those flows have simply never been exercised over HTTP.

**Allocation — three PRs, in this order:**

**① Bryan (M2) — decorator hardening. Merge first.** The swap has one behavioral gap we must close before it lands: Flask-Login's `current_user` is never `None` (a failed user load is treated as anonymous), but `get_current_user()` returns `None` when the session's `user_id` no longer matches a user. Our `login_required` only checks that the session key exists, so a stale session would sail past the decorator and 500 inside the view. Harden the decorators per **M2 item 2** below — that item also delivers the mid-session half of `CONFLICT-002` (suspension taking effect immediately, not at next login).

**② Chun (M4) — the swap itself, immediately after ① merges.** In `cart_routes.py` and `order_routes.py`: replace `from flask_login import login_required, current_user` with `from app.security.rbac import login_required`, and set `current_user = get_current_user()` at the top of each view that uses it (same `User` model object — every `cart_service`/`order_service` call works unchanged). Then delete `login_manager` from `app/extensions.py`, the `init_app` + `user_loader` block from `app/__init__.py`, and `flask-login` from requirements. Templates need no change — template `current_user` already comes from our own context processor, not Flask-Login.
**Prove it:** an integration test that logs in through the real login route and loads the cart page. That exact test was impossible before this fix — it is the direct evidence the outage is gone.

**③ JR (M6) — closing sweep, after ② merges.** Grep the repo for any remaining `flask_login` reference (code, requirements, docs/diagrams) and remove or replace it, so the D3 QA team finds zero trace of an undeclared auth library. Two checks while you're in there: (a) confirm `/dev/login_as_seller` sets `user_id` **and** `role` in the session exactly like the real login does, or demos will half-work; (b) make sure our 401 error template is a friendly page with a login link — Flask-Login used to redirect anonymous browsers to the login page, our 401 contract doesn't, so the template is what keeps the demo presentable.

**Deadlock rule:** ① before ② is protection against an edge case (stale session for a deleted user → 500), not a hard technical dependency. If ① is not merged by **Saturday 5 Jul noon**, Chun proceeds with ② anyway and Bryan's hardening lands right after. Chun's list is the longest — it must not idle behind an edge-case guard.

---

## M1 — Authentication & Session (BX)

### 1. Registration doesn't meet FR-01 — missing name and phone (`TRACE-001`, high)

**Problem:** FR-01 says a guest registers with **name, email, phone number, password**. Our `RegistrationForm` and `auth_service.register_user` only take email + password + confirm. The Profile model exists but nothing creates a profile at registration.

**Why it matters:** This is straight requirement traceability — the graders map FRs to code. It also blocks others: profile-ownership tests (M6) need a profile row to exist per user.

**What to do:** Add `name` and `phone` fields to `RegistrationForm` with length/format validators (phone: digits + reasonable length; name: max length, stripped). Extend `register_user(email, password, name, phone)` to create the `User` **and** their `Profile` in the same transaction so we never get a user without a profile.

**Prove it:** tests for successful registration (user + profile rows both created), and rejection of missing/overlong/garbage name and phone.

### 2. Session inactivity timeout is wired but unproven (`CTRL-004` — smaller than the audit says)

**Correction after code check:** the audit claimed no `before_request` hook enforces the timeout — that's a false positive caused by the audit's context truncation (it never saw `app/__init__.py`). The hook **is** registered in the app factory and calls `check_inactivity_timeout` / `set_activity_timestamp` correctly.

**What's actually left:** (a) review the skip-list — it currently exempts `static`, `auth.login`, `auth.register` by endpoint name; confirm nothing else public 404s/500s under an expired session; (b) the control has **zero tests**, so for grading purposes it doesn't exist yet.

**Prove it:** test that backdates `last_activity` beyond `SESSION_TIMEOUT_MINUTES` and asserts the next request is treated as logged-out (redirect + cleared session), a test that activity within the limit keeps the session alive, then flip OWASP mapping row 13 to passing.

### 3. Auth events are not audited — the calls are commented out (`CTRL-003`, high)

**Problem:** `auth_service` contains audit calls for registration, failed login, successful login and logout — **commented out**. So none of our most security-relevant events leave a trace.

**Why it matters:** D1 promises audit logging for all sensitive actions, and failed-login logging is an OWASP mapping row. An empty audit trail also guts Wayne's admin log viewer demo.

**What to do:** Uncomment and wire the `audit_service.record(...)` calls. Log the event type, user id (or attempted email for failures), timestamp, IP if available. **Never** log passwords, hashes, or session tokens.

**Prove it:** one test per event asserting an `AuditLog` row appears, plus an assertion that the row contains no password/secret material.

### 4. Suspended accounts can still log in (`CONFLICT-002`, medium)

**Problem:** Login checks account lockout but never checks `AccountStatus.SUSPENDED`. FR-13 lets admins suspend users — but suspension does nothing if login ignores it.

**What to do:** In the login path, after password verification, deny suspended accounts with the same generic error as bad credentials (don't leak account state), and record a security event. Coordinate with Wayne — he is building the admin suspension action (M5) that sets this status. Note the split with Bryan: you block suspended users **at login**; his decorator hardening (M2 item 2) kills their **already-active sessions** — together they close `CONFLICT-002` completely.

**Prove it:** test that a suspended user with the correct password cannot log in and a security-event row is written.

---

## M2 — RBAC, Ownership & 2FA (Bryan)

Good news first: the audit rated RBAC, ownership enforcement, and admin 2FA as **consistent with the design** (`TRACE-008`). The three items below are about extending that work to where it's still missing. Item 2 is your most urgent — it gates Chun's Flask-Login removal.

### 1. Provide order-ownership helpers for workflow transitions (`CTRL-002`, critical — joint with Chun)

**Problem:** `workflow_service` checks *role* only. Any user with the seller role can transition **any** order — Seller A can mark Seller B's order shipped. Role checks answer "are you a seller?"; nothing answers "are you *this order's* seller?".

**Why it matters:** This is the seller-fraud / workflow-manipulation threat from our own D1 threat model, and it's an IDOR: the order id comes from the URL and nothing binds it to the actor.

**What to do:** Add helpers to `app/security/ownership.py` — e.g. `require_order_seller(order, user)` (order's listing `seller_id` must equal the user) and `require_order_buyer(order, user)`. Chun calls these inside every transition (see M4.2); you own the helpers and their unit tests so the pattern matches the existing profile-ownership code.

**Prove it:** unit tests on the helpers; the end-to-end "Seller A cannot transition Seller B's order → 403 + security event" test lives with M4.

### 2. Harden `login_required` / `role_required` to resolve the user (Flask-Login-swap prerequisite + `CONFLICT-002`, high — do this first, it blocks Chun)

**Problem:** Our decorators check only that `session['user_id']` exists — they never confirm the user still exists or is still active. Two consequences: (a) once Flask-Login is removed, a live session whose user has been deleted slips past `login_required` and the view crashes with a 500 on `current_user.id` (Flask-Login absorbed this case by treating a failed user load as anonymous — we must do the same); (b) a suspended user keeps their existing session working until it expires, so suspension only takes effect at their *next login*.

**Why it matters:** (a) is a crash path an attacker can trigger and notice; (b) undermines FR-13 — an admin suspends an account and it stays active for up to the session lifetime.

**What to do:** In both decorators, resolve the user once per request (reuse `get_current_user()`). If the user is missing **or** `AccountStatus.SUSPENDED`: clear the session, record a security event, and return 401. And since you now hold the fresh DB user anyway, make `role_required` authorize against **`user.role` from the database, not `session['role']`** — the session copy is captured at login and goes stale the moment an admin changes a role, which is the same privilege-retention bug as suspension. `session['role']` becomes display-only (or gets dropped). Stash the loaded user on `flask.g` so views and `get_current_user()` don't hit the database twice in one request. This PR should merge **before** Chun's Flask-Login removal (task ① in the decision section — see the deadlock rule there).

**Prove it:** a request with a session for a deleted user returns 401 with the session cleared (no 500); suspending a logged-in user makes their very next request return 401; changing a logged-in user's role changes what `role_required` lets them reach on their next request without re-login.

### 3. Document and production-test the dev quick-login route (`DOC-002`, low)

**Problem:** `public_routes.py` exposes `/dev/login_as_seller`, guarded by debug/TESTING mode. Fine for development — but it's an authentication-affecting endpoint that appears nowhere in our attack-surface docs.

**What to do:** Add it to the attack-surface documentation as a development-only surface, and add a test that with a production config the route returns 403/404. If nobody actually uses it, delete it before freeze — the safest documented route is one that doesn't exist.

**Prove it:** the production-config test above.

---

## M3 — Listings & Upload (Tason)

### 1. Unapproved listings are publicly visible (`TRACE-003`, high)

**Problem:** The proposal says second-hand items stay **hidden until admin approval**. `ProductListing` has `approval_status`, but `listing_service.get_public_listings` filters only `is_active=True`. A pending or rejected listing that is active shows up in public browsing.

**Why it matters:** Listing approval is one of our core anti-counterfeit controls — this is a business-logic access-control failure, the exact class of bug this module is graded on.

**What to do:** Filter public queries (index, detail, search) on `approval_status == ApprovalStatus.APPROVED` **and** `is_active`. Ensure newly created listings default to `PENDING`. Wayne builds the admin approve/reject action (M5) — agree on the status values together.

**Prove it:** tests that pending and rejected listings appear in none of index/detail/search for anonymous and buyer users, while approved ones do.

### 2. Product detail, search and filtering are missing/broken (`TRACE-004`, medium)

**Problem:** FR-05/FR-06 require a product detail page (photos, seller info, specs) and search/filter by category, brand, condition, price. The audit found the detail route references unresolved variables and no search/filter route at all.

**What to do:** Finish the detail route + template (all user-supplied text rendered through Jinja auto-escaping — no `|safe`), and add server-side search/filter params. Validate each param against the enum/range it belongs to and query through the ORM only — filters built from request args are a classic injection point.

**Prove it:** tests for detail rendering of an approved listing, 404 for unapproved, and filter combinations returning only matching approved listings; one test with a hostile filter value (e.g. `' OR 1=1--`) asserting it's treated as data.

### 3. Upload validation exists but isn't wired end-to-end (`SURFACE-002`, medium)

**Problem:** `file_validation.py` (extension, size, magic bytes) and randomized stored filenames are good — but listing create/edit read raw `request.files` with no form-level validation, and there's no evidenced safe download/display path.

**Why it matters:** File upload is one of the proposal's named abuse cases. Validation that can be bypassed because the route doesn't consistently call it is worth zero in the report.

**What to do:** Put the upload behind a WTForm `FileField` whose validator calls the `file_validation` helpers, so every path through create/edit validates. Serve images only via a route that resolves the stored (randomized) name inside the upload directory — never user-supplied paths.

**Prove it:** tests for disallowed extension, spoofed magic bytes (a `.png` that's actually PHP/HTML), oversize file, and a path-traversal filename (`../../etc/passwd`) on both upload and retrieval.

---

## M4 — Cart & Order Workflow (Chun) — heaviest list, start today

### 0. First PR: remove Flask-Login (task ② in the decision section at the top)

Every item below needs HTTP-level tests against the cart/order routes — which is impossible today, because those routes reject *all* logged-in users (see the decision section). Do the swap the moment Bryan's decorator PR merges; the full file list and the proving test are spelled out up top. Everything else on your list builds on it.

**Heads-up before you run the proving test:** your routes render `cart/view.html`, `orders/list.html`, and `orders/detail.html` — none of these templates exist yet (the folders hold only `.gitkeep`), so the pages will 500 with TemplateNotFound even after the swap. Create minimal templates (extend `base.html`, plain tables, all user text auto-escaped) in the same PR.

### 1. The workflow state machine contradicts the D1 design (`CTRL-001`, critical — the #1 finding)

**Problem:** D1's flow — the whole point of the platform — is `committed → awaiting_shipment → shipped → under_authentication → authenticated/rejected → sold/refunded`. Our `ALLOWED_TRANSITIONS` allows `shipped → sold` **directly**, `under_authentication` is unreachable (nothing transitions into it), and `authenticated` is terminal instead of leading to `sold`.

**Why it matters:** An order can complete without ever passing the in-house authentication step. That bypasses the platform's core innovation and its main anti-counterfeit control. Graders reading D1 next to the code will see this immediately.

**What to do:** Rewrite the transition map to exactly the documented flow: add `shipped → under_authentication`, make `authenticated → sold` and `rejected → refunded/cancelled`, and **delete** `shipped → sold`. Then set actor roles per edge: seller edges (accept/ship), admin edges (authentication outcomes), buyer edges (cancel where allowed).

**Prove it:** a parametrized test over the **full** status × status matrix asserting the allowed set is exactly the documented one — every illegal jump (especially `shipped → sold`) rejected. This one test is our strongest workflow evidence for the report.

### 2. Transitions check role but not ownership (`CTRL-002`, critical — with Bryan)

**Problem/why:** see M2.1 — any seller can move any order.

**What to do:** Inside every transition, after the role check, call Bryan's `require_order_seller` / `require_order_buyer` helpers so the actor must be *this* order's seller (or buyer for buyer actions). Admin edges skip ownership but require admin + 2FA.

**Prove it:** integration test — Seller A attempts a transition on Seller B's order → 403 + security event; the legitimate seller succeeds.

### 3. Simulated checkout / payment transitions don't exist (`TRACE-007`, critical)

**Problem:** FR-11 requires simulated checkout with payment states `Pending → Paid → Failed → Refunded`. We have the `PaymentStatus` enum and a default of `PENDING` — and no service or route that ever moves it.

**What to do:** Build a checkout service that transitions payment status **server-side only**: the client sends "pay for order N" and nothing else — never a status value. Enforce prerequisites (buyer owns the order, order in a payable state), record the result in the audit log, allow `refunded` only from the admin/refund path.

**Prove it:** tests for the happy path, an attempt to POST `payment_status=paid` directly (must be ignored/rejected), paying someone else's order, and paying in a wrong state.

### 4. The transition endpoint is a single over-exposed door (`SURFACE-001`, high)

**Problem:** `/orders/<id>/transition` sits behind bare `@login_required` and takes any `new_status` string from the form. All enforcement is buried in the service, and the route accepts arbitrary status strings from any logged-in user.

**What to do:** Either split into per-actor endpoints (`/orders/<id>/ship` for sellers, `/orders/<id>/authenticate` for admins…) or keep one endpoint with: explicit role decorator, `new_status` validated against the enum, ownership check, CSRF, and an audit row for **every** accepted *and* rejected attempt (rejected attempts are the attack evidence).

**Prove it:** tests for invalid status strings, wrong role, wrong owner, missing CSRF token.

### 5. Negative tests for workflow abuse (`TEST-003`, critical)

**Problem:** The OWASP table's "workflow transition rejection" row is still pending, and none of the abuse cases in our own threat model have tests.

**What to do:** After items 1–4, add one end-to-end happy-path test (commit → ship → authenticate → sold) and negative tests per role: buyer can't ship, seller can't authenticate, nobody jumps states, checkout blocked before authentication.

---

## M5 — Admin, Audit & Security Events (Wayne)

### 1. Admin operations for FR-12–15 are mostly missing (`TRACE-006`, critical)

**Problem:** Admin currently has an index page and a read-only logs page. FR-12–15 require: user **suspension**, **listing approval/rejection**, and **order/workflow status updates**. None exist.

**Why it matters:** Two other milestones dead-end without you: BX's suspended-login check needs a way to suspend, and Tason's approval filter needs an approval action. Admin ops are also the highest-privilege attack surface — prime report material.

**What to do:** Three POST actions behind `role_required(admin)` **+** `admin_2fa_required` **+** CSRF, each writing an audit row: suspend/unsuspend user (sets `AccountStatus`), approve/reject listing (sets `ApprovalStatus`), and admin workflow update (drives the admin edges of Chun's state machine). Plain forms are fine — evidence beats polish.

**Prove it:** per action — admin succeeds + audit row exists; buyer/seller/anonymous get 403; admin without 2FA is blocked (`TEST-004`, high, covers this).

### 2. The authentication-review step has no implementation (`THREAT-002`, high)

**Problem:** The `AuthenticationReview` model exists, but no admin route/service records a physical-verification outcome, and (until Chun's fix) the workflow can't even reach `under_authentication`. Our headline anti-counterfeit control currently exists only in the data model.

**What to do:** Admin action on an order in `under_authentication`: record pass/fail + notes in `AuthenticationReview`, transition the order to `authenticated` or `rejected` via `workflow_service` (never by writing the status directly). Coordinate the edge names with Chun.

**Prove it:** test that an admin review flips the state and writes the review + audit rows, and that a seller/buyer calling the same endpoint gets 403.

### 3. Sensitive actions don't consistently reach the audit log (`CTRL-003`, high)

**Problem:** `audit_service` exists, but `workflow_service` writes only `OrderStatusHistory` (a business record, not an audit trail), auth events are commented out (BX fixes those), and listing/order/admin flows have no audit calls.

**What to do:** Own the policy: one short list in the code/docs of what MUST be audited — login success/fail, logout, registration, suspension, listing create/edit/approve/reject, order placement, every workflow transition, payment change, admin 2FA events. Then chase each owner to call `audit_service.record` at those points; you review, they wire.

**Prove it:** each owner's feature tests assert their audit row; add one test asserting no secrets appear in any logged row.

---

## M6 — Secure-coding Cross-cuts & Profile (JR)

Your helpers (input sanitization, output encoding, ownership) were rated consistent with the design (`TRACE-008`) — the audit's criticism is that they aren't yet wired into every business route. Your job this week is **integration sweeper**:

1. **Sweep every new route/template as M1–M5 land.** Checklist per PR you review: user-supplied text rendered escaped (no `|safe` on user data), inputs validated through forms/helpers, ownership checked before object access, audit call present if the action is on Wayne's sensitive list. You are the second reviewer on the M3 detail page and M4 order pages — those render the most user-controlled text (XSS surface).
2. **Profile creation at registration** — pair with BX on M1.1 so `register_user` creates the Profile and your existing profile-ownership tests run against real registration output.
3. **Flask-Login sweep** (task ③ in the decision section) — after Chun's removal PR merges, grep the whole repo for any remaining `flask_login` reference (imports, requirements, docs, diagrams) and remove or replace it. The goal: the D3 QA team should find zero trace of an undeclared auth library.

---

## M7 — DevSecOps, CI/CD & Test Harness (Yi Phang — me)

1. **Close the OWASP mapping table** (`TEST-001`, high). Many rows still say pending (password hashing, session flags, timeout, fixation, lockout, admin 2FA, upload validation, audit rows…). Most map 1:1 to items above — I will chase each owner and update the row the day the test merges, and build the requirement→test traceability matrix for the report.
2. **Create `docs/qa/`** (`DOC-001`, medium). The audit found no QA docs at all. I'll write: test strategy, how to run the suite, CI evidence links, SAST/DAST (Bandit/Semgrep/ZAP) results summary, known limitations + residual risks (including the M8–M12 descope below).
3. **Fix audit tooling input truncation.** This run's report carries a "context truncated" flag: input budgets (`AI_MAX_CONTEXT_CHARS` 90k etc.) cut 101 files including tests and the app factory — several "insufficient evidence" findings are artifacts of that, not real gaps (the timeout hook "gap" above was one). I'll raise the budgets in the workflow env and add a priority rule for `app/__init__.py`, then **re-run the audit after the fixes above land** so the report cites a clean run.
4. **Ship the canonical test-login fixture before the weekend test wave.** Five people are about to write HTTP tests that need "a logged-in client." I'll add `login_as(client, user)` (and `login_as_role(...)`) to `tests/conftest.py`, driving the **real** login route — not a session hack — so every member's tests exercise the actual auth path consistently. Use it; don't invent your own.
5. **Flask-Login removal ripples into the report.** The D2 dependency inventory + dependency-check evidence must reflect `flask-login`'s removal, and no report diagram (login sequence, class/package diagrams) may show `LoginManager`. Upside to claim: the episode — *audit flagged mixed auth → investigation showed cart/order routes rejected all logged-in users (dead code path) → undeclared library removed* — goes straight into D2's "findings worth learning and sharing" section. That section is explicitly graded; this is our best entry for it.

---

## Residual D1 gaps NOT covered by the audit follow-ups (verified against code, 4 Jul)

The AI audit checked security traceability; it did not check every D1 NFR or the deploy layer (it couldn't see those files). A manual pass against the full D1 document found these extra items. None are big — each is either ~1 hour of work or a deliberate sentence in the report's residual-risks section. Silence is the only wrong option: the D3 QA team receives our D1 and will check it line by line.

1. **Rate limiting / bot filtering — CONFIRMED missing at both layers** (FSR-05 IP throttling, FSR-06, FSR-23, FSR-24, NFSR-12). App side has *account* lockout only (`rate_limit.py`'s own comment says "to be implemented"); neither nginx config contains `limit_req`. **Owner: Yi Phang (M7)** — add `limit_req` zones for login/register/search to the nginx config; document in the report as the edge-protection layer from D1 §8.2.
2. **FR-14 "reported" listings — decision needed.** Wayne's admin item covers approve/reject, but D1 says admins review "suspicious or **reported**" listings and no user-facing report mechanism exists. **Owner: Wayne (M5)** — either a minimal "report listing" button + flag column, or we word the report as "admin-initiated monitoring; user reporting deferred." Decide by Sun.
3. **Performance NFRs have zero planned evidence** (NFR-05–10, NFSR-13–16: 3s pages, 2s search, 50 concurrent users, 1,000 listings). **Owner: Yi Phang (M7)** — one cheap load-test pass against the deployed VM after freeze-week fixes land; screenshot the numbers into the report, or declare as lightly-tested limitations.
4. **Browser compatibility** (NFR-12 / SDR-18: latest + last two majors of Chrome, Edge, Firefox). **Owner: first person whose core items hit DoD** — ~30 min manual pass + screenshots.
5. **Security event alerting framing** (NFSR-20 / D1 §9.3.6 "administrator-visible alerts"). We have SecurityEvent rows + the admin log viewer — defensible as the minimal alerting surface, but the report must *explicitly* frame the admin security-events page as the alert channel. **Owner: report writer for M5 section.**
6. **FR-10 framing — in our favour.** Shipment tracking is only *half* descoped: the M9 stretch is the `Shipment` entity/routes, but FR-10's core (seller updates awaiting-shipment/shipped for own orders) IS delivered by Chun's workflow transitions + Bryan's ownership checks. The report claims FR-10 as substantially met, with tracking-reference detail deferred. Don't lump FR-10 wholesale into the descope list.
7. **`zxcvbn` in the dependency inventory.** The password policy uses the third-party `zxcvbn` strength estimator — good control, but it must appear in the D2 dependency inventory / dependency-check evidence like every other package (same module rule on declared libraries).

**Verified genuinely covered (no action):** security headers incl. CSP + HSTS (`headers.py`), password policy strength (FSR-02), TLS config quality — TLS 1.2/1.3, modern ECDHE ciphers, OCSP stapling (`deploy/nginx/chateau-collective.tls.conf`, prime §2.3 report material), uptime monitoring workflow for NFR-01 evidence (`.github/workflows/uptime.yml`).

## Explicitly NOT in scope before freeze (don't pick these up)

The audit rates these critical/high **against the full D1 design**, but we descoped them to stretch tickets M8–M12 on 29 Jun. They go in the report's residual-risks section, not your worklist: shipment tracking (`TRACE-005` → M9), reviews (`THREAT-001` → M8), disputes (`TRACE-005` → M11), seller application review (`TRACE-002` → M10), backup/restore (`CTRL-005` → M12). Stretch tickets may be claimed **only after** your core items above hit full DoD.

## Process reminders

- Branch per ticket, PR reviewed by another member — this is graded contribution evidence, no direct pushes to `main`.
- Small, frequent commits (Actions run history is evidence too).
- Every fix ships **with its test in the same PR**. If the audit taught us one thing: an unwired or untested control is indistinguishable from a missing one.
