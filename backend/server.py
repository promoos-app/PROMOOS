from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid, logging, jwt, bcrypt, io, base64, json, random, string, re, asyncio
from datetime import datetime, timezone, timedelta
import qrcode
import resend
from twilio.rest import Client as TwilioClient

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGO = "HS256"
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

TWILIO_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM_SMS = os.environ.get('TWILIO_FROM_SMS', '')
TWILIO_FROM_WHATSAPP = os.environ.get('TWILIO_FROM_WHATSAPP', '')
twilio_client = TwilioClient(TWILIO_SID, TWILIO_TOKEN) if (TWILIO_SID and TWILIO_TOKEN) else None
PUBLIC_APP_URL = os.environ.get('PUBLIC_APP_URL', '').rstrip('/')

app = FastAPI()
api = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("promoos")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def create_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    token = auth[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require_writer(user: dict):
    if user.get("role") == "viewer":
        raise HTTPException(403, "Viewers have read-only access")


# ---------------- Models ----------------
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    workspace_name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class BrandIn(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    font: Optional[str] = None
    currency: Optional[str] = None


class CouponRules(BaseModel):
    min_cart: float = 0
    scope: str = "all"          # all | product | category
    scope_value: str = ""
    usage_limit: int = 0        # 0 = unlimited
    per_customer_limit: int = 1
    stackable: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    referral_enabled: bool = False
    referral_credit_pct: float = 10


class CouponIn(BaseModel):
    name: str
    type: str = "percentage"
    discount_value: float = 0
    code: Optional[str] = None
    headline: str = ""
    description: str = ""
    terms: str = ""
    cta: str = ""
    state: str = "draft"
    rules: CouponRules = Field(default_factory=CouponRules)
    image_url: Optional[str] = None


class StateIn(BaseModel):
    state: str


class BulkIn(BaseModel):
    count: int = 10


class ValidateIn(BaseModel):
    code: str
    cart_value: float = 0


class RedeemIn(BaseModel):
    code: str
    amount: float = 0
    customer: Optional[str] = None


class AICopyIn(BaseModel):
    prompt: str


class AIImageIn(BaseModel):
    prompt: str


class SendCouponEmailIn(BaseModel):
    to: List[EmailStr]
    subject: Optional[str] = None
    landing_url: Optional[str] = None


class SendCouponMessageIn(BaseModel):
    to: List[str]                # E.164 phone numbers
    channel: str = "sms"         # "sms" or "whatsapp"
    landing_url: Optional[str] = None


class ExperimentCreateIn(BaseModel):
    n: int = 3
    prompt: Optional[str] = None
    use_ai: bool = True


class ExperimentPromoteIn(BaseModel):
    variant_id: Optional[str] = None   # if None, auto-pick highest redemption rate


class LoyaltyConfigIn(BaseModel):
    enabled: bool = True
    points_per_dollar: float = 1.0
    tiers: List[dict] = []              # [{"name":"Bronze","threshold":0}, ...]


# ---------------- QR ----------------
def gen_qr(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0A0A0A", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def rand_code(prefix="SAVE"):
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ---------------- Auth routes ----------------
@api.post("/auth/register")
async def register(body: RegisterIn):
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    ws_id = str(uuid.uuid4())
    workspace = {
        "id": ws_id,
        "name": body.workspace_name or f"{body.name}'s Workspace",
        "logo_url": "", "primary_color": "#005CEE", "secondary_color": "#CCFF00",
        "font": "Cabinet Grotesk", "currency": "USD", "created_at": now_iso(),
    }
    await db.workspaces.insert_one(workspace)
    uid = str(uuid.uuid4())
    user = {"id": uid, "name": body.name, "email": email,
            "password_hash": hash_password(body.password), "role": "owner",
            "workspace_id": ws_id, "created_at": now_iso()}
    await db.users.insert_one(user)
    token = create_token(uid, email)
    return {"token": token, "user": {k: user[k] for k in ("id", "name", "email", "role", "workspace_id")}}


@api.post("/auth/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    # Brute-force lockout: 5 failed attempts in last 15 min => 429 (locked by email)
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    fails = await db.login_attempts.count_documents({"identifier": email, "created_at": {"$gt": cutoff}})
    if fails >= 5:
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.insert_one({"identifier": email, "created_at": now_iso()})
        raise HTTPException(401, "Invalid email or password")
    await db.login_attempts.delete_many({"identifier": email})
    token = create_token(user["id"], email)
    response.set_cookie(
        key="access_token", value=token, httponly=True, secure=True,
        samesite="none", max_age=7 * 24 * 3600, path="/")
    return {"token": token, "user": {k: user[k] for k in ("id", "name", "email", "role", "workspace_id")}}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ---------------- Workspace ----------------
@api.get("/workspace")
async def get_workspace(user: dict = Depends(get_current_user)):
    ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0})
    return ws


@api.put("/workspace/brand")
async def update_brand(body: BrandIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    if upd:
        await db.workspaces.update_one({"id": user["workspace_id"]}, {"$set": upd})
    return await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0})


@api.get("/team")
async def team(user: dict = Depends(get_current_user)):
    members = await db.users.find(
        {"workspace_id": user["workspace_id"]},
        {"_id": 0, "password_hash": 0}).to_list(100)
    return members


# ---------------- Coupons ----------------
def coupon_public(c: dict) -> dict:
    c.pop("_id", None)
    return c


@api.get("/coupons")
async def list_coupons(user: dict = Depends(get_current_user), state: Optional[str] = None):
    q = {"workspace_id": user["workspace_id"]}
    if state and state != "all":
        q["state"] = state
    coupons = await db.coupons.find(q, {"_id": 0, "qr_code": 0}).sort("created_at", -1).to_list(500)
    return coupons


@api.post("/coupons")
async def create_coupon(body: CouponIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    code = (body.code or rand_code()).upper()
    cid = str(uuid.uuid4())
    doc = {
        "id": cid, "workspace_id": user["workspace_id"],
        "name": body.name, "type": body.type, "discount_value": body.discount_value,
        "code": code, "codes": [], "headline": body.headline, "description": body.description,
        "terms": body.terms, "cta": body.cta or "Claim Offer", "state": body.state,
        "rules": body.rules.model_dump(), "image_url": body.image_url or "",
        "qr_code": gen_qr(code),
        "stats": {"impressions": 0, "clicks": 0, "redemptions": 0, "revenue": 0.0},
        "created_at": now_iso(),
    }
    await db.coupons.insert_one(doc)
    return coupon_public(doc)


@api.get("/coupons/{cid}")
async def get_coupon(cid: str, user: dict = Depends(get_current_user)):
    c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Coupon not found")
    return c


@api.put("/coupons/{cid}")
async def update_coupon(cid: str, body: CouponIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]})
    if not c:
        raise HTTPException(404, "Coupon not found")
    code = (body.code or c["code"]).upper()
    upd = {"name": body.name, "type": body.type, "discount_value": body.discount_value,
           "code": code, "headline": body.headline, "description": body.description,
           "terms": body.terms, "cta": body.cta, "state": body.state,
           "rules": body.rules.model_dump(), "image_url": body.image_url or c.get("image_url", "")}
    if code != c["code"]:
        upd["qr_code"] = gen_qr(code)
    await db.coupons.update_one({"id": cid}, {"$set": upd})
    return await db.coupons.find_one({"id": cid}, {"_id": 0})


@api.delete("/coupons/{cid}")
async def delete_coupon(cid: str, user: dict = Depends(get_current_user)):
    require_writer(user)
    await db.coupons.delete_one({"id": cid, "workspace_id": user["workspace_id"]})
    return {"ok": True}


@api.post("/coupons/{cid}/state")
async def set_state(cid: str, body: StateIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    valid = ["draft", "scheduled", "active", "paused", "expired", "archived"]
    if body.state not in valid:
        raise HTTPException(400, "Invalid state")
    r = await db.coupons.update_one(
        {"id": cid, "workspace_id": user["workspace_id"]}, {"$set": {"state": body.state}})
    if r.matched_count == 0:
        raise HTTPException(404, "Coupon not found")
    return await db.coupons.find_one({"id": cid}, {"_id": 0})


@api.post("/coupons/{cid}/bulk-codes")
async def bulk_codes(cid: str, body: BulkIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]})
    if not c:
        raise HTTPException(404, "Coupon not found")
    codes = [rand_code(c["code"][:4] + "-") for _ in range(min(body.count, 500))]
    await db.coupons.update_one({"id": cid}, {"$push": {"codes": {"$each": codes}}})
    return {"generated": len(codes), "codes": codes}


@api.post("/coupons/validate")
async def validate(body: ValidateIn, user: dict = Depends(get_current_user)):
    code = body.code.upper()
    c = await db.coupons.find_one(
        {"workspace_id": user["workspace_id"],
         "$or": [{"code": code}, {"codes": code}]})
    if not c:
        return {"valid": False, "reason": "Code not found"}
    if c["state"] != "active":
        return {"valid": False, "reason": f"Coupon is {c['state']}, not active"}
    rules = c.get("rules", {})
    if body.cart_value < rules.get("min_cart", 0):
        return {"valid": False, "reason": f"Minimum cart value is {rules.get('min_cart')}"}
    limit = rules.get("usage_limit", 0)
    if limit and c["stats"]["redemptions"] >= limit:
        return {"valid": False, "reason": "Usage limit reached"}
    return {"valid": True, "coupon": {"name": c["name"], "type": c["type"],
            "discount_value": c["discount_value"], "headline": c["headline"]}}


@api.post("/coupons/redeem")
async def redeem(body: RedeemIn, user: dict = Depends(get_current_user)):
    code = body.code.upper()
    c = await db.coupons.find_one(
        {"workspace_id": user["workspace_id"],
         "$or": [{"code": code}, {"codes": code}]})
    if not c:
        raise HTTPException(404, "Code not found")
    if c["state"] != "active":
        raise HTTPException(400, f"Coupon is {c['state']}")
    # fraud: duplicate redemption within 5s by same customer
    recent = await db.redemptions.find_one({
        "coupon_id": c["id"], "customer": body.customer or "guest",
        "created_at": {"$gt": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()}})
    if recent:
        raise HTTPException(429, "Duplicate redemption detected")
    percent_types = {"percentage", "flash_sale", "seasonal", "vip",
                     "first_time", "birthday", "referral"}
    if c["type"] in percent_types:
        discount = body.amount * c["discount_value"] / 100
    elif c["type"] == "fixed":
        discount = min(c["discount_value"], body.amount)
    elif c["type"] == "bogo":
        discount = body.amount * 0.5
    else:  # free_shipping and any other: no line-item discount
        discount = 0
    discount = round(min(discount, body.amount), 2)
    rev = round(max(body.amount - discount, 0), 2)
    await db.redemptions.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"], "coupon_id": c["id"],
        "code": code, "customer": body.customer or "guest", "amount": body.amount,
        "discount": discount, "revenue": rev, "created_at": now_iso()})
    await db.coupons.update_one({"id": c["id"]}, {"$inc": {
        "stats.redemptions": 1, "stats.revenue": rev}})
    return {"ok": True, "discount": discount, "revenue": rev}


# ---------------- Dashboard / analytics ----------------
@api.get("/dashboard/stats")
async def dashboard(user: dict = Depends(get_current_user)):
    ws = user["workspace_id"]
    coupons = await db.coupons.find({"workspace_id": ws}, {"_id": 0, "qr_code": 0}).to_list(1000)
    active = [c for c in coupons if c["state"] == "active"]
    total_redemptions = sum(c["stats"]["redemptions"] for c in coupons)
    total_revenue = sum(c["stats"]["revenue"] for c in coupons)
    top = sorted(coupons, key=lambda c: c["stats"]["revenue"], reverse=True)[:5]
    by_state = {}
    for c in coupons:
        by_state[c["state"]] = by_state.get(c["state"], 0) + 1
    return {
        "active_coupons": len(active),
        "total_coupons": len(coupons),
        "total_redemptions": total_redemptions,
        "total_revenue": round(total_revenue, 2),
        "top_campaigns": [{"name": c["name"], "revenue": round(c["stats"]["revenue"], 2),
                           "redemptions": c["stats"]["redemptions"], "type": c["type"]} for c in top],
        "by_state": by_state,
    }


@api.get("/analytics/timeseries")
async def timeseries(user: dict = Depends(get_current_user)):
    ws = user["workspace_id"]
    reds = await db.redemptions.find({"workspace_id": ws}, {"_id": 0}).to_list(5000)
    buckets: Dict[str, Dict[str, float]] = {}
    for i in range(13, -1, -1):
        d = (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d")
        buckets[d] = {"date": d, "redemptions": 0, "revenue": 0.0}
    for r in reds:
        d = r["created_at"][:10]
        if d in buckets:
            buckets[d]["redemptions"] += 1
            buckets[d]["revenue"] += r.get("revenue", 0)
    return list(buckets.values())


# ---------------- AI ----------------
def parse_json_block(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


@api.post("/ai/copy")
async def ai_copy(body: AICopyIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    system = ("You are a world-class promotional marketing copywriter for an e-commerce coupon platform. "
              "Given a business prompt, produce a single JSON object with keys: "
              "name (short internal campaign name), type (one of percentage, fixed, bogo, free_shipping, "
              "first_time, vip, flash_sale, seasonal, referral, birthday), discount_value (number), "
              "headline (punchy, max 8 words), description (1-2 sentences), terms (concise legal terms), "
              "cta (short call to action, max 4 words). Respond with ONLY the JSON object, no prose.")
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"copy-{uuid.uuid4()}",
                   system_message=system).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=body.prompt))
    except Exception as e:
        logger.exception("AI copy failed")
        raise HTTPException(502, f"AI copy generation failed: {e}")
    data = parse_json_block(resp if isinstance(resp, str) else str(resp))
    if not data:
        raise HTTPException(502, "AI returned unparseable response")
    return data


@api.post("/ai/image")
async def ai_image(body: AIImageIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"img-{uuid.uuid4()}",
                   system_message="You generate professional promotional coupon and marketing visuals.")
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    prompt = (f"A modern, premium promotional marketing visual for a coupon/offer. {body.prompt}. "
              "Bold clean design, vibrant, e-commerce banner style, no watermark, high quality.")
    try:
        text, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    except Exception as e:
        logger.exception("AI image failed")
        raise HTTPException(502, f"AI image generation failed: {e}")
    if not images:
        raise HTTPException(502, "No image generated")
    img = images[0]
    return {"image_url": f"data:{img['mime_type']};base64,{img['data']}"}


# ---------------- Email ----------------
def render_coupon_email(coupon: dict, brand: dict, landing_url: str) -> str:
    primary = brand.get("primary_color") or "#005CEE"
    secondary = brand.get("secondary_color") or "#CCFF00"
    brand_name = brand.get("name") or "PromoOS"
    code = coupon.get("code", "")
    headline = coupon.get("headline") or coupon.get("name") or "A gift for you"
    description = coupon.get("description") or ""
    cta = coupon.get("cta") or "Claim Offer"
    terms = coupon.get("terms") or ""
    hero = coupon.get("image_url") or ""
    hero_html = (f'<tr><td style="padding:0"><img src="{hero}" alt="" '
                 f'style="display:block;width:100%;max-width:600px;border-radius:8px"/></td></tr>'
                 if hero.startswith("http") else "")
    return f"""
<!doctype html>
<html><body style="margin:0;padding:0;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#0A0A0A">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:24px 0">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:12px;overflow:hidden">
        <tr><td style="padding:20px 28px;background:{primary};color:#FFFFFF;font-weight:700;font-size:14px;letter-spacing:1px;text-transform:uppercase">{brand_name}</td></tr>
        {hero_html}
        <tr><td style="padding:32px 28px 8px 28px">
          <h1 style="margin:0 0 12px 0;font-size:28px;line-height:1.15;color:#0A0A0A">{headline}</h1>
          <p style="margin:0 0 20px 0;font-size:15px;line-height:1.55;color:#3F3F46">{description}</p>
          <table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 20px 0">
            <tr>
              <td style="padding:14px 18px;border:2px dashed {primary};border-radius:8px;font-family:'Courier New',monospace;font-size:20px;font-weight:700;color:{primary};letter-spacing:2px">{code}</td>
            </tr>
          </table>
          <a href="{landing_url or '#'}" style="display:inline-block;background:{primary};color:#FFFFFF;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:700;font-size:15px">{cta}</a>
        </td></tr>
        <tr><td style="padding:16px 28px 28px 28px">
          <p style="margin:0;font-size:11px;line-height:1.5;color:#71717A">{terms}</p>
        </td></tr>
        <tr><td style="padding:16px 28px;background:#FAFAFA;border-top:1px solid #E4E4E7;font-size:11px;color:#71717A">
          Sent by {brand_name} via PromoOS
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>
""".strip()


@api.post("/coupons/{cid}/send-email")
async def send_coupon_email(cid: str, body: SendCouponEmailIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    if not RESEND_API_KEY:
        raise HTTPException(400, "Email not configured. Add RESEND_API_KEY to backend/.env")
    c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Coupon not found")
    ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
    subject = body.subject or f"{c.get('headline') or c.get('name')} — use code {c.get('code')}"
    html = render_coupon_email(c, ws, body.landing_url or "")
    params = {"from": SENDER_EMAIL, "to": body.to, "subject": subject, "html": html}
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
    except Exception as e:
        logger.exception("Resend send failed")
        raise HTTPException(502, f"Email send failed: {e}")
    email_id = result.get("id") if isinstance(result, dict) else None
    await db.email_events.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"], "coupon_id": cid,
        "to": body.to, "subject": subject, "resend_id": email_id, "created_at": now_iso()})
    return {"ok": True, "email_id": email_id, "sent_to": body.to}


# ---------------- Public (no auth) ----------------
def _coupon_public_payload(c: dict, ws: dict) -> dict:
    return {
        "code": c["code"], "name": c["name"], "type": c["type"],
        "discount_value": c["discount_value"], "headline": c.get("headline", ""),
        "description": c.get("description", ""), "terms": c.get("terms", ""),
        "cta": c.get("cta", "Claim Offer"), "state": c["state"],
        "image_url": c.get("image_url", ""), "qr_code": c.get("qr_code", ""),
        "referral": c.get("rules", {}).get("referral_enabled", False),
        "referral_credit_pct": c.get("rules", {}).get("referral_credit_pct", 10),
        "brand": {
            "name": ws.get("name", "PromoOS"),
            "primary_color": ws.get("primary_color", "#005CEE"),
            "secondary_color": ws.get("secondary_color", "#CCFF00"),
            "font": ws.get("font", "Cabinet Grotesk"),
            "logo_url": ws.get("logo_url", ""),
        },
    }


@api.get("/public/coupons/{code}")
async def public_coupon(code: str, ref: Optional[str] = None, v: Optional[str] = None,
                        request: Request = None):
    code_u = code.upper()
    c = await db.coupons.find_one({"$or": [{"code": code_u}, {"codes": code_u}]}, {"_id": 0})
    if not c or c["state"] in ("draft", "archived"):
        raise HTTPException(404, "Coupon not found")
    ws = await db.workspaces.find_one({"id": c["workspace_id"]}, {"_id": 0}) or {}
    # count impression (fire and forget)
    await db.coupons.update_one({"id": c["id"]}, {"$inc": {"stats.impressions": 1}})
    if ref:
        await db.referral_visits.insert_one({
            "id": str(uuid.uuid4()), "coupon_id": c["id"], "ref": ref,
            "created_at": now_iso()})
    payload = _coupon_public_payload(c, ws)
    # A/B experiment: pick a variant and overlay copy
    exp = await db.experiments.find_one(
        {"coupon_id": c["id"], "status": "running"}, {"_id": 0})
    if exp and exp.get("variants"):
        variant = None
        if v:
            variant = next((x for x in exp["variants"] if x["id"] == v), None)
        if not variant:
            seed = (ref or (request.client.host if request and request.client else "anon") + "_" + code_u)
            variant = _pick_variant(exp, seed)
        if variant:
            payload["headline"] = variant.get("headline") or payload["headline"]
            payload["description"] = variant.get("description") or payload["description"]
            payload["cta"] = variant.get("cta") or payload["cta"]
            payload["variant_id"] = variant["id"]
            payload["experiment_id"] = exp["id"]
            await db.experiments.update_one(
                {"id": exp["id"], "variants.id": variant["id"]},
                {"$inc": {"variants.$.impressions": 1}})
    return payload


class PublicRedeemIn(BaseModel):
    code: str
    amount: float = 0
    customer: Optional[str] = None
    ref: Optional[str] = None
    variant_id: Optional[str] = None


@api.post("/public/coupons/redeem")
async def public_redeem(body: PublicRedeemIn):
    """Public redemption endpoint used by /c landing pages and embed widget.
    Applies same discount + fraud rules; credits referrer when `ref` is present."""
    code = body.code.upper()
    c = await db.coupons.find_one({"$or": [{"code": code}, {"codes": code}]})
    if not c:
        raise HTTPException(404, "Code not found")
    if c["state"] != "active":
        raise HTTPException(400, f"Coupon is {c['state']}")
    customer = (body.customer or "guest").strip()[:120]
    recent = await db.redemptions.find_one({
        "coupon_id": c["id"], "customer": customer,
        "created_at": {"$gt": (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()}})
    if recent:
        raise HTTPException(429, "Duplicate redemption detected")
    percent_types = {"percentage", "flash_sale", "seasonal", "vip",
                     "first_time", "birthday", "referral"}
    if c["type"] in percent_types:
        discount = body.amount * c["discount_value"] / 100
    elif c["type"] == "fixed":
        discount = min(c["discount_value"], body.amount)
    elif c["type"] == "bogo":
        discount = body.amount * 0.5
    else:
        discount = 0
    discount = round(min(discount, body.amount), 2)
    rev = round(max(body.amount - discount, 0), 2)
    referral_credit = 0.0
    if body.ref and c.get("rules", {}).get("referral_enabled"):
        pct = float(c.get("rules", {}).get("referral_credit_pct", 10))
        referral_credit = round(rev * pct / 100, 2)
        await db.referrals.insert_one({
            "id": str(uuid.uuid4()), "workspace_id": c["workspace_id"],
            "coupon_id": c["id"], "referrer": body.ref, "referred_customer": customer,
            "amount": body.amount, "credit": referral_credit,
            "created_at": now_iso()})
    await db.redemptions.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": c["workspace_id"], "coupon_id": c["id"],
        "code": code, "customer": customer, "amount": body.amount,
        "discount": discount, "revenue": rev, "ref": body.ref,
        "variant_id": body.variant_id, "source": "public", "created_at": now_iso()})
    inc = {"stats.redemptions": 1, "stats.revenue": rev}
    if referral_credit:
        inc["stats.referral_credit"] = referral_credit
    await db.coupons.update_one({"id": c["id"]}, {"$inc": inc})
    # A/B: increment variant redemption + revenue
    if body.variant_id:
        await db.experiments.update_one(
            {"coupon_id": c["id"], "status": "running", "variants.id": body.variant_id},
            {"$inc": {"variants.$.redemptions": 1, "variants.$.revenue": rev}})
    # Loyalty: credit points to customer
    ws = await db.workspaces.find_one({"id": c["workspace_id"]}, {"_id": 0}) or {}
    loyalty_awarded = 0.0
    loyalty = ws.get("loyalty") or {}
    if loyalty.get("enabled") and customer and customer != "guest":
        ppd = float(loyalty.get("points_per_dollar", 1.0))
        loyalty_awarded = round(rev * ppd, 2)
        member = await db.loyalty_members.find_one(
            {"workspace_id": c["workspace_id"], "customer": customer})
        new_points = round((member["points"] if member else 0) + loyalty_awarded, 2)
        new_lifetime = round((member["lifetime_points"] if member else 0) + loyalty_awarded, 2)
        tier = _tier_for(new_lifetime, loyalty.get("tiers") or DEFAULT_TIERS)
        await db.loyalty_members.update_one(
            {"workspace_id": c["workspace_id"], "customer": customer},
            {"$set": {
                "workspace_id": c["workspace_id"], "customer": customer,
                "points": new_points, "lifetime_points": new_lifetime,
                "tier": tier, "last_activity": now_iso(),
             }, "$setOnInsert": {"created_at": now_iso(), "id": str(uuid.uuid4())}},
            upsert=True)
    return {"ok": True, "discount": discount, "revenue": rev,
            "referral_credit": referral_credit,
            "loyalty_points_awarded": loyalty_awarded}


# ---------------- Referrals (auth) ----------------
@api.get("/coupons/{cid}/referrals")
async def coupon_referrals(cid: str, user: dict = Depends(get_current_user)):
    c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Coupon not found")
    refs = await db.referrals.find(
        {"workspace_id": user["workspace_id"], "coupon_id": cid},
        {"_id": 0}).sort("created_at", -1).to_list(500)
    visits = await db.referral_visits.count_documents({"coupon_id": cid})
    by_ref: Dict[str, Dict[str, float]] = {}
    for r in refs:
        key = r["referrer"]
        b = by_ref.setdefault(key, {"referrer": key, "count": 0, "credit": 0.0})
        b["count"] += 1
        b["credit"] += float(r.get("credit", 0))
    leaders = sorted(by_ref.values(), key=lambda x: x["credit"], reverse=True)[:20]
    total_credit = round(sum(r.get("credit", 0) for r in refs), 2)
    return {
        "visits": visits,
        "redemptions": len(refs),
        "total_credit": total_credit,
        "leaders": [{**l, "credit": round(l["credit"], 2)} for l in leaders],
        "recent": refs[:50],
    }


# ---------------- Embed widget (public JS) ----------------
@api.get("/embed/coupon.js")
async def embed_js(request: Request):
    # Compute the public origin so the widget hits the right backend
    origin = os.environ.get("PUBLIC_ORIGIN", "").rstrip("/")
    if not origin:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        origin = f"{proto}://{host}"
    js = f"""
(function(){{
  var API="{origin}";
  var scripts=document.querySelectorAll('script[data-promoos-code]');
  scripts.forEach(function(s){{
    var code=(s.getAttribute('data-promoos-code')||'').toUpperCase();
    var ref=s.getAttribute('data-ref')||'';
    if(!code) return;
    var host=document.createElement('div');
    host.setAttribute('data-promoos-widget',code);
    s.parentNode.insertBefore(host,s);
    fetch(API+'/api/public/coupons/'+encodeURIComponent(code)+(ref?('?ref='+encodeURIComponent(ref)):''))
      .then(function(r){{return r.ok?r.json():Promise.reject(r)}})
      .then(function(d){{
        var primary=d.brand.primary_color||'#005CEE';
        var secondary=d.brand.secondary_color||'#CCFF00';
        var landing=API.replace(/\\/api$/,'')+'/c/'+encodeURIComponent(d.code);
        host.innerHTML=''
          +'<div style="font-family:Helvetica,Arial,sans-serif;max-width:420px;padding:20px;border-radius:14px;background:#0A0A0A;color:#fff;border:1px solid #27272A;box-shadow:0 10px 30px rgba(0,0,0,.35)">'
          +'<div style="font-size:11px;letter-spacing:.12em;color:'+secondary+';text-transform:uppercase;font-weight:700">'+d.brand.name+'</div>'
          +'<div style="font-size:22px;font-weight:800;line-height:1.15;margin:8px 0 6px">'+d.headline+'</div>'
          +'<div style="font-size:13px;color:#A1A1AA;margin-bottom:14px">'+d.description+'</div>'
          +'<div style="display:flex;align-items:center;gap:10px">'
          +'<div id="pos-code-'+code+'" style="flex:1;padding:12px 14px;border:2px dashed '+primary+';border-radius:10px;font-family:monospace;font-weight:700;font-size:18px;color:'+primary+';letter-spacing:2px;text-align:center">'+d.code+'</div>'
          +'<button data-pos-copy style="background:'+secondary+';color:#0A0A0A;border:0;padding:12px 14px;border-radius:10px;font-weight:700;cursor:pointer">Copy</button>'
          +'</div>'
          +'<a href="'+landing+(ref?('?ref='+encodeURIComponent(ref)):'')+'" target="_blank" rel="noopener" style="display:block;text-align:center;margin-top:14px;background:'+primary+';color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700">'+d.cta+'</a>'
          +'</div>';
        var btn=host.querySelector('[data-pos-copy]');
        btn.addEventListener('click',function(){{
          navigator.clipboard.writeText(d.code).then(function(){{btn.textContent='Copied!';setTimeout(function(){{btn.textContent='Copy'}},1500)}});
        }});
      }})
      .catch(function(){{ host.innerHTML='<div style="padding:12px;border:1px solid #27272A;border-radius:10px;color:#A1A1AA;font-family:sans-serif;font-size:12px">Offer unavailable</div>'; }});
  }});
}})();
""".strip()
    return Response(content=js, media_type="application/javascript",
                    headers={"Cache-Control": "public, max-age=60"})


# ---------------- SMS / WhatsApp (Twilio) ----------------
def _short_msg(coupon: dict, brand_name: str, landing_url: str, channel: str) -> str:
    hl = coupon.get("headline") or coupon.get("name") or "A gift for you"
    code = coupon.get("code", "")
    dv = coupon.get("discount_value", 0)
    prefix = f"{brand_name}: " if brand_name else ""
    body = f"{prefix}{hl} — {dv}% off. Code: {code}. "
    if landing_url:
        body += f"Redeem: {landing_url}"
    return body[:1550] if channel == "whatsapp" else body[:320]


async def _twilio_send_one(to: str, body: str, channel: str) -> str:
    if channel == "whatsapp":
        return await asyncio.to_thread(
            lambda: twilio_client.messages.create(
                from_=f"whatsapp:{TWILIO_FROM_WHATSAPP}",
                to=f"whatsapp:{to}", body=body).sid)
    return await asyncio.to_thread(
        lambda: twilio_client.messages.create(
            from_=TWILIO_FROM_SMS, to=to, body=body).sid)


@api.post("/coupons/{cid}/send-message")
async def send_coupon_message(cid: str, body: SendCouponMessageIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    channel = body.channel.lower()
    if channel not in ("sms", "whatsapp"):
        raise HTTPException(400, "channel must be 'sms' or 'whatsapp'")
    if not twilio_client:
        raise HTTPException(400, "SMS/WhatsApp not configured. Add TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to backend/.env")
    if channel == "sms" and not TWILIO_FROM_SMS:
        raise HTTPException(400, "TWILIO_FROM_SMS not set")
    if channel == "whatsapp" and not TWILIO_FROM_WHATSAPP:
        raise HTTPException(400, "TWILIO_FROM_WHATSAPP not set")
    c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Coupon not found")
    ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
    landing = body.landing_url or (f"{PUBLIC_APP_URL}/c/{c['code']}" if PUBLIC_APP_URL else "")
    text = _short_msg(c, ws.get("name", ""), landing, channel)
    sids: List[str] = []
    failures: List[str] = []
    for to in body.to:
        try:
            sid = await _twilio_send_one(to, text, channel)
            sids.append(sid)
        except Exception as e:
            failures.append(f"{to}: {e}")
    if not sids:
        raise HTTPException(502, "; ".join(failures) or "All messages failed")
    await db.message_events.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"], "coupon_id": cid,
        "channel": channel, "to": body.to, "body": text, "sids": sids,
        "failures": failures, "created_at": now_iso()})
    return {"ok": True, "channel": channel, "sent": sids, "failures": failures}


# ---------------- A/B Testing ----------------
def _pick_variant(experiment: dict, seed: str) -> dict:
    variants = experiment.get("variants", [])
    if not variants:
        return {}
    # deterministic bucket by hashing seed → variant index
    idx = sum(ord(ch) for ch in seed) % len(variants)
    return variants[idx]


@api.post("/coupons/{cid}/experiments")
async def create_experiment(cid: str, body: ExperimentCreateIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    c = await db.coupons.find_one({"id": cid, "workspace_id": user["workspace_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Coupon not found")
    n = max(2, min(int(body.n or 3), 5))
    variants: List[dict] = []
    if body.use_ai:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        system = (
            "You are a promotional copy A/B test generator. Produce a JSON array of exactly "
            f"{n} variants for a coupon campaign. Each variant is an object with keys: "
            "headline (max 8 words, distinct angle), description (1-2 sentences), cta (max 4 words). "
            "Vary the emotional angle across variants (urgency, curiosity, value, social proof, "
            "aspirational). Respond with ONLY the JSON array.")
        prompt = body.prompt or (
            f"Base coupon: name='{c.get('name')}' headline='{c.get('headline')}' "
            f"description='{c.get('description')}' discount={c.get('discount_value')}% "
            f"type={c.get('type')}. Generate {n} bold headline/description/CTA variants.")
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"ab-{uuid.uuid4()}",
                       system_message=system).with_model("anthropic", "claude-sonnet-5")
        try:
            resp = await chat.send_message(UserMessage(text=prompt))
        except Exception as e:
            logger.exception("AI variants failed")
            raise HTTPException(502, f"AI variant generation failed: {e}")
        text = resp if isinstance(resp, str) else str(resp)
        m = re.search(r"\[.*\]", text, re.DOTALL)
        try:
            arr = json.loads(m.group(0)) if m else []
        except Exception:
            arr = []
        for v in arr[:n]:
            if not isinstance(v, dict):
                continue
            variants.append({
                "id": str(uuid.uuid4())[:8],
                "headline": str(v.get("headline", ""))[:120],
                "description": str(v.get("description", ""))[:400],
                "cta": str(v.get("cta", "Claim Offer"))[:40],
                "impressions": 0, "redemptions": 0, "revenue": 0.0,
            })
    if not variants:
        # Fallback / manual placeholders
        for i in range(n):
            variants.append({
                "id": str(uuid.uuid4())[:8],
                "headline": c.get("headline", "Great offer") + (f" (v{i+1})" if i else ""),
                "description": c.get("description", ""),
                "cta": c.get("cta", "Claim Offer"),
                "impressions": 0, "redemptions": 0, "revenue": 0.0,
            })
    exp = {
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"], "coupon_id": cid,
        "status": "running", "variants": variants, "winner_variant_id": None,
        "created_at": now_iso(),
    }
    await db.experiments.insert_one({**exp})
    # Only one active experiment per coupon
    await db.experiments.update_many(
        {"coupon_id": cid, "id": {"$ne": exp["id"]}, "status": "running"},
        {"$set": {"status": "archived"}})
    return {k: v for k, v in exp.items() if k != "_id"}


@api.get("/coupons/{cid}/experiments")
async def list_experiments(cid: str, user: dict = Depends(get_current_user)):
    docs = await db.experiments.find(
        {"coupon_id": cid, "workspace_id": user["workspace_id"]},
        {"_id": 0}).sort("created_at", -1).to_list(50)
    for d in docs:
        for v in d.get("variants", []):
            imp = v.get("impressions", 0) or 0
            v["cvr"] = round((v.get("redemptions", 0) / imp * 100), 2) if imp else 0.0
    return docs


@api.post("/experiments/{eid}/promote")
async def promote_experiment(eid: str, body: ExperimentPromoteIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    exp = await db.experiments.find_one({"id": eid, "workspace_id": user["workspace_id"]}, {"_id": 0})
    if not exp:
        raise HTTPException(404, "Experiment not found")
    variants = exp.get("variants", [])
    if not variants:
        raise HTTPException(400, "No variants")
    if body.variant_id:
        winner = next((v for v in variants if v["id"] == body.variant_id), None)
    else:
        def rate(v):
            imp = v.get("impressions", 0) or 0
            return (v.get("redemptions", 0) / imp) if imp else 0
        total_imp = sum(v.get("impressions", 0) or 0 for v in variants)
        if total_imp == 0:
            # No traffic yet — fall back to redemption count, then revenue.
            winner = max(variants, key=lambda v: (v.get("redemptions", 0), v.get("revenue", 0)))
        else:
            winner = max(variants, key=rate)
    if not winner:
        raise HTTPException(400, "Variant not found")
    await db.coupons.update_one(
        {"id": exp["coupon_id"], "workspace_id": user["workspace_id"]},
        {"$set": {"headline": winner["headline"], "description": winner["description"],
                  "cta": winner["cta"], "updated_at": now_iso()}})
    await db.experiments.update_one(
        {"id": eid}, {"$set": {"status": "complete", "winner_variant_id": winner["id"],
                               "completed_at": now_iso()}})
    return {"ok": True, "winner": winner}


# ---------------- Loyalty ----------------
DEFAULT_TIERS = [
    {"name": "Bronze", "threshold": 0},
    {"name": "Silver", "threshold": 500},
    {"name": "Gold", "threshold": 2000},
    {"name": "Platinum", "threshold": 5000},
]


def _tier_for(points: float, tiers: List[dict]) -> str:
    t = sorted(tiers or DEFAULT_TIERS, key=lambda x: x.get("threshold", 0))
    name = t[0]["name"] if t else "Bronze"
    for tier in t:
        if points >= tier.get("threshold", 0):
            name = tier["name"]
    return name


@api.put("/workspace/loyalty")
async def update_loyalty_config(body: LoyaltyConfigIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    tiers = body.tiers or DEFAULT_TIERS
    await db.workspaces.update_one(
        {"id": user["workspace_id"]},
        {"$set": {
            "loyalty.enabled": body.enabled,
            "loyalty.points_per_dollar": float(body.points_per_dollar),
            "loyalty.tiers": tiers,
            "updated_at": now_iso()}})
    return {"ok": True}


@api.get("/loyalty")
async def loyalty_members(user: dict = Depends(get_current_user)):
    ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
    loyalty = ws.get("loyalty", {}) or {}
    members = await db.loyalty_members.find(
        {"workspace_id": user["workspace_id"]},
        {"_id": 0}).sort("points", -1).to_list(500)
    total_points = sum(m.get("points", 0) for m in members)
    by_tier: Dict[str, int] = {}
    for m in members:
        by_tier[m.get("tier", "Bronze")] = by_tier.get(m.get("tier", "Bronze"), 0) + 1
    return {
        "config": {
            "enabled": bool(loyalty.get("enabled", False)),
            "points_per_dollar": float(loyalty.get("points_per_dollar", 1.0)),
            "tiers": loyalty.get("tiers") or DEFAULT_TIERS,
        },
        "total_members": len(members),
        "total_points": round(total_points, 2),
        "by_tier": by_tier,
        "members": members[:200],
    }


app.include_router(api)

# CORS: reflect incoming Origin with credentials. Wildcard "*" is browser-rejected
# alongside credentials, so we echo whichever Origin the request presents (or the
# explicit list from CORS_ORIGINS when set to something other than "*").
_cors_env = os.environ.get('CORS_ORIGINS', '*')
if _cors_env.strip() == '*':
    app.add_middleware(
        CORSMiddleware, allow_credentials=True,
        allow_origin_regex=".*",
        allow_methods=["*"], allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware, allow_credentials=True,
        allow_origins=_cors_env.split(','),
        allow_methods=["*"], allow_headers=["*"],
    )


# ---------------- Seed ----------------
async def seed():
    await db.users.create_index("email", unique=True)
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    existing = await db.users.find_one({"email": admin_email})
    if existing:
        return
    ws_id = str(uuid.uuid4())
    await db.workspaces.insert_one({
        "id": ws_id, "name": "Acme Swimwear Co.", "logo_url": "",
        "primary_color": "#005CEE", "secondary_color": "#CCFF00",
        "font": "Cabinet Grotesk", "currency": "USD", "created_at": now_iso()})
    admin_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": admin_id, "name": "Alex Owner", "email": admin_email,
        "password_hash": hash_password(os.environ["ADMIN_PASSWORD"]), "role": "owner",
        "workspace_id": ws_id, "created_at": now_iso()})
    await db.users.insert_one({
        "id": str(uuid.uuid4()), "name": "Morgan Marketer", "email": "marketer@promoos.com",
        "password_hash": hash_password("marketer123"), "role": "marketer",
        "workspace_id": ws_id, "created_at": now_iso()})
    await db.users.insert_one({
        "id": str(uuid.uuid4()), "name": "Val Viewer", "email": "viewer@promoos.com",
        "password_hash": hash_password("viewer123"), "role": "viewer",
        "workspace_id": ws_id, "created_at": now_iso()})

    samples = [
        ("Summer Swimwear Sale", "flash_sale", 25, "SUMMER25", "active",
         "Dive Into 25% Off Swimwear", "Beat the heat with 25% off all swimwear. New customers welcome!",
         "Valid on swimwear only. Ends Sunday. Cannot be combined.", "Shop Now", 0),
        ("First Order Freebie", "first_time", 15, "WELCOME15", "active",
         "15% Off Your First Splash", "New here? Enjoy 15% off your very first order.",
         "First-time customers only. One use per customer.", "Claim Offer", 0),
        ("VIP Loyalty Reward", "vip", 30, "VIP30", "active",
         "VIP Members Save 30%", "An exclusive thank-you for our most loyal customers.",
         "VIP tier only. Not stackable.", "Redeem", 0),
        ("Free Shipping Weekend", "free_shipping", 0, "FREESHIP", "active",
         "Free Shipping All Weekend", "No minimum. Free shipping on every order this weekend.",
         "Valid Sat-Sun only.", "Get It", 0),
        ("Holiday Flash 40", "seasonal", 40, "HOLIDAY40", "scheduled",
         "40% Off Holiday Blowout", "Our biggest seasonal sale of the year is coming.",
         "Select items. While supplies last.", "Notify Me", 0),
        ("Birthday Treat", "birthday", 20, "HAPPYBDAY", "draft",
         "Happy Birthday — 20% Off", "Celebrate with a little gift from us.",
         "Valid during birthday month.", "Unwrap", 0),
        ("Spring Clearance", "percentage", 50, "SPRING50", "expired",
         "50% Off Spring Clearance", "Last chance on spring styles.",
         "Clearance items only.", "Shop Sale", 0),
    ]
    now = datetime.now(timezone.utc)
    for idx, (name, typ, val, code, state, head, desc, terms, cta, _u) in enumerate(samples):
        cid = str(uuid.uuid4())
        redemptions = random.randint(20, 180) if state in ("active", "expired") else 0
        revenue = round(redemptions * random.uniform(35, 95), 2)
        await db.coupons.insert_one({
            "id": cid, "workspace_id": ws_id, "name": name, "type": typ,
            "discount_value": val, "code": code, "codes": [],
            "headline": head, "description": desc, "terms": terms, "cta": cta, "state": state,
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "", "usage_limit": 0,
                      "per_customer_limit": 1, "stackable": False,
                      "start_date": None, "end_date": None},
            "image_url": "", "qr_code": gen_qr(code),
            "stats": {"impressions": redemptions * random.randint(8, 20),
                      "clicks": redemptions * random.randint(2, 5),
                      "redemptions": redemptions, "revenue": revenue},
            "created_at": (now - timedelta(days=idx * 3)).isoformat()})
        # redemption events over last 14 days
        for _ in range(redemptions):
            day = random.randint(0, 13)
            amt = round(random.uniform(40, 120), 2)
            disc = amt * val / 100 if typ in ("percentage", "flash_sale", "seasonal", "vip",
                                              "first_time", "birthday") else 0
            await db.redemptions.insert_one({
                "id": str(uuid.uuid4()), "workspace_id": ws_id, "coupon_id": cid, "code": code,
                "customer": f"cust{random.randint(1,300)}", "amount": amt, "discount": round(disc, 2),
                "revenue": round(amt - disc, 2),
                "created_at": (now - timedelta(days=day, hours=random.randint(0, 23))).isoformat()})
    logger.info("Seed complete")


@app.on_event("startup")
async def startup():
    try:
        await db.login_attempts.create_index("identifier")
        await seed()
    except Exception as e:
        logger.error(f"Seed error: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
