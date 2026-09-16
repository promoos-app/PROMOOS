# PromoOS — AI Promotional Commerce Platform (PRD)

## STATUS: FEATURE-COMPLETE (Feb 2026)

## Latest (Iter 25, Feb 2026) — Public API Rate Limits + Daily Auto-Backup
- `/api/public/*` middleware with 3-tier per-IP token buckets (strict 30/min · standard 120/min · loose 300/min); emits `X-RateLimit-*` + `Retry-After` headers; persists throttled 429 events
- Daily 03:15 UTC in-process Mongo backup via `/app/scripts/backup_mongo.sh`; auto-disables if `mongodump` missing; superadmin can trigger manually
- Admin → **Ops** tab surfaces backup status + rate-limit events + top-offenders



## Latest (Iter 24, Feb 2026) — Go-Live Automation
- Seeded marketplace preset packs — 7 curated packs (4 coupon + 3 gift-card, 28 tap-to-apply presets) via `routers/marketplace_seed.py`, idempotent on startup
- Admin Health-Check endpoint + UI tab — 20 checks across env, integrations, Mongo indexes, content, compliance; flags `ready_for_launch` when zero criticals + ≤2 warnings
- Mongo backup script `/app/scripts/backup_mongo.sh` — gzipped, auto-pruned, cron-friendly
- Everything reasonable is coded; remaining launch work is exclusively human ops (Stripe live, Resend domain, DNS, credential rotation, first merchant onboarding — all documented in `PROVISIONING_RUNBOOK.md`)



## Latest (Iter 23, Feb 2026) — Load Testing + Provisioning + DSAR SLA + Preset Pack Comments
- Preset Pack Marketplace Comments (`POST /api/preset-packs/{id}/rate`, `GET /api/preset-packs/{id}/comments`) with shared `PresetPackFeedback` UI in both Coupon editor and Gift Card studio
- DSAR SLA Email Alerts — fire-and-forget email to all superadmins on every `/api/me/data/delete`, with 30-day GDPR deadline visible
- Load testing harnesses — `scripts/loadtest.k6.js` (500 rps, k6) + `scripts/loadtest_bench.py` (in-container asyncio bench) with strict-mode thresholds
- Provisioning Runbook — 8-phase walkthrough at `/app/PROVISIONING_RUNBOOK.md` covering Stripe live, Resend domain, first merchant onboarding, compliance switches, and rollback
- New indexes: `preset_pack_ratings {pack_id, workspace_id}` unique; `deletion_requests {status, created_at}`



## Latest (Iter 22, Feb 2026) — Compliance + Sticky Mappers + Rating Comments + Crash Reporter
- Sticky Mapper Presets (`GET/POST /api/coupons/import-mapping`; auto-restore on preflight)
- Rating Comments (`RateIn.comment`, `GET /api/journey-templates/{tid}/comments`)
- Error Boundary Reporter (`POST /api/errors`, superadmin `GET /api/admin/errors`)
- CSV Delimiter Auto-Detect (`,` `;` `\t` sniffed at preflight; badge in UI)
- DSAR endpoints (`GET /api/me/export`, `POST /api/me/data/delete`, admin queue)
- List-Unsubscribe (RFC 8058) headers on every send-email; `POST/GET /api/unsubscribe/{token}`
- AI-generated metadata on `/ai/image` and `/giftcards/regenerate`; pill overlay in Coupon editor + Gift Card studio
- RFC 9116 `security.txt` (backend `/api/.well-known/` + frontend `public/.well-known/`)
- Cookie Consent Banner on every public funnel; persisted decision in `promoos_cookie_consent`
- Mongo indexes on coupons/redemptions/customers/funnels/email_events/csv_mapping_presets/error_reports for 100k-user scale


**56 modules shipped. Deployed at `https://campaign-hub-436.emergent.host`.**

## Iteration 14 (Feb 2026) — Bulk request: password reset · products · publish · bulk delete · funnel media · admin affiliates

### Password reset ✅
- `POST /api/auth/password-reset/request` — always 200 (no email enumeration); sends via Resend if configured, else logs the URL.
- `POST /api/auth/password-reset/complete` — validates token (SHA-256, 2h expiry), sets new password.
- `POST /api/auth/change-password` — authenticated in-app password change.
- Frontend: `/forgot-password` + `/reset-password` routes, plus **Forgot password?** link on the sign-in page.

### Products + workspace payments ✅
- `products` collection with `name/price/currency/description/image_url`. CRUD via `/api/products/*`.
- `POST /api/public/products/checkout` — creates Stripe Checkout for a product on any coupon/funnel page. Uses platform Stripe key (workspace-level Stripe Connect is Phase 5).
- New funnel block type: **product** — attach `product_id` + optional `coupon_code`; renders a **Buy now** button that goes straight to Stripe.

### Funnel enrichment ✅
- New block types wired into editor AND public renderer:
  - **image** (URL or upload from Emergent object storage)
  - **video** (mp4/YouTube/Vimeo, poster + autoplay support)
  - **audio** (mp3/wav)
  - **countdown** (real-time countdown to `ends_at` with days/hours/minutes/seconds)
  - **product** (Buy Now → Stripe)
  - **row** (two-column layout with nested blocks)

### Publish coupon ✅
- `POST /api/coupons/{id}/publish` and `/unpublish` toggle status between `active` and `draft`.
- Coupons list dropdown: **Publish** action.

### Customer bulk delete ✅
- `POST /api/customers/bulk-delete {ids}` — mass soft-delete.
- Customers page: checkbox column, select-all header, sticky "N selected · Delete selected" bar.

### Admin enrichments ✅
- `GET /api/admin/users-detailed` — returns plan / subscription_status / next_billing / joined_at / coupon_count / customer_count per user.
- `GET /api/admin/affiliates` — aggregates referral loops into an affiliates leaderboard (referrer, referrals, revenue).

### Testing
- All new endpoints verified via curl end-to-end (password reset, products, publish, bulk delete, affiliates). Frontend compiled clean.

## The app is feature-complete. Deploy and onboard your first merchant.


## Iteration 13 (Feb 2026) — Final P1 hardenings

### QR scan de-duplication ✅
- Same `(tracking_id + IP)` pair only counts once per 15-min window.
- Bot prefetches, refreshes, and Slack unfurl bots no longer inflate scan analytics.
- Verified: 3 rapid hits → `scan_count: 1`.

### Razorpay INR default ✅
- Basic plan now bills ₹4075 INR (≈$49) via UPI/NetBanking/cards.
- Pro plan now bills ₹6570 INR (≈$79).
- USD amounts preserved for other providers; only Razorpay uses `razorpay_currency`.

### Per-workspace LLM rate limit ✅
- 30 credits/hour on `POST /giftcards/regenerate` (text = 1 credit, image_bg = 3 credits).
- 429 with clear "wait a few minutes" message when exceeded.
- Prevents runaway UI mash from burning the Universal LLM Key budget.
- `llm_usage` collection tracks per-workspace usage for future billing tie-ins.

### Verified regressions
- iter-8 through iter-12 endpoints all remain green.
- Router split at 2523 lines (`server.py`) + 8 modules in `/routers/`.

## The app is done. What remains is deployment ops, not coding.


## Iteration 12 (Feb 2026) — Router split wave 3 · Cloudflare-for-SaaS · QR print sheets · OAuth runbook

### Router split — Wave 3 ✅
- Extracted `routers/pos.py` (6 endpoints: `/pos/{ws}/shopify`, `/pos/{ws}/woocommerce`, `/pos/rotate-secret`, `/pos/secret/{provider}`, `/pos/secrets`, `/pos/snippets`).
- server.py: **2777 → 2523 lines** (net -254). Wave-3 dropped POS block (~230 lines) + admin block from Wave 2.
- Deps threaded through `register()`: `encrypt_str`, `decrypt_str`, `_hmac_ok`, `_apply_from_pos` — same pattern as billing/qr/funnels routers.

### Cloudflare-for-SaaS custom-domain SSL automation ✅
- `POST /api/funnels/{id}/domain` now enrolls the hostname with **Cloudflare Custom Hostnames API** when `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ZONE_ID` are set — SSL provisioned automatically once the CNAME is added.
- `POST /api/funnels/{id}/verify-domain` polls Cloudflare status; marks `domain_verified=true` when both `status=active` AND `ssl.status=active`.
- Response payload: `cloudflare_enrolled`, `cloudflare_status`, `cloudflare_ssl_status`, plus DNS instructions that switch between the fallback CNAME target (`funnels.promoos.app`) and the Cloudflare-for-SaaS target (`cname.promoos.app`).
- Without CF keys, funnels still work — user just adds a CNAME to the fallback subdomain and platform issues SSL the old way.

### QR Print-Ready Sheets ✅
- New `POST /api/qr/print-sheet` — takes `{ids: [...], format: 'a4'|'letter', columns: 1-4}` and renders a paginated PDF grid via reportlab.
- Each QR is re-rendered at print resolution (box_size=20), labeled with its user-set name and payload preview.
- Frontend `/qr` — click cards to select, format dropdown (A4 / US Letter), **Print sheet ({n})** button that downloads the PDF instantly. Perfect for restaurant menus, event stickers, storefront signage.

### OAuth apps provisioning ✅
- `.env` seeded with placeholder keys for Facebook, Instagram, LinkedIn, TikTok, Mailchimp, PayPal, Razorpay, Paystack, Cloudflare — restart-safe.
- `PROVISIONING_RUNBOOK.md` — step-by-step per-provider setup (developer portal URLs, required scopes, exact env keys, verification `curl` snippets).
- Runbook auto-linkable from the /integrations page.

### Testing (iter-12)
- **Router split verified live**: `/api/pos/snippets` + `/api/pos/secrets` + `/api/pos/rotate-secret` all return correct data after extraction. Admin stats endpoint unchanged.
- **QR PDF verified**: 3-QR sheet request returns valid PDF (366KB, header `%PDF-`).
- **Cloudflare fallback verified**: unset env → `cloudflare_enrolled: false` + correct fallback CNAME instructions.
- **Regression sweep**: `/currencies` (145), `/giftcard-templates` (20), `/admin/stats` all pass.

## Backlog remaining (P2)
1. Deploy Caddy or Cloudflare-for-SaaS in front of the app so custom-domain funnels actually resolve (code is ready; needs infra).
2. Router split wave 4 — extract embed script + exports + journeys from server.py (currently ~2523 lines).
3. Razorpay INR default (currently USD).
4. QR scan de-dup (per-IP+per-tracking cool-off).
5. Radix `DialogDescription` a11y warnings on Publish/Share dialogs.


## Iteration 11 (Feb 2026) — Router split (admin) · Real social publishing · Payment expansion · QR scan analytics

### Router Split — Wave 2 ✅
- Extracted `routers/admin.py` from server.py (10 endpoints, ~120 lines removed from server.py).
- Pattern established: `register(api, db, now_iso, get_current_user, require_superadmin, hash_password, _admin_log)` — future waves will pick off `pos`, `embed`, `exports`, `journeys`.

### Real social publishing ✅
`POST /api/oauth/{provider}/publish` now actually calls provider APIs when connected + not scheduled:
- **Facebook Pages**: `POST /{page_id}/photos` (with image) or `/feed` (text + optional link).
- **Instagram Business**: 2-step — create media container → publish.
- **LinkedIn**: `POST /v2/ugcPosts` with member/org URN + optional article link.
- **Mailchimp**: create campaign → set HTML → send.
- **TikTok**: returns 501 immediately (hoisted above token check) with clear "requires video content + production API approval" message.
- Scheduled path (`scheduled_at` set) queues in `social_posts` collection without hitting the provider.

### Payment providers expansion ✅
New `routers/payments_alt.py`:
- `GET /api/billing/providers` — Stripe (configured) + PayPal, Razorpay, Paystack (returns `configured: false` + exact env-var list when unset).
- `POST /api/billing/alt-checkout` — creates real subscription checkout with PayPal Billing / Razorpay Subscriptions / Paystack Transactions when keys are present; returns clean 501 with `Set X in backend/.env` when not.
- Frontend `/pricing`: `payment-provider-selector` row with 4 chips; disabled providers show `(setup)` suffix.

### QR scan analytics ✅
- `POST /api/qr/preview {tracking: true, save: true, origin_url}` — rewrites URL payload to a short redirect service and stores `destination` server-side.
- `GET /api/qr/r/{tracking_id}` — public 302 redirect + increments `scan_count` + logs event (UA, IP, referer, timestamp) to `qr_scans` collection.
- `GET /api/qr/saved/{qid}/scans` — returns `{scan_count, scans:[…], trackable}`.
- Frontend `/qr`: `qr-tracking-toggle` checkbox, live scan-count chip on each saved-QR card.
- **URL scheme allowlist** — only `http://` and `https://` allowed (blocks `javascript:`, `data:`, `file:` etc.).

### Testing (iter-11)
- **36/36 backend pytest passed** in ~6s. **4/4 frontend flows passed**. Zero critical bugs.

### Post-testing hardenings applied
- **TikTok 501** hoisted above token check — real users now see the accurate "coming in Phase 4" message immediately instead of a red-herring "not connected".
- **OAuth `configured` flag** now requires BOTH client_id_env AND client_secret_env (was false-positive with partial config).
- **Encryption fallback logging** — emits a warning if `encrypt_str/decrypt_str` fails to import from server, so ops sees plaintext-storage regression.
- **QR redirect URL scheme allowlist** — `http://` and `https://` only, preventing `javascript:` and `data:` scheme redirect abuse.

## Backlog (P1)
1. **Continue server.py router split** — auth · coupons · campaigns · pos_webhooks · journeys · ai_copy · analytics · exports · embed · customers · library · api_keys still in server.py (~2600 lines remaining). Each future wave shrinks server.py further.
2. **Provision real OAuth apps** for FB/IG/LinkedIn/Mailchimp/TikTok — code path is complete; just needs `FACEBOOK_APP_ID`, etc. in env.
3. **Provision real payment keys** for PayPal/Razorpay/Paystack — code path is complete; add `PAYPAL_CLIENT_ID`, etc.
4. **QR scan de-dup** — same per-IP+per-tracking cool-off idea as `funnel.views`. Naive counter today.
5. **Razorpay INR default** — currently hardcoded USD in plan; INR/UPI is Razorpay's primary market.
6. **Radix DialogDescription a11y** — add descriptions to all `DialogContent`s to remove SR warnings.


## Iteration 10 (Feb 2026) — QR Studio + Login layout fix

### QR Code Studio ✅
- **7 content types**: URL · Text · Phone (tel:) · SMS (SMSTO) · Email (mailto) · WiFi (WIFI:) · vCard.
- **6 module shapes**: square · rounded · circle · gapped · vertical bars · horizontal bars.
- **4 color modes**: solid · radial gradient · horizontal gradient · vertical gradient.
- **10 curated presets**: neon-lime, electric, sunset, midnight, champagne, monochrome, forest, royal-blue, berry, print-safe.
- **Center logo overlay** from Emergent Object Storage uploads.
- **Error correction levels** L/M/Q/H (H tolerates ~30% of the code being obscured by a logo).
- Endpoints: `GET /api/qr/options`, `POST /api/qr/preview`, `POST /api/qr/download`, `GET /api/qr/saved`, `DELETE /api/qr/saved/{id}`.
- Frontend: `/qr` — live preview updates on every field change (debounced 400ms), Save-to-library, Download PNG, saved-QR gallery with delete.
- New sidebar item: **QR Studio** (QrCode icon).

### Login page layout fix ✅
- Wrapped the two-panel layout in `flex flex-col` so the footer (`©` + Pricing / Privacy / Terms / Admin) sits **below** the full-height auth area instead of squeezing the login box.
- Superadmin credentials hint replaced with a note pointing to `/app/memory/test_credentials.md` (no longer shows the old rotated-away password).


## Stack
React + Tailwind + shadcn/ui · FastAPI + Motor + `/routers/` package · JWT Bearer + httpOnly cookie · background asyncio journey worker · Fernet encryption for POS + OAuth tokens · Emergent LLM Universal Key (Claude sonnet-5 + Gemini nano-banana) · Emergent Object Storage · Resend · Twilio · **Stripe** · reportlab · qrcode · Pillow · dnspython.

## Iteration 9 (Feb 2026) — Phase 2: Gift Card Studio · OAuth Hub · Funnel Builder · Router Split

### Router Split ✅ (P1)
- Created `/app/backend/routers/` package.
- `extras.py` → `routers/billing.py` (Stripe, uploads, currencies, fonts, coupon share/download).
- New: `routers/giftcards.py`, `routers/oauth_hub.py`, `routers/funnels.py`.
- server.py registration pattern established for future extractions.

### Gift Card Studio ✅ (P0)
- **20 templates** across 9 categories (luxury, birthday, holiday, anniversary, minimalist, corporate, playful, nature, bold).
- `GET /api/giftcard-templates`, `GET /api/giftcard-templates/{id}`.
- `POST /api/giftcards/design` — instantiate a gift card from a template with amount, recipient, and full override fields (headline/subline/background/accent/font/logo).
- `POST /api/giftcards/regenerate` — AI Copilot regenerates headline / subline / background image via Emergent Claude sonnet-5 + Gemini nano-banana.
- Frontend: `/gift-cards/studio` gallery + drag-drop editor with live preview and inline AI regenerate buttons.
- Coupons page dropdown shows the studio via **Design gallery** button.

### OAuth Hub ✅ (P0)
- 6 providers: **Mailchimp · SendGrid · Facebook Pages · Instagram Business · LinkedIn · TikTok**.
- OAuth 2.0 flow: `GET /api/oauth/{provider}/start` → provider consent → `GET /api/oauth/callback` → tokens stored **Fernet-encrypted at rest** in `oauth_tokens` collection.
- API-key mode (SendGrid): `POST /api/oauth/{provider}/connect` with `{api_key}` — also encrypted.
- `GET /api/oauth/providers` lists configured status per provider; `GET /api/oauth/tokens` returns previews only (no plaintext); `DELETE /api/oauth/{provider}` revokes.
- `POST /api/oauth/{provider}/publish` — queues social posts (worker for real provider delivery = future work).
- OAuth state tokens auto-expire via **10-minute TTL index**.
- Frontend: /integrations `OAuthConnector` cards with real Connect/Disconnect buttons + API-key dialog for SendGrid.

### Funnel Builder ✅ (P0)
- **6 luxury templates**: Diamond · Champagne · Noir · Emerald · Rosé · Electric.
- Block types: `hero · coupon · giftcard · cta · features · testimonial · faq · heading · paragraph`.
- Full CRUD: `POST/GET/PUT/DELETE /api/funnels/*`, `POST /api/funnels/{id}/publish`.
- **Custom domain publishing**: `POST /api/funnels/{id}/domain` returns CNAME + TXT verification records; `POST /api/funnels/{id}/verify-domain` does DNS TXT lookup (now correctly handles multi-string records).
- **Public renderer**: `/api/public/f/{slug}` hydrates coupon (workspace-scoped for tenant isolation) + gift-card blocks and streams the full theme + block tree.
- Frontend: `/funnels` list + `/funnels/{id}/edit` block editor + `/f/{slug}` public renderer.

### Testing (iter-9)
- **Backend 34/34 pytest passed** in 15.6s. Frontend **10/10 flows passed**. Zero critical bugs. Verified LLM regeneration returns real Claude output (headline: 65 chars, subline: 78 chars).

### Post-testing hardenings applied
- OAuth tokens + API keys are now **Fernet-encrypted at rest** (same helper as POS secrets).
- Fixed broken DNS TXT parsing (`for _ in [0]` generator was a no-op) — now correctly handles multi-string TXT records.
- Public funnel coupon hydration is **workspace-scoped** to prevent cross-tenant coupon leaks.
- Removed duplicate `cfg = PROVIDERS.get(provider)` dead code in oauth callback.
- `oauth_states` collection has a 10-minute TTL index — unbounded state tokens no longer accumulate.

## Backlog (P1)
1. **Deep server.py router split** — Extract auth · coupons · campaigns · pos-webhooks · journeys · ai-copy · analytics · exports · embed · customers · admin · library · api-keys from server.py (currently ~2777 lines) into `/routers/*`.
2. **Real OAuth publishing** — Wire the real Facebook Graph, Instagram Graph, LinkedIn REST, TikTok Content Posting, and Mailchimp Campaigns POSTs behind `POST /api/oauth/{provider}/publish`; today it queues the intent only.
3. **Per-workspace LLM rate limit** — Protect EMERGENT_LLM_KEY budget from runaway UI button-mash on regenerate.
4. **Image_bg via /uploads** — Return `/api/uploads/{id}` URL instead of inline base64 for AI-generated gift-card backgrounds.
5. **Funnel list `?summary=true`** — Drop the heavy `blocks` array from list responses at scale.
6. **Payment providers Phase 4** — PayPal + Razorpay + Paystack live integrations for regions where Stripe is limited.


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
