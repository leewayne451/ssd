# Dependency Inventory (D2 report §3 — "inventory of all dependencies")

Evidence row 3 companion. Source of truth: `requirements.txt` (runtime) and
`requirements-dev.txt` (dev/security tooling — never in the production image).
Automated check: **pip-audit** runs on every push/PR (CI workflow) and its JSON
report is uploaded as a `ci-reports-*` artifact; screenshots of a green run +
one artifact listing complete this row.

## Runtime dependencies (deployed in the Docker image)

| Package | Version | Purpose | Security relevance |
|---|---|---|---|
| Flask | 3.1.3 | Web framework | Session signing (SECRET_KEY), routing, error handling |
| Flask-SQLAlchemy | 3.1.1 | ORM integration | Parameterized queries — SQL-injection defence (SDR-03) |
| Flask-Migrate | 4.1.0 | DB schema migrations | Reproducible schema; runs on container start |
| Werkzeug | 3.1.6 | WSGI utilities | `generate_password_hash`/`check_password_hash` (SDR-05), ProxyFix |
| python-dotenv | 1.2.2 | Loads `.env` in dev | Keeps secrets out of code (SDR-11) |
| Flask-WTF | 1.3.0 | Forms + CSRF | CSRF token generation/validation (FSR-21) |
| email_validator | 2.3.0 | Email validation | Input validation on registration (SDR-01) |
| zxcvbn | 4.5.0 | Password strength estimation | Password policy (FSR-02) |
| gunicorn | 23.0.0 | Production WSGI server | Non-debug production serving (NFSR-21) |

## Development / security tooling (never deployed)

| Package | Version | Purpose |
|---|---|---|
| pytest | 9.0.3 | Test runner (132 tests) |
| pytest-flask | 1.3.0 | Flask test fixtures |
| pytest-cov | 7.0.0 | Coverage reports for CI artifacts |
| bandit | 1.8.3 | SAST (Python) — gated in CI |
| semgrep | 1.118.0 (Linux/CI only) | SAST — pinned rulesets + project rules |
| pip-audit | 2.9.0 | Dependency vulnerability check (rubric §3) |

## Infrastructure images (pinned in Dockerfile / compose / workflows)

| Image / action | Version | Purpose |
|---|---|---|
| python | 3.12-slim-bookworm | App base image |
| nginx | 1.27-alpine | TLS termination / reverse proxy |
| certbot/certbot | latest at issue time | Let's Encrypt certificate issuance |
| zaproxy/action-baseline | v0.14.0 | DAST in CI |
| aquasecurity/trivy-action | v0.36.0 | Image CVE scanning |
| gitleaks/gitleaks-action | v2 | Secret scanning |

**Update policy (SDR-17):** versions are pinned; upgrades are deliberate PRs
that must pass pip-audit + the scan gates before merge.
