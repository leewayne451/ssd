# CI/CD Pipeline — Sequence Diagram (D2 report §2.1)

Evidence row 17. Render with any mermaid viewer (GitHub renders it natively);
export to PNG for the report.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Team member
    participant GH as GitHub (leewayne451/ssd)
    participant CI as Actions: CI
    participant SS as Actions: Security Scan
    participant DZ as Actions: DAST (ZAP)
    participant TV as Actions: Trivy
    participant DP as Actions: Deploy
    participant VM as AWS VM (Docker Compose)

    Dev->>GH: git push feature branch + open PR
    par on every PR / push
        GH->>CI: trigger
        CI->>CI: pytest (132 tests) + coverage
        CI->>CI: pip-audit (dependency check)
        CI-->>GH: status + junit/coverage/audit artifacts
    and
        GH->>SS: trigger
        SS->>SS: Bandit (security/bandit.yaml)
        SS->>SS: Semgrep (p/python p/flask p/secrets + project rules)
        SS->>SS: gitleaks (secret scan, full history)
        SS-->>GH: status + SAST report artifacts
    and
        GH->>DZ: trigger
        DZ->>DZ: build app image, boot via compose
        DZ->>DZ: OWASP ZAP baseline vs http://localhost:8000
        DZ-->>GH: status + ZAP report artifact
    and on Dockerfile/deps change
        GH->>TV: trigger
        TV->>TV: build image + Trivy CVE scan
        TV-->>GH: status
    end

    Note over GH: Branch protection: PR needs 1 approval<br/>+ green CI + Security Scan to merge
    Dev->>GH: teammate reviews & merges PR into main

    GH->>DP: push to main triggers deploy
    DP->>VM: SSH (key from GitHub secrets, host = DuckDNS domain)
    VM->>VM: git reset --hard origin/main
    VM->>VM: docker compose up -d --build
    VM->>VM: migrations run on container start
    DP->>VM: health gate: curl /healthz (fail -> red run)
    VM-->>DP: {"status":"ok"}
    DP-->>GH: deploy run green (evidence row 10)

    loop every 30 min (schedule)
        GH->>VM: Uptime Check: curl APP_URL/healthz
        VM-->>GH: 200 OK (NFSR-09 evidence trail)
    end
```

**Tools named for report §2.1:** GitHub Actions, pytest, coverage, pip-audit,
Bandit, Semgrep, gitleaks, OWASP ZAP, Trivy, Docker/Compose, nginx, Gunicorn,
certbot/Let's Encrypt, DuckDNS.
