# PromoOS — AI Promotional Commerce Platform (PRD)

## Original Problem Statement
Full 53-section product spec. User asked to "Build everything according to orders" then requested Journey Runtime + POS Connectors. After iteration 5, coverage is **30/53 ✅ · 12/53 🟡 · 11/53 🔲**.

## Stack
- **Frontend**: React (CRA) + Tailwind + shadcn/ui + sonner.
- **Backend**: FastAPI + Motor (async MongoDB), JWT Bearer + httpOnly cookie, background asyncio worker for journey runtime.
- **AI**: Emergent LLM Universal Key — Claude sonnet-5 + Gemini nano-banana. **⚠️ Budget currently exhausted — top up at Profile → Manage plan → Universal Key → Add Balance to re-enable AI features.**
- **Email**: Resend. **SMS + WhatsApp**: Twilio. Both graceful when unset.
- **POS**: Shopify + WooCommerce webhook receivers, `/pos/snippets` for install instructions.

## Personas
Owner · Marketer · Viewer.

## Iteration 5 (Feb 2026) — Journey Runtime + POS Connectors
- **Journey Runtime**: `journey_worker` asyncio task ticks every 30s, processes any due `journey_runs`. Step types: `wait` (schedules next_at), `send_email` (Resend when configured, otherwise logged skip), `send_sms` (Twilio when configured), `send_coupon` (auto-creates a JRN- code with usage_limit=1 and emails it if possible). `_fire_trigger` auto-enrolls the customer on any active `trigger='purchase'` journey when they redeem publicly. New endpoints: `POST /api/journeys/{id}/enroll`, `GET /api/journeys/{id}/runs`. UI: Enroll panel + auto-refreshing recent runs feed on every journey card in `/campaigns`.
- **POS Connectors**: `POST /api/public/coupons/validate` (no-auth preview + end_date guard), `POST /api/pos/{workspace_id}/shopify` (accepts `orders/create` JSON; matches `X-PromoOS-Code` header OR `note_attributes` promoos entry), `POST /api/pos/{workspace_id}/woocommerce` (accepts `order.created` JSON; matches `meta_data.promoos` OR `coupon_lines[].code` fallback), `GET /api/pos/snippets` returns fully-qualified webhook URLs + step-by-step install instructions. Integrations page renders both connector cards with copyable URLs and a generic-curl block for any other system.

## Test Status
- **iter-5 pytest: 24/24 pass** in 58.6s (real 60-95s worker-tick test included).
- **iter-4 pytest: 33/33 pass**. All earlier suites still green.
- 1 pre-existing failing test (`test_cors_uses_explicit_origin_with_credentials`) — Cloudflare edge preflight override, infra not code.
- LLM budget exhausted: AI endpoints return 429 with friendly top-up message; every non-AI feature remains functional.

## Backlog (top 12 remaining)
1. HMAC signature verification for Shopify + Woo webhooks (per-workspace shared secret) — currently trust-based.
2. Multi-location hierarchy.
3. API-key auth middleware to actually enforce `pk_live_*` keys on public endpoints.
4. Widget variants — popup / bar / wheel / grid / carousel / wallet.
5. Barcode formats — UPC / EAN / Code128 / Code39.
6. Full CAC/CLV attribution + CSV/PDF exports.
7. Affiliate coupons attribution.
8. White-label + custom domain.
9. Platform Admin Command Center.
10. Pricing tiers + Stripe billing.
11. Geo-fenced trigger endpoint.
12. `server.py` router split (2100 lines).

## User inputs pending
- `RESEND_API_KEY`, `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_SMS/FROM_WHATSAPP`, `PUBLIC_APP_URL`.
- **Top up Universal LLM key** to re-enable all AI endpoints.
