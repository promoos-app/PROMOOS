## Feb 2026 — Hotfix: OAuth providers unblocked with access-token fallback

- **Bug**: Mailchimp, Facebook, Instagram Business, LinkedIn, and TikTok cards showed a static "Configure ..._CLIENT_ID + ..._CLIENT_SECRET in backend/.env" message. Merchants couldn't connect without waiting on a platform-owner env change.
- **Fix (backend, `routers/oauth_hub.py`)**:
  - `POST /api/oauth/{provider}/connect` now accepts pasted access tokens for OAuth providers too (stored `mode: "access_token"` vs `"api_key"`).
  - `GET /api/oauth/providers` now returns `configured` (always true — user can always paste a token), `oauth_configured` (env-based, controls whether OAuth button appears), plus `key_hint` and `token_docs` link for every OAuth provider.
  - Added helpful token hints and docs URLs for Mailchimp, Facebook, Instagram, LinkedIn, TikTok (Meta Graph Explorer, LinkedIn Developer Portal, TikTok Developer docs).
- **Fix (frontend, `pages/Integrations.js`)**:
  - OAuth cards now render an always-available **Connect with access token** dialog (falls back to primary CTA when OAuth env isn't set).
  - When OAuth env IS set, the **Connect with OAuth** primary button appears above the token-paste fallback.
  - Each dialog surfaces the provider-specific token hint + a "How to get one →" link to the official docs page.
- Verified: Mailchimp + Facebook token-paste both persisted (`mode: access_token`). UI screenshot confirms all 5 providers render a live Connect button.


## Feb 2026 — Next Action Items shipped

### 👁️ Template Preview (Campaigns page)
- Every automation template card now has a **Preview** button (eye icon) next to *Install*. Opens a dialog listing each step in order: `wait` (hours), `send_email` (subject + body), `send_sms` (body), `send_coupon` (headline / description / discount).
- The dialog exposes a shortcut "Install this template" button that hands off to the existing apply flow.
- Data-testids: `journey-template-preview-{id}`, `journey-template-preview-dialog`, `journey-preview-step-{i}`, `journey-template-apply-from-preview-{id}`.

### 🖼️ Bulk Coupon Backgrounds (Coupons list)
- New endpoint `POST /api/coupons/bulk-background` (`{coupon_ids[], bg_image}`) — updates `design.bg_image` on every matched coupon in a single `update_many`. Verified: HTTP 200, `updated: N`.
- Coupons list: checkbox column + "select all visible" header checkbox. Selection > 0 renders a sticky-look bar with **Set background**. Dialog offers drag-drop / file picker / URL paste using the same `/api/uploads` object storage flow.
- Data-testids: `coupons-select-all`, `coupon-select-{id}`, `coupons-bulk-bar`, `coupons-bulk-bg-btn`, `coupons-bulk-bg-dialog`, `coupons-bulk-bg-dropzone`, `coupons-bulk-bg-file`, `coupons-bulk-bg-url`, `coupons-bulk-bg-apply`.

### 🔥 Hyperlink Heatmap (Funnel editor)
- Each block card in the funnel editor now shows a live click badge `<Link2/> {clicks} · {ctr}%` when the hyperlink analytics endpoint has data for that block. Full detail table still lives in the analytics section.
- Data-testid: `block-heatmap-{block_id}`.

### 📤 Preset Pack Export (Admin)
- New **Export** action on every pack row: builds a clean JSON payload matching the `POST /admin/preset-packs/import` schema (strips `id/created_by/etc.`) and triggers an in-browser download as `{slug}.preset-pack.json`. Agencies can now hand a pack to a partner with one click.
- Data-testid: `preset-pack-export-{id}`.


## Feb 2026 — Integrations Activated (17 new providers)

- All previously-static "Not Configured" cards on `/integrations` are now real, per-workspace **Connect with API key** flows via the existing `/api/oauth/{provider}/connect` pipeline (encrypted-at-rest with Fernet).
- Added 17 providers to `routers/oauth_hub.py` `PROVIDERS` dict with `category` and `key_hint`:
  - **Email**: Resend, ConvertKit, Brevo (Sendinblue), Postmark, Mailgun, AWS SES, Klaviyo.
  - **Social**: X (Twitter), YouTube, Pinterest, Threads, Snapchat Ads.
  - **Delivery**: Twilio, PayPal, Razorpay, Paystack, Telegram Bot.
- `GET /api/oauth/providers` now includes `category` + `key_hint`; the UI renders a placeholder + inline hint on each connect dialog.
- `Publish` button is now gated to `category==="social"` providers so email/delivery cards no longer expose an irrelevant action.
- Verified: 23 providers listed (9/9/5); Twilio connect + tokens list + disconnect all HTTP 200.
- Frontend: replaced every static `ConnectorCard` in the email/social/delivery grids with a live `OAuthConnector`. Data-testids for the new dialogs match the existing pattern: `connector-{id}`, `connect-{id}`, `api-key-input-{id}`, `api-key-submit-{id}`, `disconnect-{id}`.


## Feb 2026 — Uploader + Import + Link Analytics + Automation Templates

### 📤 Coupon Cover Uploader (`CouponEditor.js`)
- Drag-and-drop zone on the coupon design panel: drop any image → uploads to `/api/uploads` (Emergent object storage) → auto-sets `design.bg_image`.
- Fallback file picker button and existing URL input both preserved. Shows uploaded thumbnail + filename when a background is active. Data-testids: `coupon-bg-dropzone`, `coupon-bg-upload-btn`.

### 📥 Preset Pack Import (Admin)
- New endpoint `POST /api/admin/preset-packs/import` — parses a JSON blob, validates every preset has `key/label/prompt`, rejects duplicates, tags the record with `source: "import"`.
- Admin UI: new **Import JSON** button next to *New pack* opens a modal with a monospace textarea, a "Fill with sample" helper, and validation surfaced from the backend. Data-testids: `preset-pack-import-btn`, `preset-pack-import-textarea`, `preset-pack-import-submit`.
- Verified: valid payload returned `source: import`; invalid payload (missing prompt) returned HTTP 400 with the exact field error.

### 🔗 Hyperlink Analytics (Funnel editor)
- New endpoint `GET /api/funnels/{fid}/hyperlink-analytics` — aggregates `hyperlink_click` events grouped by `block_id`, joined with each block's `link_url` and `type`, sorted by clicks desc. Returns `{views, total_clicks, rows[]}` with per-row CTR%.
- Whitelisted `hyperlink_click` in `POST /public/f/{slug}/track` so the public renderer's clicks actually get recorded.
- Funnel editor renders a per-block table under storefront analytics (Block · Destination · Clicks · CTR). Data-testids: `hyperlink-analytics-panel`, `hyperlink-analytics-totals`, `hyperlink-row-{block_id}`.
- Verified: 3 tracked clicks on `b1` → aggregation shows 3 clicks, 300% CTR (1 view baseline).

### ⚡ Automation Templates (Campaigns page)
- New endpoints in `routers/journeys.py`:
  - `GET /api/journey-templates` — returns 3 built-in packs.
  - `POST /api/journey-templates/{tid}/apply` — clones the template into the workspace as an enabled journey, tagged `source: template:{tid}`.
- Templates shipped:
  1. **Welcome flow** (`signup`): email → wait 24h → 10% coupon.
  2. **Cart abandonment** (`inactive_30d`): wait 4h → email → wait 20h → 15% coupon.
  3. **Birthday reward** (`birthday`): email → 20% coupon.
- Campaigns page hero strip renders the 3 templates with a one-click **Install** button per card. Data-testids: `journey-templates-strip`, `journey-template-{id}`, `journey-template-apply-{id}`.
- Verified: template list returned all 3; applying "welcome" created a live journey.


## Feb 2026 — Wave 3: Router Split + Marketplace + Hyperlinks

### 🧹 Router Split Wave 3 — `server.py` 2589 → 2100 lines (−489)
- `routers/embed.py` — `/api/embed/coupon.js` (5 variants: inline, popup, bar, wheel, wallet).
- `routers/exports.py` — `/api/analytics/export?format=csv|pdf`.
- `routers/journeys.py` — full journey CRUD + `journey_worker` bg loop + `_fire_trigger` re-exported to `server.py` for `/coupons/redeem` and `/v1/coupons/redeem`.
- Verified: all three endpoints return HTTP 200 in place, journey worker restarts cleanly.

### 💳 Stripe Payment Link Webhook Fix
- `POST /api/stripe/webhook` now handles hosted Payment Link sessions from the Pricing page:
  - Falls back to `client_reference_id` when `metadata.workspace_id` is missing.
  - Infers `lookup_key` from `amount_total` against the PLANS table.
  - Tags upgrade with `subscription.source = "payment_link" | "checkout"` for downstream audit.
- Verified: synthetic `checkout.session.completed` payload with amount 7900 and workspace as `client_reference_id` upgraded the workspace to `pro_monthly` / `active`.

### 🎨 Coupon Studio — one-tap Style Presets
- Same 5 curated chips as gift cards: Champagne, Neon, Minimal, Botanical, Midnight.
- Reads pack presets from `/api/preset-packs?scope=coupon` and merges with built-ins.
- data-testids: `coupon-style-presets`, `coupon-preset-{key}`.

### 🏪 Preset Marketplace (Admin)
- New router `routers/preset_packs.py`:
  - `POST/GET/PUT/DELETE /api/admin/preset-packs` — superadmin CRUD.
  - `GET /api/preset-packs?scope=coupon|gift_card` — authenticated read of public packs (union: pack.scope in [scope, "both"]).
- New Admin tab **Preset Packs**: create pack (name, scope, is_public), inline preset rows (key/label/accent/prompt), edit/delete. Data-testids: `admin-tab-presets`, `admin-preset-packs`, `preset-pack-new-btn`, `preset-pack-save`, `preset-pack-row-{id}`.
- Both studios auto-hydrate published packs on mount; new custom presets appear alongside built-ins with a pack-name tooltip.
- Verified: full CRUD via curl + admin UI screenshot.

### 🔗 Universal Hyperlink System (Funnels)
- Every block (text, heading, paragraph, image, video, audio, product, cta, etc.) now supports `props.link_url` + optional `props.link_target` ("_blank" default, "_self" opt-in via checkbox).
- Editor: universal hyperlink row inserted at the top of every block card in `Funnels.js` (Link2 icon + URL input + "Same tab" toggle). Data-testids: `block-hyperlink-{id}`, `block-link-url-{id}`, `block-link-same-tab-{id}`.
- Public renderer: `PublicFunnel.js` `Block()` wraps `<Comp />` in an `<a>` when `link_url` is set. Emits `hyperlink_click` funnel event on click with the target `href` in `meta`.
- Verified: create/update funnel → public payload preserves `link_url` and `link_target`.


## Feb 2026 — Verified: Embed Snippet & Image Style Presets

### Embed Snippet — verified end-to-end
- Rendered the coupon `VIPELITJRIXE` on an external HTML page via `<script async src=".../api/embed/coupon.js" data-promoos-code="…"></script>`.
- Browser test confirmed: card renders, headline/description/code visible, Copy button reactive, `/api/public/coupons/{code}` returns full brand + coupon payload.
- No code changes required — endpoint at `server.py:834` (`GET /embed/coupon.js`) supports 5 variants (inline, popup, bar, wheel, wallet).

### Gift Card AI Style Presets (`GiftCardStudio.js`)
- Added 5 one-tap style chips under the Background section: **Champagne**, **Neon**, **Minimal**, **Botanical**, **Midnight**.
- Each chip stores a curated prompt + accent color. Clicking calls `POST /api/giftcards/regenerate` with `field="image_bg"` and the preset's prompt, then swaps the card accent to the preset's palette.
- No prompt writing required. Extended `regen()` signature to accept an optional `promptOverride` (kept fully backwards-compatible with the existing `AI regenerate` and `AI generate image` buttons).
- data-testid: `gc-style-presets`, `preset-champagne`, `preset-neon`, `preset-minimal`, `preset-botanical`, `preset-midnight`.


## Feb 2026 — Hotfix: Gift Card AI Image (Cloudflare 502)
- **Bug**: `/api/giftcards/regenerate` with `field: "image_bg"` returned Cloudflare 502 (invalid/incomplete upstream response). Local backend showed `HTTPException(502): emergentintegrations not installed: No module named 'emergentintegrations.llm.googleai'`.
- **Root cause**: `routers/giftcards.py` imported the removed `GeminiImageGeneration` class + `gemini-2.5-flash-image` model. In the installed `emergentintegrations 0.2.0`, the `googleai` submodule does not exist.
- **Fix**: Switched to the canonical multimodal pattern used by `/api/ai/image`: `LlmChat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])` + `send_message_multimodal_response(...)`. Returns proper `data:{mime_type};base64,{data}` URL.
- **Verified**: HTTP 200, ~750KB image, ~11s response, no more 502.
- **File**: `/app/backend/routers/giftcards.py` (lines ~222–248).


# PromoOS — CHANGELOG

## Iteration 21 (Feb 2026) — Multi-Step Editor UI + A/B Dashboard + Footer block + Currency dropdown + Coupon graphics

### Multi-Step Funnel Editor UI ✅ (P0 — user request)
- `Funnels.js` FunnelEditor gained a **surface tab bar** (`data-testid="funnel-surface-tabs"`) with tabs for the main page + each step + each A/B variant. Merchants can click to switch which surface they're editing; `currentBlocks()`/`setCurrentBlocks()` route all block edits (add/move/remove/property changes) to the active surface.
- Steps CRUD: `tab-add-step` (renames auto-slug), `tab-step-name-<id>`, `tab-step-remove-<id>`, up/down reorder buttons.
- Save persists `steps[]` + `variants[]` to `PUT /api/funnels/{id}`.
- Public `/f/{slug}` sticky top nav (`funnel-step-nav`) renders **Main + all steps** so the merchant's main page stays reachable after adding steps (fix from testing iter21).

### A/B Test Dashboard ✅ (P0)
- `tab-add-variant` clones the **active surface** into a new variant (context-preserving) and switches to it. `promoteVariant` promotes the winning variant to main and clears variants.
- Per-variant analytics panel (`funnel-variants-analytics`) shows conversion % per variant + Winner badge (`variant-winning-badge`) once any variant has ≥20 views. Backend `/api/funnels/{fid}/variants-analytics` aggregates events by `variant_id`.
- Variant selection is scoped to the main surface — never overrides step blocks (precedence fix from iter21).

### Funnel Footer Block ✅ (P0)
- New `footer` block type with fields: brand, address, phone, email, privacy_url, terms_url, cookies_url, copyright_extra. Public renders a 3-column footer with unsubscribe capture (`footer-unsub-email` + `footer-unsub-btn` → tracks event `cta_click block_type=footer_unsubscribe`). Auto-injects year.

### 40-currency Product dropdown ✅ (P0)
- `product-currency-select` covers USD/EUR/GBP/CAD/AUD/JPY/CHF/INR/AED/SAR/SGD/HKD/MXN/BRL/ZAR/NGN/KES/PLN/CZK/HUF/TRY/RUB/THB/IDR/PHP/MYR/VND/KRW/CNY/TWD/ILS/EGP/ARS/CLP/COP/PEN/NOK/DKK/SEK/NZD.
- New `fmtMoney(amount, currency)` helper renders proper symbols/positions per currency (€29.50, £29.50, ¥4900 for zero-decimal, ₹29.50, etc.). Applied to Products page + PublicFunnel product block.

### Coupon Custom Design: Background Graphics ✅ (P0)
- `coupon-design-bg_image` URL input on the Custom Design panel + 4 preset preview buttons (Confetti / Neon / Marble / Sunset). Backend `CouponDesign.bg_image` field persists and returns in `/api/public/coupons/{code}`.

### Sequence Delivery via Resend ✅ (P0 — from iter19 backlog)
- `iter19.py` gained `deliver_due_sequence_emails()` + a 60s background loop (started from `server.py` startup). Each due schedule step sends via Resend, marks `sent`/`failed` with `resend_id`, and completes the enrollment when all steps land.
- Manual trigger: `POST /api/sequences/deliver-now` (auth required).

### Gift Card Buy Button ✅ (P0 — from iter19 backlog)
- `PublicFunnel` GiftCardBlock now renders an amount + email form under the card with `giftcard-buy-btn` → hits `POST /api/public/giftcards/checkout`. Success page polling at `/api/public/giftcards/order/{session_id}` mints the code idempotently.

### Testing
- **Iter20**: 5/5 P0 items 100% + 3 targeted follow-ups. **Iter21**: 11/11 backend + 3/3 frontend fixes verified. Currency localization, main-page reachability, variant clone context — all confirmed. Precedence bug fixed post-verification.

---

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
