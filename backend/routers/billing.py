"""Phase 1 extras — Stripe billing, object storage, currencies, fonts, coupon share/download.
Attached to the main `api` router via `register_extras(api, db, deps)` in server.py.
"""
import os, uuid, io, base64, json, urllib.request, urllib.error, csv as _csv
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Header, UploadFile, File, Response
from pydantic import BaseModel
import requests
import stripe
import qrcode


# --------------------- Currencies (150+ ISO 4217) ---------------------
CURRENCIES = [
    {"code":"USD","name":"US Dollar","symbol":"$"},{"code":"EUR","name":"Euro","symbol":"€"},
    {"code":"GBP","name":"British Pound","symbol":"£"},{"code":"JPY","name":"Japanese Yen","symbol":"¥"},
    {"code":"CNY","name":"Chinese Yuan","symbol":"¥"},{"code":"INR","name":"Indian Rupee","symbol":"₹"},
    {"code":"AUD","name":"Australian Dollar","symbol":"A$"},{"code":"CAD","name":"Canadian Dollar","symbol":"C$"},
    {"code":"CHF","name":"Swiss Franc","symbol":"Fr"},{"code":"HKD","name":"Hong Kong Dollar","symbol":"HK$"},
    {"code":"SGD","name":"Singapore Dollar","symbol":"S$"},{"code":"SEK","name":"Swedish Krona","symbol":"kr"},
    {"code":"NOK","name":"Norwegian Krone","symbol":"kr"},{"code":"DKK","name":"Danish Krone","symbol":"kr"},
    {"code":"NZD","name":"New Zealand Dollar","symbol":"NZ$"},{"code":"MXN","name":"Mexican Peso","symbol":"$"},
    {"code":"BRL","name":"Brazilian Real","symbol":"R$"},{"code":"ARS","name":"Argentine Peso","symbol":"$"},
    {"code":"CLP","name":"Chilean Peso","symbol":"$"},{"code":"COP","name":"Colombian Peso","symbol":"$"},
    {"code":"PEN","name":"Peruvian Sol","symbol":"S/"},{"code":"UYU","name":"Uruguayan Peso","symbol":"$U"},
    {"code":"ZAR","name":"South African Rand","symbol":"R"},{"code":"AED","name":"UAE Dirham","symbol":"د.إ"},
    {"code":"SAR","name":"Saudi Riyal","symbol":"﷼"},{"code":"QAR","name":"Qatari Riyal","symbol":"﷼"},
    {"code":"KWD","name":"Kuwaiti Dinar","symbol":"د.ك"},{"code":"BHD","name":"Bahraini Dinar","symbol":".د.ب"},
    {"code":"OMR","name":"Omani Rial","symbol":"﷼"},{"code":"JOD","name":"Jordanian Dinar","symbol":"د.ا"},
    {"code":"ILS","name":"Israeli Shekel","symbol":"₪"},{"code":"TRY","name":"Turkish Lira","symbol":"₺"},
    {"code":"EGP","name":"Egyptian Pound","symbol":"£"},{"code":"NGN","name":"Nigerian Naira","symbol":"₦"},
    {"code":"KES","name":"Kenyan Shilling","symbol":"KSh"},{"code":"GHS","name":"Ghanaian Cedi","symbol":"₵"},
    {"code":"UGX","name":"Ugandan Shilling","symbol":"USh"},{"code":"TZS","name":"Tanzanian Shilling","symbol":"TSh"},
    {"code":"MAD","name":"Moroccan Dirham","symbol":"د.م."},{"code":"TND","name":"Tunisian Dinar","symbol":"د.ت"},
    {"code":"DZD","name":"Algerian Dinar","symbol":"د.ج"},{"code":"XOF","name":"West African CFA","symbol":"CFA"},
    {"code":"XAF","name":"Central African CFA","symbol":"FCFA"},{"code":"KRW","name":"South Korean Won","symbol":"₩"},
    {"code":"TWD","name":"Taiwan Dollar","symbol":"NT$"},{"code":"THB","name":"Thai Baht","symbol":"฿"},
    {"code":"VND","name":"Vietnamese Dong","symbol":"₫"},{"code":"IDR","name":"Indonesian Rupiah","symbol":"Rp"},
    {"code":"MYR","name":"Malaysian Ringgit","symbol":"RM"},{"code":"PHP","name":"Philippine Peso","symbol":"₱"},
    {"code":"PKR","name":"Pakistani Rupee","symbol":"₨"},{"code":"BDT","name":"Bangladeshi Taka","symbol":"৳"},
    {"code":"LKR","name":"Sri Lankan Rupee","symbol":"Rs"},{"code":"NPR","name":"Nepalese Rupee","symbol":"₨"},
    {"code":"KZT","name":"Kazakhstani Tenge","symbol":"₸"},{"code":"UZS","name":"Uzbekistani Som","symbol":"сўм"},
    {"code":"RUB","name":"Russian Ruble","symbol":"₽"},{"code":"UAH","name":"Ukrainian Hryvnia","symbol":"₴"},
    {"code":"PLN","name":"Polish Zloty","symbol":"zł"},{"code":"CZK","name":"Czech Koruna","symbol":"Kč"},
    {"code":"HUF","name":"Hungarian Forint","symbol":"Ft"},{"code":"RON","name":"Romanian Leu","symbol":"lei"},
    {"code":"BGN","name":"Bulgarian Lev","symbol":"лв"},{"code":"HRK","name":"Croatian Kuna","symbol":"kn"},
    {"code":"RSD","name":"Serbian Dinar","symbol":"дин"},{"code":"ISK","name":"Icelandic Krona","symbol":"kr"},
    {"code":"MDL","name":"Moldovan Leu","symbol":"L"},{"code":"GEL","name":"Georgian Lari","symbol":"₾"},
    {"code":"AMD","name":"Armenian Dram","symbol":"֏"},{"code":"AZN","name":"Azerbaijani Manat","symbol":"₼"},
    {"code":"BYN","name":"Belarusian Ruble","symbol":"Br"},{"code":"CRC","name":"Costa Rican Colón","symbol":"₡"},
    {"code":"DOP","name":"Dominican Peso","symbol":"RD$"},{"code":"GTQ","name":"Guatemalan Quetzal","symbol":"Q"},
    {"code":"HNL","name":"Honduran Lempira","symbol":"L"},{"code":"JMD","name":"Jamaican Dollar","symbol":"J$"},
    {"code":"NIO","name":"Nicaraguan Córdoba","symbol":"C$"},{"code":"PAB","name":"Panamanian Balboa","symbol":"B/."},
    {"code":"PYG","name":"Paraguayan Guaraní","symbol":"₲"},{"code":"BOB","name":"Bolivian Boliviano","symbol":"Bs"},
    {"code":"VEF","name":"Venezuelan Bolívar","symbol":"Bs"},{"code":"TTD","name":"Trinidad Dollar","symbol":"TT$"},
    {"code":"BBD","name":"Barbadian Dollar","symbol":"Bds$"},{"code":"BSD","name":"Bahamian Dollar","symbol":"B$"},
    {"code":"BZD","name":"Belize Dollar","symbol":"BZ$"},{"code":"XCD","name":"East Caribbean Dollar","symbol":"EC$"},
    {"code":"GYD","name":"Guyanese Dollar","symbol":"G$"},{"code":"SRD","name":"Surinamese Dollar","symbol":"$"},
    {"code":"FJD","name":"Fijian Dollar","symbol":"FJ$"},{"code":"PGK","name":"Papua New Guinean Kina","symbol":"K"},
    {"code":"SBD","name":"Solomon Islands Dollar","symbol":"SI$"},{"code":"TOP","name":"Tongan Paʻanga","symbol":"T$"},
    {"code":"WST","name":"Samoan Tala","symbol":"WS$"},{"code":"VUV","name":"Vanuatu Vatu","symbol":"VT"},
    {"code":"XPF","name":"CFP Franc","symbol":"₣"},{"code":"KHR","name":"Cambodian Riel","symbol":"៛"},
    {"code":"LAK","name":"Lao Kip","symbol":"₭"},{"code":"MMK","name":"Myanmar Kyat","symbol":"K"},
    {"code":"MNT","name":"Mongolian Tögrög","symbol":"₮"},{"code":"BND","name":"Brunei Dollar","symbol":"B$"},
    {"code":"MOP","name":"Macanese Pataca","symbol":"MOP$"},{"code":"AFN","name":"Afghan Afghani","symbol":"؋"},
    {"code":"IRR","name":"Iranian Rial","symbol":"﷼"},{"code":"IQD","name":"Iraqi Dinar","symbol":"ع.د"},
    {"code":"LBP","name":"Lebanese Pound","symbol":"ل.ل"},{"code":"SYP","name":"Syrian Pound","symbol":"£"},
    {"code":"YER","name":"Yemeni Rial","symbol":"﷼"},{"code":"SDG","name":"Sudanese Pound","symbol":"£"},
    {"code":"SOS","name":"Somali Shilling","symbol":"Sh"},{"code":"DJF","name":"Djiboutian Franc","symbol":"Fdj"},
    {"code":"ETB","name":"Ethiopian Birr","symbol":"Br"},{"code":"ERN","name":"Eritrean Nakfa","symbol":"Nfk"},
    {"code":"RWF","name":"Rwandan Franc","symbol":"FRw"},{"code":"BIF","name":"Burundian Franc","symbol":"FBu"},
    {"code":"CDF","name":"Congolese Franc","symbol":"FC"},{"code":"MZN","name":"Mozambican Metical","symbol":"MT"},
    {"code":"MWK","name":"Malawian Kwacha","symbol":"MK"},{"code":"ZMW","name":"Zambian Kwacha","symbol":"ZK"},
    {"code":"BWP","name":"Botswanan Pula","symbol":"P"},{"code":"NAD","name":"Namibian Dollar","symbol":"N$"},
    {"code":"LSL","name":"Lesotho Loti","symbol":"L"},{"code":"SZL","name":"Swazi Lilangeni","symbol":"E"},
    {"code":"MUR","name":"Mauritian Rupee","symbol":"₨"},{"code":"SCR","name":"Seychellois Rupee","symbol":"₨"},
    {"code":"MVR","name":"Maldivian Rufiyaa","symbol":"Rf"},{"code":"BTN","name":"Bhutanese Ngultrum","symbol":"Nu."},
    {"code":"KGS","name":"Kyrgystani Som","symbol":"с"},{"code":"TJS","name":"Tajikistani Somoni","symbol":"SM"},
    {"code":"TMT","name":"Turkmenistan Manat","symbol":"T"},{"code":"CUP","name":"Cuban Peso","symbol":"₱"},
    {"code":"HTG","name":"Haitian Gourde","symbol":"G"},{"code":"AWG","name":"Aruban Florin","symbol":"ƒ"},
    {"code":"ANG","name":"Neth. Antillean Guilder","symbol":"ƒ"},{"code":"KYD","name":"Cayman Islands Dollar","symbol":"CI$"},
    {"code":"BMD","name":"Bermudan Dollar","symbol":"BD$"},{"code":"GIP","name":"Gibraltar Pound","symbol":"£"},
    {"code":"FKP","name":"Falkland Pound","symbol":"£"},{"code":"SHP","name":"Saint Helena Pound","symbol":"£"},
    {"code":"GGP","name":"Guernsey Pound","symbol":"£"},{"code":"JEP","name":"Jersey Pound","symbol":"£"},
    {"code":"IMP","name":"Manx Pound","symbol":"£"},{"code":"BTC","name":"Bitcoin","symbol":"₿"},
    {"code":"ETH","name":"Ethereum","symbol":"Ξ"},{"code":"USDT","name":"Tether","symbol":"₮"},
    {"code":"USDC","name":"USD Coin","symbol":"$"},
]

# --------------------- Fonts library ---------------------
FONTS = [
    "Cabinet Grotesk","Inter","Poppins","Montserrat","Playfair Display","Roboto",
    "Open Sans","Lato","Nunito","Merriweather","Raleway","Oswald","Bebas Neue",
    "PT Sans","PT Serif","Source Sans Pro","Roboto Slab","Roboto Condensed","Rubik",
    "Work Sans","Fira Sans","Fira Code","JetBrains Mono","IBM Plex Sans","IBM Plex Serif",
    "IBM Plex Mono","Space Grotesk","Space Mono","DM Sans","DM Serif Display","DM Mono",
    "Manrope","Karla","Barlow","Cormorant Garamond","Libre Baskerville","Libre Franklin",
    "Archivo","Archivo Black","Archivo Narrow","Josefin Sans","Josefin Slab","Quicksand",
    "Comfortaa","Pacifico","Dancing Script","Great Vibes","Satisfy","Sacramento",
    "Caveat","Amatic SC","Permanent Marker","Lobster","Righteous","Anton","Abel",
    "Alegreya","Alegreya Sans","Assistant","Barlow Condensed","Bitter","Cairo","Catamaran",
    "Chivo","Crimson Text","Dosis","EB Garamond","Exo 2","Fjalla One","Hind","Kanit",
    "Muli","Noto Sans","Noto Serif","Nunito Sans","Oxygen","Public Sans","Questrial","Sora",
    "Titillium Web","Ubuntu","Varela Round","Vollkorn","Yanone Kaffeesatz","Zilla Slab",
]


def register_extras(api, db, EMERGENT_LLM_KEY, PUBLIC_APP_URL, now_iso, get_current_user,
                    require_writer, admin_log):
    """Register all Phase 1 extras onto the main api router. Called from server.py."""

    # ---------- Stripe setup ----------
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    # Plan catalog: 3-day trial for both plans, "unlimited" tier gating handled in app.
    # `payment_link` is a hosted Stripe Payment Link (public URL) — merchants who don't want to
    # wire full webhook automation can subscribe instantly via the hosted checkout.
    PLANS = [
        {"lookup_key": "basic_monthly", "name": "Basic", "amount_cents": 4900, "currency": "usd",
         "interval": "month", "trial_days": 3,
         "payment_link": "https://buy.stripe.com/5kQ28qcDSfMK3ni5MD2kw0f",
         "features": ["Unlimited coupons","Unlimited gift cards","AI Copilot","Email + SMS + WhatsApp",
                      "Loyalty program","Referral engine","5 widget variants","POS connectors",
                      "Public REST API","Admin portal"]},
        {"lookup_key": "pro_monthly", "name": "Pro", "amount_cents": 7900, "currency": "usd",
         "interval": "month", "trial_days": 3,
         "payment_link": "https://buy.stripe.com/eVqfZg33igQO9LG5MD2kw0e",
         "features": ["Everything in Basic","Priority AI compute","Unlimited API keys",
                      "Custom domain publishing","Funnel Builder","Multi-workspace",
                      "Advanced analytics + exports","Dedicated support"]},
    ]

    @api.get("/billing/plans")
    async def billing_plans():
        # Expose lookup_keys and marketing metadata to frontend.
        return {"plans": [
            {"lookup_key": p["lookup_key"], "name": p["name"], "price": p["amount_cents"] / 100,
             "currency": p["currency"], "interval": p["interval"], "trial_days": p["trial_days"],
             "payment_link": p.get("payment_link", ""),
             "features": p["features"]} for p in PLANS
        ], "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", "")}

    async def _ensure_stripe_catalog():
        """Idempotent: create products/prices in Stripe. Called on first checkout request."""
        for p in PLANS:
            product_id = f"promoos_{p['lookup_key']}"
            # look up product by metadata.emergent_product_id
            existing_product = None
            for prod in stripe.Product.list(active=True, limit=100).auto_paging_iter():
                if prod.to_dict().get("metadata", {}).get("emergent_product_id") == product_id:
                    existing_product = prod; break
            if not existing_product:
                existing_product = stripe.Product.create(
                    name=f"PromoOS {p['name']}",
                    tax_code="txcd_10103001",  # SaaS
                    metadata={"managed_by": "emergent", "emergent_product_id": product_id})
            # ensure price with lookup_key
            prices = stripe.Price.list(lookup_keys=[p["lookup_key"]], active=True, limit=1).data
            need_create = False
            if not prices:
                need_create = True
            elif prices[0].unit_amount != p["amount_cents"] or prices[0].currency != p["currency"]:
                stripe.Price.modify(prices[0].id, active=False); need_create = True
            if need_create:
                stripe.Price.create(product=existing_product.id, unit_amount=p["amount_cents"],
                    currency=p["currency"], lookup_key=p["lookup_key"], transfer_lookup_key=True,
                    recurring={"interval": p["interval"], "trial_period_days": p["trial_days"]})

    class CheckoutRequest(BaseModel):
        lookup_key: str
        origin_url: str

    def _validate_origin(origin_url: str, request: Request) -> str:
        # Whitelist: PUBLIC_APP_URL, the request's own Origin header, or its host.
        # Prevents an authenticated user from redirecting Stripe post-checkout to an arbitrary domain.
        allowed = set()
        if PUBLIC_APP_URL:
            allowed.add(PUBLIC_APP_URL.rstrip("/"))
        origin_hdr = request.headers.get("origin")
        if origin_hdr:
            allowed.add(origin_hdr.rstrip("/"))
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if host:
            allowed.add(f"{proto}://{host}".rstrip("/"))
        candidate = (origin_url or "").rstrip("/")
        if not any(candidate == a or candidate.startswith(a + "/") for a in allowed):
            # Fall back to request-derived origin instead of trusting client.
            return f"{proto}://{host}" if host else (PUBLIC_APP_URL or "").rstrip("/")
        return candidate

    @api.post("/billing/checkout")
    async def billing_checkout(req: CheckoutRequest, request: Request, user: dict = Depends(get_current_user)):
        plan = next((p for p in PLANS if p["lookup_key"] == req.lookup_key), None)
        if not plan:
            raise HTTPException(400, "Unknown plan")
        origin = _validate_origin(req.origin_url, request)
        try:
            await _ensure_stripe_catalog()
            prices = stripe.Price.list(lookup_keys=[req.lookup_key], active=True, limit=1).data
            if not prices:
                raise HTTPException(500, f"Price not found: {req.lookup_key}")
            session = stripe.checkout.Session.create(
                line_items=[{"price": prices[0].id, "quantity": 1}],
                mode="subscription",
                subscription_data={"trial_period_days": plan["trial_days"],
                                   "metadata": {"workspace_id": user["workspace_id"],
                                                "user_id": user["id"], "lookup_key": req.lookup_key}},
                success_url=f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{origin}/billing/cancel",
                metadata={"workspace_id": user["workspace_id"], "user_id": user["id"],
                          "lookup_key": req.lookup_key})
        except stripe.error.StripeError as e:
            raise HTTPException(502, f"Stripe error: {e.user_message or str(e)}")
        await db.payment_transactions.insert_one({
            "id": str(uuid.uuid4()), "session_id": session.id,
            "workspace_id": user["workspace_id"], "user_id": user["id"],
            "lookup_key": req.lookup_key, "amount": plan["amount_cents"] / 100,
            "currency": plan["currency"], "status": "initiated", "payment_status": "pending",
            "created_at": now_iso(), "updated_at": now_iso()})
        return {"checkout_url": session.url, "session_id": session.id}

    @api.get("/billing/status/{session_id}")
    async def billing_status(session_id: str):
        rec = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
        if not rec:
            raise HTTPException(404, "Transaction not found")
        # Sync from Stripe if still pending (webhook fallback).
        if rec.get("payment_status") != "paid":
            try:
                s = stripe.checkout.Session.retrieve(session_id)
                if s.payment_status == "paid" or s.status == "complete":
                    await db.payment_transactions.update_one(
                        {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                        {"$set": {"status": "completed", "payment_status": "paid",
                                  "stripe_subscription_id": s.subscription,
                                  "stripe_customer_id": s.customer,
                                  "updated_at": now_iso()}})
                    # Activate subscription on workspace
                    if s.subscription and rec.get("workspace_id"):
                        await db.workspaces.update_one(
                            {"id": rec["workspace_id"]},
                            {"$set": {"subscription": {
                                "status": "active",
                                "plan": rec.get("lookup_key"),
                                "stripe_subscription_id": s.subscription,
                                "stripe_customer_id": s.customer,
                                "activated_at": now_iso()}}})
                    rec = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
            except stripe.error.StripeError:
                pass
        return {"session_id": rec["session_id"], "status": rec["status"],
                "payment_status": rec["payment_status"],
                "lookup_key": rec.get("lookup_key")}

    @api.get("/billing/subscription")
    async def billing_subscription(user: dict = Depends(get_current_user)):
        ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
        sub = ws.get("subscription") or {}
        return {"status": sub.get("status", "trialing" if not sub else sub.get("status")),
                "plan": sub.get("plan"), "activated_at": sub.get("activated_at"),
                "trial_ends_at": sub.get("trial_ends_at")}

    @api.post("/stripe/webhook")
    async def stripe_webhook(request: Request):
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        try:
            if STRIPE_WEBHOOK_SECRET:
                event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
            elif os.environ.get("STRIPE_MODE", "test") == "test":
                # Sandbox only: accept unsigned bodies for local development.
                event = json.loads(payload.decode())
            else:
                raise HTTPException(500, "STRIPE_WEBHOOK_SECRET not configured (required in live mode)")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(400, "Invalid signature")
        obj, t = event["data"]["object"], event["type"]
        if t == "checkout.session.completed":
            sid = obj.get("id")
            meta = obj.get("metadata") or {}
            ws_id = meta.get("workspace_id")
            lookup_key = meta.get("lookup_key")
            # Fallback: Payment Links (from Pricing page) don't attach workspace_id via metadata.
            # We pass workspace_id as client_reference_id from the frontend, and infer the plan
            # from amount_total when lookup_key is missing.
            if not ws_id:
                ws_id = obj.get("client_reference_id")
            if not lookup_key:
                amt = obj.get("amount_total")
                if amt:
                    for _p in PLANS:
                        if _p["amount_cents"] == amt:
                            lookup_key = _p["lookup_key"]; break
            await db.payment_transactions.update_one(
                {"session_id": sid, "payment_status": {"$ne": "paid"}},
                {"$set": {"status": "completed", "payment_status": obj.get("payment_status", "paid"),
                          "stripe_subscription_id": obj.get("subscription"),
                          "stripe_customer_id": obj.get("customer"),
                          "updated_at": now_iso()}})
            if ws_id:
                await db.workspaces.update_one({"id": ws_id}, {"$set": {"subscription": {
                    "status": "active", "plan": lookup_key,
                    "stripe_subscription_id": obj.get("subscription"),
                    "stripe_customer_id": obj.get("customer"),
                    "activated_at": now_iso(),
                    "source": "payment_link" if not meta.get("workspace_id") else "checkout"}}})
        elif t in ("customer.subscription.deleted", "customer.subscription.updated"):
            sub_id = obj.get("id"); status = obj.get("status")
            await db.workspaces.update_one({"subscription.stripe_subscription_id": sub_id},
                {"$set": {"subscription.status": status}})
        return {"status": "ok"}

    # ---------- Object storage upload ----------
    STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
    STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
    APP_NAME = "promoos"
    _storage_key = {"value": None}

    def _init_storage(force=False):
        if _storage_key["value"] and not force:
            return _storage_key["value"]
        try:
            r = requests.post(f"{STORAGE_URL}/init",
                              json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
            r.raise_for_status()
            _storage_key["value"] = r.json()["storage_key"]
        except Exception:
            _storage_key["value"] = None
        return _storage_key["value"]

    def _put_object(path, data, content_type):
        k = _init_storage()
        if not k:
            raise HTTPException(502, "Storage not initialized. Check EMERGENT_LLM_KEY.")
        r = requests.put(f"{STORAGE_URL}/objects/{path}",
                         headers={"X-Storage-Key": k, "Content-Type": content_type},
                         data=data, timeout=120)
        if r.status_code == 404:
            _init_storage(force=True)
            r = requests.put(f"{STORAGE_URL}/objects/{path}",
                             headers={"X-Storage-Key": _storage_key["value"], "Content-Type": content_type},
                             data=data, timeout=120)
        r.raise_for_status()
        return r.json()

    def _get_object(path):
        k = _init_storage()
        r = requests.get(f"{STORAGE_URL}/objects/{path}",
                         headers={"X-Storage-Key": k}, timeout=60)
        if r.status_code == 404:
            _init_storage(force=True)
            r = requests.get(f"{STORAGE_URL}/objects/{path}",
                             headers={"X-Storage-Key": _storage_key["value"]}, timeout=60)
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "application/octet-stream")

    ALLOWED_UPLOAD_MIMES = {"image/jpeg", "image/png", "image/webp", "image/svg+xml",
                            "image/gif", "image/heic", "image/heif"}
    MAX_UPLOAD_BYTES = 10 * 1024 * 1024

    @api.post("/uploads")
    async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
        require_writer(user)
        ct = (file.content_type or "").lower()
        if ct not in ALLOWED_UPLOAD_MIMES:
            raise HTTPException(400, f"Unsupported type {ct}. Allowed: JPG, PNG, WebP, SVG, GIF, HEIC.")
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, f"File too large. Max {MAX_UPLOAD_BYTES // 1024 // 1024}MB.")
        ext = (file.filename or "bin").split(".")[-1].lower() if "." in (file.filename or "") else "bin"
        fid = str(uuid.uuid4())
        path = f"{APP_NAME}/uploads/{user['workspace_id']}/{fid}.{ext}"
        try:
            result = _put_object(path, data, ct)
        except Exception as e:
            raise HTTPException(502, f"Upload failed: {e}")
        doc = {"id": fid, "workspace_id": user["workspace_id"], "user_id": user["id"],
               "storage_path": result["path"], "original_filename": file.filename,
               "content_type": ct, "size": result.get("size", len(data)),
               "is_deleted": False, "created_at": now_iso()}
        await db.uploads.insert_one({**doc})
        return {"id": fid, "url": f"/api/uploads/{fid}", "size": doc["size"],
                "content_type": ct, "path": result["path"]}

    @api.get("/uploads/{fid}")
    async def download_file(fid: str):
        rec = await db.uploads.find_one({"id": fid, "is_deleted": False}, {"_id": 0})
        if not rec:
            raise HTTPException(404, "File not found")
        try:
            data, ct = _get_object(rec["storage_path"])
        except Exception as e:
            raise HTTPException(502, f"Fetch failed: {e}")
        return Response(content=data, media_type=rec.get("content_type", ct),
                        headers={"Cache-Control": "public, max-age=3600"})

    @api.get("/uploads")
    async def list_uploads(user: dict = Depends(get_current_user)):
        docs = await db.uploads.find(
            {"workspace_id": user["workspace_id"], "is_deleted": False},
            {"_id": 0, "storage_path": 0}).sort("created_at", -1).to_list(200)
        for d in docs:
            d["url"] = f"/api/uploads/{d['id']}"
        return docs

    @api.delete("/uploads/{fid}")
    async def delete_upload(fid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.uploads.update_one(
            {"id": fid, "workspace_id": user["workspace_id"]},
            {"$set": {"is_deleted": True, "deleted_at": now_iso()}})
        if r.matched_count == 0:
            raise HTTPException(404, "Not found")
        return {"ok": True}

    # ---------- Currencies + Fonts ----------
    @api.get("/currencies")
    async def currencies_route():
        return CURRENCIES

    @api.get("/fonts")
    async def fonts_route():
        return {"fonts": FONTS}

    # ---------- Coupon share/embed/download ----------
    @api.get("/coupons/{cid}/share")
    async def coupon_share(cid: str, request: Request, user: dict = Depends(get_current_user)):
        c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]},
                                       {"_id": 0}) or None
        if not c:
            raise HTTPException(404, "Coupon not found")
        origin = (PUBLIC_APP_URL or "").rstrip("/")
        if not origin:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
            origin = f"{proto}://{host}"
        code = c["code"]
        landing_url = f"{origin}/c/{code}"
        # URL-encode all dynamic values so headlines with quotes/spaces/emoji
        # don't produce broken share intents (X in particular fails silently
        # on unencoded quote characters).
        from urllib.parse import quote
        headline = c.get("headline") or c.get("name") or "Save on your next order"
        name_ = c.get("name") or "Special offer"
        e_url = quote(landing_url, safe="")
        e_text = quote(headline, safe="")
        e_subj = quote(f"Special offer from {name_}", safe="")
        return {
            "code": code, "cid": cid,
            "landing_url": landing_url,
            "embed_snippets": {v: f'<script src="{origin}/api/embed/coupon.js?variant={v}" data-promoos-code="{code}" async></script>'
                                for v in ("inline","popup","bar","wheel","wallet")},
            "share_links": {
                "email": f"mailto:?subject={e_subj}&body={e_url}",
                "twitter": f"https://x.com/intent/post?url={e_url}&text={e_text}",
                "facebook": f"https://www.facebook.com/sharer/sharer.php?u={e_url}",
                "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={e_url}",
                "whatsapp": f"https://wa.me/?text={e_text}%20{e_url}",
                "telegram": f"https://t.me/share/url?url={e_url}&text={e_text}",
                "pinterest": f"https://pinterest.com/pin/create/button/?url={e_url}&description={e_text}",
                "reddit": f"https://reddit.com/submit?url={e_url}&title={e_text}",
            },
        }

    @api.get("/coupons/{cid}/download.png")
    async def coupon_download_png(cid: str, user: dict = Depends(get_current_user)):
        c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]}, {"_id": 0})
        if not c:
            raise HTTPException(404, "Coupon not found")
        # Render a printable card as PNG via PIL
        from PIL import Image, ImageDraw, ImageFont
        W, H = 1200, 630
        img = Image.new("RGB", (W, H), color=(10, 10, 10))
        draw = ImageDraw.Draw(img)
        try:
            f_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
            f_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
            f_code = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 72)
        except Exception:
            f_big = ImageFont.load_default(); f_med = f_big; f_code = f_big
        draw.rectangle([(0,0),(W,10)], fill=(0,92,238))
        draw.rectangle([(0,H-10),(W,H)], fill=(204,255,0))
        headline = (c.get("headline") or c.get("name") or "Special Offer")[:40]
        draw.text((60, 90), headline, fill=(255,255,255), font=f_big)
        desc = (c.get("description") or "")[:80]
        draw.text((60, 220), desc, fill=(180,180,180), font=f_med)
        draw.text((60, 340), "USE CODE", fill=(204,255,0), font=f_med)
        draw.rectangle([(60, 400),(W-60, 520)], outline=(0,92,238), width=4)
        draw.text((80, 420), c.get("code", ""), fill=(255,255,255), font=f_code)
        # QR to bottom right
        try:
            qr_img = qrcode.make(c.get("code", ""))
            qr_img = qr_img.resize((160,160))
            img.paste(qr_img, (W-220, 340))
        except Exception:
            pass
        buf = io.BytesIO(); img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png",
                        headers={"Content-Disposition": f'attachment; filename="coupon-{c.get("code","")}.png"'})

    # ---------- Admin: Stripe onboarding info ----------
    @api.get("/admin/stripe-onboarding")
    async def admin_stripe_onboarding(user: dict = Depends(get_current_user)):
        if user.get("role") != "superadmin":
            raise HTTPException(403, "Superadmin only")
        return {
            "onboarding_url": os.environ.get("STRIPE_ONBOARDING_URL", ""),
            "mode": os.environ.get("STRIPE_MODE", "test"),
            "account_id": os.environ.get("STRIPE_ACCOUNT_ID", ""),
            "publishable_key": os.environ.get("STRIPE_PUBLISHABLE_KEY", ""),
        }

    return {
        "init_storage": _init_storage,
    }
