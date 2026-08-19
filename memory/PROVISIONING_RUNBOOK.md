# PromoOS — Third-Party App Registration Runbook

The Publish and Alt-Payment buttons in PromoOS light up as soon as their env vars are set in `backend/.env`. This runbook takes you from zero → live for each provider in ~15 min.

After adding keys, restart the backend: `sudo supervisorctl restart backend`.

---

## Social publishing (OAuth apps)

### Facebook Pages + Instagram Business
Both use the same Facebook app.

1. Go to https://developers.facebook.com/apps and create a new app (type: **Business**).
2. Add product: **Facebook Login for Business** → set OAuth redirect URI to `https://<your-promoos-domain>/api/oauth/callback`.
3. Add product: **Instagram** if you want IG publishing.
4. In App settings → Basic, copy **App ID** and **App Secret**.
5. Request permissions:
   - `pages_manage_posts`, `pages_show_list`, `pages_read_engagement` for Pages
   - `instagram_basic`, `instagram_content_publish`, `pages_show_list` for IG
6. Submit for App Review to publish outside Sandbox mode.
7. Set in `backend/.env`:
   ```
   FACEBOOK_APP_ID="…"
   FACEBOOK_APP_SECRET="…"
   IG_BUSINESS_ACCOUNT_ID="…"   # optional — auto-detected on first publish
   ```

### LinkedIn
1. Go to https://www.linkedin.com/developers/apps and create an app.
2. Add products: **Sign In with LinkedIn using OpenID Connect** + **Share on LinkedIn**.
3. OAuth 2.0 redirect: `https://<your-promoos-domain>/api/oauth/callback`.
4. Copy **Client ID** and **Client Secret**.
5. If publishing on behalf of a Company Page, note the Organization URN (`urn:li:organization:1234567`).
6. Set:
   ```
   LINKEDIN_CLIENT_ID="…"
   LINKEDIN_CLIENT_SECRET="…"
   LINKEDIN_ORG_URN="urn:li:organization:…"   # optional — publishes as user if empty
   ```

### TikTok
1. Go to https://developers.tiktok.com and create a **TikTok for Developers** app.
2. Enable **Content Posting API** — this requires business verification and can take 5-10 days.
3. Redirect URI: `https://<your-promoos-domain>/api/oauth/callback`.
4. Scopes: `user.info.basic`, `video.publish`, `video.upload`.
5. Copy **Client Key** and **Client Secret**.
6. Set:
   ```
   TIKTOK_CLIENT_KEY="…"
   TIKTOK_CLIENT_SECRET="…"
   ```
7. NOTE: TikTok publishing requires video content — the current PromoOS text-post flow returns 501 with a Coming-in-Phase-4 message until video upload is wired.

### Mailchimp
1. Go to https://us1.admin.mailchimp.com/account/oauth2/ (change the datacenter subdomain to yours if different).
2. Click **Register An App** → provide name + redirect: `https://<your-promoos-domain>/api/oauth/callback`.
3. Copy **Client ID** and **Client Secret**.
4. Set:
   ```
   MAILCHIMP_CLIENT_ID="…"
   MAILCHIMP_CLIENT_SECRET="…"
   ```
5. When connecting from PromoOS, add `audience_id` in the OAuth metadata so campaigns target the right list.

---

## Payment providers

### PayPal
1. https://developer.paypal.com/dashboard/applications/sandbox → create a REST app.
2. Copy **Client ID** and **Secret**.
3. For live: create a live app under the Live tab.
4. Set:
   ```
   PAYPAL_CLIENT_ID="…"
   PAYPAL_SECRET="…"
   ```
5. `routers/payments_alt.py` defaults to Sandbox base URL. Change `PAYPAL_BASE` to `https://api-m.paypal.com` when going live.

### Razorpay (India / UPI / NetBanking)
1. https://dashboard.razorpay.com/app/keys → generate Key ID + Secret.
2. Set:
   ```
   RAZORPAY_KEY_ID="rzp_test_…"
   RAZORPAY_SECRET="…"
   ```
3. The current plan currency is USD — for INR, edit `payments_alt.py::razorpay_checkout` to use `"currency": "INR"`.

### Paystack (Africa)
1. https://dashboard.paystack.com/#/settings/developers → copy the **Secret Key** (`sk_test_…` or `sk_live_…`).
2. Set:
   ```
   PAYSTACK_SECRET_KEY="sk_test_…"
   ```

---

## Custom-domain SSL (Cloudflare-for-SaaS)

When you set `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ZONE_ID`, PromoOS will automatically enroll every custom-domain funnel with Cloudflare Custom Hostnames — SSL is issued in the background once DNS verifies.

1. Sign up for **Cloudflare-for-SaaS** on your existing Cloudflare account (Pro plan or higher).
2. Under the zone that serves `funnels.promoos.app` (or whatever fallback subdomain), enable Custom Hostnames.
3. Create an API token with the **Zone → SSL and Certificates → Edit** + **Zone → Zone → Read** permissions on that zone.
4. Copy the token + zone ID and set:
   ```
   CLOUDFLARE_API_TOKEN="…"
   CLOUDFLARE_ZONE_ID="…"
   ```
5. Restart backend. Now when a user does `POST /api/funnels/{id}/domain`, PromoOS calls Cloudflare Custom Hostnames API and returns `cloudflare_enrolled: true` + a pending status. Users add a CNAME to `cname.promoos.app` and SSL issues automatically.
6. `POST /api/funnels/{id}/verify-domain` polls Cloudflare's status endpoint and marks the funnel `domain_verified: true` once both `status=active` and `ssl.status=active`.

---

## Verifying the wiring

After adding any provider's keys and restarting the backend:

```bash
API=https://<your-promoos-domain>
TOKEN=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" -d '{"email":"admin@promoos.com","password":"admin123"}' | jq -r .token)

# Social — should return configured=true after keys are set
curl -s "$API/api/oauth/providers" -H "Authorization: Bearer $TOKEN" | jq

# Payments — should return configured=true after keys are set
curl -s "$API/api/billing/providers" -H "Authorization: Bearer $TOKEN" | jq
```

Frontend `/integrations` and `/pricing` pages auto-detect and show live "Connect" / "Subscribe" buttons instead of `(setup)` placeholders.
