# CI/CD Pipelines

All automation runs on GitHub Actions under `.github/workflows/`. The table
below summarizes each workflow; details follow.

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `ci.yml` | Push / PR to `main` | Tests, coverage, dependency audit |
| `security-scan.yml` | Push / PR to `main` | Bandit + Semgrep SAST, gitleaks secret scan |
| `dast-zap.yml` | Push / PR to `main`, manual | ZAP scan against the app built in CI |
| `image-scan.yml` | Push / PR to `main` (Docker-related paths), manual | Trivy scan of the built container image |
| `deploy-aws.yml` | Push to `main`, manual | Docker Compose deploy to the AWS VM |
| `zap-baseline.yml` | Manual (`workflow_dispatch`) | ZAP baseline scan against a deployed URL |
| `uptime.yml` | Schedule (every 30 min), manual | `/healthz` check of the deployed site |

## `ci.yml` — CI

Runs on pushes and pull requests to `main`.

- Install runtime and development dependencies with pip.
- Run `pytest` with JUnit and coverage reports.
- Run `pip-audit` dependency audit.
- Upload test and audit reports as build artifacts.

The job name `Run Tests and Dependency Audit` is referenced by the branch
protection rule on `main` — do not rename it without updating the required
status checks.

## `security-scan.yml` — SAST and secret scanning

Runs on pushes and pull requests to `main`.

- Run Bandit against `app` using `security/bandit.yaml`.
- Run Semgrep with pinned rulesets plus project rules in `security/semgrep.yaml`.
- Run gitleaks secret scanning over the full git history.
- Upload SAST reports as build artifacts.

## `dast-zap.yml` — DAST against the in-CI app

Runs on pushes and pull requests to `main`, and manually via
`workflow_dispatch`.

- Build and start the app inside the runner with
  `docker compose -f docker-compose.yml -f docker-compose.ci.yml up -d --build web`.
- Wait for `http://localhost:8000/healthz` to come up.
- Run the OWASP ZAP scan against `http://localhost:8000`.

This complements `zap-baseline.yml`, which targets the deployed HTTPS site.

## `image-scan.yml` — container image scan

Runs on pushes and pull requests to `main` when Docker-related paths change.

- Build the application image from the root `Dockerfile`.
- Scan the image with Trivy for known vulnerabilities.

## `deploy-aws.yml` — deployment

Runs on pushes to `main` and manually via `workflow_dispatch`.

- Connect to the AWS VM over SSH (`appleboy/ssh-action`).
- Pull the latest `main` branch on the VM.
- Rebuild and restart the stack with `docker compose up -d --build`.
- Prune dangling images and print `docker compose ps` / recent `web` logs for
  verification.

Required repository secrets:

- `AWS_HOST`
- `AWS_USER`
- `AWS_SSH_PRIVATE_KEY`

## `zap-baseline.yml` — ZAP baseline against a deployed site

Manual only (`workflow_dispatch`) — takes a `target_url` input.

- Run the OWASP ZAP baseline scan against the given URL.
- Use `security/zap/zap-baseline.conf`.
- Report findings without failing deployment by default.

## `uptime.yml` — uptime check

Runs every 30 minutes on a cron schedule (only on the default branch) and
manually via `workflow_dispatch`.

- `curl` the deployed site's `/healthz` endpoint using the `APP_URL` repository
  variable; skips silently until `APP_URL` is configured.

## Concurrency & run-retention policy

Validation runs are D2 evidence, so cancellation is branch-dependent:

| Where | Behaviour | Why |
|---|---|---|
| PR / feature branches | New push **cancels** the superseded in-flight run | Only the latest code matters; saves runner minutes |
| `main` | Runs **queue, never cancelled** | Every merge commit keeps a complete validation record |
| Deploys (any) | **Never cancelled** once started | A half-finished deploy leaves the VM in an unknown state |

Implementation: `cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`
in `ci.yml`, `security-scan.yml`, `dast-zap.yml`, `image-scan.yml`;
`cancel-in-progress: false` in `deploy-aws.yml`.

Guards and verification:

- `tests/unit/test_workflow_policies.py` asserts the exact expressions, that
  every workflow declares token `permissions`, and that files referenced by
  this document exist (structural guard — it cannot prove GitHub's runtime
  evaluation).
- Runtime behaviour was verified empirically: merge commit `c1e0867` had its
  runs cancelled by a merge 32 s later (the incident that motivated this
  policy), and post-fix merges each retain complete run sets.
- After any future workflow-policy change, re-verify manually once: push
  twice to a PR branch (first run should cancel), and merge two PRs in quick
  succession (both main run sets should complete).
