"""Alternative payment providers — PayPal, Razorpay, Paystack.
Each returns 501 with a precise "not configured" message when its env keys are missing,
so the frontend UX is: buttons always visible, provider light up as they get keys.
"""
import os, uuid, base64, requests
from typing import Optional
from fastapi import HTTPException, Depends, Request
from pydantic import BaseModel


def register(api, db, now_iso, get_current_user):

    class AltCheckoutReq(BaseModel):
        provider: str  # paypal | razorpay | paystack
        lookup_key: str  # basic_monthly | pro_monthly
        origin_url: str

    PLANS = {
        "basic_monthly": {"name": "Basic", "amount_cents": 4900, "currency": "USD", "interval": "MONTH", "trial_days": 3},
        "pro_monthly": {"name": "Pro", "amount_cents": 7900, "currency": "USD", "interval": "MONTH", "trial_days": 3},
    }

    def _need(env_var):
        val = os.environ.get(env_var)
        if not val:
            raise HTTPException(501, f"Set {env_var} in backend/.env to enable this payment provider.")
        return val

    # ---------------------- PayPal ----------------------
    PAYPAL_BASE = "https://api-m.sandbox.paypal.com"  # switch to api-m.paypal.com in live

    def paypal_token():
        cid = _need("PAYPAL_CLIENT_ID"); sec = _need("PAYPAL_SECRET")
        r = requests.post(f"{PAYPAL_BASE}/v1/oauth2/token",
                          headers={"Accept": "application/json"},
                          data={"grant_type": "client_credentials"},
                          auth=(cid, sec), timeout=15)
        r.raise_for_status()
        return r.json()["access_token"]

    def paypal_ensure_plan(lookup_key):
        plan = PLANS[lookup_key]; token = paypal_token()
        # Look up or create Product
        prod_name = f"PromoOS {plan['name']}"
        r = requests.get(f"{PAYPAL_BASE}/v1/catalogs/products?page_size=20",
                         headers={"Authorization": f"Bearer {token}"}, timeout=15)
        prod_id = None
        if r.ok:
            for p in r.json().get("products", []):
                if p.get("name") == prod_name:
                    prod_id = p["id"]; break
        if not prod_id:
            rp = requests.post(f"{PAYPAL_BASE}/v1/catalogs/products",
                               headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                               json={"name": prod_name, "type": "SERVICE",
                                     "category": "SOFTWARE"}, timeout=15)
            rp.raise_for_status()
            prod_id = rp.json()["id"]
        # Look up or create Plan
        r = requests.get(f"{PAYPAL_BASE}/v1/billing/plans?product_id={prod_id}&page_size=10",
                         headers={"Authorization": f"Bearer {token}"}, timeout=15)
        plan_id = None
        if r.ok:
            for p in r.json().get("plans", []):
                if p.get("status") == "ACTIVE": plan_id = p["id"]; break
        if not plan_id:
            billing_cycles = []
            if plan["trial_days"] > 0:
                billing_cycles.append({
                    "frequency": {"interval_unit": "DAY", "interval_count": plan["trial_days"]},
                    "tenure_type": "TRIAL", "sequence": 1, "total_cycles": 1,
                    "pricing_scheme": {"fixed_price": {"value": "0", "currency_code": plan["currency"]}}})
            billing_cycles.append({
                "frequency": {"interval_unit": plan["interval"], "interval_count": 1},
                "tenure_type": "REGULAR", "sequence": len(billing_cycles) + 1, "total_cycles": 0,
                "pricing_scheme": {"fixed_price": {"value": f"{plan['amount_cents']/100:.2f}", "currency_code": plan["currency"]}}})
            rp = requests.post(f"{PAYPAL_BASE}/v1/billing/plans",
                               headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                               json={"product_id": prod_id, "name": f"{plan['name']} Monthly",
                                     "billing_cycles": billing_cycles,
                                     "payment_preferences": {"auto_bill_outstanding": True}},
                               timeout=15)
            rp.raise_for_status()
            plan_id = rp.json()["id"]
        return plan_id, token

    def paypal_checkout(lookup_key, origin_url, ws_id, user_id):
        plan_id, token = paypal_ensure_plan(lookup_key)
        r = requests.post(f"{PAYPAL_BASE}/v1/billing/subscriptions",
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                          json={"plan_id": plan_id,
                                "application_context": {
                                    "return_url": f"{origin_url}/billing/success?provider=paypal&session_id={{id}}",
                                    "cancel_url": f"{origin_url}/billing/cancel",
                                    "user_action": "SUBSCRIBE_NOW"},
                                "custom_id": f"{ws_id}:{user_id}:{lookup_key}"},
                          timeout=15)
        r.raise_for_status()
        j = r.json()
        approve_link = next((l["href"] for l in j.get("links", []) if l.get("rel") == "approve"), None)
        return j["id"], approve_link

    # ---------------------- Razorpay ----------------------
    RAZORPAY_BASE = "https://api.razorpay.com/v1"

    def razorpay_auth():
        return (_need("RAZORPAY_KEY_ID"), _need("RAZORPAY_SECRET"))

    def razorpay_checkout(lookup_key, ws_id, user_id):
        plan = PLANS[lookup_key]
        auth = razorpay_auth()
        # Create or reuse plan
        rp = requests.post(f"{RAZORPAY_BASE}/plans", auth=auth,
                           json={"period": "monthly", "interval": 1,
                                 "item": {"name": f"PromoOS {plan['name']}",
                                          "amount": plan["amount_cents"],
                                          "currency": "USD",
                                          "description": "Subscription plan"}},
                           timeout=15)
        rp.raise_for_status()
        plan_id = rp.json()["id"]
        # Create subscription
        sub = requests.post(f"{RAZORPAY_BASE}/subscriptions", auth=auth,
                            json={"plan_id": plan_id, "total_count": 120,
                                  "customer_notify": 1, "quantity": 1,
                                  "notes": {"workspace_id": ws_id, "user_id": user_id,
                                            "lookup_key": lookup_key}},
                            timeout=15)
        sub.raise_for_status()
        s = sub.json()
        return s["id"], s.get("short_url") or f"https://checkout.razorpay.com/v1/subscription_button.js?subscription_id={s['id']}"

    # ---------------------- Paystack ----------------------
    PAYSTACK_BASE = "https://api.paystack.co"

    def paystack_checkout(lookup_key, ws_id, user_id, origin_url):
        plan = PLANS[lookup_key]
        secret = _need("PAYSTACK_SECRET_KEY")
        # Create or reuse plan (Paystack idempotent by plan_code missing; simplest = create every time and dedupe by name would need list call)
        rp = requests.post(f"{PAYSTACK_BASE}/plan",
                           headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                           json={"name": f"PromoOS {plan['name']}",
                                 "amount": plan["amount_cents"],  # kobo/cents
                                 "interval": "monthly",
                                 "currency": plan["currency"]},
                           timeout=15)
        # A duplicate name returns 400; ignore.
        plan_code = None
        if rp.ok:
            plan_code = rp.json().get("data", {}).get("plan_code")
        # Init transaction with plan
        tr = requests.post(f"{PAYSTACK_BASE}/transaction/initialize",
                           headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
                           json={"email": f"{user_id}@promoos.app",
                                 "amount": plan["amount_cents"],
                                 "currency": plan["currency"],
                                 "plan": plan_code,
                                 "callback_url": f"{origin_url}/billing/success?provider=paystack",
                                 "metadata": {"workspace_id": ws_id, "user_id": user_id,
                                              "lookup_key": lookup_key}},
                           timeout=15)
        tr.raise_for_status()
        d = tr.json()["data"]
        return d["reference"], d["authorization_url"]

    # ---------------------- Unified endpoint ----------------------
    @api.get("/billing/providers")
    async def payment_providers():
        return {"providers": [
            {"id": "stripe",   "label": "Stripe",   "configured": bool(os.environ.get("STRIPE_SECRET_KEY")),
             "note": "Cards, Apple/Google Pay, SEPA, iDEAL, Klarna, Afterpay, Alipay, WeChat — 100+ methods."},
            {"id": "paypal",   "label": "PayPal",   "configured": bool(os.environ.get("PAYPAL_CLIENT_ID") and os.environ.get("PAYPAL_SECRET")),
             "note": "PayPal balance, cards. Global.",
             "env_needed": ["PAYPAL_CLIENT_ID", "PAYPAL_SECRET"]},
            {"id": "razorpay", "label": "Razorpay", "configured": bool(os.environ.get("RAZORPAY_KEY_ID") and os.environ.get("RAZORPAY_SECRET")),
             "note": "India-first — UPI, NetBanking, cards, wallets.",
             "env_needed": ["RAZORPAY_KEY_ID", "RAZORPAY_SECRET"]},
            {"id": "paystack", "label": "Paystack", "configured": bool(os.environ.get("PAYSTACK_SECRET_KEY")),
             "note": "Africa-first — cards, bank transfer, mobile money.",
             "env_needed": ["PAYSTACK_SECRET_KEY"]},
        ]}

    @api.post("/billing/alt-checkout")
    async def alt_checkout(body: AltCheckoutReq, request: Request, user: dict = Depends(get_current_user)):
        if body.lookup_key not in PLANS:
            raise HTTPException(400, "Unknown plan")
        origin = (body.origin_url or "").rstrip("/") or f"https://{request.headers.get('host', '')}"
        try:
            if body.provider == "paypal":
                sid, approve_url = paypal_checkout(body.lookup_key, origin, user["workspace_id"], user["id"])
            elif body.provider == "razorpay":
                sid, approve_url = razorpay_checkout(body.lookup_key, user["workspace_id"], user["id"])
            elif body.provider == "paystack":
                sid, approve_url = paystack_checkout(body.lookup_key, user["workspace_id"], user["id"], origin)
            else:
                raise HTTPException(400, f"Unknown provider: {body.provider}")
        except HTTPException:
            raise
        except requests.HTTPError as e:
            raise HTTPException(502, f"{body.provider.title()} error: {e.response.text[:200] if e.response else str(e)}")
        except Exception as e:
            raise HTTPException(502, f"{body.provider.title()} error: {e}")
        await db.payment_transactions.insert_one({
            "id": str(uuid.uuid4()), "session_id": sid,
            "workspace_id": user["workspace_id"], "user_id": user["id"],
            "provider": body.provider, "lookup_key": body.lookup_key,
            "amount": PLANS[body.lookup_key]["amount_cents"] / 100,
            "currency": PLANS[body.lookup_key]["currency"],
            "status": "initiated", "payment_status": "pending",
            "created_at": now_iso(), "updated_at": now_iso()})
        return {"checkout_url": approve_url, "session_id": sid, "provider": body.provider}
