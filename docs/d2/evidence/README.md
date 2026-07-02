# D2 Evidence Pack — collection index

Drop evidence here as it is produced (per the DoD in `docs/d2/dev_task_tickets.md`,
§5). This index tracks the M7 items; other owners add theirs alongside.

## M7 — DevSecOps / CI/CD / Deploy evidence

| # | Evidence item | Source | Status |
|---|---|---|---|
| 1 | CI run history (repeated, multiple authors/dates) | GitHub → Actions tab screenshots | ☐ |
| 2 | pytest + coverage reports | `ci-reports-*` artifact from any CI run | ☐ (auto) |
| 3 | pip-audit JSON + dependency inventory | `ci-reports-*` artifact; `requirements*.txt` | ☐ (auto) |
| 4 | Bandit + Semgrep reports | `sast-reports-*` artifact from Security Scan runs | ☐ (auto) |
| 5 | Secret-scan (gitleaks) green run | Security Scan run log | ☐ |
| 6 | ZAP DAST report (in-CI) | `zap-report-*` artifact from DAST workflow | ☐ (auto) |
| 7 | ZAP DAST vs live HTTPS site | manual `zap-baseline.yml` run post-deploy | ☐ |
| 8 | Trivy image scan output | Docker Image Scan run log | ☐ |
| 9 | "CI gate works" demo | screenshot: deliberately red PR check, then green | ☐ |
| 10 | Auto-deploy run history | Deploy to AWS runs (green, with health gate log) | ☐ |
| 11 | Live HTTPS proof | browser padlock + `openssl s_client -connect <domain>:443` cipher output | ☐ |
| 12 | TLS config + key storage note | `deploy/nginx/chateau-collective.tls.conf` + `deploy/README.md` | ☐ |
| 13 | Server hardening | AWS security-group screenshot (only 22/80/443) | ☐ |
| 14 | Secrets management | `ls -l ~/ssd/.env` (0600, untracked) + GitHub secrets page screenshot | ☐ |
| 15 | Backup + restore test | `deploy/scripts/` + terminal transcript of restore cycle | ☐ |
| 16 | Uptime history (NFSR-09) | Uptime Check workflow run list screenshot | ☐ |
| 17 | CI/CD sequence diagram | to draw (mermaid) for report §2.1 | ☐ |
| 18 | Repository Access & Freeze appendix | repo URL, branch, final SHA, collaborators screenshot | ☐ |

**Rule:** name files `mm7-<nn>-<short-name>.<ext>` matching the row number so
the report can reference them unambiguously.
