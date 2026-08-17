# PromoOS — AI Promotional Commerce Platform (PRD)

## Coverage after Iteration 8
**42 ✅ · 5 🟡 · 6 🔲** out of 53 spec sections.

## Stack
React + Tailwind + shadcn/ui · FastAPI + Motor · JWT Bearer + httpOnly cookie · background asyncio journey worker · Fernet-encrypted webhook secrets · Emergent LLM Universal Key (Claude sonnet-5 + Gemini nano-banana) · Emergent Object Storage · Resend · Twilio · **Stripe** · reportlab · qrcode · Pillow.

## Iteration 8 (Feb 2026) — Phase 1: Billing + Storage + Scale Foundations

### Stripe Billing (P0 ✅)
- **Plans**: Basic $49/mo + Pro $79/mo, each with **3-day free trial**. Stripe products+prices auto-created via `_ensure_stripe_catalog()` on first checkout.
- **Endpoints**: `GET /billing/plans`, `POST /billing/checkout`, `GET /billing/status/{sid}`, `GET /billing/subscription`, `POST /stripe/webhook`, `GET /admin/stripe-onboarding` (superadmin).
- **Frontend**: `/pricing` (public), `/billing/success` (polls status), `/billing/cancel`. Subscribe button auth-gated → redirects to Stripe checkout.
- **Security**: `origin_url` whitelisted vs. PUBLIC_APP_URL / request Origin / Host (prevents redirect hijack). Webhook signature enforced in live mode; sandbox-only permissive fallback.
- **Admin Payments tab**: "Connected" Stripe card with account_id, publishable key preview, and **Claim your Stripe account to go live** deep-link.

### Security P0
- **Superadmin credentials rotated**: `SUPERADMIN_PASSWORD=sZpRBNpLKypsQDURBQNqMIzE`. Seed logic re-hashes on every startup to match env — idempotent rotation.
- **API-key prefix indexing**: `api_keys.key_prefix` (first 16 chars) indexed → O(1) lookup instead of O(N) bcrypt scan. Legacy keys backfilled on next use.

### Global Currencies & Fonts
- `GET /api/currencies` → **145 ISO-4217 codes** (fiat + BTC/ETH/USDT/USDC).
- `GET /api/fonts` → **85 Google/Adobe font families**.
- Settings page currency + font dropdowns bound to these endpoints.

### Object Storage & Logo Upload
- Emergent Object Storage integrated (namespaced under `promoos/uploads/{workspace_id}/`).
- `POST /api/uploads` (multipart, `file` field, max 10MB, JPG/PNG/WebP/SVG/GIF/HEIC).
- `GET /api/uploads/{id}` streams the file. `GET /api/uploads` lists workspace assets. `DELETE /api/uploads/{id}` soft-deletes.
- Settings page: Upload logo button + live preview + fallback URL input.

### Coupon Share · Embed · Download
- `GET /api/coupons/{cid}/share` → landing_url + 5 embed snippets (inline/popup/bar/wheel/wallet) + 7 share links (email/twitter/facebook/linkedin/whatsapp/telegram/pinterest).
- `GET /api/coupons/{cid}/download.png` → 1200×630 printable PNG with headline/description/code/QR (Pillow-rendered).
- Coupons list dropdown → **Share & embed** dialog + **Download PNG**.

### Expanded Integrations Page
- **Email marketing** grid: Resend · SendGrid · Mailchimp · ConvertKit · Brevo · Postmark · Mailgun · AWS SES · Klaviyo.
- **Social & AI auto-publish** grid: Facebook · Instagram · X · LinkedIn · TikTok · YouTube · Pinterest · Threads · Snapchat.
- **Delivery** grid: Twilio · **Stripe (connected)** · PayPal · Razorpay · Paystack · Telegram.

### Footer
- Public **Admin login** link (`/login?admin=1`) alongside Privacy, Terms, Pricing.

### Testing (iter-8)
- **Backend 30/30 pytest passed** in ~7.5s. Frontend **9/9 flows passed**. Zero critical bugs.

## Backlog (P1 — next iterations)
1. **Phase 2 — Gift Card Studio & Integrations Hub** (20+ gift-card templates + editor + OAuth flows for email & social platforms).
2. **Phase 3 — Funnel Builder** (drag-drop + coupon/gift-card blocks + custom-domain publishing via Caddy/Cloudflare).
3. **Phase 4 — Scale + Payment coverage** (Redis cache, Mongo index audit, rate limits, CDN for widgets; PayPal + Razorpay + Paystack live integrations).
4. **Router split** of `server.py` (now 2777 LOC) + `extras.py` (467 LOC) into `/routers/*`.
5. **Optional hardening**: async storage/PIL via httpx + thread executor, cached Stripe price IDs, magic-byte MIME sniffing on uploads, `/logout` route.


## Iteration 7 (Feb 2026) — Ship Everything

### Security hardening
- **Webhook secrets encrypted at rest** with `cryptography.Fernet` (key derived from JWT_SECRET). Preview stored separately; plaintext only ever exists in RAM during verification.
- **`POST /api/v1/coupons/redeem`** requires `Authorization: Bearer pk_live_...`. Owner/marketer/viewer scoped by API-key `scopes: ["read","write"]`. Missing/invalid/revoked → 401. Missing scope → 403.
- **Suspended/deleted account block**: `/api/auth/login` returns 403 with clear reason.

### Full Admin Portal (superadmin only)
- **New role**: `superadmin` seeded on startup (`SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD`, defaults `superadmin@promoos.com` / `superadmin123`).
- **Endpoints**: `/api/admin/stats`, `/api/admin/users` (list + create), `/api/admin/users/{id}/{suspend|activate|restore}`, `DELETE /api/admin/users/{id}` (soft), `/api/admin/workspaces` (with per-workspace counts), `/api/admin/logs` (audit trail), `/api/admin/payments`.
- **Every write is audited** to `admin_logs` collection.
- **UI**: `/admin` page (client-side + backend gated to superadmin) with tabs Stats / Users / Workspaces / Payments / Audit Log; user rows expose Suspend / Activate / Restore / Delete action icons; sidebar Admin link only appears for superadmin role.

### Coupon Library (all 23 types)
- `GET /api/library/coupon-types` returns the full 23-item catalog with `id/name/cat/desc/default_value/audience`.
- 13 categories: Discount · Bundle · Perk · Acquisition · Retention · Growth · Lifecycle · Loyalty · Urgency · Geo · Campaign · Recurring · Attribution.
- **UI**: `/library` gallery with category filter chips + search + "Use this style" that jumps to `/coupons/new` with type/value/audience preset.

### Legal + Footer
- `/privacy` and `/terms` public routes with 8+ sections each.
- **Global footer** on every authenticated page and (compact) on `/login`: "© 2026 PromoOS. All rights reserved. A Division of Glorified Technology Solution (GTS)." + Privacy Policy + Terms of Use links.

### Testing
- **iter-7 pytest: 45/45 pass** in 11.5s.
- **All frontend flows verified**: superadmin sidebar filtering, /admin tabs, user lifecycle (create → suspend → activate → delete → restore), /library filter+search, /privacy + /terms rendering, footer everywhere.
- Zero critical, zero UI bugs.

## Backlog (P1)
1. Split `server.py` (2744 lines) into routers.
2. Dedicated `FERNET_KEY` env var so JWT_SECRET can rotate independently.
3. `verify_api_key` index by prefix instead of O(N) bcrypt scan.
4. Audit trail on `DELETE /api/pos/secret/{provider}`.
5. Multi-location workspace hierarchy.
6. Widget variants beyond current 5 (grid, carousel).
7. Barcode formats — UPC / EAN / Code128.
8. Affiliate coupons attribution.
9. Stripe billing wire-up for the /admin Payments tab.

## User inputs pending
- Top up Universal LLM key.
- `RESEND_API_KEY`, `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_SMS/FROM_WHATSAPP`, `PUBLIC_APP_URL`.
- Optional: `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` (change defaults for production).
