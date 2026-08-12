# PromoOS — ROADMAP (Sourced from the full 52-module PRD PDF)

Mapping every requested module against current build status. Anything ✅ is live; 🟡 partial (core built, some sub-features remain); 🔲 backlog.

## Phase 1 — Foundation ✅ SHIPPED
- **31. Multi-Tenant Architecture** ✅ Workspace isolation on every read/write.
- **41. Rate Limiting** 🟡 Brute-force lockout on login (5/15min). Public endpoints uncapped.
- **31. Auth** ✅ JWT Bearer + httpOnly cookie, bcrypt, roles (owner/marketer/viewer).
- **37. Brand Kit** ✅ Colors + name in `workspaces`, used by email template & public page.

## Phase 2 — Coupon Management ✅ MVP SHIPPED
- **2. Coupon Types** 🟡 percentage, flash_sale, seasonal, vip, first_time, birthday, referral, fixed, bogo, free_shipping — all with correct discount math. Missing: buy-X-get-Y-variant nuances, mystery-box, spin-wheel.
- **3. Add Coupon** ✅ Editor with rules, dates, scope, per-customer limit, stackable, referral toggle.
- **17. QR Codes** ✅ Server-side, downloadable.
- **29. Fraud Guard** 🟡 5-second duplicate-redemption block. Missing: velocity per IP, device fingerprinting.
- **32. Coupon Vault (bulk one-time codes)** ✅.
- **9. Coupon Duplication** 🔲 backlog (1-click clone).
- **44. Import/Export** 🔲 backlog.

## Phase 3 — AI Copilot ✅ SHIPPED
- **6. AI Copy Generator** ✅ Claude sonnet-5 → structured JSON.
- **6. AI Image Generator** ✅ Gemini nano-banana → base64.
- **26. AI A/B Test** ✅ AI variants + deterministic bucketing + auto-promote winner.
- **6. AI Translation** 🔲 backlog.
- **6. AI Segmentation** 🔲 Phase 5.

## Phase 4 — Distribution ✅ MOSTLY SHIPPED
- **19. Embed Widget** ✅ `/api/embed/coupon.js` copy-paste snippet.
- **20. Public Coupon Landing** ✅ `/c/:code` with brand colors, QR, redeem, share.
- **17. QR Codes** ✅ (see above).
- **18. Email Delivery** ✅ Resend + branded HTML (needs user API key to send live).
- **18. SMS Delivery** ✅ Twilio (needs user creds).
- **18. WhatsApp Delivery** ✅ Twilio (needs user creds).
- **28. Push Notifications** 🔲 backlog.
- **28. Social Publishing** 🔲 backlog (Instagram/Facebook auto-post).
- **20. Custom Landing Templates** 🔲 backlog (multiple layouts).

## Phase 5 — Loyalty & Referrals ✅ CORE SHIPPED
- **10. Referral Program** ✅ toggle per coupon, personal `?ref=` link, credit accrual, leaderboard.
- **11. Loyalty Points + Tiers** ✅ ppd config, per-tier thresholds, auto-tier on redeem.
- **11. Points Redemption at Checkout** 🔲 backlog (deduct points for reward).
- **12. Gift Cards** 🔲 backlog.
- **13. Customer CRM** 🔲 backlog (customers list, segments).
- **14. Reviews & UGC pull-in** 🔲 backlog.

## Phase 6 — Analytics & Optimization 🟡 PARTIAL
- **24. Dashboard KPIs** ✅ active/total, redemptions, revenue, top campaigns.
- **24. 14-day Timeseries** ✅.
- **25. Cohort/RFM Analysis** 🔲 backlog.
- **26. A/B Testing** ✅ (see Phase 3).
- **27. Export CSV/PDF Reports** 🔲 backlog.
- **34. Funnel Attribution** 🔲 backlog.

## Phase 7 — Platform & Enterprise 🔲 BACKLOG
- **43. Webhooks** 🔲.
- **45. Public API + docs** 🔲.
- **46. Event Stream** 🟡 events written to `email_events`, `message_events`, `referrals`, `experiments`. Missing: consumer stream.
- **47. White-label / Custom Domains** 🔲.
- **48. Agency Console** 🔲.
- **49. SLA + Uptime** 🔲.
- **50. Marketplace of AI templates** 🔲.
- **52. Enterprise SSO/SAML** 🔲.

## Modules explicitly deferred (per PRD scope note "Phases 1-3 MVP")
- 14 (Reviews), 22 (Print materials), 33 (Compliance packs), 38 (Blockchain-backed vouchers), 39 (NFT drops), 40 (Metaverse redemption), 42 (Voice-activated redemption), 51 (VR try-on).

---
Legend: ✅ done · 🟡 partial · 🔲 backlog
