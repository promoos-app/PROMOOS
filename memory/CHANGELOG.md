# PromoOS — CHANGELOG

## Iteration 3 (Feb 2026) — Twilio + A/B + Loyalty
- **Twilio SMS + WhatsApp** delivery. `POST /api/coupons/{id}/send-message` with `channel: sms | whatsapp`. Frontend adds a channel-tab selector on the coupon detail. Graceful 400 when TWILIO creds are empty.
- **AI A/B Test Copy**. `POST /api/coupons/{id}/experiments` uses Claude sonnet-5 to generate N (2-5) distinct variants, deterministic per-visitor bucketing on the public page, per-variant impression/redemption tracking, `POST /api/experiments/{id}/promote` (specific or auto by CVR with count fallback). Frontend A/B panel on coupon detail with per-variant stats and promote actions.
- **Loyalty Points + Tiers**. `PUT /api/workspace/loyalty` for config (enabled, points_per_dollar, tiers). Public redeem now credits points to the customer identifier and computes tier. New `/rewards` page with stat cards, config form (Bronze/Silver/Gold/Platinum default), and top-members table.
- Backend: 25/25 new pytest pass (`test_iter3_features.py`). Regression suites all green.

## Iteration 2 (Feb 2026) — Growth
- **Public coupon landing** `/c/:code`.
- **Embed widget** `/api/embed/coupon.js`.
- **Referral loops** with credit accrual + leaderboard.
- Backend: 20/20 new pytest pass (`test_growth_features.py`).

## Iteration 1 (Feb 2026) — MVP
- Multi-tenant auth (JWT Bearer + httpOnly cookie, bcrypt, brute-force lockout).
- Coupon CRUD + state machine + validate/redeem with fraud guard + bulk one-time codes + server-side QR.
- AI Copilot: Claude sonnet-5 copy + Gemini nano-banana images.
- Dashboard + analytics (KPIs + 14-day timeseries).
- Email (Resend) with branded HTML template.
- Seed workspace **Acme Swimwear Co.** with 3 roles + 7 coupons + realistic redemptions.
- Backend: 30/31 pass (1 known Cloudflare edge CORS preflight override — infra, not code).
