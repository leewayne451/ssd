# Deployment — Château Collective (Docker on AWS VM)

Reverse-proxied Flask app, containerized with Docker Compose.

```
Internet ──▶ nginx (:80/:443, TLS)  ──▶  web (Gunicorn :8000, Flask)
             [nginx container]             [app container]
                                              │
                              named volumes: instance/ (SQLite DB),
                                             uploads/, logs/
```

- **web** — Flask app under Gunicorn, built from the root `Dockerfile`. Runs as a
  non-root user. Not published to the host; only nginx reaches it.
- **nginx** — TLS termination + reverse proxy. The only publicly exposed service.
- **Migrations** run automatically on container start (`flask db upgrade` in
  `docker-entrypoint.sh`).

## One-time VM setup

1. **Install Docker Engine + Compose** (see project chat / Docker docs) and allow
   your user to run Docker without sudo:
   ```bash
   sudo usermod -aG docker $USER   # then log out and back in
   ```
2. **Clone the repo to `~/ssd`** using the read-only deploy key:
   ```bash
   git clone git@github.com:leewayne451/ssd.git ~/ssd
   cd ~/ssd
   ```
3. **Create the `.env` file** (git-ignored) next to `docker-compose.yml` with a
   strong, stable secret:
   ```bash
   printf 'SECRET_KEY=%s\n' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env
   ```
   > Keep this value stable — regenerating it invalidates all user sessions.
4. **Bring the stack up (HTTP first):**
   ```bash
   docker compose up -d --build
   curl -fsS http://127.0.0.1/healthz    # -> {"status":"ok"}
   ```

## Enable HTTPS/TLS

Requires a domain pointing at the VM's public IP (a free DuckDNS/nip.io host works).

1. Obtain a certificate (webroot challenge is served by the running nginx):
   ```bash
   sudo docker run --rm \
     -v /etc/letsencrypt:/etc/letsencrypt \
     -v chateau-collective_certbot-webroot:/var/www/certbot \
     certbot/certbot certonly --webroot -w /var/www/certbot \
     -d chateaucollective.duckdns.org --email you@example.com --agree-tos --no-eff-email
   ```
2. The TLS config (`deploy/nginx/chateau-collective.tls.conf`) is already set
   for `chateaucollective.duckdns.org`.
3. Point the nginx mount in `docker-compose.yml` at the TLS config:
   ```yaml
   - ./deploy/nginx/chateau-collective.tls.conf:/etc/nginx/conf.d/default.conf:ro
   ```
4. Reload: `docker compose up -d`. Verify: `curl -I https://chateaucollective.duckdns.org`.

**Private key storage:** the TLS private key lives at
`/etc/letsencrypt/live/chateaucollective.duckdns.org/privkey.pem`, owned by `root` (mode `600`),
mounted **read-only** into the nginx container. It is never committed to git.

**TLS policy** (see `chateau-collective.tls.conf`): TLS 1.2 + 1.3 only; ECDHE key
exchange (forward secrecy); AES-GCM / ChaCha20-Poly1305 AEAD ciphers; HSTS on.

## CI/CD auto-deploy

`.github/workflows/deploy-aws.yml` runs on every push to `main`: it SSHes to the
VM, `git reset --hard origin/main`, `docker compose up -d --build`, prunes old
images, and fails the run unless `/healthz` returns healthy.

Required repo secrets: `AWS_HOST` (set it to `chateaucollective.duckdns.org`,
not the raw IP — survives IP changes), `AWS_USER` (`student31`),
`AWS_SSH_PRIVATE_KEY` (the PEM private key contents).

## Common operations

```bash
docker compose ps                 # status
docker compose logs -f web        # app logs
docker compose up -d --build      # redeploy after code change
docker compose down               # stop the stack
```

## School EC2 constraints & disaster recovery

Per teaching-faculty rules for the provided EC2 instances:

- **Allowed inbound ports: TCP 22, 80, 443, 8080, 8888 only** (pre-opened in
  the AWS Security Group). We use 22/80/443 and bind nothing to 8080/8888.
- **Do NOT enable ufw on the VM.** The Security Group already does the
  filtering, and Docker's published ports bypass ufw's rules anyway (Docker
  programs iptables directly), so ufw adds lockout risk (SSH) without adding
  protection. If it is ever enabled, `sudo ufw allow 22/tcp` FIRST.
- **The EC2 can be reset if unrecoverable — treat the VM as disposable.**
  Everything needed to rebuild is in this repo (Dockerfile, compose, this
  runbook); the *only* state that must leave the VM regularly:
    1. `~/backups/chateau/` (DB snapshots + checksums, from backup.sh) —
       download to a team member's machine at least weekly and before freeze
       (WinSCP or `pscp -i key.ppk -r student31@<ip>:backups/chateau .`).
    2. The uploads volume (listing images) if re-shootable demo data matters.
  The `.env` SECRET_KEY and TLS certs are re-creatable (new key just logs
  everyone out; certbot re-issues certs).
- **A reset may change the public IP.** Mitigation: point the `AWS_HOST`
  GitHub secret and browsers at the **DuckDNS domain**, never the raw IP —
  after an IP change, update the IP once in the DuckDNS dashboard and
  everything (deploys, uptime monitor, bookmarks) keeps working.
- Access credentials (IP, username, key file) stay within the team only.
