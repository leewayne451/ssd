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
     -d YOUR_DOMAIN --email you@example.com --agree-tos --no-eff-email
   ```
2. Edit `deploy/nginx/chateau-collective.tls.conf`, replacing `YOUR_DOMAIN`.
3. Point the nginx mount in `docker-compose.yml` at the TLS config:
   ```yaml
   - ./deploy/nginx/chateau-collective.tls.conf:/etc/nginx/conf.d/default.conf:ro
   ```
4. Reload: `docker compose up -d`. Verify: `curl -I https://YOUR_DOMAIN`.

**Private key storage:** the TLS private key lives at
`/etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem`, owned by `root` (mode `600`),
mounted **read-only** into the nginx container. It is never committed to git.

**TLS policy** (see `chateau-collective.tls.conf`): TLS 1.2 + 1.3 only; ECDHE key
exchange (forward secrecy); AES-GCM / ChaCha20-Poly1305 AEAD ciphers; HSTS on.

## CI/CD auto-deploy

`.github/workflows/deploy-aws.yml` runs on every push to `main`: it SSHes to the
VM, `git reset --hard origin/main`, `docker compose up -d --build`, prunes old
images, and fails the run unless `/healthz` returns healthy.

Required repo secrets: `AWS_HOST` (public IP/DNS), `AWS_USER` (e.g. `student31`),
`AWS_SSH_KEY` (the PEM private key contents).

## Common operations

```bash
docker compose ps                 # status
docker compose logs -f web        # app logs
docker compose up -d --build      # redeploy after code change
docker compose down               # stop the stack
```
