"""POS webhook receivers + secret rotation + install snippets. Extracted from server.py iter-12.

Receives Shopify orders/create and WooCommerce order.created webhooks. HMAC-verifies when a
webhook_secrets.{provider} is set on the workspace; otherwise runs in trust-mode (dev only).
"""
import json, secrets as _pysecrets
from typing import Optional
from fastapi import HTTPException, Depends, Request
from pydantic import BaseModel


def register(api, db, PUBLIC_APP_URL, now_iso, get_current_user,
             encrypt_str, decrypt_str, hmac_ok, apply_from_pos):

    @api.post("/pos/{workspace_id}/shopify")
    async def shopify_webhook(workspace_id: str, request: Request):
        ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
        if not ws:
            raise HTTPException(404, "Workspace not found")
        raw = await request.body()
        ws_secrets = ws.get("webhook_secrets") or {}
        enc = ws_secrets.get("shopify")
        secret = decrypt_str(enc) if enc else None
        if secret:
            if not hmac_ok(secret, raw, request.headers.get("X-Shopify-Hmac-Sha256")):
                raise HTTPException(401, "Invalid HMAC signature")
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            raise HTTPException(400, "Invalid JSON body")
        total = float(payload.get("total_price") or payload.get("subtotal_price") or 0)
        order_id = str(payload.get("id") or payload.get("order_id") or "")
        customer_email = ((payload.get("customer") or {}).get("email") or
                          payload.get("email") or "shopify-guest")
        code = request.headers.get("X-PromoOS-Code")
        if not code:
            for na in payload.get("note_attributes") or []:
                if str(na.get("name", "")).lower() == "promoos":
                    code = na.get("value"); break
        if not code:
            return {"applied": False, "reason": "no PromoOS code on order"}
        return await apply_from_pos("shopify", workspace_id, code, total,
                                     customer_email, order_id,
                                     payload.get("currency"))

    @api.post("/pos/{workspace_id}/woocommerce")
    async def woocommerce_webhook(workspace_id: str, request: Request):
        ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
        if not ws:
            raise HTTPException(404, "Workspace not found")
        raw = await request.body()
        ws_secrets = ws.get("webhook_secrets") or {}
        enc = ws_secrets.get("woocommerce")
        secret = decrypt_str(enc) if enc else None
        if secret:
            if not hmac_ok(secret, raw, request.headers.get("X-WC-Webhook-Signature")):
                raise HTTPException(401, "Invalid HMAC signature")
        try:
            payload = json.loads(raw or b"{}")
        except Exception:
            raise HTTPException(400, "Invalid JSON body")
        total = float(payload.get("total") or 0)
        order_id = str(payload.get("id") or "")
        billing = payload.get("billing") or {}
        customer_email = billing.get("email") or "woo-guest"
        code = None
        for meta in payload.get("meta_data") or []:
            if str(meta.get("key", "")).lower() == "promoos":
                code = meta.get("value"); break
        if not code:
            for cline in payload.get("coupon_lines") or []:
                code = cline.get("code"); break
        if not code:
            return {"applied": False, "reason": "no PromoOS code on order"}
        return await apply_from_pos("woocommerce", workspace_id, code, total,
                                     customer_email, order_id,
                                     payload.get("currency"))

    class RotateSecretIn(BaseModel):
        provider: str  # 'shopify' or 'woocommerce'

    @api.post("/pos/rotate-secret")
    async def rotate_pos_secret(body: RotateSecretIn, user: dict = Depends(get_current_user)):
        if user.get("role") != "owner":
            raise HTTPException(403, "Only owners can rotate webhook secrets")
        if body.provider not in ("shopify", "woocommerce"):
            raise HTTPException(400, "provider must be shopify or woocommerce")
        secret = "whsec_" + _pysecrets.token_urlsafe(30)
        await db.workspaces.update_one(
            {"id": user["workspace_id"]},
            {"$set": {f"webhook_secrets.{body.provider}": encrypt_str(secret),
                      f"webhook_secrets.{body.provider}_rotated_at": now_iso(),
                      f"webhook_secrets.{body.provider}_preview": secret[:14] + "…"}})
        return {"ok": True, "provider": body.provider, "secret": secret}

    @api.delete("/pos/secret/{provider}")
    async def clear_pos_secret(provider: str, user: dict = Depends(get_current_user)):
        if user.get("role") != "owner":
            raise HTTPException(403, "Only owners can clear webhook secrets")
        if provider not in ("shopify", "woocommerce"):
            raise HTTPException(400, "provider must be shopify or woocommerce")
        await db.workspaces.update_one(
            {"id": user["workspace_id"]},
            {"$unset": {f"webhook_secrets.{provider}": "",
                        f"webhook_secrets.{provider}_rotated_at": "",
                        f"webhook_secrets.{provider}_preview": ""}})
        return {"ok": True}

    @api.get("/pos/secrets")
    async def get_pos_secrets(user: dict = Depends(get_current_user)):
        ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
        ws_secrets = ws.get("webhook_secrets") or {}
        out = {}
        for p in ("shopify", "woocommerce"):
            s = ws_secrets.get(p)
            out[p] = {
                "configured": bool(s),
                "preview": (s[:14] + "…") if s else None,
                "rotated_at": ws_secrets.get(f"{p}_rotated_at"),
            }
        return out

    @api.get("/pos/snippets")
    async def pos_snippets(request: Request, user: dict = Depends(get_current_user)):
        origin = (PUBLIC_APP_URL or "").rstrip("/")
        if not origin:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
            origin = f"{proto}://{host}"
        wid = user["workspace_id"]
        shopify_url = f"{origin}/api/pos/{wid}/shopify"
        woo_url = f"{origin}/api/pos/{wid}/woocommerce"
        return {
            "shopify": {
                "webhook_url": shopify_url,
                "topic": "orders/create",
                "instructions": [
                    "In your Shopify admin: Settings → Notifications → Webhooks → Create webhook.",
                    f"Event: 'Order creation', Format: JSON, URL: {shopify_url}",
                    "Add a Note attribute at checkout: name='promoos', value='CODE' (or send X-PromoOS-Code header from a custom app).",
                    "Every order will be posted to PromoOS. If the coupon is active, the redemption + revenue are logged automatically.",
                ],
            },
            "woocommerce": {
                "webhook_url": woo_url,
                "topic": "order.created",
                "instructions": [
                    "In WordPress admin: WooCommerce → Settings → Advanced → Webhooks → Add webhook.",
                    f"Topic: 'Order created', Delivery URL: {woo_url}, API version: v3.",
                    "In your theme or a snippet, set order meta_data { key:'promoos', value:'CODE' } before checkout — or use the built-in WooCommerce coupon field and PromoOS will match on coupon_lines[].code.",
                    "Every completed order fires the webhook, PromoOS records the redemption and attributes revenue.",
                ],
            },
            "generic_curl": (
                f"curl -X POST '{origin}/api/public/coupons/redeem' "
                "-H 'Content-Type: application/json' "
                "-d '{\"code\":\"CODE\",\"amount\":100,\"customer\":\"buyer@example.com\"}'"
            ),
        }
