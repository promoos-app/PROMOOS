# PromoOS — CHANGELOG

## Iteration 4 (Feb 2026) — Six-bundle mega-ship
Ran through the full 53-section product spec and shipped every core surface across 6 bundles in one iteration.

### Bundle A — Autopilot & AI Command Center (sections 4, 5, 6, 38, 43, 50, 52)
- `PUT/GET /api/autopilot/config` — enabled, goal, max_discount, frequency, require_approval, brand_voice, audience (guardrails).
- `POST /api/ai/todays-promo` — Claude sonnet-5 reads workspace stats and drafts today's optimal promo with reasoning.
- `POST /api/ai/weekly-calendar` — 7-day promotional plan, per-day variety enforced.
- `POST /api/ai/one-click-campaign` — one prompt → coupon + email + SMS + WhatsApp + push + social + landing + ad copy.
- `POST /api/ai/one-click-campaign/approve` — persists coupon with campaign_assets.
- Dashboard "Today's AI Promo" widget, `/calendar` page, One-Click Campaign modal, Settings > Autopilot.

### Bundle B — Commerce (sections 10, 12, 20)
- Gift Cards: issue, list, redeem, public balance, branded delivery email via Resend.
- Store Credits: issue with reason enum, by-customer aggregation.
- Public `/wallet/:token` — customer sees their gift cards, store credit, loyalty points, tier, redemption history in one branded page.
- `/gift-cards` admin page + Wallet page.

### Bundle C — Campaign Journeys (sections 28)
- `POST /api/journeys` CRUD with trigger (signup / purchase / inactive_30d / birthday) + step chips (send_email / send_sms / send_coupon / wait).
- `/campaigns` page with enable/disable toggle + per-journey stats.

### Bundle D — Customer CRM + AI Segmentation (sections 21, 22, 23)
- `GET /api/customers` aggregates redemptions + loyalty + credits per customer and auto-segments into vip / frequent / regular / new / at_risk.
- `POST /api/ai/segment-promo` — Claude writes copy tuned to a specific segment.
- `/customers` page with segment chips, search, one-click segment promo generator.

### Bundle E — Template Marketplace + Design Studio (sections 8, 37)
- `GET /api/templates` — 6 starter aesthetics (Luxe Black, Neon Flash, Playful Candy, Minimal Mono, Holiday Warm, VIP Onyx).
- `POST /api/templates/apply` — applies palette to brand kit.
- `/design` gallery page.

### Bundle F — Platform (sections 32, 44)
- `POST/GET/POST revoke /api/api-keys` — owner-only key mint + list (preview only) + revoke, bcrypt-hashed at rest.
- `/integrations` page with connector cards for Resend / Twilio / Stripe / Shopify / WooCommerce / Square + public API key management.

### Testing
- **33/33 iter-4 pytest passed** (`test_iter4_features.py`, real Claude sonnet-5 outputs verified).
- Frontend: all data-testids present, all non-AI flows E2E green.
- Known blocker: Universal LLM key hit $1 budget cap during testing — 429 returned with clear top-up instructions. Fix applied.
- Also fixed: gift-card amount now quantized to 2 decimals + capped at $10,000.

## Iteration 3 (Feb 2026) — Twilio + A/B + Loyalty
See earlier entries.

## Iteration 2 (Feb 2026) — Growth (Public page, Embed widget, Referrals)
See earlier entries.

## Iteration 1 (Feb 2026) — MVP
See earlier entries.
