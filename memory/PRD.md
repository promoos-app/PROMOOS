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
- **Viewer** — read-only (403 "Viewers have read-only access" on writes).

## What's Implemented (Feb 2026)

### Auth & Multi-tenancy
- Register / login / me (JWT Bearer + httpOnly `access_token` cookie).
- Bcrypt (`$2b$`) password hashes.
- Brute-force lockout: 5 failed logins/15 min per email → HTTP 429.
- CORS reflects incoming Origin with credentials.
- Multi-tenant workspace isolation on every route.
- Seeded workspace **Acme Swimwear Co.** with 3 roles + 7 sample coupons + realistic redemptions.

### Coupons
- CRUD, state machine (`draft → scheduled → active → paused → expired → archived`).
- Validate & Redeem with duplicate-redemption fraud guard (5s → 429).
- Redeem discount math covers all types: `percentage/flash_sale/seasonal/vip/first_time/birthday/referral` → %, `fixed` → capped, `bogo` → 50%, `free_shipping` → 0-line-item.
- Bulk one-time code generation.
- Server-side QR code with client download.

### AI Copilot
- `POST /api/ai/copy` — Claude Sonnet 5 → structured JSON.
- `POST /api/ai/image` — Nano Banana → base64 promo visual.

### Email (Resend) — NEW this iteration
- `POST /api/coupons/{id}/send-email` — branded HTML template using workspace colors, code, CTA, terms.
- Non-blocking (`asyncio.to_thread`), logged to `email_events` collection.
- Frontend "Send by Email" panel on coupon detail.

### Dashboard & Analytics
- `/api/dashboard/stats`, `/api/analytics/timeseries` (14-day).

## Test Credentials
See `/app/memory/test_credentials.md`.

## Test Status
- Backend pytest: **30/31 pass**.
- 1 failing: `test_cors_uses_explicit_origin_with_credentials` — Cloudflare edge in the preview URL overrides preflight CORS headers. Passes locally on uvicorn. Doesn't affect app since frontend uses JWT Bearer.
- Real AI providers verified (Claude + Gemini).

## Backlog

### P0 — awaiting user
- **Resend API key** — paste `RESEND_API_KEY=re_...` into `backend/.env` (get from resend.com/api-keys). Point `SENDER_EMAIL` to a verified domain for prod.

### P1 — Phase 4: Distribution & Embed
- Public coupon landing pages (`/c/:code`).
- Embeddable JS widget snippet.
- SMS / WhatsApp via Twilio.

### P2 — Phase 5: Customers, Loyalty & Referrals
- Customer CRM + AI segmentation.
- Points / tiers, gift cards, referral trees.

### P3 — Phase 6: Analytics & Optimization
- A/B testing for headlines/CTAs, exportable CSV/PDF reports.

### P4 — Phase 7: Platform & Enterprise
- Universal webhooks, white-label custom domains, agency console.
