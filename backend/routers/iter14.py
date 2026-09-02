"""Iter-14 batch: password reset, products+checkout, customer bulk ops, coupon publish/preview, funnel enrichment."""
import os, uuid, secrets, hashlib
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Depends
from pydantic import BaseModel, EmailStr

def register(api, db, now_iso, get_current_user, require_writer,
             hash_password, verify_password, PUBLIC_APP_URL):
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

    # ---------- Password reset ----------
    class PWResetReqIn(BaseModel):
        email: EmailStr

    class PWResetCompleteIn(BaseModel):
        token: str
        new_password: str

    def _hash_token(t): return hashlib.sha256(t.encode()).hexdigest()

    @api.post("/auth/password-reset/request")
    async def pw_reset_request(body: PWResetReqIn):
        user = await db.users.find_one({"email": body.email.lower()})
        # Always return 200 to avoid email enumeration.
        if user and not user.get("deleted_at"):
            token = secrets.token_urlsafe(32)
            await db.password_resets.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"], "email": user["email"],
                "token_hash": _hash_token(token),
                "used": False,
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
                "created_at": now_iso(),
            })
            origin = (PUBLIC_APP_URL or "").rstrip("/")
            reset_url = f"{origin}/reset-password?token={token}" if origin else f"/reset-password?token={token}"
            # Deliver via Resend if configured; log otherwise (dev mode).
            if RESEND_API_KEY:
                try:
                    import requests
                    requests.post("https://api.resend.com/emails",
                                  headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                                           "Content-Type": "application/json"},
                                  json={"from": SENDER_EMAIL, "to": [user["email"]],
                                        "subject": "Reset your PromoOS password",
                                        "html": f"<p>Click to reset: <a href='{reset_url}'>{reset_url}</a></p><p>Link expires in 2 hours. If you did not request this, ignore.</p>"},
                                  timeout=10)
                except Exception:
                    pass
            else:
                import logging as _l
                _l.getLogger(__name__).warning(f"Password reset (RESEND_API_KEY unset) — deliver manually: {reset_url}")
        return {"ok": True, "message": "If that email exists, a reset link has been sent."}

    @api.post("/auth/password-reset/complete")
    async def pw_reset_complete(body: PWResetCompleteIn):
        if len(body.new_password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")
        rec = await db.password_resets.find_one({"token_hash": _hash_token(body.token), "used": False})
        if not rec:
            raise HTTPException(400, "Invalid or expired token")
        if rec["expires_at"] < now_iso():
            raise HTTPException(400, "Token expired")
        await db.users.update_one({"id": rec["user_id"]},
            {"$set": {"password_hash": hash_password(body.new_password),
                      "password_changed_at": now_iso()}})
        await db.password_resets.update_one({"id": rec["id"]},
            {"$set": {"used": True, "used_at": now_iso()}})
        return {"ok": True}

    class PWChangeIn(BaseModel):
        current_password: str
        new_password: str

    @api.post("/auth/change-password")
    async def pw_change(body: PWChangeIn, user: dict = Depends(get_current_user)):
        u = await db.users.find_one({"id": user["id"]})
        if not u or not verify_password(body.current_password, u.get("password_hash", "")):
            raise HTTPException(400, "Current password incorrect")
        if len(body.new_password) < 8:
            raise HTTPException(400, "New password must be at least 8 characters")
        await db.users.update_one({"id": user["id"]},
            {"$set": {"password_hash": hash_password(body.new_password),
                      "password_changed_at": now_iso()}})
        return {"ok": True}

    # ---------- Products (for coupon/funnel Buy-Now blocks) ----------
    class ProductIn(BaseModel):
        name: str
        description: Optional[str] = ""
        price: float
        currency: str = "USD"
        image_url: Optional[str] = None
        stripe_price_id: Optional[str] = None

    @api.get("/products")
    async def list_products(user: dict = Depends(get_current_user)):
        docs = await db.products.find(
            {"workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"_id": 0}).sort("created_at", -1).to_list(200)
        return docs

    @api.post("/products")
    async def create_product(body: ProductIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        doc = {"id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
               **body.model_dump(), "is_deleted": False, "created_at": now_iso()}
        await db.products.insert_one({**doc})
        return doc

    @api.put("/products/{pid}")
    async def update_product(pid: str, body: ProductIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.products.update_one(
            {"id": pid, "workspace_id": user["workspace_id"]},
            {"$set": {**body.model_dump(), "updated_at": now_iso()}})
        if r.matched_count == 0: raise HTTPException(404, "Not found")
        return {"ok": True}

    @api.delete("/products/{pid}")
    async def delete_product(pid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        await db.products.update_one({"id": pid, "workspace_id": user["workspace_id"]},
                                      {"$set": {"is_deleted": True}})
        return {"ok": True}

    class BuyNowIn(BaseModel):
        product_id: str
        origin_url: str
        coupon_code: Optional[str] = None

    @api.post("/public/products/checkout")
    async def public_product_checkout(body: BuyNowIn):
        """Public — used by coupon/funnel Buy-Now buttons. Creates Stripe Checkout via platform Stripe.
        If a coupon_code is provided AND it belongs to the same workspace as the product AND it's
        active, the discount is applied to the line-item price at checkout so the customer actually
        pays the discounted amount. Applied discount is recorded on the order for reconciliation.
        """
        p = await db.products.find_one({"id": body.product_id, "is_deleted": {"$ne": True}}, {"_id": 0})
        if not p: raise HTTPException(404, "Product not found")
        original_price = float(p["price"])
        final_price = original_price
        applied_coupon = None
        applied_discount = 0.0
        if body.coupon_code:
            code_upper = body.coupon_code.upper()
            c = await db.coupons.find_one({
                "code": code_upper,
                "workspace_id": p["workspace_id"],
                "state": "active",
                "is_deleted": {"$ne": True},
            }, {"_id": 0})
            if c:
                ctype = (c.get("type") or "").lower()
                dval = float(c.get("discount_value") or 0)
                if ctype in ("fixed", "fixed_amount", "amount"):
                    applied_discount = min(dval, original_price)
                elif ctype in ("percentage", "percent", "%", "vip", "frequent", "regular",
                                 "new", "at_risk", "flash", "launch", "loyalty", "welcome", "seasonal"):
                    applied_discount = original_price * (dval / 100.0)
                # cap non-negative
                applied_discount = max(0.0, min(applied_discount, original_price))
                final_price = max(0.01, original_price - applied_discount)  # Stripe requires >0
                applied_coupon = code_upper
        try:
            import stripe
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
            if not stripe.api_key: raise HTTPException(501, "Stripe not configured")
            product_data = {"name": p["name"], "description": p.get("description", "")[:500] or None}
            if applied_coupon:
                # Surface the discount in the customer-visible product name.
                product_data["name"] = f'{p["name"]} — {applied_coupon} applied'
            price_data = {"currency": (p.get("currency") or "USD").lower(),
                          "product_data": product_data,
                          "unit_amount": int(round(final_price * 100))}
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": price_data, "quantity": 1}],
                mode="payment",
                success_url=f"{body.origin_url}/thank-you?product={body.product_id}&session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{body.origin_url}",
                metadata={"product_id": body.product_id, "workspace_id": p["workspace_id"],
                          "coupon_code": applied_coupon or "",
                          "original_amount": f"{original_price:.2f}",
                          "applied_discount": f"{applied_discount:.2f}",
                          "final_amount": f"{final_price:.2f}"})
            await db.product_orders.insert_one({
                "id": str(uuid.uuid4()), "session_id": session.id,
                "product_id": body.product_id, "workspace_id": p["workspace_id"],
                "coupon_code": applied_coupon, "original_amount": original_price,
                "applied_discount": applied_discount, "amount": final_price,
                "currency": p["currency"], "status": "initiated",
                "created_at": now_iso()})
            return {"checkout_url": session.url, "session_id": session.id,
                    "original_price": original_price, "final_price": final_price,
                    "applied_discount": applied_discount, "coupon_applied": applied_coupon}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, f"Stripe error: {e}")

    # ---------- Customers bulk operations ----------
    class BulkCustomerIn(BaseModel):
        ids: List[str]

    @api.post("/customers/bulk-delete")
    async def bulk_delete_customers(body: BulkCustomerIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.customers.update_many(
            {"id": {"$in": body.ids}, "workspace_id": user["workspace_id"]},
            {"$set": {"is_deleted": True, "deleted_at": now_iso()}})
        return {"deleted": r.modified_count}

    # ---------- Publish/unpublish coupon ----------
    @api.post("/coupons/{cid}/publish")
    async def publish_coupon(cid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        # `state` is the canonical field the public endpoint (/api/public/coupons/{code})
        # gates on; keep `status` in sync for legacy consumers.
        r = await db.coupons.update_one(
            {"id": cid, "workspace_id": user["workspace_id"]},
            {"$set": {"state": "active", "status": "active", "published_at": now_iso()}})
        if r.matched_count == 0: raise HTTPException(404, "Not found")
        return {"ok": True, "state": "active", "status": "active"}

    @api.post("/coupons/{cid}/unpublish")
    async def unpublish_coupon(cid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.coupons.update_one(
            {"id": cid, "workspace_id": user["workspace_id"]},
            {"$set": {"state": "draft", "status": "draft"}})
        if r.matched_count == 0: raise HTTPException(404, "Not found")
        return {"ok": True, "state": "draft", "status": "draft"}

    # ---------- Admin enrichment ----------
    @api.get("/admin/users-detailed")
    async def admin_users_detailed(user: dict = Depends(get_current_user)):
        if user.get("role") != "superadmin":
            raise HTTPException(403, "Superadmin only")
        rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(2000)
        ws_docs = await db.workspaces.find({}, {"_id": 0}).to_list(500)
        ws_map = {w["id"]: w for w in ws_docs}
        for r in rows:
            ws = ws_map.get(r.get("workspace_id"), {})
            sub = ws.get("subscription") or {}
            r["workspace_name"] = ws.get("name", "")
            r["plan"] = sub.get("plan", "trial")
            r["subscription_status"] = sub.get("status", "trialing")
            r["next_billing"] = sub.get("next_billing_at")
            r["state"] = "deleted" if r.get("deleted_at") else ("suspended" if r.get("suspended") else "active")
            r["joined_at"] = r.get("created_at")
            # coupon/customer counts (best-effort)
            r["coupon_count"] = await db.coupons.count_documents({"workspace_id": r.get("workspace_id")})
            r["customer_count"] = await db.customers.count_documents({"workspace_id": r.get("workspace_id"), "is_deleted": {"$ne": True}})
        return rows

    @api.get("/admin/affiliates")
    async def admin_affiliates(user: dict = Depends(get_current_user)):
        if user.get("role") != "superadmin":
            raise HTTPException(403, "Superadmin only")
        # Aggregate referral loops → each unique referrer becomes an affiliate.
        pipeline = [
            {"$match": {"referrer": {"$exists": True, "$nin": [None, ""]}}},
            {"$group": {"_id": "$referrer",
                        "referrals": {"$sum": 1},
                        "revenue": {"$sum": {"$ifNull": ["$revenue", 0]}}}},
            {"$sort": {"referrals": -1}},
            {"$limit": 500},
        ]
        cursor = db.redemptions.aggregate(pipeline)
        rows = []
        async for r in cursor:
            rows.append({"referrer": r["_id"], "referrals": r["referrals"], "revenue": round(r.get("revenue") or 0, 2)})
        return rows
