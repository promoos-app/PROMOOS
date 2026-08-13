# PromoOS — AI Promotional Commerce Platform (PRD)

## Coverage after Iteration 7
**36 ✅ · 8 🟡 · 9 🔲** out of 53 spec sections.

## Stack (unchanged)
React + Tailwind + shadcn/ui · FastAPI + Motor · JWT Bearer + httpOnly cookie · background asyncio journey worker · Fernet-encrypted webhook secrets at rest · Emergent LLM Universal Key (Claude sonnet-5 + Gemini nano-banana) · Resend · Twilio · reportlab (PDF) · cryptography.

## Iteration 7 (Feb 2026) — Ship Everything

### Security hardening
- **Webhook secrets encrypted at rest** with `cryptography.Fernet` (key derived from JWT_SECRET). Preview stored separately; plaintext only ever exists in RAM during verification.
- **`POST /api/v1/coupons/redeem`** requires `Authorization: Bearer pk_live_...`. Owner/marketer/viewer scoped by API-key `scopes: ["read","write"]`. Missing/invalid/revoked → 401. Missing scope → 403.
- **Suspended/deleted account block**: `/api/auth/login` returns 403 with clear reason.

### Full Admin Portal (superadmin only)
- **New role**: `superadmin` seeded on startup (`SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD`, defaults `superadmin@promoos.com` / `superadmin123`).
- **Endpoints**: `/api/admin/stats`, `/api/admin/users` (list + create), `/api/admin/users/{id}/{suspend|activate|restore}`, `DELETE /api/admin/users/{id}` (soft), `/api/admin/workspaces` (with per-workspace counts), `/api/admin/logs` (audit trail), `/api/admin/payments`.
- **Every write is audited** to `admin_logs` collection.
- **UI**: `/admin` page (client-side + backend gated to superadmin) with tabs Stats / Users / Workspaces / Payments / Audit Log; user rows expose Suspend / Activate / Restore / Delete action icons; sidebar Admin link only appears for superadmin role.

### Coupon Library (all 23 types)
- `GET /api/library/coupon-types` returns the full 23-item catalog with `id/name/cat/desc/default_value/audience`.
- 13 categories: Discount · Bundle · Perk · Acquisition · Retention · Growth · Lifecycle · Loyalty · Urgency · Geo · Campaign · Recurring · Attribution.
- **UI**: `/library` gallery with category filter chips + search + "Use this style" that jumps to `/coupons/new` with type/value/audience preset.

### Legal + Footer
- `/privacy` and `/terms` public routes with 8+ sections each.
- **Global footer** on every authenticated page and (compact) on `/login`: "© 2026 PromoOS. All rights reserved. A Division of Glorified Technology Solution (GTS)." + Privacy Policy + Terms of Use links.

### Testing
- **iter-7 pytest: 45/45 pass** in 11.5s.
- **All frontend flows verified**: superadmin sidebar filtering, /admin tabs, user lifecycle (create → suspend → activate → delete → restore), /library filter+search, /privacy + /terms rendering, footer everywhere.
- Zero critical, zero UI bugs.

## Backlog (P1)
1. Split `server.py` (2744 lines) into routers.
2. Dedicated `FERNET_KEY` env var so JWT_SECRET can rotate independently.
3. `verify_api_key` index by prefix instead of O(N) bcrypt scan.
4. Audit trail on `DELETE /api/pos/secret/{provider}`.
5. Multi-location workspace hierarchy.
6. Widget variants beyond current 5 (grid, carousel).
7. Barcode formats — UPC / EAN / Code128.
8. Affiliate coupons attribution.
9. Stripe billing wire-up for the /admin Payments tab.

## User inputs pending
- Top up Universal LLM key.
- `RESEND_API_KEY`, `TWILIO_ACCOUNT_SID/AUTH_TOKEN/FROM_SMS/FROM_WHATSAPP`, `PUBLIC_APP_URL`.
- Optional: `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` (change defaults for production).
