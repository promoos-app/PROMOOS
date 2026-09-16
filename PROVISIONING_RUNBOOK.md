# PromoOS — Provisioning Runbook

**Audience**: platform operator turning a demo instance into a production merchant environment.
**Time**: ~45 minutes end-to-end (mostly waiting for DNS + Stripe verification).
**Prereqs**: SSH/console access to the pod, admin access to Stripe + Resend accounts.

---

## Phase 0 — Sanity check the demo instance

```bash
# 1. Both services running?
sudo supervisorctl status
# → backend RUNNING · frontend RUNNING

# 2. Backend responding on /api/*?
curl -s https://<your-domain>/api/.well-known/security.txt
# → RFC 9116 contact info

# 3. Superadmin login works?
curl -s -X POST https://<your-domain>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"superadmin@promoos.com","password":"'"$SUPERADMIN_PASSWORD"'"}'
# → {"token":"…","user":{"role":"superadmin",…}}
```

If any of these fail, stop here and check `/var/log/supervisor/backend.*.log`.

---

## Phase 1 — Rotate all seed credentials

The demo ships with well-known passwords. In production you MUST rotate them.

```bash
# In /app/backend/.env replace:
#   SUPERADMIN_PASSWORD=… (32+ random chars)
#   ADMIN_PASSWORD=…      (owner of the first workspace)
#   JWT_SECRET=…          (rotating this logs everyone out — do it now, once)
python3 -c "import secrets; print(secrets.token_urlsafe(36))"   # generate

sudo supervisorctl restart backend
```

The seed logic is idempotent — passwords hash to the new values on next startup.
Save the values in your password manager AND `/app/memory/test_credentials.md`.

---

## Phase 2 — Stripe live keys

The demo uses the Emergent-provisioned test Stripe key. To take real payments:

1. **Get your live keys** from https://dashboard.stripe.com/apikeys.
2. **Add them to `/app/backend/.env`**:
   ```
   STRIPE_SECRET_KEY=sk_live_…
   STRIPE_WEBHOOK_SECRET=whsec_…
   ```
3. **Register the webhook** at https://dashboard.stripe.com/webhooks:
   - Endpoint: `https://<your-domain>/api/stripe/webhook`
   - Events: `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
     `checkout.session.async_payment_failed`
   - Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.
4. **Restart backend** and verify:
   ```bash
   sudo supervisorctl restart backend
   curl -s -H "Authorization: Bearer $TOKEN" https://<your-domain>/api/billing/plans
   # → 2 plans returned (Basic $49, Pro $79)
   ```
5. **Smoke test a checkout** by clicking "Upgrade" in the app → Stripe test-mode → confirm
   `/api/billing/subscription` reflects the new plan.

> **Never** commit live keys. `.env` is in `.gitignore`. Rotate immediately if leaked.

---

## Phase 3 — Resend domain (transactional + marketing email)

1. **Add your sending domain** at https://resend.com/domains (e.g. `mail.acme.com`).
2. **Publish DNS records**: SPF + DKIM + optional DMARC. Resend gives you exact records.
   Wait 10–20 min for verification to flip to ✅.
3. **Add to `/app/backend/.env`**:
   ```
   RESEND_API_KEY=re_…
   SENDER_EMAIL=hello@mail.acme.com
   ```
4. **Restart backend**, then send a test:
   ```bash
   TOKEN=$(curl -s -X POST https://<your-domain>/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@promoos.com","password":"'"$ADMIN_PASSWORD"'"}' \
     | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

   curl -s -X POST https://<your-domain>/api/coupons/<coupon_id>/send-email \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"to":["you@example.com"],"landing_url":"https://<your-domain>/c/SUMMER25"}'
   ```
5. **Verify inbox headers** include:
   ```
   List-Unsubscribe: <https://<your-domain>/api/unsubscribe/…>, <mailto:unsubscribe+…@promoos.com>
   List-Unsubscribe-Post: List-Unsubscribe=One-Click
   ```
   Gmail's Feb-2024 sender rules require this for anyone sending > 5k msgs/day.

---

## Phase 4 — Public URL & CORS

`/app/backend/.env`:
```
PUBLIC_APP_URL=https://<your-domain>
CORS_ORIGINS=https://<your-domain>
```

`CORS_ORIGINS=*` is fine for the demo; set the strict origin for prod so
credentials-with-wildcard doesn't get browser-rejected.

Frontend `/app/frontend/.env`:
```
REACT_APP_BACKEND_URL=https://<your-domain>
```

Restart both services.

---

## Phase 5 — Onboard the first merchant

**Option A — via UI** (recommended):
1. Log in as superadmin → **Admin** → **Workspaces** → **Create workspace**.
2. Create an owner user for that workspace → email them a temporary password.
3. Owner logs in → Settings → Brand kit (logo, colors, font, currency).
4. Owner visits Integrations → connects Stripe (workspace-level), Mailchimp, Meta, etc.

**Option B — programmatically**:
```bash
curl -X POST https://<your-domain>/api/admin/users \
  -H "Authorization: Bearer $SUPERADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "owner@newmerchant.com",
    "password": "'$(python3 -c 'import secrets;print(secrets.token_urlsafe(16))')'",
    "role": "owner",
    "workspace_name": "New Merchant Ltd."
  }'
```

---

## Phase 6 — Compliance switches

Confirm the following pages/endpoints are live before opening the doors:

| What | Where | Notes |
|---|---|---|
| Privacy policy | `/privacy` | Merchant may want to override with their own copy |
| Terms of use | `/terms` | Same |
| Cookie consent banner | shows on every `/f/:slug` | Persisted in `promoos_cookie_consent` |
| DSAR: export | `Settings → Privacy & data rights → Export JSON` | Returns full workspace dump |
| DSAR: delete | `Settings → Privacy & data rights → Request deletion` | Emails all superadmins with a 30-day SLA |
| List-Unsubscribe | Every marketing send | Auto-injected header + `/api/unsubscribe/{token}` |
| RFC 9116 | `/api/.well-known/security.txt` (canonical) + `/.well-known/security.txt` (mirror) | Update `SECURITY_CONTACT_EMAIL` env if you want a non-default contact |

Optional but recommended:
- Fill `SECURITY_CONTACT_EMAIL` in `.env` so `security.txt` points at your inbox.
- Add a real cookie-consent copy for the merchant's jurisdiction (French CNIL, etc.).

---

## Phase 7 — Load test before opening

```bash
# Fast in-container smoke (20 s, no k6 needed)
python3 scripts/loadtest_bench.py --duration 30 --concurrency 100

# Full 500 rps ramp (requires k6)
BASE_URL=https://<your-domain> FUNNEL_SLUG=<published_slug> COUPON_CODE=<active_code> \
  k6 run scripts/loadtest.k6.js
```

Pass criteria (as coded in the harness):
- p95(funnel read) < 500 ms
- p95(coupon validate) < 700 ms
- Error rate < 1 %

Any breach → check `db.currentOp()` for missing indexes, `/var/log/supervisor/backend.err.log` for exceptions.

---

## Phase 8 — Post-launch checklist

- [ ] All seed passwords rotated
- [ ] Stripe live key + webhook verified with a real $1 purchase
- [ ] Resend domain fully verified (green in dashboard)
- [ ] `PUBLIC_APP_URL` + `CORS_ORIGINS` are strict
- [ ] Cookie banner appears on `/f/:slug`
- [ ] Sending yourself a coupon email lands in inbox with `List-Unsubscribe` header visible
- [ ] `/api/admin/errors` empty (no silent crashes)
- [ ] `python3 scripts/loadtest_bench.py --strict` exits 0
- [ ] Superadmin owns a backup of `/app/memory/*` + Mongo dump

---

## Break-glass — rolling back

Emergent snapshots the whole pod on every step. To revert:
- Use the **Rollback** control in the chat input (free, restores everything).
- Never `git reset` — it won't roll back `.env`, uploads, or Mongo state.

To take Mongo out for offline surgery:
```bash
mongodump --uri="$MONGO_URL" --archive=/tmp/promoos-$(date +%F).gz --gzip
# … after fix …
mongorestore --uri="$MONGO_URL" --archive=/tmp/promoos-YYYY-MM-DD.gz --gzip
```

---

## Support contacts

- Emergent platform issues: use the in-app **Support** flow (agent will triage credits/refund questions).
- Stripe issues: https://support.stripe.com/
- Resend issues: https://resend.com/support
- Your `security.txt` contact: whatever you set as `SECURITY_CONTACT_EMAIL`.
