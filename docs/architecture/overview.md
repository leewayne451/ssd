# Architecture Overview

Chateau Collective is structured as a layered monolith. The codebase keeps the
application in one deployable Flask service while separating responsibilities
across clear layers. In production the service runs as a Docker Compose stack:
nginx (TLS termination and reverse proxy) in front of the Flask app served by
Gunicorn (see [deploy/README.md](../../deploy/README.md)).

## Layers

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
front of the Flask application. The stack is containerized with Docker Compose:
only the nginx container is exposed publicly; the app container is reachable
solely on the internal Compose network.

Responsibilities:

- Nginx reverse proxy and TLS termination.
- Gunicorn application serving.
- Container build, orchestration, and startup migrations.
- Baseline web scanning (OWASP ZAP via CI).

> Note: HTTP security headers (HSTS, CSP, X-Frame-Options,
> X-Content-Type-Options, Referrer-Policy) are emitted **only by the
> application layer** (`app/security/headers.py`) — nginx intentionally does
> not duplicate them (doubled headers were flagged by ZAP). The deploy
> pipeline verifies they are present on live responses after every deploy.

Relevant paths:

- `Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh`
- `docker-compose.ci.yml` (CI override used by the DAST workflow)
- `deploy/nginx/chateau-collective.conf` (HTTP) and
  `deploy/nginx/chateau-collective.tls.conf` (HTTPS)
- `deploy/gunicorn/gunicorn.conf.py`
- `security/zap/zap-baseline.conf`
- `deploy/systemd/chateau-collective.service` (legacy — superseded by the
  Docker Compose deployment)

### 3. Web Application Layer

The web application layer contains Flask routes, forms, templates, static files,
application configuration, extension initialization, and logging setup.

Responsibilities:

- Register Flask routes.
- Bind forms and templates to user workflows.
- Apply application configuration.
- Initialize database and migration extensions.
- Apply security headers (sole source: `app/security/headers.py`, set on
  every response via `after_request` — including error pages).

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
- Store local development data in the Flask `instance` folder. In production
  the SQLite database lives on a named Docker volume so it survives redeploys.

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
|   +-- workflows                           # CI/CD pipelines (see ci_cd.md)
|       |-- ci.yml                          # pytest + coverage + pip-audit
|       |-- dast-zap.yml                    # ZAP full scan vs in-CI app
|       |-- deploy-aws.yml                  # Docker Compose deploy to AWS VM
|       |-- image-scan.yml                  # Trivy container image scan
|       |-- security-scan.yml               # Bandit + Semgrep + gitleaks
|       |-- uptime.yml                      # Scheduled /healthz check
|       +-- zap-baseline.yml                # Manual ZAP baseline vs deployed site
|-- app
|   |-- models                              # -- Data/Storage Layer --
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
|   |-- security                            # Security control modules
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
|   |-- services                            # -- Business Service Layer --
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
|   |-- web                                 # -- Web Application Layer --
|   |   |-- forms                           # Server-side form validation
|   |   |-- routes                          # Flask route modules
|   |   |-- static                          # CSS, JS, images
|   |   +-- templates                       # -- Client Layer --
|   |-- __init__.py                         # App factory
|   |-- config.py                           # Config (dev/test/prod)
|   |-- extensions.py                       # SQLAlchemy, Migrate, CSRF init
|   +-- logging_config.py                   # Audit + security log setup
|-- deploy                                  # -- Edge Protection Layer --
|   |-- README.md                           # Deployment guide (Docker on AWS VM)
|   |-- gunicorn
|   |   +-- gunicorn.conf.py
|   |-- nginx
|   |   |-- chateau-collective.conf         # HTTP site config
|   |   +-- chateau-collective.tls.conf     # HTTPS site config
|   |-- scripts
|   |   +-- backup.sh                       # SQLite backup script
|   +-- systemd                             # Legacy (pre-Docker) service unit
|       +-- chateau-collective.service
|-- doc                                     # Course/project PDFs (proposal, D1)
|-- docs                                    # Project documentation
|   |-- architecture                        # This overview + CI/CD docs
|   |-- d1
|   |-- d2                                  # Deliverable 2 evidence
|   +-- qa
|-- instance                                # SQLite DB (gitignored)
|-- migrations                              # Alembic migrations
|   +-- versions
|-- security                                # SAST/DAST configs
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
|   |-- test_admin_logs.py
|   |-- test_app_boots.py
|   +-- test_audit_service.py
|-- .env.example
|-- .gitignore
|-- Dockerfile                              # App container image (Gunicorn)
|-- docker-compose.yml                      # Production stack (web + nginx)
|-- docker-compose.ci.yml                   # CI override for DAST
|-- docker-entrypoint.sh                    # Runs migrations, then Gunicorn
|-- manage.py                               # Dev server entry point
|-- pyproject.toml                          # Project metadata + pytest config
|-- README.md
|-- requirements.txt                        # Runtime dependencies (pip)
|-- requirements-dev.txt                    # Dev/security tooling (pip)
|-- uv.lock                                 # Lockfile for uv (optional)
+-- wsgi.py                                 # WSGI entry point
```

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

These controls are supported by the automated security workflows described in
[ci_cd.md](ci_cd.md).
