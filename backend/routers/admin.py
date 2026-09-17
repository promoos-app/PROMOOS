"""Admin portal routes — superadmin only. Extracted from server.py in iter-11."""
import uuid
from typing import Optional
from fastapi import HTTPException, Depends
from pydantic import BaseModel, EmailStr


def register(api, db, now_iso, get_current_user, require_superadmin, hash_password, admin_log):

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
            return {"ok": True, "already_exists": True,
                    "user_id": existing["id"],
                    "workspace_id": existing["workspace_id"]}
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
        return {"ok": True, "already_exists": False,
                "user_id": uid, "workspace_id": wid,
                "publication_id": pub_id}


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

