# PromoOS — CHANGELOG

## Iteration 14 (Feb 2026) — Storefront Template + Preview crash fixes

### Storefront funnel template ✅ (P0 — user-requested)
- New `storefront` template in `/api/funnels/templates` — full product landing page in one click.
- Block sequence: **hero → video → countdown → product → features → testimonial (3 reviews) → faq → cta**.
- Countdown auto-resolves `duration_hours` (default 72h) into a concrete `ends_at` at create time.
- Auto-attach on create: if the workspace has any product/coupon, the newest ones are wired into the product block automatically; otherwise renders as placeholders the merchant fills in.
- Multi-item testimonial variant with `items: [{quote, author, role, avatar_url}]` — placeholders now, structured enough to link to a real reviews collection later.
- Public renderer hydrates `block.props.product` (name / price / image / currency) and `block.props.coupon` (workspace-scoped, no tenant leaks) so the storefront looks like a real product page immediately.
- Product block now shows product image, name, description, price with strike-through discounted price if a coupon is attached, and a proper "Buy now" CTA (fallback: "Attach a product to enable checkout" when unattached).
- Video block auto-hides when its URL is empty (no more dead vertical gap on the storefront default).
- Frontend `computeDiscounted()` supports the platform's 23-type coupon taxonomy via an explicit allow-list (vip, frequent, regular, new, at_risk, flash, launch, loyalty, welcome, seasonal, percentage) + fixed-amount types.

### Preview crash fixes ✅ (P0 — reported)
- Fixed a real syntax error in `PublicFunnel.js` (missing closing brace on `ProductBlock`) that was blocking the entire preview build with "'import' and 'export' may only appear at the top level".
- Fixed a Babel `Maximum call stack size exceeded` triggered by the long `if (block.type === "…") return …` chain — refactored to a `REGISTRY` component map and split heavy components (`Countdown`, `ProductBlock`, `Testimonials`) into `PublicFunnelBlocks.js`.
- Fixed a critical hydration regression: `GET /api/public/f/{slug}` was projecting `workspace_id` **out** of the Mongo document before using it to scope the product/coupon lookups, so **no coupon block on any funnel had ever hydrated in this iteration**. Removed the projection, kept the `d.pop("workspace_id", None)` before return, so hydration works and no tenant data leaks.
- Cleaned up the dead `raise HTTPException(400, "Not found") if False else HTTPException(404, "Not found")` in `verify_domain`.

### Funnel editor upgrades ✅
- Product block: `<select>` of workspace products (`data-testid="block-product-select-<id>"`) instead of raw UUID input, plus a coupon dropdown.
- Testimonial block: when `items[]` is present, renders a JSON editor with a hint about linking to real reviews later; legacy quote/author form has a one-click "Convert to multi-review section" button.

### Testing
- **Iter 12** flagged 1 CRITICAL + 3 minor issues → **all fixed**.
- **Iter 13**: 15/15 backend pytest pass (`test_iter13_hydration.py`), including positive cross-tenant isolation with foreign-workspace product/coupon controls; 100% frontend flows pass (storefront render with $39.20 strike-through vs $49.00, video hidden when empty, /customers bulk-delete UI, /funnels editor).

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
