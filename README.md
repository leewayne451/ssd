# Chateau Collective

Chateau Collective is a secure marketplace for luxury goods, developed for
ICT2216 Secure Software Development (AY2025 Trimester 3) by Team 31,
Chateau Nexus.

The platform supports the listing, purchase, shipment, and authentication of
high-value luxury products. Its design prioritizes role-based access control,
secure session handling, input validation, auditability, and automated security
checks as part of the software delivery workflow.

## Tech Stack

- **Application**: Flask, Jinja2, SQLAlchemy, Flask-Migrate, SQLite,
  Bootstrap 5
- **Runtime**: Gunicorn behind nginx, containerized with Docker Compose
- **Testing and quality**: pytest, GitHub Actions
- **Security tooling**: Bandit, Semgrep, gitleaks, OWASP ZAP, Trivy, pip-audit

## Getting Started (Local Development)

Requires Python 3.12+.

```bash
git clone <repository-url>
cd ICT2216_Secure-Software-Development

# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# 3. Configure environment variables
cp .env.example .env               # Windows PowerShell: Copy-Item .env.example .env

# 4. Apply database migrations (SQLite at instance/chateau.db)
flask db upgrade

# 5. Run the development server
python manage.py
```

The `.env.example` defaults are fine for local development. Set a strong
`SECRET_KEY` before running anywhere else.

## Testing

```bash
pytest
```

Tests are split into `tests/unit`, `tests/integration`, and `tests/security`.

## Security Checks

```bash
bandit -c security/bandit.yaml -r app
semgrep scan --config p/python --config p/flask --config p/secrets --config security/semgrep.yaml app
pip-audit
```

Note: Semgrep ships no native Windows wheels — run it on macOS/Linux or rely
on CI. The same scans (plus gitleaks, OWASP ZAP, and Trivy) run automatically
in GitHub Actions; see [docs/architecture/ci_cd.md](docs/architecture/ci_cd.md).

## Deployment

Production runs as a Docker Compose stack (nginx + Gunicorn/Flask) on an AWS
VM, deployed automatically from `main`. See
[deploy/README.md](deploy/README.md) for the full guide, including TLS setup.

## Documentation

- [docs/architecture/overview.md](docs/architecture/overview.md) —
  architecture layers, user roles, marketplace workflow states, directory
  tree, and security design notes
- [docs/architecture/ci_cd.md](docs/architecture/ci_cd.md) — CI/CD workflows
  and required secrets
- [deploy/README.md](deploy/README.md) — deployment guide (Docker on AWS VM)
- `docs/d2/` — Deliverable 2 evidence and checklists

## Team Members

- Bryan Toh
- Ong Bang Xi
- Wayne Lee Soo Wei
- Leong Yi Phang
- Tason Chua Dong Xuan
- Cheng Chun Yuan
- Oh Jia Rong
