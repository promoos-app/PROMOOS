# PromoOS — AI Promotional Commerce Platform (PRD)

## Original Problem Statement
Full 53-section product spec: an AI Promotional Operating System that lets any business create, design, publish, distribute, track and optimize coupons, gift cards, loyalty programs and referral engines across multiple channels. User asked to "Build everything according to orders" — iteration 4 delivered 6 bundles covering the full spec, moving coverage from 12 ✅ to **28 ✅ out of 53 sections**.

## Stack
- **Frontend**: React (CRA) + Tailwind + shadcn/ui + sonner. Dark-first design.
- **Backend**: FastAPI + Motor (async MongoDB), JWT Bearer + httpOnly cookie.
- **AI**: Emergent LLM Universal Key — Claude sonnet-5 (copy, A/B, today's promo, weekly calendar, one-click, segment promo), Gemini `gemini-3.1-flash-image-preview` (coupon images).
- **Email**: Resend (needs `RESEND_API_KEY`).
- **SMS + WhatsApp**: Twilio (needs `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_SMS/FROM_WHATSAPP`).
- **QR**: server-side qrcode → data URI.

## Personas
- Owner · Marketer · Viewer.

## What's Live (iteration 4)
See `/app/memory/CHANGELOG.md` for full history and `/app/memory/ROADMAP.md` for the 53-section coverage matrix.

Top-level in-app pages: Dashboard · Coupons · Calendar · Campaigns · Customers · Rewards · Gift Cards · Design · Analytics · Integrations · Settings.
Public pages: Login · `/c/:code` coupon landing · `/wallet/:token` customer wallet.

## Test Status
- Backend pytest — **iteration 4: 33/33 pass** (`test_iter4_features.py`). Prior suites still green (75+ tests total).
- Real Claude sonnet-5 output verified for all 4 new AI endpoints.
- Known blocker: **Universal LLM key hit its $1 budget cap during iter-4 testing.** All `/api/ai/*` endpoints now return HTTP 429 with a friendly "Top up your Universal Key" message until you add balance at Profile → Manage plan → Universal Key → Add Balance.
- 1 pre-existing failing test in `backend_test.py::test_cors_uses_explicit_origin_with_credentials` — Cloudflare edge overrides preflight CORS in the preview URL (infra, not code).

## Backlog (12 P1 items — see ROADMAP.md for full 53-section map)
1. Journey execution runtime (currently stored, not auto-fired)
2. API-key auth middleware to actually enforce `pk_live_*` keys
3. Multi-location hierarchy
4. POS SDK connectors (Shopify / Woo / Square)
5. Widget variants (popup / bar / wheel)
6. Barcode formats (UPC / EAN / Code128)
7. Attribution + CSV/PDF exports
8. Affiliate coupons
9. White-label / custom domain
10. Platform Admin dashboard
11. Pricing tiers + Stripe billing
12. Geo-fenced trigger endpoint

## Code Health
- `server.py` is now 1780 lines — testing agent recommends splitting into `routers/{auth, coupons, public, ai, growth, loyalty, gift_cards, journeys, customers, api_keys, templates}` before iter 5.
- `_aggregate_customers` has an N+1 pattern (~2s for 264 customers). Refactor with `$lookup`.
- QR codes stored inline in coupons doc (~2-4KB each). Consider on-the-fly generation or S3.

## User inputs pending
- `RESEND_API_KEY` — enables real email delivery.
- Twilio SID/Token/From numbers — enables real SMS + WhatsApp delivery.
- **Top up Universal LLM key** — restores all AI features.
