# Chateau Collective — D2 GitHub Issue Plan

Blueprint for the GitHub issues. Owners kept abstract (**Owner 1–7**) — map names later.
Granularity: **epics + sub-issues**. Source of truth: `docs/d2/dev_task_tickets.md` + `docs/d2/sequencing_and_load.md`.

> GitHub has no native "epic" object. We model an epic as a **parent issue** (label `epic`) whose body holds a task-list linking its sub-issues. Each sub-issue is a normal issue with its own branch/PR — that's what produces per-task contribution evidence for D2.

---

## 1. Label scheme

| Label | Values | Purpose |
|---|---|---|
| Owner | `owner-1` … `owner-7` | who owns it (D2 contribution attribution) |
| Phase | `phase-0` `phase-1` `phase-2` | spine / breadth / harden-deploy |
| Priority | `p1-core` `p2-stretch` | committed vs stretch backlog (M8–M12) |
| Type | `type-feature` `type-security` `type-test` `type-devops` `type-docs` | work category |
| Epic | `epic` | parent/tracking issues |

## 2. Milestones (tied to your gates)

| Milestone | Due | Meaning |
|---|---|---|
| `Spine merged` | Wed 1 Jul | Owner 1 + 2 + Day-1 contracts landed |
| `Slices end-to-end` | Sun 5 Jul | all core slices working together |
| `Freeze` | Tue 7 Jul | harden + deploy + evidence complete; code frozen |
| `Report submitted` | Thu 9 Jul | report + appendix submitted 09:00 |

## 3. Issue body template (every issue stamped from this)

```markdown
**Owner:** Owner N   **Phase:** phase-X   **Priority:** p1-core
**Depends on:** #<id> (and/or "Day-1 contracts")
**Blocks:** #<id>

### Goal
<one line>

### Tasks
- [ ] ...
- [ ] ...

### Security controls demonstrated
<D1 control(s) / OWASP item(s)>

### Acceptance criteria
- [ ] <observable, testable outcome>

### Tests required
- [ ] positive: ...
- [ ] negative/abuse: ...

### Evidence to capture (→ docs/d2/evidence/)
- <screenshot / snippet / log>

### Definition of Done
Code runs · control wired into a real route · tests green · PR reviewed+merged by another owner · CI green · evidence captured
```

---

## 4. Epic → sub-issue inventory

**Counts:** 1 contract epic + 7 owner epics + ~31 core sub-issues + 5 stretch epics ≈ **44 issues**.
*(If you want fewer, collapse Owner 5/6/7 sub-issues into their epic checklists — see note at end.)*

### E0 — Phase-0 Contracts *(epic · phase-0 · p1-core)* — **do first**
The shared signatures everyone codes against. Freeze these Day 1; treat as a contract.
- **0.1** Publish `audit_service.record(actor, action, target, meta)` signature *(owner-5, type-security)*
- **0.2** Publish RBAC decorators `login_required` / `role_required(role)` + `assert_owner(resource, user)` signatures *(owner-2, type-security)*
- **0.3** Publish `current_user` accessor + session contract *(owner-1, type-security)*
- **0.4** Test harness/fixtures (`conftest.py`, app/client/db_session) ready for all *(owner-7, type-test)*

### E1 — Owner 1: Auth & Session *(epic · phase-0 · critical-path)*
- **1.1** Register: password policy + Werkzeug hashing + duplicate-email reject *(type-feature)*
- **1.2** Login: `check_password_hash` + failed-attempt logging + rate-limit/lockout *(type-security)*
- **1.3** Logout + session invalidation *(type-security)*
- **1.4** Session policy: ID regeneration on login, inactivity timeout, Secure/HttpOnly/SameSite cookies *(type-security)*
- **1.5** Auth forms + templates + login **sequence diagram** + tests *(type-test)*

### E2 — Owner 2: RBAC & Access Control *(epic · phase-0 · critical-path)*
- **2.1** Finalize `login_required` / `role_required` decorators *(type-security)*
- **2.2** Ownership/IDOR helper `assert_owner` → 403 *(type-security)*
- **2.3** Admin 2FA gate on `/admin` *(type-security)*
- **2.4** Apply decorators across all protected routes + role/IDOR negative tests *(type-test)*

### E3 — Owner 3: Listings & Upload *(epic · phase-1)*
- **3.1** Public listing index + detail (buyer **read path — deliver by Fri 3**) *(type-feature)*
- **3.2** Seller create/edit listing (RBAC + ownership) *(type-feature)*
- **3.3** Upload hardening: extension + **MIME/signature** + size cap + safe storage *(type-security)*
- **3.4** Templates/forms + tests (reject `.php`/oversize/spoofed-MIME; XSS in title escaped) *(type-test)*

### E4 — Owner 4: Cart & Order Workflow *(epic · phase-1)*
- **4.1** Cart add/update/remove, user-scoped, server-side qty/price validation *(type-feature)*
- **4.2** Order placement + `order_status_history` *(type-feature)*
- **4.3** `workflow_service`: legal state transitions only (reject illegal jumps) *(type-security)*
- **4.4** Ownership/IDOR on cart & orders + price-tamper negative tests *(type-test)*

### E5 — Owner 5: Admin, Audit & Security Events *(epic · phase-0 interface + phase-1 UI)*
- **5.1** Audit + security-event persistence (consumes 0.1) *(type-security)*
- **5.2** Admin dashboard log viewer, paginated, read-only, 2FA-gated *(type-feature)*
- **5.3** "No secrets in logs" guarantee + tests (non-admin 403, action writes a row) *(type-test)*

### E6 — Owner 6: Secure-coding Cross-cuts & Profile *(epic · phase-0 globals + phase-1 profile)*
- **6.1** CSRF integration: token in every form + verification *(type-security · phase-0)*
- **6.2** Secure headers: CSP, X-Frame-Options, X-Content-Type-Options, HSTS *(type-security · phase-0)*
- **6.3** Input validation + output encoding helpers; safe 400/403/404/500 handlers *(type-security)*
- **6.4** Profile view/edit (owner-scoped IDOR demo) *(type-feature)*
- **6.5** OWASP mapping table (practice → file → snippet → test) *(type-docs)*

### E7 — Owner 7: DevSecOps, CI/CD, Deploy *(epic · phase-0 harness + phase-2 deploy)*
- **7.1** Keep CI green: pytest + pip-audit on every PR *(type-devops)*
- **7.2** Security scans: Bandit + Semgrep + ZAP baseline *(type-devops)*
- **7.3** AWS deploy: Nginx + Gunicorn + systemd + **HTTPS/TLS** *(type-devops · phase-2)*
- **7.4** Evidence: Actions run history, pip-audit output, **Repository Access & Freeze appendix** *(type-docs · phase-2)*

### Stretch epics (p2-stretch · pull in only per §6 rules of the tickets doc)
- **E8 — Reviews** *(top priority — XSS-defence evidence)*
- **E9 — Shipment**
- **E10 — Seller-application review**
- **E11 — Disputes**
- **E12 — Backup**

> Each stretch epic stays a single epic for now; split into sub-issues only when claimed.

---

## 5. Still open before creation (your two quick calls)

| Decision | Options | Default if unspecified |
|---|---|---|
| **Board** | GitHub Project board (Todo/In-progress/In-review/Done) vs issues+milestones only | **Board** |
| **Creation method** | I run `gh issue create` · I hand you a script · I draft bodies to paste | **Script** |

**Lighter-weight option:** if ~44 issues feels heavy, collapse Owner 5/6/7 sub-issues into their epic checklists → drops to ~30 issues, keeping full sub-issues only on the critical path (Owners 1–4).
