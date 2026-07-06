# Edge rate limiting & bot filtering (E-04)

Covers FSR-05 (IP-level brute-force throttling on top of the app's per-account
lockout), FSR-06 (account-abuse / fake-registration flooding), FSR-23
(application-layer excessive-request protection), FSR-24 (bot/automated-traffic
filtering), NFSR-12 (excessive-request resilience) and SDR-15 (traffic-filtering
config reviewed before deployment).

## Where it lives

`deploy/nginx/chateau-collective.conf` (HTTP) and
`deploy/nginx/chateau-collective.tls.conf` (HTTPS) — whichever is mounted at
`/etc/nginx/conf.d/default.conf` by `docker-compose.yml`.

## Two complementary layers

| Layer | Control | What it catches |
|---|---|---|
| Application | `app/security/rate_limit.py` — per-**account** lockout, escalating 5→15→60 min after 3/5/10 failed logins | Targeted guessing of one account (`tests/unit/test_auth.py::test_account_lockout_after_failed_attempts`) |
| Edge (nginx) | per-**IP** `limit_req` zones + `limit_conn` + bad-UA `map` | Distributed guessing, credential stuffing across many accounts, fake-registration floods, scraping, scanners — things the app can't see per-IP |

The app control alone can be side-stepped by rotating the target account; the
edge control alone can't tell a locked account from a fresh one. Together they
cover D1's threat model rows R-01 (brute force), R-06 (fake accounts), R-12
(scraping) and R-15 (search/API flooding).

## Zones and limits

```nginx
limit_req_zone $binary_remote_addr zone=auth_zone:10m    rate=5r/m;   # login/register
limit_req_zone $binary_remote_addr zone=search_zone:10m  rate=30r/m;  # /listings
limit_req_zone $binary_remote_addr zone=general_zone:10m rate=120r/m; # everything else
limit_conn_zone $binary_remote_addr zone=conn_per_ip:10m;
limit_req_status 429;  limit_conn_status 429;
```

- `/auth/login`, `/auth/register` → `auth_zone` (5 req/min/IP, burst 5). Slows
  online guessing to a crawl without locking out legitimate retries.
- `/listings` (browse/search) → `search_zone` (30 req/min/IP, burst 20).
  Frustrates catalogue scraping while allowing normal browsing.
- everything → `general_zone` (120 req/min/IP) + `limit_conn 20` per IP.

## Bot / scanner filtering

A `map` on `$http_user_agent` sets `$bad_bot` for empty UAs and known
scanner/scraper agents (sqlmap, nikto, nmap, masscan, nessus, and default
scripting clients such as python-requests / curl / scrapy). Matched requests
get an immediate `403` before reaching the app.

## Verification (run on the VM after deploy)

1. **Syntax:** `docker compose exec nginx nginx -t` → `syntax is ok / test is successful`.
2. **Auth throttle:** `for i in $(seq 1 12); do curl -s -o /dev/null -w "%{http_code}\n" https://<domain>/auth/login; done`
   → first ~5 return `200`, the rest `429`.
3. **Bot block:** `curl -s -o /dev/null -w "%{http_code}\n" -A "sqlmap/1.7" https://<domain>/`
   → `403`.

Capture the terminal output of steps 1–3 as `mm7-19-rate-limiting.txt` in this
folder for the report appendix.

> Note: `limit_req` keys on `$binary_remote_addr`. Because the app sits behind
> nginx, this is the real client IP at the edge; the app additionally trusts
> `X-Forwarded-For` only from the proxy. No live `nginx -t` was run at authoring
> time (Docker daemon offline on the dev box) — run step 1 on the VM before the
> demo.
