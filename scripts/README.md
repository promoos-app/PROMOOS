# PromoOS — Load Testing

Two harnesses live here. Pick the one that matches your intent.

## 1. `loadtest.k6.js` — Real 500 rps run

External load test with real ramping stages and pass/fail thresholds.

**Install k6** (one-time):
```bash
# macOS
brew install k6
# Linux
sudo apt install k6         # or: sudo snap install k6
# Windows
choco install k6
# Docker
docker run --rm -i grafana/k6 run - < scripts/loadtest.k6.js
```

**Run against your preview or prod URL:**
```bash
BASE_URL=https://campaign-hub-436.preview.emergentagent.com \
FUNNEL_SLUG=qa-storefront-live \
COUPON_CODE=SUMMER25 \
k6 run scripts/loadtest.k6.js
```

**Stages** (`options.scenarios` in the script):
- Reads ramp to **500 rps** and hold for 2 min
- Validates ramp to **100 rps** and hold for 2m30s

**Thresholds** (build fails if breached):
- p95 funnel read < 500 ms
- p95 coupon validate < 700 ms
- Error rate < 1 %

Grafana Cloud output:
```bash
K6_CLOUD_TOKEN=... k6 run --out cloud scripts/loadtest.k6.js
```

## 2. `loadtest_bench.py` — In-container smoke bench

Fast (20 s default), zero external tooling. Runs mixed reads + validates against
whatever URL is in `frontend/.env` — no k6 install required.

```bash
python3 scripts/loadtest_bench.py --duration 20 --concurrency 50
```

Flags:
- `--duration 60` (seconds)
- `--concurrency 200` (parallel coroutines)
- `--mix-validate 40` (percentage hitting `/api/public/coupons/validate`)
- `--strict` (exit 1 when thresholds are breached — useful for CI)

Environment overrides (all optional):
- `BASE_URL` — target URL (defaults to `REACT_APP_BACKEND_URL`)
- `SLUG` — published funnel slug (default `qa-storefront-live`)
- `CODE` — coupon code to validate (default `SUMMER25`)

## When to use which

| Question | Tool |
|---|---|
| "Will the app survive 500 rps sustained for 2 minutes?" | `k6` |
| "Did adding an index actually help p95?" | `loadtest_bench.py --strict` |
| "Give me a graph for the ops post-mortem" | `k6 --out json=`|
| "I don't have k6 installed, quick check please" | `loadtest_bench.py` |
