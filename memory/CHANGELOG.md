# PromoOS — CHANGELOG

## Iteration 19 (Feb 2026) — Funnel Builder scroll fix + Automations + Multi-step/A-B foundation + Gift Card checkout

### P0 BUG FIX: Funnel Builder dialog was unreachable ✅
- Reported: "Funnel Builder is absolutely static and not accessible. Cannot scroll to Funnel Page tabs."
- Root cause: with 19 templates in a 2-col grid, `DialogContent` had no `max-h` + `overflow-y-auto`, so both the lower template cards AND the "Create funnel" button sat below the visible fold at any normal viewport height.
- Fix: `DialogContent` → `max-h-[85vh] overflow-y-auto`; templates grid → `max-h-[52vh] overflow-y-auto pr-1`, expanded to 3 columns on `lg`.
- Testing agent verified live at 1440×900: dialog `clientHeight=706` (fits viewport), grid `scrollHeight=543` scrolls to expose all 19 cards, `funnel-tpl-info_page` clickable, `create-funnel-submit` in viewport (y=743..779) — funnel created successfully.
- Also fixed contrast on selected template card (was black-on-black for light-theme templates).

### Automations (Email Sequences) ✅ (P0 — user backlog)
- New `/sequences` page + full CRUD backend at `/api/sequences`.
- Trigger types: `optin`, `funnel_view`, `coupon_redeem`.
- Steps with `delay_hours`, `subject`, `body`. Enable/pause toggle. Lead-tag filter + optional funnel scoping.
- Opt-in submits automatically enroll matching sequences and schedule emails (`db.sequence_enrollments`).
- Sidebar link "Automations" added.

### Multi-Step Funnels + A/B Split Testing foundation ✅
- Funnel model now accepts optional `steps: [{id, name, slug_suffix, blocks: []}]` and `variants: [{id, name, weight, blocks: []}]` arrays alongside the flat `blocks[]`.
- Public `/api/public/f/{slug}?step=<slug_suffix>&variant=<id>&vb=<visitor_bucket>` picks the right page/variant and hydrates only that page's blocks.
- Deterministic weighted A/B selection by hashing the visitor bucket into the weighted pool — same visitor always sees the same variant unless variant weights change.
- Existing legacy funnels (no `steps`/`variants`) render exactly as before (fully backward compatible).

### Gift Card Purchase Flow ✅
- New `POST /api/public/giftcards/checkout` creates a Stripe Checkout Session for the gift-card amount + template. Metadata carries workspace_id, template_id, purchaser/recipient details.
- `GET /api/public/giftcards/order/{session_id}` polls Stripe; on paid, idempotently mints a real gift card (code `GC-XXXXXXXXXX`) and returns it.

### Testing
- Iter19 verification: **100% backend + 100% frontend** on the reported scroll bug + Sequences page + Public funnel regression.

---

## Iteration 18 (Feb 2026) — Complete funnel page types + Products upload + payment activation + regression fixes

### Merchant-facing feature completeness ✅ (P0 — user batch)
- **7 new funnel templates** to complete systeme.io parity — Sales Page, Order Form, Downsell, Inline Form, Popup Form, Link in Bio, Info Page. Combined with prior work the platform now ships **19 professional templates** covering the full launch/optin/webinar/sales/checkout/thank-you lifecycle.
- **Products page** at `/products` with full image upload via Emergent Object Storage (POST `/api/uploads`). Merchants can now upload product PNG/JPEG/WebP (≤5MB), set price/currency/stripe_price_id, and use products in Funnel product blocks. Sidebar link added.
- **Bulk unique codes** in the Coupon editor: `BulkCodesPanel` component with generate (count 1–500), select-all, per-row checkboxes, copy to clipboard, CSV export, and bulk delete. Backed by `POST /api/coupons/{cid}/bulk-codes`, `GET /api/coupons/{cid}/codes`, `POST /api/coupons/{cid}/codes/delete`.
- **Coupon Stripe payment link**: `payment_link` field on the coupon model → `/c/{code}` gains a prominent "Buy now with this discount" anchor when set (with `client_reference_id={code}` for reconciliation). Merchants sell + receive payments without leaving the platform.
- **X (Twitter) share fixed**: shares now use `https://x.com/intent/post` with URL-encoded params (was `twitter.com/intent/tweet` with raw text — silently failed on quotes/emojis). All 8 share platforms URL-encoded.

### Coupon discount now actually applied at Stripe checkout ✅ (P0 — reported revenue-loss defect)
- `POST /api/public/products/checkout` now computes the discount for the passed `coupon_code`, applies it to Stripe `line_item.unit_amount`, and records `original_amount`, `applied_discount`, `final_amount` on the order + Stripe metadata. Verified live: `VIPELITJRIXE` on $49 hoodie → **Stripe session amount_total = 3920 cents ($39.20)**.
- Coupon `publish/unpublish` endpoints now write both `state` and `status` (canonical + legacy). Publishing a coupon immediately makes it visible on `GET /api/public/coupons/{code}`.

### Auth flow polish ✅
- `/login?admin=1` routes superadmins straight to `/admin` on success; owners are told they need superadmin access. `?next=` query param supported. Login fields no longer prefill test credentials (production hygiene).
- `AuthContext.login/register` now return the user object so callers can inspect role.

### Products image URL contract fixed
- Frontend was double-prefixing `/api` on uploaded image URLs. `Products.js` now composes `${REACT_APP_BACKEND_URL}${data.url}`.

### Testing
- Iter18 verification: **100% backend (14/14 new + 7/7 auth playbook regression)**, **100% frontend Playwright**. Stripe session `line_item.unit_amount` verified end-to-end via `stripe.checkout.Session.retrieve`.

---

## Iteration 16 (Feb 2026) — Stripe payment links + Industrial funnel builder + WCAG contrast

### Stripe payment activation ✅ (P0 — user-provided links)
- Wired both hosted Stripe Payment Links so merchants can pay in one click:
  - **Basic** ($49/mo · 3-day trial) → `buy.stripe.com/5kQ28qcDSfMK3ni5MD2kw0f`
  - **Pro** ($79/mo · 3-day trial) → `buy.stripe.com/eVqfZg33igQO9LG5MD2kw0e`
- Backend `/billing/plans` returns each plan's `payment_link` alongside pricing metadata.
- Pricing page auto-injects `client_reference_id` (workspace) and `prefilled_email` (user email) into the Stripe URL so returning customers land back in the app with attribution intact.
- Legacy `/billing/checkout` session-mode flow still works for merchants who prefer server-driven webhook automation.

### Industrial funnel builder ✅ (P0 — systeme.io feature parity request)
- 9 new professional block types: **logo_bar, stats, guarantee, pricing_table, order_bump, upsell, optin, spacer, divider**.
- 5 new templates: **Lead Magnet Opt-in, Webinar Registration, Product Launch (long-form), Application Funnel, Thank You**.
- Opt-in lead capture: `POST /api/public/f/{slug}/optin` with dedupe (workspace + email + funnel), lead tagging, and analytics event emission. `GET /api/funnels/{fid}/leads` returns all captured leads (workspace-scoped, cross-tenant safe, is_deleted guarded).
- Analytics extended to track `optin_submit` events + `optin_conversion_pct`.
- Funnel editor palette re-categorized into **Layout / Conversion / Trust / Rewards** with per-block property editors for every new type (headline, text, price, tiers JSON, form fields JSON, logos list, height, etc.).

### WCAG contrast pass ✅ (P0 — accessibility)
- New `/lib/contrast.js` `getContrastText()` helper: computes actual WCAG ratios against both #FFFFFF and #0A0A0A and returns whichever wins. Guarantees ≥4.5:1 AA on all mid-tone brand colors (F97316 orange, 22C55E green, EAB308 amber, etc.). Verified live on `/c/VIPELITJRIXE` at 7.06:1 across all buttons + brand badge + discount placeholder.
- Applied to every dynamic-colored surface: PublicCoupon (copy/redeem/referral/brand-badge/discount-gradient), PublicFunnel Hero + CTA, PublicFunnelBlocks ProductBlock buy button, PublicFunnelIndustrial pricing_table/upsell/optin CTAs.

### Admin Portal footer fix ✅ (P0 — reported unresponsive)
- Site footer now context-aware: superadmins see a highlighted **"Admin Portal" pill** (`data-testid="footer-admin-portal"`) that links straight to `/admin`; plain owners see the legacy Admin sign-in link.

### Reviews Collection ✅ (P0)
- New `/reviews` page + CRUD API (create/list/patch/approve/soft-delete). Delete is now idempotent (`is_deleted` guard).
- Testimonial block gets a `source: "reviews"` mode that pulls approved workspace reviews live at public-render time (no JSON editing required).

### Per-block color overrides ✅ (P0)
- Every funnel block now has bg + accent color pickers in the editor (`data-testid="block-bg-color-<id>"`, `block-accent-color-<id>`). Coupon editor gained a full "Custom Design" panel (5 pickers) that persists a `design` object shipped in `/api/public/coupons/{code}`.

### Countdown picker ✅ (P0)
- Datetime input now shows the merchant's local time; internally converts to UTC ISO for storage; displays "UTC: …" preview for clarity.

### Regression / minor fixes (iter14+15)
- Coupon `PUT /api/coupons/{cid}` is now partial-update (only sets fields present in body — no more field-wiping).
- Restored VIPELITJRIXE to active/vip/20% off after the field-wipe.
- Public wallet no longer 500s on gift cards missing a `state` field.
- `/api/journeys` no longer leaks `workspace_id`.
- ProductBlock hides strike-through when discount is 0%.
- PublicCoupon redeem falls back to "Claim Offer" when the merchant leaves `cta` empty.
- Public funnel view tracker de-duped with `useRef` (React StrictMode-safe).
- Clipboard copy on coupon block wrapped in try/catch with `execCommand` fallback + "✓ Copied" feedback (no more red overlay in insecure/iframe contexts).

### Testing
- **Iter 16** verification: FIX #2 100% pass (18/18 block editors + persistence), FIX #1 initially at 60% due to a threshold-only luminance implementation; fixed to compute actual WCAG ratios → verified 7.06:1 live on all buttons and brand badge on `/c/VIPELITJRIXE`. 12/12 backend pytest pass.

---

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
