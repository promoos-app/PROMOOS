# PromoOS — AI Promotional Commerce Platform (PRD)

## Original Problem Statement
Build a web-based SaaS "Promotional Operating System" to create, design, publish, and track coupons, gift cards, and campaigns. MVP covers Phases 1–3 (Auth, Master Dashboard, Coupon Management, AI Copilot) with the user-requested addition of email sending and demo data seeding.

## Stack
- **Frontend**: React (CRA), Tailwind, shadcn/ui, sonner. Dark-first design system.
- **Backend**: FastAPI + Motor (async MongoDB). Bearer JWT + httpOnly cookie (dual-mode).
- **AI**: Emergent LLM Key — Claude Sonnet 5 (copy), Gemini Nano Banana `gemini-3.1-flash-image-preview` (images).
- **Email**: Resend (`resend>=2.0.0`). Requires `RESEND_API_KEY` in `backend/.env` to send; graceful 400 when unset.
- **QR**: `qrcode` (server-side, embedded as data URI).

## Personas
- **Owner** — full access.
- **Marketer** — create/update coupons, run AI, send emails.
- **Viewer** — read-only (403 on writes).

## What's Implemented

### Iteration 1 (Feb 2026)
- Auth: register/login/me, JWT Bearer + httpOnly `access_token` cookie, bcrypt `$2b$`, brute-force lockout (5/15min per email → 429), origin-echo CORS.
- Multi-tenant workspace isolation. Seed workspace **Acme Swimwear Co.** with 3 roles + 7 sample coupons + realistic redemptions.
- Coupons: CRUD, state machine, validate/redeem with fraud guard, bulk one-time codes, server-side QR.
- Redeem discount math for percentage/flash_sale/seasonal/vip/first_time/birthday/referral (%), fixed (capped), bogo (50%), free_shipping (0).
- AI Copilot: `POST /api/ai/copy` (Claude → structured JSON), `POST /api/ai/image` (Nano Banana → base64 promo visual).
- Dashboard & analytics: `/api/dashboard/stats`, `/api/analytics/timeseries` (14-day).
- Email (Resend): `POST /api/coupons/{id}/send-email` with branded HTML template; "Send by Email" panel on coupon detail.

### Iteration 2 (Feb 2026) — Growth features
- **Public coupon page** at `/c/:code` (standalone, no auth): brand pill, hero, dashed-border code, one-tap copy, redeem CTA, QR, terms. Records impression on view.
- **Embed widget**: `GET /api/embed/coupon.js` — origin-echoing JS. Any site pastes `<script async src=".../api/embed/coupon.js" data-promoos-code="CODE"></script>` and gets a branded coupon card with copy + CTA. UI in coupon detail to grab the snippet.
- **Referral loops**: Rules toggle (`referral_enabled` + `referral_credit_pct`, default 10). Public page has "Share & earn N%" panel that generates a personal `?ref=<token>` link. Public redeem accrues `stats.referral_credit` and logs to `referrals`. Coupon detail shows a "Referral Program" panel with visits/redemptions/credit + top-referrers leaderboard.

## Test Credentials
See `/app/memory/test_credentials.md`.

## Test Status
- Backend pytest — iteration 2:
  - `/app/backend/tests/test_growth_features.py` — **20/20 pass** (new suite by testing agent).
  - `/app/backend/tests/backend_test.py` — 30/31 pass (1 known: Cloudflare edge overrides preflight CORS in preview; passes locally; brute-force test can be flaky across runs — flush `db.login_attempts` between runs).
- Real AI (Claude + Gemini) verified in iteration 1, unchanged.

## Backlog

### P0 — awaiting user
- **Resend API key** — paste `RESEND_API_KEY=re_...` into `backend/.env` (get from resend.com/api-keys). Update `SENDER_EMAIL` to a verified domain for production.

### P1 — Phase 4 continued
- SMS / WhatsApp via Twilio.
- Impression dedupe per session/IP (currently every request bumps stats.impressions).
- Public referral leaderboard aggregation to show `stats.referral_credit` on coupon detail summary card.

### P2 — Phase 5: Customers, Loyalty & Referrals
- Customer CRM + AI segmentation.
- Points / tiers, gift cards.
- Persistent referrer accounts (map ref token → verified email, redeem credit at checkout).

### P3 — Phase 6: Analytics & Optimization
- A/B testing for headlines/CTAs, exportable CSV/PDF reports.

### P4 — Phase 7: Platform & Enterprise
- Universal webhooks, white-label custom domains, agency console.

### Code-review notes from iteration_2
- Consider role-gating `/api/coupons/{cid}/referrals` (currently any workspace user).
- Hash/validate `customer` field on public redeem (currently free-form string, trimmed to 120 chars).
