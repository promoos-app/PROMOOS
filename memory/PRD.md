# PromoOS — AI Promotional Commerce Platform (PRD)

## Original Problem Statement
AI-powered "Promotional Operating System" for businesses to create, design, publish, distribute, track, and optimize coupons, gift cards, loyalty & referral campaigns from one command center. MVP scope = Phases 1–3.

## Architecture
- **Frontend:** React (JS) + Tailwind + shadcn/ui + Recharts + React Query. Dark-first "Command Center" UI (Linear + Stripe inspired), Cabinet Grotesk / Satoshi / JetBrains Mono. Token auth via localStorage (`promoos_token`).
- **Backend:** FastAPI async, JWT Bearer auth, role gating (owner/marketer/viewer), multi-tenant via `workspace_id` scoping.
- **DB:** MongoDB — users, workspaces, coupons, redemptions. UUID string IDs (no ObjectId).
- **AI:** Claude `claude-sonnet-5` (copy) + Gemini `gemini-3.1-flash-image-preview` Nano Banana (images) via emergentintegrations + EMERGENT_LLM_KEY.
- **QR:** server-side `qrcode` → base64 data URL per coupon.

## User Personas
- SMB / D2C merchant running promotions
- Marketing team member
- Viewer (read-only stakeholder)

## Core Requirements (static)
- JWT auth + roles + workspaces
- Master dashboard, brand kit, sidebar shell
- Coupon CRUD, all types, 6 states, rule builder, unique + bulk codes, QR, validate/redeem with fraud checks
- AI Copilot copy + AI visual generation with live multi-format preview

## Implemented (2026-06)
- ✅ Auth (login/register/me), 3 seeded users, role-based 403 gating
- ✅ Multi-tenant workspaces + Brand Kit (colors/font/currency/logo) + Team list
- ✅ Dashboard: metrics, 14-day chart, AI Promotion Engine recs, top campaigns
- ✅ Coupons: list + filters + search, create/edit, 10 types, 6 states, rule builder, QR, bulk codes
- ✅ Validate/redeem endpoints with duplicate (5s) + state + min-cart + usage-limit checks; discount math for all types
- ✅ AI Copilot copy (Claude Sonnet 5) + AI visual (Nano Banana) with live preview across card/email/social
- ✅ Analytics page (area/pie/bar)
- ✅ Placeholder modules for Campaigns/Customers/Rewards/Design/Integrations
- Verified: backend 24/24 pytest, frontend E2E 100% (iteration_1.json)

## Backlog (deferred Phases 4–7)
- P1: Barcode gen, coupon scheduling calendar auto-planner, AI Promo Kit (email HTML/SMS export)
- P1: Email distribution (Resend) + shareable landing pages + UTM
- P2: Customer CRM + AI segmentation, loyalty points/tiers, gift cards, referral engine
- P2: A/B testing, CSV/PDF export, AI optimizer
- P2: White-label / agency console, webhooks, MFA, audit logs, GDPR

## Next Tasks
- Wire email sending (needs Resend/SendGrid key) — user requested, deferred pending key
- Public hosted coupon landing pages + embeddable widget snippet
