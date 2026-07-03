# AI Review Setup

This document describes the advisory GPT-powered GitHub Actions integration
for Chateau Collective: what it does, what it deliberately does not do, its
trust model, and how to operate, disable or troubleshoot it.

## Purpose

Three advisory AI workflows complement the deterministic tooling (pytest,
pip-audit, Bandit, Semgrep, OWASP ZAP):

1. **AI Contextual PR Review** — reviews each same-repository pull request
   diff for application-specific security issues, implementation-versus-
   design drift, and missing tests, grounded in the project's own
   documentation.
2. **AI Security Triage** — triages Bandit/Semgrep findings from the
   Security Scan workflow (true positive / false positive / needs
   investigation), with application-specific impact and remediation notes.
3. **AI Milestone Audit** — a manually dispatched consistency audit that
   compares the authoritative documents (proposal, Deliverable 1 brief,
   FR/NFR, SFR/FSR/NFSR/SDR, textual use/misuse cases, threat model, attack
   surface, architecture) against the implementation and tests.

**Scanners remain authoritative.** AI output is advisory only: it never
gates, approves, merges, suppresses, fixes or deploys anything. Pass/fail
decisions still come exclusively from pytest, pip-audit, Bandit, Semgrep and
the existing workflow gates.

## Architecture

```text
.github/workflows/
  ai-contextual-pr-review.yml   (workflow_run <- CI)
  ai-security-triage.yml        (workflow_run <- Security Scan)
  ai-milestone-audit.yml        (workflow_dispatch)

tools/ai_review/                shared deterministic Python package
  config.py                     env-driven bounded limits, model variables
  schemas.py                    strict Pydantic response schemas
  path_filter.py                deny-first sensitive-path exclusion
  redaction.py                  secret-pattern redaction (secondary control)
  context_builder.py            bounded, prioritised diff context
  document_loader.py            manifest-driven trusted doc loading
  scanner_parser.py             Bandit/Semgrep/pip-audit JSON parsing
  openai_client.py              Responses API, store=False, no tools
  render.py                     deterministic Markdown rendering
  github_comment.py             single-comment upsert via stable marker
  review_pr.py                  PR review orchestrator
  triage_scans.py               scanner triage orchestrator
  milestone_audit.py            milestone audit orchestrator
  document_manifest.yml         the only source of trusted documents
  prompts/                      system prompts with injection defences

tests/ai_review/                unit tests (mocked, no real API calls)
requirements-ai.txt             CI-only pinned dependencies
```

## Workflow sequence

1. A pull request triggers **CI** (pytest + pip-audit) and **Security Scan**
   (Bandit + Semgrep) exactly as before.
2. When CI completes successfully for a same-repository PR, **AI Contextual
   PR Review** runs from the default branch, fetches the diff as text via
   the GitHub API, builds bounded context, makes one model call, and upserts
   one PR comment (marker `<!-- chateau-ai-contextual-review -->`).
3. When Security Scan completes (pass or fail), it has already uploaded
   `bandit-report.json` / `semgrep-report.json` as a short-retention
   artifact. **AI Security Triage** downloads the reports, parses them
   locally, skips OpenAI entirely if there are no findings, and otherwise
   upserts one PR comment (marker `<!-- chateau-ai-security-triage -->`) or
   writes to the job summary when no PR exists.
4. **AI Milestone Audit** runs only when a maintainer dispatches it.

## Trust model (workflow_run, no PR-head checkout)

- All three workflows execute **only default-branch code**. The PR review
  and triage workflows use `workflow_run`, which always runs the workflow
  definition and scripts from the default branch — a PR cannot modify the
  AI tooling that reviews it.
- **PR head code is never checked out, imported or executed** in any job
  holding `OPENAI_API_KEY`. The diff is fetched through the GitHub API and
  handled strictly as untrusted text.
- `pull_request_target` is not used anywhere.
- **Fork PRs are skipped by default** (head repository must equal the base
  repository), so the API key is never spent on — or exposed to workflows
  triggered by — untrusted external activity. To review an external
  contribution, a maintainer can push the branch into this repository.
- Explicit least-privilege permissions per job; `permissions: {}` at the
  workflow level. Concurrency groups with `cancel-in-progress` and explicit
  job timeouts bound every run.
- Untrusted PR metadata (branch names, titles) is never interpolated into
  shell commands; scripts receive validated integers and fixed paths only.

### Action pinning

The AI workflows use only official GitHub actions (`actions/checkout@v4`,
`actions/setup-python@v5`, `actions/upload-artifact@v4`,
`actions/download-artifact@v4`), pinned by version tag to match the
convention already used by `ci.yml` and `security-scan.yml`. They remain
version-tag pinned (not commit-SHA pinned); tightening all workflows to
immutable SHAs is a possible follow-up hardening step.

## Prompt-injection defence

All repository content — code, comments, strings, Markdown, tests, docs,
filenames, branch names, PR titles, commit messages, scanner messages — is
treated as untrusted data. Defences:

- Prompts declare that instructions inside repository content must be
  ignored and cannot change the model's role, task or output schema.
- Untrusted content is fenced in explicit boundaries
  (`<UNTRUSTED_PR_DIFF>`, `<UNTRUSTED_SCANNER_REPORT>`,
  `<UNTRUSTED_REPOSITORY_CONTENT>`) and never placed in the instruction
  text.
- Responses must match a strict JSON schema (`extra="forbid"`); anything
  instruction-shaped the model adds (for example an `execute_command`
  field) is rejected as ordinary invalid data.
- **No model output is ever executed** or passed to shells, subprocess,
  eval/exec, SQL, Git, filenames, workflow expressions, GitHub API
  endpoints or deployment scripts. GitHub endpoints are built only from a
  validated `owner/repo` slug and a validated integer PR number.
- The models are called with `store=False`, no tools, no web search, no
  code execution and no file search.

## Data sent to OpenAI

- Bounded, redacted unified diffs of **relevant, non-sensitive** changed
  files (filenames preserved).
- Bounded excerpts of the trusted documents listed in
  `tools/ai_review/document_manifest.yml` (PR reviews load only documents
  relevant to the changed files; audits use the broader audit-enabled set).
- Bounded, redacted scanner findings (rule id, severity, path, line,
  message) for triage.

## Data never sent to OpenAI

Deny-first path exclusion (see `path_filter.py`) blocks, among others:
`.env*`, `instance/`, `*.db`/`*.sqlite*`, `uploads/`, `backups/`, `logs/`
and audit/security log content, `*.pem`/`*.ppk`/`*.key` and other key or
certificate material, SSH/AWS/GitHub credentials, virtual environments,
caches, `node_modules`, build output, binary and compiled files, and
coverage databases. The lecture PDF is deliberately absent from the
document manifest.

## Context limits and redaction

Per-file, per-document and total character limits are enforced (see
`config.py`; overridable via `AI_MAX_*` environment variables). Anything cut
is explicitly marked truncated, and reports state that truncated content was
**not** reviewed. Redaction (`redaction.py`) masks secret-shaped strings
(OpenAI/AWS/GitHub keys, bearer tokens, private keys, `password=`/`secret=`/
`token=` assignments) both before content reaches the API and again before
rendering. Redaction is a secondary control; path exclusion is primary.

## Comment upsertion

Each workflow maintains exactly one PR conversation comment, found and
updated via its stable HTML marker. Re-runs update the comment in place;
duplicates are never posted.

## Scanner-report handling

`security-scan.yml` now produces `bandit-report.json` and
`semgrep-report.json`, uploads them (plus small run metadata) as a
7-day-retention artifact, and then re-applies the original pass/fail policy:
a failing scanner still fails the workflow, and report generation can never
turn a failing scan into a passing one. No source code, environment files,
databases, logs, uploads or secrets are uploaded. pip-audit remains an
independent deterministic control inside CI; AI triage covers Bandit and
Semgrep (a second pip-audit run is intentionally not added).

## Configuration

GitHub Actions **secret** (already configured):

```text
OPENAI_API_KEY=sk-placeholder-do-not-use   # placeholder shape, not a real key
```

GitHub Actions **repository variables** (already configured):

| Variable | Default | Used by |
| --- | --- | --- |
| `AI_REVIEW_MODEL` | `gpt-5.4-mini` | ai-contextual-pr-review |
| `AI_TRIAGE_MODEL` | `gpt-5.4-mini` | ai-security-triage |
| `AI_AUDIT_MODEL`  | `gpt-5.5`      | milestone audit default |

The milestone audit accepts only allowlisted models (`gpt-5.5`,
`gpt-5.4-mini`) and scopes (`full`, `security`, `requirements`,
`architecture`, `tests`), enforced both by the workflow input choices and
again inside `milestone_audit.py`.

## Running the milestone audit

1. GitHub → Actions → **AI Milestone Audit** → Run workflow.
2. Dispatch it **from the default branch** (the job checks out default-
   branch content regardless, but the workflow definition itself comes from
   the selected ref).
3. Pick model and scope; defaults are `gpt-5.5` / `full`.
4. Read the report in the job summary or download the
   `ai-milestone-audit-<run id>` artifact (`.md` + `.json`).

## Disabling and key rotation

- Disable one workflow: GitHub → Actions → select the workflow →
  “…” → **Disable workflow** (or delete its YAML file in a PR).
- Disable everything AI: remove the `OPENAI_API_KEY` secret — every AI
  workflow then fails fast without affecting CI, Security Scan, ZAP or
  deployment.
- Rotate the key: create a new key in the OpenAI dashboard, update the
  repository secret, then revoke the old key. The key is used nowhere else.

## Token usage and cost controls

Every report footer includes the model, input/output token usage (when the
API returns it) and the truncation state. Cost is bounded by: relevance
filtering (irrelevant PRs make no API call), no-findings short-circuit in
triage, hard input character limits, `max_output_tokens`, one model call per
run, bounded retries, and comment/artifact size caps.

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| AI review never runs on a PR | `workflow_run` workflows must exist on the **default branch**; merge the workflow first. Fork PRs are skipped by design. CI must complete successfully. |
| “No associated open same-repository pull request; skipping.” | The triggering commit has no open same-repo PR — expected for pushes to `main`. |
| Review comment says “Skipped: no relevant reviewable files” | The PR touched only excluded/generated/non-relevant paths (e.g. CSS or images). No API call was made. |
| Workflow fails at the model call | Check the `OPENAI_API_KEY` secret exists and is valid, and the model variable names a model the account can access. |
| Triage step cannot download artifacts | The Security Scan run may have been cancelled before upload; re-run it. |
| Schema-validation error in logs | The model returned malformed output; re-run the workflow. Nothing was posted. |

## Human-review duties

AI output is a starting point, not a verdict. A human must: verify each
finding before acting on it, treat “likely false positive” as *unconfirmed*
until checked, never close scanner findings solely on AI advice, and keep
doing normal code review — the AI comment does not replace an approving
review from a teammate.

## Known limitations

- Findings can be wrong in both directions (missed issues and false
  alarms); confidence fields are the model's self-assessment, not ground
  truth.
- Context is bounded: very large PRs and documents are truncated (always
  labelled in the report).
- PDF extraction is text-only and imperfect; **use/misuse diagrams are
  intentionally ignored** (they are being redrawn — only the textual
  descriptions are authoritative).
- Requirement identifiers are only cited when supported by the loaded
  documents; areas without loadable evidence are listed under
  “insufficient evidence”.
- **Intentionally not implemented:** issue classification, automated issue
  creation, automatic fixes, automatic commits, PR approval, merging,
  deployment, scanner suppression, execution of model-generated commands,
  application of model-generated patches.

## Local development

```bash
pip install -r requirements-ai.txt
pytest tests/ai_review -q          # deterministic tests; no API calls
```
