# Chateau Collective Deliverable 2 Gap Checklist

Prepared from:

- `doc/project_description.pdf`
- `doc/proposal.pdf`
- `doc/ICT2116_P2_team31_Deliverable_One.pdf`
- `doc/Lecture 5.5 Second Half Intro AY2025T3.pdf`

## Summary

Deliverable 1 already gives Chateau Collective a strong design foundation: security requirements, abuse and misuse cases, threat modelling, attack surface analysis, layered Flask architecture, security design decisions, workflow state rules, and a class/database model.

Deliverable 2 must now prove that the design has been implemented. The main gap is not the written design; it is technical evidence: actual code snippets, configuration files, CI/CD run history, screenshots, automated test results, deployment proof, and contribution evidence.

## Gap Checklist

| D2 requirement | Evidence likely already exists from D1 | New artifact/code/config screenshot still needed | Can prepare immediately this week |
| --- | --- | --- | --- |
| Design review/refinements from D1 | D1 already has security requirements, threat model, layered Flask architecture, security design decisions, workflow state rules, and class/database model. | Short "what changed since D1" table: original design -> implementation refinement -> security benefit. | Compare D1 sections 8-9 against current repo layout and write 3-5 refinements, especially modular files, CI/CD, deployment, and test evidence. |
| CI/CD process and tools | Proposal names pytest, GitHub Actions, pip-audit, Bandit, Semgrep, and OWASP ZAP. | Actual workflow snippets and screenshots of runs: `.github/workflows/ci.yml`, `.github/workflows/security-scan.yml`, `.github/workflows/zap-baseline.yml`. | Capture workflow files, run-history screenshots, and a short CI/CD sequence diagram. |
| Repeated successful GitHub Actions triggers | D1 only planned DevSecOps testing, not run evidence. | GitHub Actions history showing multiple push/PR runs across implementation, not just one final run. | Push small legitimate commits from each member and collect Actions run screenshots with dates/status. |
| GitHub repo access for markers and D3 QA | D1 says the app is a development-team deliverable and will be reviewed later. | Screenshot of repo collaborators/access, public/private access confirmation, final commit hash. | Prepare a "Repository Access and Freeze" appendix page with repo URL, branch, commit SHA, and access screenshot. |
| Directory/file listing and QA-oriented organization | D1 architecture maps Client, Edge, Web Application, Business Service, and Data/Storage layers. README already has a directory tree. | Current tree screenshot plus explanation tying files to D1 layers. | Use `README.md` as the base; update/capture `tree` output or the GitHub file browser. |
| UML diagrams mapped to GitHub files | D1 already has class/component architecture and database model rationale. | D2 diagrams must reference actual files/classes, not only conceptual components. | Generate class/package diagrams from `app/models`, `app/services`, `app/security`, and map each diagram box to filenames. |
| Every member contribution evidence | D1 has team list only. | GitHub contributors graph, commit list filtered by author, PR review/merge screenshots. | Assign small real tasks per member: tests, forms, routes, security helpers, docs, and collect commit evidence. |
| Auto-trigger deployment to AWS VM | D1 planned AWS VM and edge/deployment controls. | Successful deploy workflow screenshot plus AWS/server proof; workflow exists at `.github/workflows/deploy-aws.yml`. | Verify GitHub secrets, run deployment, capture Actions log and `systemctl status`/browser healthcheck screenshot. |
| Secure login implementation | D1 covers admin 2FA, password policy, password hashing, brute-force protection, and account abuse logging. | Actual login/register/logout code, sequence diagram, screenshots, and snippets. Current `app/web/routes/auth_routes.py` is still TODO and `app/services/auth_service.py` is empty. | Implement login flow with Werkzeug hashing, failed-login logging, rate limiting, tests, and a login sequence diagram. |
| HTTPS/server authentication/key handling | D1 requires HTTPS/TLS, secure storage, and no exposed private keys. | Nginx/TLS config, enabled cipher/TLS version screenshot, private-key storage explanation without exposing secrets. | Fill out Nginx config, capture SSL Labs/browser certificate details or `openssl s_client` output, document key path/permissions. |
| Password storage and protection | D1 FSR-02/03 and SDR-05 already justify secure password handling. Current model has `password_hash`; password policy helper exists. | Code proving hash generation/checking and no plaintext storage/logging. | Add snippets from `User.password_hash`, auth service, password policy tests, and DB screenshot showing hash-like values only. |
| Session management | D1 FSR-04/SDR-06 covers secure sessions and timeout. Current `app/config.py` has cookie flags and production secure cookies. | Session lifecycle proof: token/cookie structure, logout invalidation, inactivity timeout, replay/hijack mitigations. `app/security/session_policy.py` is only a placeholder. | Implement timeout/regeneration/logout clearing, capture browser cookie flags, add tests for protected route and logout. |
| Access control | D1 covers RBAC, buyer/seller/admin ownership checks, IDOR prevention, and workflow controls. Current `app/security/rbac.py` has basic decorators, but route integration is still thin. | Code snippets showing decorators applied to real routes, ownership checks, denied-access screenshots, negative tests. | Implement role/ownership checks for profile/cart/order/listing/admin routes and produce buyer-vs-seller-vs-admin test screenshots. |
| Secure coding best practices | D1 SDR list covers input validation, output encoding, SQLAlchemy/parameterized queries, CSRF, upload validation, audit logging, errors. | Evidence from actual files and tests. Current headers and file extension/size checks exist, but MIME/signature validation, audit persistence, CSRF form usage, and many routes still need proof. | Build an OWASP mapping table: practice -> file -> snippet -> test. Include `app/security/headers.py`, `app/security/file_validation.py`, CSRF, audit, and validation snippets. |
| Dependency inventory and dependency check | Proposal and D2 both name dependency checks. Workflows run `pip-audit`. | `requirements.txt`, `requirements-dev.txt`, pip-audit output, remediation note for findings. | Run `pip-audit`, save output, screenshot CI dependency-audit step, and include dependency inventory table. |
| Automated testing/TDD evidence | D1 planned access-control, negative, audit, backup, dependency, and browser tests. Current tests are smoke tests only in `tests/test_app_boots.py`. | Pytest results for auth, session, RBAC, upload, workflow, audit, backup, and negative cases. | Add focused unit/security tests first, then CI screenshots showing pytest passing repeatedly. |
| D2 report packaging and freeze | Project PDF says D2 is Report II, 30 pages excluding appendices, due Week 10 Thursday 9 July 9:00 am; lecture says source code must be complete/frozen on submission. | Final report, appendix evidence pack, frozen commit SHA, peer appraisal completion. | Start a D2 evidence folder now: screenshots, snippets, diagrams, test logs, final commit hash, and traceability matrix. |

## Priority Work This Week

1. Implement and test the missing secure login/session/access-control flows.
2. Collect GitHub Actions screenshots showing repeated successful CI/security/deploy runs.
3. Prepare a file-to-layer repository map for D3 QA review.
4. Build the D2 evidence appendix while implementation is still happening.
5. Assign small implementation/test tasks to every member so contribution evidence is balanced.

## Evidence Pack To Collect

| Evidence item | Suggested source |
| --- | --- |
| CI workflow file snippets | `.github/workflows/ci.yml`, `.github/workflows/security-scan.yml`, `.github/workflows/zap-baseline.yml` |
| Deployment workflow snippet | `.github/workflows/deploy-aws.yml` |
| GitHub Actions run screenshots | GitHub repository Actions tab |
| AWS deployment proof | Browser healthcheck, `systemctl status`, Nginx/Gunicorn logs |
| Login code snippets | `app/web/routes/auth_routes.py`, `app/services/auth_service.py`, `app/models/user.py` |
| Session management snippets | `app/config.py`, `app/security/session_policy.py`, logout route |
| Access control snippets | `app/security/rbac.py`, `app/security/ownership.py`, protected routes |
| Password storage proof | `app/models/user.py`, auth service hash/check functions, database screenshot |
| Secure headers proof | `app/security/headers.py`, browser devtools response headers |
| Upload validation proof | `app/security/file_validation.py`, upload route/service, negative tests |
| Audit/security event proof | `app/models/audit_log.py`, `app/models/security_event.py`, audit service, admin log screen |
| Automated test proof | `tests/unit`, `tests/integration`, `tests/security`, pytest output |
| Dependency check proof | `requirements.txt`, `requirements-dev.txt`, `pip-audit` output |
| Member contribution proof | GitHub contributors graph, commit history, PR history |

## Main Risk

The written D1 design is much more complete than the current implementation evidence. D2 should not only describe planned controls; it must show exact files, snippets, screenshots, and tests proving the controls actually run.
