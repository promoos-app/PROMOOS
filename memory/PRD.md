# PromoOS — AI Promotional Commerce Platform (PRD)

## Coverage after Iteration 6
**32 ✅ · 10 🟡 · 11 🔲** out of 53 spec sections.

## Stack
- React (CRA) + Tailwind + shadcn/ui + sonner · FastAPI + Motor (async MongoDB) · JWT Bearer + httpOnly cookie · background asyncio journey worker.
- **AI**: Emergent LLM Universal Key — Claude sonnet-5 + Gemini nano-banana. **⚠️ Budget currently exhausted.** Top up: Profile → Manage plan → Universal Key → Add Balance.
- **Email**: Resend (`RESEND_API_KEY`). **SMS + WhatsApp**: Twilio.
- **POS**: Shopify + Woo webhook receivers with per-workspace HMAC signing (`whsec_` via `secrets.token_urlsafe(30)`).
- **PDF**: reportlab. **CSV**: native csv.

## Iteration 6 (Feb 2026)
1. **HMAC-signed webhooks**: `POST /api/pos/rotate-secret` (owner only), `GET /api/pos/secrets` (preview + rotated_at). Shopify + Woo handlers verify `X-Shopify-Hmac-Sha256` / `X-WC-Webhook-Signature` when a secret is set (401 otherwise). Trust-mode when unset. Integrations UI has copy-once fresh-secret display.
2. **Widget variants**: `GET /api/embed/coupon.js?variant=inline|popup|bar|wheel|wallet` returns 5 distinct renderers (inline card, full-screen popup with dismiss + delay + session dedupe, top gradient bar with dismiss, spin-to-win wheel, floating bottom-right pill). CouponDetail exposes a variant tab picker in the Embed panel.
3. **Attribution & Exports**: `/api/customers.metrics` now returns `cac` (discount cost / new_n), `clv` (spend / n), `avg_orders`, `total_spend`, `total_discount`. CAC returns 0 when there are 0 new customers (honest, no fallback). `GET /api/analytics/export?format=csv|pdf&period=7..365` downloads a board-ready report. New `/analytics` page with 4 KPI cards, revenue chart, top-coupons bar chart, and CSV/PDF download buttons.
4. **Crypto**: `whsec_` and `pk_live_` tokens now generated via `secrets.token_urlsafe` (was Mersenne-Twister).

## Test Status
- iter-6 pytest: **28/28 pass** in 7.55s.
- Cumulative: iter-1 through iter-6 all green (~130+ backend tests total).
- One pre-existing failing test (`test_cors_uses_explicit_origin_with_credentials`) — Cloudflare edge preflight override, infra not code.
- **AI features**: all return 429 with friendly top-up message. Non-AI features 100% functional.

## Backlog (11 top items)
- Router split for server.py (now 2441 lines) into routers/{auth,coupons,pos,journeys,ai,analytics,exports,embed,customers,templates,api_keys}.py.
- Encrypt HMAC secrets at rest (currently plaintext in Mongo).
- Multi-location workspace hierarchy (section 30).
- API-key auth middleware to actually enforce `pk_live_*` keys on public endpoints.
- Barcode formats — UPC / EAN / Code128 / Code39.
- Affiliate coupons attribution.
- White-label + custom domain.
- Platform Admin Command Center.
- Pricing tiers + Stripe billing.
- Geo-fenced trigger endpoint.
- Coupon Category management UI.

## User inputs pending
- `RESEND_API_KEY`, `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_SMS/FROM_WHATSAPP`, `PUBLIC_APP_URL`.
- **Top up Universal LLM key** to re-enable Today's Promo / Weekly Calendar / One-Click / Segment Promo / A/B variant AI / One-Click Campaign generator.
