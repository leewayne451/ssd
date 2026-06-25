# Chateau Collective

Chateau Collective is a secure marketplace for luxury goods, developed for
ICT2216 Secure Software Development, AY2025 Trimester 3. The project is built
by Team 31, Chateau Nexus.

The platform supports the listing, purchase, shipment, and authentication of
high-value luxury products. Its design prioritizes role-based access control,
secure session handling, input validation, auditability, and automated security
checks as part of the software delivery workflow.

## Project Information

| Item | Details |
| --- | --- |
| Project | Chateau Collective |
| Course | ICT2216 Secure Software Development |
| Academic Term | AY2025 Trimester 3 |
| Team | Team 31, Chateau Nexus |
| Application Type | Secure luxury goods marketplace |

## Team Members

- Bryan Toh
- Ong Bang Xi
- Wayne Lee Soo Wei
- Leong Yi Phang
- Tason Chua Dong Xuan
- Cheng Chun Yuan
- Oh Jia Rong

## Tech Stack

### Application

- Flask
- Jinja2
- SQLite
- SQLAlchemy
- Flask-Migrate
- Werkzeug
- Bootstrap 5

### Testing and Quality

- pytest
- GitHub Actions

### Security Tooling

- Bandit
- Semgrep
- OWASP ZAP
- pip-audit

## Architecture

Chateau Collective is structured as a layered monolith. The codebase keeps the
application in one deployable Flask service while separating responsibilities
across clear layers.

### 1. Client Layer

The client layer is the browser-facing interface. It uses server-rendered Jinja2
templates, Bootstrap 5 styling, and static assets under `app/web/static`.

Responsibilities:

- Render public, authentication, listing, cart, order, seller, admin, and error
  pages.
- Submit form data to Flask routes.
- Present workflow and transaction state to users.

### 2. Edge Protection Layer

The edge protection layer contains deployment and perimeter controls that sit in
front of the Flask application.

Responsibilities:

- Nginx reverse proxy configuration.
- Gunicorn application serving.
- systemd service management.
- Security headers and baseline web scanning.

Relevant paths:

- `deploy/nginx/chateau-collective.conf`
- `deploy/gunicorn/gunicorn.conf.py`
- `deploy/systemd/chateau-collective.service`
- `security/zap/zap-baseline.conf`

### 3. Web Application Layer

The web application layer contains Flask routes, forms, templates, static files,
application configuration, extension initialization, and logging setup.

Responsibilities:

- Register Flask routes.
- Bind forms and templates to user workflows.
- Apply application configuration.
- Initialize database and migration extensions.
- Apply security headers.

Relevant paths:

- `app/__init__.py`
- `app/config.py`
- `app/extensions.py`
- `app/logging_config.py`
- `app/web/routes`
- `app/web/forms`
- `app/web/templates`
- `app/web/static`

### 4. Business Service Layer

The business service layer contains marketplace use cases and workflow logic.

Responsibilities:

- Authentication and user account operations.
- Listing, cart, order, shipment, review, dispute, and seller workflows.
- Admin, audit, upload, backup, and security event operations.
- Product and order workflow transitions.

Relevant paths:

- `app/services`
- `app/security`
- `app/utils`

### 5. Data and Storage Layer

The data and storage layer contains SQLAlchemy models, repository placeholders,
SQLite storage, and Flask-Migrate migration structure.

Responsibilities:

- Persist users, profiles, listings, carts, orders, shipments, disputes, reviews,
  authentication reviews, audit logs, security events, uploaded files, and
  backup records.
- Manage database schema changes through Flask-Migrate.
- Store local development data in the Flask `instance` folder.

Relevant paths:

- `app/models`
- `app/repositories`
- `migrations`
- `instance`

## User Roles

### Guest

An unauthenticated visitor. Guests can browse public pages and access
authentication or registration entry points.

### Buyer

A registered user who can browse listings, manage a cart, place orders, track
shipment progress, and leave reviews where permitted.

### Seller

A registered user approved to create and manage luxury product listings,
prepare committed items for shipment, and participate in order fulfillment.

### Admin

A privileged user responsible for platform oversight, seller application review,
authentication review handling, dispute support, audit visibility, and security
operations.

## Marketplace Workflow States

Luxury goods move through the marketplace using the following business states:

1. Available
   - The product is listed and can be selected by a buyer.

2. Committed
   - A buyer has committed to the item through the purchase flow.

3. Awaiting Shipment
   - The order is ready for seller shipment preparation.

4. Shipped
   - The seller has shipped the item for the next stage of processing.

5. Under Authentication
   - The product is being reviewed for authenticity before final completion.

6. Authenticated/Rejected
   - The product is either approved as authentic or rejected after review.

7. Sold
   - The transaction has completed successfully after authentication and order
     processing.

## Directory Tree

The current repository structure is:

```text
ICT2216_Secure-Software-Development/
|-- .github
|   +-- workflows                           # CI/CD pipelines
|       |-- ci.yml                          # pytest + lint + pip-audit
|       |-- deploy-aws.yml                  # Auto-deploy to AWS VM
|       |-- security-scan.yml               # Bandit + Semgrep   
|       +-- zap-baseline.yml                # OWASP ZAP DAST
|-- app
|   |-- models                              # ── Data/Storage Layer ──
|   |   |-- __init__.py
|   |   |-- audit_log.py
|   |   |-- authentication_review.py
|   |   |-- backup_record.py
|   |   |-- cart.py
|   |   |-- cart_item.py
|   |   |-- dispute.py
|   |   |-- enums.py                        # Workflow states, roles, statuses
|   |   |-- order.py
|   |   |-- order_status_history.py
|   |   |-- product_listing.py
|   |   |-- profile.py
|   |   |-- review.py
|   |   |-- security_event.py
|   |   |-- seller_application.py
|   |   |-- shipment.py
|   |   |-- uploaded_file.py
|   |   +-- user.py
|   |-- repositories                        # DB query abstraction
|   |-- security                            # ── Edge Protection Layer ──
|   |   |-- __init__.py
|   |   |-- admin_2fa.py
|   |   |-- csrf.py
|   |   |-- file_validation.py
|   |   |-- headers.py
|   |   |-- input_validation.py
|   |   |-- output_encoding.py
|   |   |-- ownership.py
|   |   |-- password_policy.py
|   |   |-- rate_limit.py
|   |   |-- rbac.py
|   |   +-- session_policy.py
|   |-- services                            # ── Business Service Layer ──
|   |   |-- __init__.py
|   |   |-- admin_service.py
|   |   |-- audit_service.py
|   |   |-- auth_service.py
|   |   |-- backup_service.py
|   |   |-- cart_service.py
|   |   |-- dispute_service.py
|   |   |-- listing_service.py
|   |   |-- order_service.py
|   |   |-- review_service.py
|   |   |-- security_event_service.py
|   |   |-- seller_service.py
|   |   |-- shipment_service.py
|   |   |-- upload_service.py
|   |   |-- user_service.py
|   |   +-- workflow_service.py
|   |-- utils                               # Shared helpers
|   |   |-- __init__.py
|   |   |-- audit.py
|   |   +-- decorators.py
|   |-- web                                 # ── Web Application Layer ──
|   |   |-- forms                           # Server-side form validation
|   |   |   |-- __init__.py
|   |   |   |-- admin_forms.py
|   |   |   |-- auth_forms.py
|   |   |   |-- cart_forms.py
|   |   |   |-- dispute_forms.py
|   |   |   |-- listing_forms.py
|   |   |   |-- order_forms.py
|   |   |   |-- profile_forms.py
|   |   |   |-- review_forms.py
|   |   |   +-- seller_forms.py
|   |   |-- routes                          # Flask route modules (NOT blueprints)
|   |   |   |-- __init__.py
|   |   |   |-- admin_routes.py
|   |   |   |-- auth_routes.py
|   |   |   |-- cart_routes.py
|   |   |   |-- dispute_routes.py
|   |   |   |-- error_routes.py
|   |   |   |-- listing_routes.py
|   |   |   |-- order_routes.py
|   |   |   |-- profile_routes.py
|   |   |   |-- public_routes.py
|   |   |   |-- review_routes.py
|   |   |   |-- seller_routes.py
|   |   |   +-- shipment_routes.py
|   |   |-- static                          # CSS, JS, images
|   |   |   |-- css
|   |   |   |-- img
|   |   |   +-- js
|   |   |-- templates                       # ── Client Layer ──
|   |   |   |-- admin
|   |   |   |-- auth
|   |   |   |-- cart
|   |   |   |-- disputes
|   |   |   |-- errors
|   |   |   |-- listings
|   |   |   |-- orders
|   |   |   |-- profile
|   |   |   |-- public
|   |   |   |   +-- index.html
|   |   |   |-- reviews
|   |   |   |-- seller
|   |   |   |-- shipments
|   |   |   +-- base.html
|   |-- __init__.py                         # App factory
|   |-- config.py                           # Config (dev/test/prod)
|   |-- extensions.py                       # SQLAlchemy, Migrate, CSRF init
|   +-- logging_config.py                   # Audit + security log setup
|-- deploy                                  # Nginx, Gunicorn, systemd, AWS scripts
|   |-- aws
|   |-- gunicorn
|   |-- nginx
|   |-- scripts
|   +-- systemd
|       +-- chateau-collective.service
|-- docs                                    # Documentations
|   |-- architecture
|   |-- d1
|   |-- d2
|   +-- qa
|-- instance                                # SQLite DB (gitignored)
|-- migrations                              # Alembic migrations
|   +-- versions
|-- security                                # Bandit/Semgrep configs, ZAP context
|   |-- zap
|   |   +-- zap-baseline.conf
|   |-- bandit.yaml
|   +-- semgrep.yaml
|-- tests
|   |-- integration                         # End-to-end flow tests
|   |-- security                            # OWASP-specific tests
|   |-- unit
|   |   |-- models
|   |   |-- security
|   |   +-- services
|   |-- conftest.py
|   +-- test_app_boots.py
|-- .env.example
|-- .gitignore
|-- manage.py                               # CLI commands
|-- README.md
|-- requirements.txt
|-- requirements-dev.txt
+-- wsgi.py                                 # WSGI entry point
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ICT2216_Secure-Software-Development
```

### 2. Create and Activate a Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

For Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Update `.env` with a strong `SECRET_KEY` before running outside local
development.

### 5. Apply Database Migrations

```bash
flask db upgrade
```

The default local database is configured as SQLite at `instance/chateau.db`.

### 6. Run the Application

```bash
python manage.py
```

The application starts the Flask development server using the app factory in
`app/__init__.py`.

## Testing

Run the test suite with:

```bash
pytest
```

The test structure is split into:

- `tests/unit`
- `tests/integration`
- `tests/security`

The current smoke test verifies that the Flask application boots successfully.

## Security Checks

Run the local security tooling with:

```bash
bandit -r app
semgrep scan --config auto app
pip-audit
```

OWASP ZAP baseline scanning is configured through GitHub Actions using:

- `security/zap/zap-baseline.conf`
- `.github/workflows/zap-baseline.yml`

## CI/CD

The repository contains the following GitHub Actions workflows:

### `ci.yml`

Runs on pushes and pull requests to `main`.

Primary jobs:

- Install runtime and development dependencies.
- Run `pytest`.
- Run `pip-audit`.

### `security-scan.yml`

Runs on pushes and pull requests to `main`.

Primary jobs:

- Run Bandit against `app`.
- Run Semgrep against `app`.

### `zap-baseline.yml`

Runs on pushes to `main`.

Primary jobs:

- Run the OWASP ZAP baseline scan.
- Use `security/zap/zap-baseline.conf`.
- Report findings without failing deployment by default.

### `deploy-aws.yml`

Runs on pushes to `main`.

Primary jobs:

- Configure AWS credentials from GitHub repository secrets.
- Connect to the AWS host over SSH.
- Pull the latest `main` branch.
- Install runtime dependencies.
- Restart the `chateau-collective` systemd service.

Required repository secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_HOST`
- `AWS_SSH_KEY`
- `AWS_USER`

## Security Design Notes

Chateau Collective includes dedicated modules for common secure software
development controls:

- Role-based access control: `app/security/rbac.py`
- Ownership checks: `app/security/ownership.py`
- Input validation: `app/security/input_validation.py`
- Output encoding: `app/security/output_encoding.py`
- CSRF support: `app/security/csrf.py`
- Password policy: `app/security/password_policy.py`
- Session policy: `app/security/session_policy.py`
- Security headers: `app/security/headers.py`
- Rate limiting: `app/security/rate_limit.py`
- File validation: `app/security/file_validation.py`
- Admin two-factor authentication support: `app/security/admin_2fa.py`
- Audit utilities: `app/utils/audit.py`

These controls are supported by automated security workflows using Bandit,
Semgrep, OWASP ZAP, and pip-audit.
