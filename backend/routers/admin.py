"""Admin portal routes — superadmin only. Extracted from server.py in iter-11."""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import HTTPException, Depends
from pydantic import BaseModel, EmailStr
import jwt as _jwt

logger = logging.getLogger("promoos")


def register(api, db, now_iso, get_current_user, require_superadmin, hash_password, admin_log, extras=None):
    extras = extras or {}
    _resend = extras.get("resend")
    _sender = extras.get("sender_email") or "onboarding@resend.dev"
    _public_url = (extras.get("public_url") or "").rstrip("/")
    _jwt_secret = extras.get("jwt_secret") or ""
    _resend_key = extras.get("resend_api_key") or ""

    def _magic_token(user_id: str, email: str, ttl_hours: int = 72) -> str:
        payload = {
            "sub": user_id, "email": email, "kind": "magic",
            "exp": datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        }
        return _jwt.encode(payload, _jwt_secret, algorithm="HS256")

    def _token_hash(token: str) -> str:
        import hashlib
        return hashlib.sha256(token.encode()).hexdigest()[:32]

    async def _send_welcome_email(to_email: str, merchant_name: str,
                                    owner_name: str, magic_url: str,
                                    login_url: str, temp_password: str,
                                    pixel_url: Optional[str] = None) -> bool:
        if not (_resend and _resend_key):
            return False
        subject = f"Your {merchant_name} workspace is ready on PromoOS"
        pixel_html = (f'<img src="{pixel_url}" alt="" width="1" height="1" '
                      f'style="display:block;width:1px;height:1px;border:0" />'
                      if pixel_url else "")
        html = f"""
<!doctype html>
<html><body style="margin:0;padding:0;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#0A0A0A">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:32px 0">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:12px;overflow:hidden">
        <tr><td style="padding:22px 28px;background:#005CEE;color:#FFFFFF;font-weight:700;font-size:14px;letter-spacing:1px;text-transform:uppercase">PromoOS</td></tr>
        <tr><td style="padding:32px 28px 8px 28px">
          <h1 style="margin:0 0 12px 0;font-size:26px;line-height:1.2;color:#0A0A0A">Welcome, {owner_name} 👋</h1>
          <p style="margin:0 0 20px 0;font-size:15px;line-height:1.55;color:#3F3F46">
            Your <strong>{merchant_name}</strong> workspace is live on PromoOS.
            Sign in with one click below — no password needed.
          </p>
          <a href="{magic_url}" style="display:inline-block;background:#005CEE;color:#FFFFFF;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px">
            Sign in to your workspace
          </a>
          <p style="margin:24px 0 8px 0;font-size:13px;color:#71717A">
            The magic link is valid for 72 hours. Prefer classic sign-in?
            Use <a href="{login_url}" style="color:#005CEE">{login_url}</a> with:
          </p>
          <table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 20px 0;font-family:'Courier New',monospace;font-size:13px">
            <tr><td style="padding:4px 12px 4px 0;color:#71717A">Email</td><td style="padding:4px 0;color:#0A0A0A">{to_email}</td></tr>
            <tr><td style="padding:4px 12px 4px 0;color:#71717A">Password</td><td style="padding:4px 0;color:#0A0A0A">{temp_password}</td></tr>
          </table>
          <p style="margin:0 0 20px 0;font-size:13px;color:#71717A">Rotate this password from Settings on first sign-in.</p>
        </td></tr>
        <tr><td style="padding:16px 28px;background:#FAFAFA;border-top:1px solid #E4E4E7;font-size:11px;color:#71717A">
          Sent by PromoOS · <a href="{login_url}" style="color:#71717A">{login_url}</a>
        </td></tr>
      </table>
      {pixel_html}
    </td></tr>
  </table>
</body></html>"""
        try:
            await asyncio.to_thread(_resend.Emails.send, {
                "from": _sender, "to": [to_email],
                "subject": subject, "html": html,
            })
            return True
        except Exception as e:
            logger.warning(f"Welcome email send failed: {e}")
            return False


    @api.get("/admin/stats")
    async def admin_stats(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        users_active = await db.users.count_documents({"suspended": {"$ne": True}, "deleted_at": None})
        users_suspended = await db.users.count_documents({"suspended": True, "deleted_at": None})
        users_deleted = await db.users.count_documents({"deleted_at": {"$ne": None}})
        workspaces = await db.workspaces.count_documents({})
        coupons = await db.coupons.count_documents({})
        redemptions = await db.redemptions.count_documents({})
        return {
            "users": {"active": users_active, "suspended": users_suspended, "deleted": users_deleted},
            "workspaces": workspaces, "coupons": coupons, "redemptions": redemptions,
        }

    @api.get("/admin/users")
    async def admin_users(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(2000)
        ws_map = {w["id"]: w.get("name", "") for w in
                  await db.workspaces.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(500)}
        for r in rows:
            r["workspace_name"] = ws_map.get(r.get("workspace_id"), "")
            r["state"] = "deleted" if r.get("deleted_at") else ("suspended" if r.get("suspended") else "active")
        return rows

    class AdminUserCreateIn(BaseModel):
        name: str
        email: EmailStr
        password: str
        role: str = "marketer"
        workspace_id: Optional[str] = None
        workspace_name: Optional[str] = None

    @api.post("/admin/users")
    async def admin_create_user(body: AdminUserCreateIn, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        if body.role not in ("owner", "marketer", "viewer", "superadmin"):
            raise HTTPException(400, "invalid role")
        existing = await db.users.find_one({"email": body.email.lower()})
        if existing:
            raise HTTPException(400, "email already registered")
        wid = body.workspace_id
        if not wid:
            wid = str(uuid.uuid4())
            await db.workspaces.insert_one({
                "id": wid, "name": body.workspace_name or f"{body.name}'s workspace",
                "primary_color": "#005CEE", "secondary_color": "#CCFF00",
                "created_at": now_iso()})
        uid = str(uuid.uuid4())
        await db.users.insert_one({
            "id": uid, "name": body.name, "email": body.email.lower(),
            "password_hash": hash_password(body.password), "role": body.role,
            "workspace_id": wid, "suspended": False, "deleted_at": None,
            "created_at": now_iso(), "created_by_admin": user["id"]})
        await admin_log(user, "user.create", target=uid, meta={"email": body.email})
        return {"ok": True, "user_id": uid, "workspace_id": wid}

    class OnboardMerchantIn(BaseModel):
        merchant_name: str          # workspace / brand name
        owner_name: str
        owner_email: EmailStr
        owner_password: str
        primary_color: Optional[str] = "#005CEE"
        secondary_color: Optional[str] = "#CCFF00"
        currency: Optional[str] = "USD"
        create_demo_publication: bool = True

    @api.post("/admin/onboard-merchant")
    async def admin_onboard_merchant(body: OnboardMerchantIn,
                                       user: dict = Depends(get_current_user)):
        """One-click merchant onboarding wizard.

        Creates the workspace, owner account, and (optionally) a demo newsletter
        publication so the merchant lands on something rather than blank state.
        Idempotent by owner_email — running twice returns the existing IDs.
        """
        require_superadmin(user)
        existing = await db.users.find_one({"email": body.owner_email.lower()},
                                             {"_id": 0, "id": 1, "workspace_id": 1})
        if existing:
            base = _public_url or "https://app.promoos.com"
            magic_url = None
            try:
                tok = _magic_token(existing["id"], body.owner_email.lower())
                magic_url = f"{base}/login?magic={tok}"
            except Exception:
                pass
            return {"ok": True, "already_exists": True,
                    "user_id": existing["id"],
                    "workspace_id": existing["workspace_id"],
                    "magic_link": magic_url,
                    "email_sent": False}
        wid = str(uuid.uuid4())
        await db.workspaces.insert_one({
            "id": wid, "name": body.merchant_name,
            "primary_color": body.primary_color or "#005CEE",
            "secondary_color": body.secondary_color or "#CCFF00",
            "currency": body.currency or "USD",
            "created_at": now_iso(),
        })
        uid = str(uuid.uuid4())
        await db.users.insert_one({
            "id": uid, "name": body.owner_name,
            "email": body.owner_email.lower(),
            "password_hash": hash_password(body.owner_password),
            "role": "owner", "workspace_id": wid,
            "suspended": False, "deleted_at": None,
            "created_at": now_iso(), "created_by_admin": user["id"],
        })
        pub_id = None
        if body.create_demo_publication:
            import re as _re
            slug_base = _re.sub(r"[^a-z0-9]+", "-",
                                 body.merchant_name.lower()).strip("-")[:40] or f"pub-{uid[:6]}"
            existing_slugs = {d["slug"] async for d in db.publications.find(
                {}, {"_id": 0, "slug": 1})}
            slug = slug_base; i = 2
            while slug in existing_slugs: slug = f"{slug_base}-{i}"; i += 1
            pub_id = str(uuid.uuid4())
            await db.publications.insert_one({
                "id": pub_id, "workspace_id": wid,
                "name": f"{body.merchant_name} Newsletter",
                "slug": slug,
                "description": f"Deals, drops, and news from {body.merchant_name}.",
                "sender_name": body.merchant_name,
                "sender_email": None,
                "primary_color": body.primary_color or "#005CEE",
                "subscribe_headline": "Join the list",
                "subscribe_body": f"Get {body.merchant_name} updates in your inbox.",
                "thanks_headline": "You're in ✓",
                "thanks_body": "Check your inbox to confirm your address.",
                "referral_rewards": [
                    {"count": 3, "coupon_percent": 10},
                    {"count": 10, "coupon_percent": 20},
                    {"count": 25, "coupon_percent": 30},
                ],
                "created_by": uid, "created_at": now_iso(), "updated_at": now_iso(),
            })
        await admin_log(user, "merchant.onboard", target=uid,
                         meta={"email": body.owner_email, "merchant": body.merchant_name})
        # Magic sign-in link (avoids sharing raw passwords by email).
        magic_url = None
        email_sent = False
        try:
            tok = _magic_token(uid, body.owner_email.lower())
            base = _public_url or "https://app.promoos.com"
            magic_url = f"{base}/login?magic={tok}"
            th = _token_hash(tok)
            await db.users.update_one({"id": uid}, {"$set": {"magic_token_hash": th}})
            pixel_url = f"{base}/api/auth/magic-open/{th}.gif"
            email_sent = await _send_welcome_email(
                to_email=body.owner_email.lower(),
                merchant_name=body.merchant_name,
                owner_name=body.owner_name,
                magic_url=magic_url,
                login_url=f"{base}/login",
                temp_password=body.owner_password,
                pixel_url=pixel_url,
            )
        except Exception as e:
            logger.warning(f"Magic link build failed: {e}")
        return {"ok": True, "already_exists": False,
                "user_id": uid, "workspace_id": wid,
                "publication_id": pub_id,
                "magic_link": magic_url,
                "email_sent": email_sent}


    @api.get("/auth/magic-open/{token_hash}.gif")
    async def magic_pixel(token_hash: str):
        """1x1 open tracking pixel embedded in the welcome email.

        Public (unauthenticated) — the token hash is a 32-char sha256 slice
        with 2^128 space, so it's not enumerable. On hit we stamp
        ``magic_first_open_at`` on the matching user (first open only).
        """
        from fastapi import Response as _R
        try:
            if len(token_hash) == 32 and token_hash.isalnum():
                await db.users.update_one(
                    {"magic_token_hash": token_hash,
                     "magic_first_open_at": {"$exists": False}},
                    {"$set": {"magic_first_open_at": now_iso()}})
        except Exception as e:
            logger.warning(f"magic-pixel stamp failed: {e}")
        # 1x1 transparent GIF (43 bytes).
        pixel = bytes([
            0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00, 0x80, 0x00,
            0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x21, 0xF9, 0x04, 0x01, 0x00,
            0x00, 0x00, 0x00, 0x2C, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
            0x00, 0x02, 0x02, 0x44, 0x01, 0x00, 0x3B,
        ])
        return _R(content=pixel, media_type="image/gif",
                  headers={"Cache-Control": "no-store, no-cache, must-revalidate",
                           "Pragma": "no-cache", "Expires": "0"})

    class BatchOnboardIn(BaseModel):
        rows: list           # [{merchant_name, owner_name, owner_email, owner_password?}]
        create_demo_publication: bool = True

    @api.post("/admin/onboard-batch")
    async def admin_onboard_batch(body: BatchOnboardIn, user: dict = Depends(get_current_user)):
        """Bulk merchant onboarding — same logic as single-merchant, run per row.

        Non-fatal per row: errors are reported, other rows continue. Returns
        summary + per-row results so the UI can render a CSV-style report.
        """
        require_superadmin(user)
        results = []
        summary = {"total": len(body.rows), "created": 0, "already_existed": 0,
                    "emails_sent": 0, "errors": 0}
        import re as _re, secrets as _secrets
        base = _public_url or "https://app.promoos.com"

        for idx, row in enumerate(body.rows[:200]):  # hard cap 200 per batch
            try:
                merchant = str(row.get("merchant_name", "")).strip()
                owner = str(row.get("owner_name", "")).strip()
                email = str(row.get("owner_email", "")).strip().lower()
                password = str(row.get("owner_password") or "").strip() or (
                    _secrets.token_urlsafe(9) + "!")
                if not (merchant and owner and "@" in email):
                    results.append({"row": idx + 1, "ok": False,
                                     "error": "Missing merchant_name / owner_name / owner_email",
                                     "email": email})
                    summary["errors"] += 1
                    continue

                existing = await db.users.find_one({"email": email},
                                                     {"_id": 0, "id": 1, "workspace_id": 1})
                if existing:
                    tok = _magic_token(existing["id"], email)
                    results.append({"row": idx + 1, "ok": True, "already_existed": True,
                                     "email": email, "user_id": existing["id"],
                                     "workspace_id": existing["workspace_id"],
                                     "magic_link": f"{base}/login?magic={tok}",
                                     "email_sent": False})
                    summary["already_existed"] += 1
                    continue

                wid = str(uuid.uuid4())
                await db.workspaces.insert_one({
                    "id": wid, "name": merchant,
                    "primary_color": "#005CEE", "secondary_color": "#CCFF00",
                    "currency": "USD", "created_at": now_iso(),
                })
                uid_ = str(uuid.uuid4())
                await db.users.insert_one({
                    "id": uid_, "name": owner, "email": email,
                    "password_hash": hash_password(password),
                    "role": "owner", "workspace_id": wid,
                    "suspended": False, "deleted_at": None,
                    "created_at": now_iso(), "created_by_admin": user["id"],
                })
                pub_id = None
                if body.create_demo_publication:
                    slug_base = _re.sub(r"[^a-z0-9]+", "-",
                                          merchant.lower()).strip("-")[:40] or f"pub-{uid_[:6]}"
                    existing_slugs = {d["slug"] async for d in db.publications.find(
                        {}, {"_id": 0, "slug": 1})}
                    slug = slug_base; i = 2
                    while slug in existing_slugs: slug = f"{slug_base}-{i}"; i += 1
                    pub_id = str(uuid.uuid4())
                    await db.publications.insert_one({
                        "id": pub_id, "workspace_id": wid,
                        "name": f"{merchant} Newsletter", "slug": slug,
                        "description": f"Deals, drops, and news from {merchant}.",
                        "sender_name": merchant, "sender_email": None,
                        "primary_color": "#005CEE",
                        "subscribe_headline": "Join the list",
                        "subscribe_body": f"Get {merchant} updates in your inbox.",
                        "thanks_headline": "You're in ✓",
                        "thanks_body": "Check your inbox to confirm your address.",
                        "referral_rewards": [
                            {"count": 3, "coupon_percent": 10},
                            {"count": 10, "coupon_percent": 20},
                            {"count": 25, "coupon_percent": 30},
                        ],
                        "created_by": uid_,
                        "created_at": now_iso(), "updated_at": now_iso(),
                    })
                await admin_log(user, "merchant.onboard", target=uid_,
                                 meta={"email": email, "merchant": merchant, "batch": True})

                tok = _magic_token(uid_, email)
                magic_url = f"{base}/login?magic={tok}"
                th = _token_hash(tok)
                await db.users.update_one({"id": uid_}, {"$set": {"magic_token_hash": th}})
                email_sent = await _send_welcome_email(
                    to_email=email, merchant_name=merchant, owner_name=owner,
                    magic_url=magic_url, login_url=f"{base}/login",
                    temp_password=password,
                    pixel_url=f"{base}/api/auth/magic-open/{th}.gif")
                if email_sent: summary["emails_sent"] += 1
                summary["created"] += 1
                results.append({"row": idx + 1, "ok": True, "already_existed": False,
                                 "email": email, "user_id": uid_, "workspace_id": wid,
                                 "publication_id": pub_id, "magic_link": magic_url,
                                 "temp_password": password, "email_sent": email_sent})
            except Exception as e:
                logger.exception(f"batch onboard row {idx + 1} failed")
                results.append({"row": idx + 1, "ok": False, "error": str(e)[:160],
                                 "email": row.get("owner_email", "")})
                summary["errors"] += 1
        return {"ok": True, "summary": summary, "results": results,
                "generated_at": now_iso()}



    @api.post("/admin/users/{uid}/suspend")
    async def admin_suspend(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        await db.users.update_one({"id": uid}, {"$set": {"suspended": True, "suspended_at": now_iso()}})
        await admin_log(user, "user.suspend", target=uid)
        return {"ok": True}

    @api.post("/admin/users/{uid}/activate")
    async def admin_activate(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        await db.users.update_one({"id": uid}, {"$set": {"suspended": False}, "$unset": {"suspended_at": ""}})
        await admin_log(user, "user.activate", target=uid)
        return {"ok": True}

    @api.post("/admin/users/{uid}/restore")
    async def admin_restore(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        await db.users.update_one({"id": uid}, {"$set": {"deleted_at": None, "suspended": False}})
        await admin_log(user, "user.restore", target=uid)
        return {"ok": True}

    @api.delete("/admin/users/{uid}")
    async def admin_delete(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        if uid == user["id"]:
            raise HTTPException(400, "Cannot delete your own account")
        await db.users.update_one({"id": uid}, {"$set": {"deleted_at": now_iso()}})
        await admin_log(user, "user.delete", target=uid)
        return {"ok": True}

    @api.get("/admin/workspaces")
    async def admin_workspaces(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        docs = await db.workspaces.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        for d in docs:
            d["user_count"] = await db.users.count_documents({"workspace_id": d["id"], "deleted_at": None})
            d["coupon_count"] = await db.coupons.count_documents({"workspace_id": d["id"]})
            d["redemption_count"] = await db.redemptions.count_documents({"workspace_id": d["id"]})
        return docs

    @api.get("/admin/logs")
    async def admin_logs(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        docs = await db.admin_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
        return docs

    @api.get("/admin/payments")
    async def admin_payments(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        docs = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        total = sum(d.get("amount", 0) for d in docs if d.get("status") == "succeeded")
        return {"total_collected": round(total, 2), "count": len(docs), "payments": docs}

    @api.get("/admin/health-check")
    async def admin_health_check(user: dict = Depends(get_current_user)):
        """Production go-live health check (Provisioning Runbook Phase 8).

        Non-destructive: only READs env, indexes, and collection counts.
        Every check reports {ok, message} so the admin UI can render a green/red list.
        """
        import os
        require_superadmin(user)
        checks = []

        def _add(name, ok, message, level="info"):
            checks.append({"name": name, "ok": bool(ok), "message": message, "level": level})

        # ---- Environment ----
        pub = os.environ.get("PUBLIC_APP_URL", "").strip()
        _add("Public URL configured", bool(pub), pub or "PUBLIC_APP_URL is empty", "critical")
        cors = os.environ.get("CORS_ORIGINS", "*").strip()
        _add("CORS restricted", cors != "*",
             cors if cors != "*" else "CORS_ORIGINS=* — restrict before opening to prod",
             "warning")
        _add("JWT secret non-default",
             len(os.environ.get("JWT_SECRET", "")) >= 24,
             "JWT_SECRET length ≥ 24 chars" if len(os.environ.get("JWT_SECRET", "")) >= 24
             else "JWT_SECRET is missing or shorter than 24 chars",
             "critical")

        # ---- Integrations ----
        stripe_ok = bool(os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_"))
        stripe_live = os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_live_")
        _add("Stripe", stripe_ok,
             "sk_live_ configured (production)" if stripe_live
             else ("sk_test_ configured (sandbox)" if stripe_ok else "STRIPE_SECRET_KEY missing"),
             "critical" if not stripe_ok else "info")
        _add("Stripe webhook secret",
             bool(os.environ.get("STRIPE_WEBHOOK_SECRET")),
             "whsec_ configured" if os.environ.get("STRIPE_WEBHOOK_SECRET")
             else "STRIPE_WEBHOOK_SECRET missing — webhooks won't verify",
             "warning")
        resend_ok = bool(os.environ.get("RESEND_API_KEY", "").startswith("re_"))
        _add("Resend (email)", resend_ok,
             "API key configured" if resend_ok else "RESEND_API_KEY missing — email disabled",
             "warning")
        twilio_ok = bool(os.environ.get("TWILIO_ACCOUNT_SID")) and bool(os.environ.get("TWILIO_AUTH_TOKEN"))
        _add("Twilio (SMS)", twilio_ok,
             "SID+Token configured" if twilio_ok else "Twilio credentials missing — SMS disabled",
             "info")
        _add("Emergent LLM key",
             bool(os.environ.get("EMERGENT_LLM_KEY")),
             "configured" if os.environ.get("EMERGENT_LLM_KEY") else "EMERGENT_LLM_KEY missing — AI features 502",
             "critical")

        # ---- Mongo indexes (scale-out) ----
        try:
            expected_indexes = {
                "coupons": ["workspace_id_1_state_1", "code_1"],
                "redemptions": ["workspace_id_1_created_at_-1", "coupon_id_1"],
                "customers": ["workspace_id_1_email_1"],
                "email_events": ["workspace_id_1_created_at_-1"],
                "csv_mapping_presets": ["workspace_id_1_signature_1"],
                "journey_template_ratings": ["template_id_1_workspace_id_1"],
                "preset_pack_ratings": ["pack_id_1_workspace_id_1"],
            }
            for coll, wanted in expected_indexes.items():
                idx = await db[coll].index_information()
                missing = [w for w in wanted if w not in idx]
                _add(f"Index: {coll}", not missing,
                     f"all present ({len(wanted)})" if not missing else f"missing: {', '.join(missing)}",
                     "warning")
        except Exception as e:
            _add("Index check", False, f"error: {str(e)[:80]}", "warning")

        # ---- Content readiness ----
        pack_count = await db.preset_packs.count_documents({"is_public": True})
        _add("Marketplace preset packs", pack_count >= 3,
             f"{pack_count} public pack(s) available",
             "info")
        pub_journeys = await db.journey_templates.count_documents({"is_public": True})
        _add("Public journey templates", True,
             f"{pub_journeys} workspace-published + 3 built-in", "info")

        # ---- Compliance surface ----
        _add("Security contact",
             bool(os.environ.get("SECURITY_CONTACT_EMAIL")),
             os.environ.get("SECURITY_CONTACT_EMAIL", "not set — /security.txt uses default"),
             "warning")
        deletion_pending = await db.deletion_requests.count_documents({"status": "pending"})
        _add("DSAR queue", True,
             f"{deletion_pending} deletion request(s) pending", "info")
        error_recent = await db.error_reports.count_documents({})
        _add("Front-end errors (all-time)", error_recent < 100,
             f"{error_recent} report(s) logged",
             "warning" if error_recent >= 100 else "info")

        critical_failed = [c for c in checks if c["level"] == "critical" and not c["ok"]]
        warnings = [c for c in checks if c["level"] == "warning" and not c["ok"]]
        return {
            "ok": len(critical_failed) == 0,
            "ready_for_launch": len(critical_failed) == 0 and len(warnings) <= 2,
            "critical_failures": len(critical_failed),
            "warnings": len(warnings),
            "checks": checks,
            "generated_at": now_iso(),
        }

    @api.get("/admin/onboarding-funnel")
    async def onboarding_funnel(user: dict = Depends(get_current_user)):
        """Superadmin funnel: onboarded → magic-opened → magic-clicked → first coupon sent.

        Reads admin_logs for `merchant.onboard` events and joins against
        the users + email_events collections. Also computes median
        time-to-first-send (hours) to identify stalled onboardings.
        """
        require_superadmin(user)
        onboard_logs = await db.admin_logs.find(
            {"action": "merchant.onboard"},
            {"_id": 0}).sort("created_at", -1).to_list(500)
        # Batch fetch users by id
        uids = [l.get("target") for l in onboard_logs if l.get("target")]
        users_map = {}
        if uids:
            async for u in db.users.find({"id": {"$in": uids}},
                                          {"_id": 0, "id": 1, "email": 1, "name": 1,
                                           "workspace_id": 1,
                                           "magic_first_open_at": 1,
                                           "magic_first_signin_at": 1,
                                           "created_at": 1}):
                users_map[u["id"]] = u
        rows = []
        onboarded = magic_opened = magic_clicked = first_sent = 0
        ttfs_hours = []   # for merchants who reached first_sent
        from datetime import datetime as _dt
        def _parse_iso(s):
            if not s: return None
            try: return _dt.fromisoformat(s.replace("Z", "+00:00"))
            except Exception: return None
        for lg in onboard_logs:
            u = users_map.get(lg.get("target"))
            if not u:
                continue
            onboarded += 1
            open_at = u.get("magic_first_open_at")
            magic_at = u.get("magic_first_signin_at")
            if open_at: magic_opened += 1
            if magic_at: magic_clicked += 1
            first_email = None
            if u.get("workspace_id"):
                ev = await db.email_events.find_one(
                    {"workspace_id": u["workspace_id"]},
                    {"_id": 0, "created_at": 1},
                    sort=[("created_at", 1)])
                if ev: first_email = ev.get("created_at")
            if first_email: first_sent += 1
            onboarded_at = lg.get("created_at") or u.get("created_at")
            hours = None
            if first_email and onboarded_at:
                a = _parse_iso(onboarded_at); b = _parse_iso(first_email)
                if a and b:
                    hours = round((b - a).total_seconds() / 3600, 2)
                    if hours >= 0: ttfs_hours.append(hours)
            rows.append({
                "user_id": u["id"], "email": u.get("email"), "name": u.get("name"),
                "workspace_id": u.get("workspace_id"),
                "merchant": (lg.get("meta") or {}).get("merchant") or u.get("name"),
                "onboarded_at": onboarded_at,
                "magic_opened_at": open_at,
                "magic_clicked_at": magic_at,
                "first_email_sent_at": first_email,
                "time_to_first_send_hours": hours,
                "stage": ("first_sent" if first_email else
                          "magic_clicked" if magic_at else
                          "magic_opened" if open_at else "onboarded"),
            })
        def _pct(n, d): return round((n / d * 100), 1) if d else 0.0
        def _median(vals):
            if not vals: return None
            s = sorted(vals); n = len(s)
            return round((s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2), 2)
        return {
            "totals": {
                "onboarded": onboarded,
                "magic_opened": magic_opened,
                "magic_clicked": magic_clicked,
                "first_email_sent": first_sent,
            },
            "conversion": {
                "onboard_to_open": _pct(magic_opened, onboarded),
                "open_to_click": _pct(magic_clicked, magic_opened),
                "onboard_to_magic": _pct(magic_clicked, onboarded),
                "magic_to_first_send": _pct(first_sent, magic_clicked),
                "onboard_to_first_send": _pct(first_sent, onboarded),
            },
            "median_time_to_first_send_hours": _median(ttfs_hours),
            "rows": rows,
            "generated_at": now_iso(),
        }

    @api.get("/admin/merchant-summary/{uid}")
    async def merchant_summary(uid: str, user: dict = Depends(get_current_user)):
        """Superadmin — everything about a merchant in one payload for the funnel drawer."""
        require_superadmin(user)
        u = await db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 0})
        if not u:
            raise HTTPException(404, "user not found")
        wid = u.get("workspace_id")
        ws = await db.workspaces.find_one({"id": wid}, {"_id": 0}) if wid else None
        coupons_total = await db.coupons.count_documents({"workspace_id": wid}) if wid else 0
        coupons_recent = await db.coupons.find(
            {"workspace_id": wid} if wid else {"_id": None},
            {"_id": 0, "id": 1, "code": 1, "name": 1, "state": 1, "type": 1,
             "created_at": 1, "discount_value": 1}
        ).sort("created_at", -1).to_list(5) if wid else []
        redemptions_total = await db.redemptions.count_documents({"workspace_id": wid}) if wid else 0
        emails_total = await db.email_events.count_documents({"workspace_id": wid}) if wid else 0
        subscribers_total = (await db.newsletter_subscribers.count_documents({"workspace_id": wid})
                              if wid else 0)
        # Last activity across a few key collections.
        candidates = []
        for coll in ("coupons", "redemptions", "email_events", "publications"):
            try:
                doc = await db[coll].find_one({"workspace_id": wid} if wid else {"_id": None},
                                                {"_id": 0, "created_at": 1},
                                                sort=[("created_at", -1)])
                if doc and doc.get("created_at"):
                    candidates.append((doc["created_at"], coll))
            except Exception:
                pass
        last_activity = max(candidates)[0] if candidates else u.get("created_at")
        last_activity_source = max(candidates)[1] if candidates else "user_created"
        return {
            "user": u, "workspace": ws,
            "stats": {"coupons": coupons_total, "redemptions": redemptions_total,
                      "emails_sent": emails_total, "newsletter_subscribers": subscribers_total},
            "recent_coupons": coupons_recent,
            "last_activity_at": last_activity,
            "last_activity_source": last_activity_source,
            "onboarding": {
                "magic_first_open_at": u.get("magic_first_open_at"),
                "magic_first_signin_at": u.get("magic_first_signin_at"),
            },
        }

    async def _find_stalled(threshold_hours: int = 72):
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=threshold_hours)).isoformat()
        onboard_logs = await db.admin_logs.find(
            {"action": "merchant.onboard", "created_at": {"$lt": cutoff}},
            {"_id": 0}).sort("created_at", -1).to_list(500)
        uids = [l.get("target") for l in onboard_logs if l.get("target")]
        if not uids: return []
        users_by_id = {}
        async for uu in db.users.find(
            {"id": {"$in": uids}, "magic_first_signin_at": {"$exists": False},
             "deleted_at": None, "suspended": {"$ne": True}},
            {"_id": 0, "id": 1, "email": 1, "name": 1, "workspace_id": 1,
             "created_at": 1, "magic_first_open_at": 1}):
            users_by_id[uu["id"]] = uu
        out = []
        from datetime import datetime as _dt
        def _p(s):
            try: return _dt.fromisoformat((s or "").replace("Z", "+00:00"))
            except Exception: return None
        now = datetime.now(timezone.utc)
        for lg in onboard_logs:
            uu = users_by_id.get(lg.get("target"))
            if not uu: continue
            onboarded_at = lg.get("created_at") or uu.get("created_at")
            pa = _p(onboarded_at)
            hours = round((now - pa).total_seconds() / 3600, 1) if pa else None
            out.append({
                "user_id": uu["id"], "email": uu.get("email"), "name": uu.get("name"),
                "workspace_id": uu.get("workspace_id"),
                "merchant": (lg.get("meta") or {}).get("merchant") or uu.get("name"),
                "onboarded_at": onboarded_at, "hours_since_onboard": hours,
                "opened_email": bool(uu.get("magic_first_open_at")),
            })
        return out

    @api.get("/admin/stalled-merchants")
    async def stalled_merchants(user: dict = Depends(get_current_user),
                                  hours: int = 72):
        """List merchants onboarded > N hours ago who never clicked their magic link."""
        require_superadmin(user)
        hours = max(1, min(720, int(hours)))
        rows = await _find_stalled(hours)
        return {"threshold_hours": hours, "count": len(rows), "rows": rows,
                "generated_at": now_iso()}

    @api.post("/admin/stalled-nudge")
    async def stalled_nudge(user: dict = Depends(get_current_user),
                              hours: int = 72):
        """Send a digest email to the superadmin with the current stalled list.

        No-op (returns list only) when Resend isn't configured — the caller
        can still see the rows in the response.
        """
        require_superadmin(user)
        hours = max(1, min(720, int(hours)))
        rows = await _find_stalled(hours)
        sent = False
        email_id = None
        if rows and _resend and _resend_key:
            base = _public_url or "https://app.promoos.com"
            rows_html = "".join(
                f'<tr><td style="padding:6px 10px;border-bottom:1px solid #E4E4E7">'
                f'<strong>{r["merchant"]}</strong><br>'
                f'<span style="font-family:monospace;color:#71717A;font-size:12px">{r["email"]}</span></td>'
                f'<td style="padding:6px 10px;border-bottom:1px solid #E4E4E7;color:#71717A;font-size:12px">'
                f'{r["hours_since_onboard"]}h ago · '
                f'{"opened" if r["opened_email"] else "no open"}</td></tr>'
                for r in rows[:50])
            html = f"""
<!doctype html><html><body style="margin:0;padding:0;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#0A0A0A">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:32px 0">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:12px;overflow:hidden">
        <tr><td style="padding:22px 28px;background:#F97316;color:#FFFFFF;font-weight:700;font-size:14px;letter-spacing:1px;text-transform:uppercase">Stalled merchant digest</td></tr>
        <tr><td style="padding:28px">
          <h2 style="margin:0 0 10px 0;font-size:22px">{len(rows)} merchant(s) stalled &gt; {hours}h</h2>
          <p style="margin:0 0 18px 0;color:#3F3F46;font-size:14px">
            These merchants were onboarded but haven't clicked their magic sign-in link yet.
            Consider a personal follow-up.
          </p>
          <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;font-size:14px">
            <thead><tr style="background:#FAFAFA">
              <th align="left" style="padding:6px 10px;border-bottom:2px solid #E4E4E7">Merchant</th>
              <th align="left" style="padding:6px 10px;border-bottom:2px solid #E4E4E7">Age</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
          </table>
          <p style="margin:20px 0 0 0;font-size:12px;color:#71717A">
            <a href="{base}/admin" style="color:#005CEE">Open Admin → Funnel</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""
            try:
                r = await asyncio.to_thread(_resend.Emails.send, {
                    "from": _sender, "to": [user.get("email")],
                    "subject": f"[PromoOS] {len(rows)} merchant(s) stalled > {hours}h",
                    "html": html,
                })
                email_id = r.get("id") if isinstance(r, dict) else None
                sent = True
            except Exception as e:
                logger.warning(f"stalled digest send failed: {e}")
        return {"ok": True, "count": len(rows), "email_sent": sent,
                "email_id": email_id, "rows": rows[:100]}

