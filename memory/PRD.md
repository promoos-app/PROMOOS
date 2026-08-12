# PromoOS — AI Promotional Commerce Platform (PRD)

## Original Problem Statement
Build a web-based SaaS "Promotional Operating System" (52-module spec) to create, design, publish, and track coupons, gift cards, and campaigns. User scoped MVP to Phases 1-3 (Auth, Master Dashboard, Coupon Management, AI Copilot) with explicit additions of email/SMS/WhatsApp delivery, A/B test copy, loyalty points, referrals, embed widget, and demo data seeding.

## Stack
- **Frontend**: React (CRA), Tailwind, shadcn/ui, sonner. Dark-first design system.
- **Backend**: FastAPI + Motor (async MongoDB). Bearer JWT + httpOnly cookie.
- **AI**: Emergent LLM Key — Claude sonnet-5 (copy + A/B variants), Gemini `gemini-3.1-flash-image-preview` (images).
- **Email**: Resend (`RESEND_API_KEY` — graceful 400 when empty).
- **SMS/WhatsApp**: Twilio (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_SMS`, `TWILIO_FROM_WHATSAPP` — graceful 400 when empty).
- **QR**: `qrcode` (server-side, embedded as data URI).

## Personas
- **Owner** — full access.
- **Marketer** — create/update coupons, run AI, send campaigns.
- **Viewer** — read-only (403 on writes).

## Feature summary — see `CHANGELOG.md` for full history, `ROADMAP.md` for phase-by-phase mapping of all 52 PDF modules.

Shipped so far (Feb 2026):
- Multi-tenant auth (JWT Bearer + httpOnly cookie, bcrypt, brute-force lockout, origin-echo CORS).
- Coupons: CRUD, state machine, validate/redeem (all discount types + 5-sec fraud guard), bulk one-time codes, QR.
- AI Copy (Claude) + AI Image (Gemini nano-banana) + AI A/B Test.
- Dashboard KPIs + 14-day timeseries.
- Email (Resend), SMS + WhatsApp (Twilio) — all graceful when creds absent.
- Public `/c/:code` landing page + copy-paste `/api/embed/coupon.js` widget.
- Referral loops (share-to-earn with leaderboard).
- Loyalty program (points-per-$, configurable tiers, auto-tier on redeem).
- Seed: **Acme Swimwear Co.** with owner/marketer/viewer + 7 sample coupons.

## Test Status (as of iteration 3)
- Backend pytest total: **75+/76 pass** across 3 test files.
  - `tests/test_iter3_features.py` 25/25 (Twilio + A/B + Loyalty).
  - `tests/test_growth_features.py` 20/20 (public page + embed + referrals).
  - `tests/backend_test.py` 30/31 (1 known Cloudflare-edge CORS preflight override).
- Real AI providers (Claude + Gemini) verified in every iteration.
- No mocked APIs. Twilio + Resend are LIVE when creds are set; otherwise both fail with a friendly "not configured" 400.

## Test Credentials
See `/app/memory/test_credentials.md`.

## Backlog Highlights
- **User inputs pending**: Resend key, Twilio SID/token + SMS/WhatsApp numbers, `PUBLIC_APP_URL` (for absolute links in messages).
- **Next natural features** (from ROADMAP.md): Points-redemption at checkout, Gift Cards, Customer CRM, CSV/PDF exports, Webhooks + Public API.
- **Code health**: `server.py` is 1147 lines and should be split into routers (`auth`, `coupons`, `public`, `growth`, `loyalty`, `ai`) before adding another major feature.
