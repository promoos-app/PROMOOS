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
import uuid, logging, jwt, bcrypt, io, base64, json, random, string, re, asyncio, secrets as _pysecrets, hashlib as _hashlib
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timezone, timedelta
import qrcode
import resend
import hmac
import hashlib
from twilio.rest import Client as TwilioClient

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGO = "HS256"
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
# Fernet key derived from JWT secret — deterministic across restarts, no external KMS needed.
_FERNET = Fernet(base64.urlsafe_b64encode(_hashlib.sha256(
    os.environ.get('JWT_SECRET', 'promoos').encode()).digest()))


def encrypt_str(s: str) -> str:
    return _FERNET.encrypt(s.encode()).decode()


def decrypt_str(s: str) -> Optional[str]:
    try:
        return _FERNET.decrypt(s.encode()).decode()
    except (InvalidToken, Exception):
        return None
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
    if user.get("deleted_at"):
        raise HTTPException(403, "Account deleted")
    if user.get("suspended"):
        raise HTTPException(403, "Account suspended — contact your administrator")
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
    # Fire "purchase" trigger for any active journeys
    email = customer if "@" in customer else None
    await _fire_trigger(c["workspace_id"], "purchase", customer, email=email)
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
async def embed_js(request: Request, variant: str = "inline"):
    """Embed script. Supports variants: inline (default card), popup, bar, wheel, wallet."""
    origin = os.environ.get("PUBLIC_ORIGIN", "").rstrip("/")
    if not origin:
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        origin = f"{proto}://{host}"
    v = (variant or "inline").lower()
    if v not in ("inline", "popup", "bar", "wheel", "wallet"):
        v = "inline"
    js = _RENDERERS[v].replace("__API__", origin)
    return Response(content=js, media_type="application/javascript",
                    headers={"Cache-Control": "public, max-age=60"})


# Common bootstrap that hydrates coupon data + brand colors
_EMBED_BOOTSTRAP = """
var API="__API__";
function poFetch(code, ref, cb){
  fetch(API+'/api/public/coupons/'+encodeURIComponent(code)+(ref?('?ref='+encodeURIComponent(ref)):''))
    .then(function(r){return r.ok?r.json():Promise.reject(r)})
    .then(cb).catch(function(){});
}
function poCopy(text, btn){
  navigator.clipboard.writeText(text).then(function(){
    var t=btn.textContent; btn.textContent='Copied!'; setTimeout(function(){btn.textContent=t;},1500);
  }).catch(function(){});
}
"""

_RENDERERS = {
    # Inline card (original)
    "inline": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase();
  var ref=s.getAttribute('data-ref')||'';
  if(!code) return;
  var host=document.createElement('div'); s.parentNode.insertBefore(host,s);
  poFetch(code, ref, function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var landing=API+'/c/'+encodeURIComponent(d.code)+(ref?('?ref='+encodeURIComponent(ref)):'');
    host.innerHTML='<div style="font-family:Helvetica,Arial,sans-serif;max-width:420px;padding:20px;border-radius:14px;background:#0A0A0A;color:#fff;border:1px solid #27272A;box-shadow:0 10px 30px rgba(0,0,0,.35)">'
      +'<div style="font-size:11px;letter-spacing:.12em;color:'+accent+';text-transform:uppercase;font-weight:700">'+d.brand.name+'</div>'
      +'<div style="font-size:22px;font-weight:800;line-height:1.15;margin:8px 0 6px">'+d.headline+'</div>'
      +'<div style="font-size:13px;color:#A1A1AA;margin-bottom:14px">'+d.description+'</div>'
      +'<div style="display:flex;gap:10px"><div style="flex:1;padding:12px 14px;border:2px dashed '+primary+';border-radius:10px;font-family:monospace;font-weight:700;font-size:18px;color:'+primary+';letter-spacing:2px;text-align:center">'+d.code+'</div>'
      +'<button data-c style="background:'+accent+';color:#0A0A0A;border:0;padding:12px 14px;border-radius:10px;font-weight:700;cursor:pointer">Copy</button></div>'
      +'<a href="'+landing+'" target="_blank" rel="noopener" style="display:block;text-align:center;margin-top:14px;background:'+primary+';color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700">'+d.cta+'</a></div>';
    host.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
  });
});
""",

    # Full-screen popup
    "popup": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  var delay=parseInt(s.getAttribute('data-delay')||'2500',10);
  if(sessionStorage.getItem('promoos_seen_'+code)) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    setTimeout(function(){
      sessionStorage.setItem('promoos_seen_'+code,'1');
      var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
      var wrap=document.createElement('div');
      wrap.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:2147483647;display:flex;align-items:center;justify-content:center;font-family:Helvetica,Arial,sans-serif;padding:20px;animation:pop-fade .3s ease';
      wrap.innerHTML='<style>@keyframes pop-fade{from{opacity:0}to{opacity:1}}@keyframes pop-in{from{transform:scale(.9);opacity:0}to{transform:scale(1);opacity:1}}</style>'
        +'<div style="background:#0A0A0A;color:#fff;max-width:460px;width:100%;padding:32px;border-radius:20px;position:relative;text-align:center;border:1px solid #27272A;animation:pop-in .3s ease">'
        +'<button data-x style="position:absolute;top:12px;right:14px;background:transparent;border:0;color:#71717A;font-size:22px;cursor:pointer;line-height:1">×</button>'
        +'<div style="font-size:11px;letter-spacing:.12em;color:'+accent+';text-transform:uppercase;font-weight:700;margin-bottom:8px">'+d.brand.name+'</div>'
        +'<div style="font-size:28px;font-weight:900;line-height:1.1;margin-bottom:8px">'+d.headline+'</div>'
        +'<div style="font-size:14px;color:#A1A1AA;margin-bottom:20px">'+d.description+'</div>'
        +'<div style="padding:14px 16px;border:2px dashed '+primary+';border-radius:12px;font-family:monospace;font-weight:700;font-size:22px;color:'+primary+';letter-spacing:3px;margin-bottom:16px">'+d.code+'</div>'
        +'<button data-c style="background:'+primary+';color:#fff;border:0;padding:14px 24px;border-radius:12px;font-weight:700;cursor:pointer;font-size:15px;width:100%">'+d.cta+' — Copy code</button></div>';
      document.body.appendChild(wrap);
      wrap.querySelector('[data-x]').addEventListener('click',function(){wrap.remove()});
      wrap.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
      wrap.addEventListener('click',function(e){if(e.target===wrap)wrap.remove()});
    }, delay);
  });
});
""",

    # Top-bar
    "bar": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var landing=API+'/c/'+encodeURIComponent(d.code);
    var bar=document.createElement('div');
    bar.style.cssText='position:fixed;top:0;left:0;right:0;background:linear-gradient(90deg,'+primary+','+accent+');color:#0A0A0A;padding:10px 18px;font-family:Helvetica,Arial,sans-serif;font-weight:700;font-size:14px;z-index:2147483646;display:flex;align-items:center;gap:12px;justify-content:center;flex-wrap:wrap;box-shadow:0 2px 8px rgba(0,0,0,.15)';
    bar.innerHTML='<span>'+d.headline+' — Code <span style="font-family:monospace;background:rgba(0,0,0,.15);padding:2px 8px;border-radius:4px">'+d.code+'</span></span>'
      +'<a href="'+landing+'" target="_blank" style="background:#0A0A0A;color:#fff;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:12px">'+d.cta+'</a>'
      +'<button data-x style="background:transparent;border:0;color:#0A0A0A;font-size:18px;cursor:pointer;padding:0 4px;line-height:1;opacity:.5">×</button>';
    document.body.appendChild(bar);
    bar.querySelector('[data-x]').addEventListener('click',function(){bar.remove()});
  });
});
""",

    # Spin-to-win wheel
    "wheel": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var slices=[d.discount_value+'%',Math.round(d.discount_value/2)+'%','Try again','5%',d.discount_value+'%','Free ship'];
    var wrap=document.createElement('div');
    wrap.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:2147483647;display:flex;align-items:center;justify-content:center;font-family:Helvetica,Arial,sans-serif;padding:20px';
    var W='<style>@keyframes spin{to{transform:rotate(var(--r))}}</style><div style="background:#0A0A0A;color:#fff;padding:32px;border-radius:20px;max-width:420px;width:100%;text-align:center;border:1px solid #27272A">';
    W+='<button data-x style="position:absolute;top:20px;right:20px;background:transparent;border:0;color:#fff;font-size:22px;cursor:pointer">×</button>';
    W+='<div style="font-size:22px;font-weight:900;margin-bottom:16px">Spin to Win</div>';
    W+='<div style="position:relative;width:260px;height:260px;margin:0 auto 20px"><div id="pw-wheel" style="width:100%;height:100%;border-radius:50%;background:conic-gradient('+primary+' 0 60deg,'+accent+' 60deg 120deg,'+primary+' 120deg 180deg,'+accent+' 180deg 240deg,'+primary+' 240deg 300deg,'+accent+' 300deg 360deg);transition:transform 4s cubic-bezier(.22,.9,.28,1);border:4px solid #fff;box-shadow:0 0 40px '+primary+'44"></div><div style="position:absolute;top:-6px;left:50%;transform:translateX(-50%);width:0;height:0;border-left:12px solid transparent;border-right:12px solid transparent;border-top:20px solid #fff"></div></div>';
    W+='<button data-spin style="background:'+primary+';color:#fff;border:0;padding:14px 32px;border-radius:12px;font-weight:700;font-size:16px;cursor:pointer">SPIN</button>';
    W+='<div id="pw-out" style="margin-top:20px;min-height:80px"></div></div>';
    wrap.innerHTML=W; document.body.appendChild(wrap);
    var out=wrap.querySelector('#pw-out'), whl=wrap.querySelector('#pw-wheel'), btn=wrap.querySelector('[data-spin]');
    wrap.querySelector('[data-x]').addEventListener('click',function(){wrap.remove()});
    btn.addEventListener('click',function(){
      btn.disabled=true; btn.style.opacity='.5';
      var winSlice=0; var deg=1800+winSlice*60+30;
      whl.style.setProperty('--r',deg+'deg'); whl.style.animation='spin 4s cubic-bezier(.22,.9,.28,1) forwards';
      setTimeout(function(){
        out.innerHTML='<div style="font-size:18px;font-weight:800;color:'+accent+'">You won '+slices[winSlice]+' off!</div>'
          +'<div style="margin-top:8px;padding:10px;border:2px dashed '+primary+';border-radius:8px;font-family:monospace;font-weight:700;font-size:18px;color:'+primary+';letter-spacing:2px">'+d.code+'</div>'
          +'<button data-c style="margin-top:10px;background:'+accent+';color:#0A0A0A;border:0;padding:10px 20px;border-radius:8px;font-weight:700;cursor:pointer">Copy code</button>';
        out.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
      },4200);
    });
  });
});
""",

    # Floating wallet pill (bottom right)
    "wallet": _EMBED_BOOTSTRAP + """
document.querySelectorAll('script[data-promoos-code]').forEach(function(s){
  var code=(s.getAttribute('data-promoos-code')||'').toUpperCase(); if(!code) return;
  poFetch(code, s.getAttribute('data-ref')||'', function(d){
    var primary=d.brand.primary_color||'#005CEE', accent=d.brand.secondary_color||'#CCFF00';
    var landing=API+'/c/'+encodeURIComponent(d.code);
    var pill=document.createElement('div');
    pill.style.cssText='position:fixed;bottom:20px;right:20px;z-index:2147483645;font-family:Helvetica,Arial,sans-serif;display:flex;flex-direction:column;align-items:flex-end;gap:8px';
    pill.innerHTML='<div id="pw-panel" style="display:none;background:#0A0A0A;color:#fff;padding:20px;border-radius:16px;border:1px solid #27272A;box-shadow:0 20px 40px rgba(0,0,0,.4);max-width:320px">'
      +'<div style="font-size:11px;letter-spacing:.1em;color:'+accent+';text-transform:uppercase;font-weight:700;margin-bottom:6px">'+d.brand.name+'</div>'
      +'<div style="font-size:16px;font-weight:800;line-height:1.15;margin-bottom:4px">'+d.headline+'</div>'
      +'<div style="font-size:12px;color:#A1A1AA;margin-bottom:12px">'+d.description+'</div>'
      +'<div style="padding:10px;border:2px dashed '+primary+';border-radius:8px;font-family:monospace;font-weight:700;color:'+primary+';text-align:center;letter-spacing:2px;margin-bottom:10px">'+d.code+'</div>'
      +'<div style="display:flex;gap:6px"><button data-c style="flex:1;background:'+accent+';color:#0A0A0A;border:0;padding:8px;border-radius:8px;font-weight:700;cursor:pointer;font-size:12px">Copy</button><a href="'+landing+'" target="_blank" style="flex:1;background:'+primary+';color:#fff;text-decoration:none;padding:8px;border-radius:8px;font-weight:700;text-align:center;font-size:12px">'+d.cta+'</a></div></div>'
      +'<button id="pw-toggle" style="background:'+primary+';color:#fff;border:0;padding:12px 18px;border-radius:99px;font-weight:700;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.3);display:flex;align-items:center;gap:8px;font-size:13px">🎁 '+d.discount_value+'% off available</button>';
    document.body.appendChild(pill);
    var panel=pill.querySelector('#pw-panel'), toggle=pill.querySelector('#pw-toggle');
    toggle.addEventListener('click',function(){panel.style.display=panel.style.display==='none'?'block':'none'});
    panel.querySelector('[data-c]').addEventListener('click',function(e){poCopy(d.code,e.target)});
  });
});
""",
}


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


# ---------------- Bundle A: Autopilot + One-Click + Calendar + Brand Guardrails ----------------
class AutopilotConfigIn(BaseModel):
    enabled: bool = False
    goal: str = "grow_sales"          # grow_sales | acquire | reactivate | clear_inventory
    max_discount: int = 25
    frequency: str = "daily"          # daily | weekdays | weekly
    require_approval: bool = True
    brand_voice: str = "confident, playful, benefit-led"
    audience: str = "all"             # all | new | returning | vip


class OneClickIn(BaseModel):
    prompt: str
    schedule_at: Optional[str] = None


class TodaysPromoIn(BaseModel):
    hint: Optional[str] = None


async def _ai_json(system: str, prompt: str, session_id: str) -> dict:
    """Call Claude and parse a JSON object out of the response."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id,
                   system_message=system).with_model("anthropic", "claude-sonnet-5")
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        msg = str(e)
        if "Budget" in msg or "budget" in msg:
            raise HTTPException(
                429, "AI budget exhausted. Top up your Universal Key: Profile → Manage plan → Universal Key → Add Balance.")
        raise HTTPException(502, f"AI request failed: {msg}")
    text = resp if isinstance(resp, str) else str(resp)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise HTTPException(502, "AI returned no JSON")
    try:
        return json.loads(m.group(0))
    except Exception as e:
        raise HTTPException(502, f"AI JSON parse failed: {e}")


def _guardrail_discount(v: float, autopilot: dict) -> float:
    cap = float(autopilot.get("max_discount", 25))
    return max(1, min(float(v), cap))


async def _workspace_context(workspace_id: str) -> str:
    """Compact JSON summary of past performance for the AI planner."""
    ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0}) or {}
    top = await db.coupons.find({"workspace_id": workspace_id}, {"_id": 0})\
        .sort("stats.redemptions", -1).limit(5).to_list(5)
    thirty = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    reds = await db.redemptions.aggregate([
        {"$match": {"workspace_id": workspace_id, "created_at": {"$gt": thirty}}},
        {"$group": {"_id": {"$hour": {"$dateFromString": {"dateString": "$created_at"}}},
                    "n": {"$sum": 1}, "rev": {"$sum": "$revenue"}}},
        {"$sort": {"n": -1}}, {"$limit": 3}]).to_list(3)
    top_summary = [{"name": c.get("name"), "type": c.get("type"),
                    "discount": c.get("discount_value"),
                    "redemptions": c.get("stats", {}).get("redemptions", 0)} for c in top]
    return json.dumps({
        "brand": ws.get("name"), "voice": ws.get("brand_voice"),
        "top_coupons": top_summary,
        "top_hours_utc": [{"hour": r["_id"], "redemptions": r["n"]} for r in reds],
    })


@api.get("/autopilot/config")
async def get_autopilot(user: dict = Depends(get_current_user)):
    ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
    ap = ws.get("autopilot") or {}
    return {
        "enabled": bool(ap.get("enabled", False)),
        "goal": ap.get("goal", "grow_sales"),
        "max_discount": int(ap.get("max_discount", 25)),
        "frequency": ap.get("frequency", "daily"),
        "require_approval": bool(ap.get("require_approval", True)),
        "brand_voice": ap.get("brand_voice", "confident, playful, benefit-led"),
        "audience": ap.get("audience", "all"),
    }


@api.put("/autopilot/config")
async def update_autopilot(body: AutopilotConfigIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    await db.workspaces.update_one(
        {"id": user["workspace_id"]},
        {"$set": {"autopilot": body.model_dump(), "updated_at": now_iso()}})
    return {"ok": True, **body.model_dump()}


@api.post("/ai/todays-promo")
async def ai_todays_promo(body: TodaysPromoIn, user: dict = Depends(get_current_user)):
    ap = (await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}).get("autopilot") or {}
    ctx = await _workspace_context(user["workspace_id"])
    system = ("You are a promotional strategist. Look at recent performance and design ONE optimal promotion for today. "
              "Return ONLY a JSON object with keys: type (percentage|flash_sale|bogo|free_shipping|first_time|vip), "
              "discount_value (integer), name (short), headline (max 8 words), description, terms, cta (max 4 words), "
              "audience (all|new|returning|vip), reasoning (1 sentence why).")
    prompt = f"Workspace context: {ctx}. Goal: {ap.get('goal','grow_sales')}. Max discount cap: {ap.get('max_discount',25)}%. Voice: {ap.get('brand_voice','confident')}. Hint: {body.hint or 'none'}."
    d = await _ai_json(system, prompt, f"todays-{uuid.uuid4()}")
    d["discount_value"] = _guardrail_discount(d.get("discount_value", 15), ap)
    return d


@api.post("/ai/weekly-calendar")
async def ai_weekly_calendar(user: dict = Depends(get_current_user)):
    ap = (await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}).get("autopilot") or {}
    ctx = await _workspace_context(user["workspace_id"])
    system = ("You are a promotional planner. Return ONLY a JSON object with key 'days' whose value is an array of "
              "exactly 7 objects, one per weekday starting Monday. Each object: day (Mon..Sun), type, discount_value (int), "
              "name (short), headline (max 8 words), audience, cta. Vary theme across the week: new-customer, flash, VIP, "
              "free shipping, bundle, weekend, loyalty. Respect the cap and the brand voice.")
    prompt = f"Context: {ctx}. Goal: {ap.get('goal','grow_sales')}. Cap: {ap.get('max_discount',25)}%. Voice: {ap.get('brand_voice','confident')}."
    d = await _ai_json(system, prompt, f"weekly-{uuid.uuid4()}")
    days = d.get("days") if isinstance(d, dict) else []
    if not isinstance(days, list) or len(days) < 7:
        raise HTTPException(502, "AI did not return 7 days")
    for x in days[:7]:
        x["discount_value"] = _guardrail_discount(x.get("discount_value", 15), ap)
    return {"days": days[:7]}


@api.post("/ai/one-click-campaign")
async def ai_one_click(body: OneClickIn, user: dict = Depends(get_current_user)):
    ap = (await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}).get("autopilot") or {}
    ctx = await _workspace_context(user["workspace_id"])
    system = ("You are a marketing director. Given a business goal, produce ONE complete campaign package as a JSON object "
              "with keys: coupon {type, discount_value, name, headline, description, terms, cta, audience}, "
              "email {subject, body_short (under 400 chars)}, sms (under 320 chars), whatsapp (under 1550 chars), "
              "push {title, body}, social_caption, landing_headline, ad_copy. Respect the discount cap.")
    prompt = f"User request: {body.prompt}. Context: {ctx}. Cap: {ap.get('max_discount',25)}%. Voice: {ap.get('brand_voice','confident')}."
    d = await _ai_json(system, prompt, f"oneclick-{uuid.uuid4()}")
    if isinstance(d.get("coupon"), dict):
        d["coupon"]["discount_value"] = _guardrail_discount(d["coupon"].get("discount_value", 15), ap)
    return d


class ApproveCampaignIn(BaseModel):
    package: dict
    schedule_at: Optional[str] = None
    activate: bool = True


@api.post("/ai/one-click-campaign/approve")
async def approve_one_click(body: ApproveCampaignIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    pkg = body.package or {}
    cp = pkg.get("coupon") or {}
    if not cp.get("name") or not cp.get("type"):
        raise HTTPException(400, "package.coupon.name and type required")
    prefix = re.sub(r"[^A-Z]", "", (cp.get("name") or "PROMO").upper())[:6] or "PROMO"
    code = rand_code(prefix)
    now = now_iso()
    state = "scheduled" if body.schedule_at else ("active" if body.activate else "draft")
    coupon = {
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
        "code": code, "codes": [code],
        "name": cp.get("name")[:80], "type": cp.get("type", "percentage"),
        "discount_value": float(cp.get("discount_value", 15)),
        "headline": cp.get("headline", "")[:120],
        "description": cp.get("description", "")[:400],
        "terms": cp.get("terms", "")[:400],
        "cta": cp.get("cta", "Claim Offer")[:40],
        "audience": cp.get("audience", "all"),
        "state": state, "image_url": "",
        "rules": {"min_cart": 0, "scope": "all", "scope_value": "", "usage_limit": 0,
                  "per_customer_limit": 1, "stackable": False, "start_date": body.schedule_at,
                  "end_date": None, "referral_enabled": False, "referral_credit_pct": 10},
        "stats": {"impressions": 0, "redemptions": 0, "revenue": 0.0, "referral_credit": 0.0},
        "created_at": now, "updated_at": now, "source": "one_click",
        "campaign_assets": {k: pkg.get(k) for k in
                            ("email", "sms", "whatsapp", "push", "social_caption",
                             "landing_headline", "ad_copy") if pkg.get(k)},
    }
    coupon["qr_code"] = gen_qr(f"{PUBLIC_APP_URL or ''}/c/{code}")
    await db.coupons.insert_one({**coupon})
    return {"ok": True, "coupon_id": coupon["id"], "code": code,
            "assets_saved": list(coupon["campaign_assets"].keys())}


# ---------------- Bundle B: Gift Cards + Store Credits + Coupon Wallet ----------------
class GiftCardIssueIn(BaseModel):
    amount: float
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    sender_name: Optional[str] = None
    message: Optional[str] = None
    send_email: bool = False


class GiftCardRedeemIn(BaseModel):
    code: str
    amount: float


class StoreCreditIssueIn(BaseModel):
    customer: str
    amount: float
    reason: str = "customer_appreciation"   # promotional | refund | referral | loyalty | customer_appreciation
    note: Optional[str] = None


def _gift_code() -> str:
    return "GC-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))


@api.post("/gift-cards")
async def issue_gift_card(body: GiftCardIssueIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    if body.amount <= 0:
        raise HTTPException(400, "amount must be > 0")
    if body.amount > 10000:
        raise HTTPException(400, "amount exceeds $10,000 limit")
    amount = round(float(body.amount), 2)
    code = _gift_code()
    doc = {
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
        "code": code, "amount": amount, "balance": amount,
        "recipient_email": body.recipient_email, "recipient_name": body.recipient_name,
        "sender_name": body.sender_name or user.get("name"),
        "message": body.message, "state": "active",
        "issued_by": user["id"], "created_at": now_iso(), "redeemed_at": None,
    }
    await db.gift_cards.insert_one({**doc})
    email_id = None
    if body.send_email and RESEND_API_KEY:
        ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
        primary = ws.get("primary_color", "#005CEE")
        html = f"""
<div style="font-family:Helvetica,Arial,sans-serif;max-width:560px;margin:auto;background:#0A0A0A;color:#fff;padding:32px;border-radius:16px">
  <div style="text-align:center;padding:20px;background:linear-gradient(135deg,{primary},#000);border-radius:12px;margin-bottom:20px">
    <div style="font-size:12px;letter-spacing:.2em;color:#fff9;text-transform:uppercase">{ws.get('name','A Gift For You')}</div>
    <div style="font-size:56px;font-weight:900;margin:12px 0">${amount:.0f}</div>
    <div style="font-size:14px;color:#fff9">Gift Card</div>
  </div>
  <p style="font-size:14px;line-height:1.5">Hi {body.recipient_name or 'there'}, {body.sender_name or 'A friend'} sent you a gift.</p>
  {(f'<p style="font-size:14px;font-style:italic;color:#A1A1AA">&ldquo;{body.message}&rdquo;</p>' if body.message else '')}
  <div style="background:#141414;border:2px dashed {primary};border-radius:10px;padding:16px;text-align:center;font-family:monospace;font-size:20px;font-weight:700;color:{primary};letter-spacing:2px;margin-top:20px">{code}</div>
  <p style="font-size:11px;color:#71717A;margin-top:20px;text-align:center">Redeem at checkout · balance visible at {PUBLIC_APP_URL or 'our store'}</p>
</div>"""
        try:
            r = await asyncio.to_thread(resend.Emails.send, {
                "from": SENDER_EMAIL, "to": [body.recipient_email],
                "subject": f"You've received a ${amount:.0f} gift card",
                "html": html})
            email_id = r.get("id") if isinstance(r, dict) else None
        except Exception as e:
            logger.warning("Gift email send failed: %s", e)
    return {"ok": True, "gift_card_id": doc["id"], "code": code, "email_id": email_id}


@api.get("/gift-cards")
async def list_gift_cards(user: dict = Depends(get_current_user)):
    docs = await db.gift_cards.find(
        {"workspace_id": user["workspace_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    total_issued = sum(d.get("amount", 0) for d in docs)
    total_balance = sum(d.get("balance", 0) for d in docs)
    return {"total_issued": round(total_issued, 2),
            "total_balance": round(total_balance, 2),
            "outstanding": round(total_balance, 2),
            "redeemed": round(total_issued - total_balance, 2),
            "cards": docs}


@api.post("/gift-cards/redeem")
async def redeem_gift_card(body: GiftCardRedeemIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    gc = await db.gift_cards.find_one({"code": body.code.upper(), "workspace_id": user["workspace_id"]})
    if not gc:
        raise HTTPException(404, "Gift card not found")
    if gc["state"] != "active":
        raise HTTPException(400, f"Gift card is {gc['state']}")
    if body.amount <= 0:
        raise HTTPException(400, "amount must be > 0")
    applied = round(min(body.amount, gc["balance"]), 2)
    new_bal = round(gc["balance"] - applied, 2)
    upd = {"balance": new_bal, "last_used_at": now_iso()}
    if new_bal <= 0:
        upd["state"] = "redeemed"
        upd["redeemed_at"] = now_iso()
    await db.gift_cards.update_one({"id": gc["id"]}, {"$set": upd})
    await db.gift_card_events.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
        "gift_card_id": gc["id"], "applied": applied, "balance_after": new_bal,
        "created_at": now_iso()})
    return {"ok": True, "applied": applied, "balance": new_bal,
            "state": upd.get("state", gc["state"])}


@api.get("/public/gift-cards/{code}")
async def public_gift_card_balance(code: str):
    gc = await db.gift_cards.find_one({"code": code.upper()}, {"_id": 0})
    if not gc:
        raise HTTPException(404, "Gift card not found")
    return {"code": gc["code"], "balance": gc["balance"], "amount": gc["amount"],
            "state": gc["state"]}


# ----- Store Credits -----
@api.post("/store-credits")
async def issue_store_credit(body: StoreCreditIssueIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    if body.amount == 0:
        raise HTTPException(400, "amount cannot be zero")
    doc = {
        "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
        "customer": body.customer, "amount": float(body.amount),
        "balance": float(body.amount), "reason": body.reason, "note": body.note,
        "issued_by": user["id"], "created_at": now_iso(),
    }
    await db.store_credits.insert_one({**doc})
    return {"ok": True, "credit_id": doc["id"], "customer": body.customer, "balance": doc["balance"]}


@api.get("/store-credits")
async def list_store_credits(customer: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = {"workspace_id": user["workspace_id"]}
    if customer:
        q["customer"] = customer
    docs = await db.store_credits.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    total = sum(d.get("balance", 0) for d in docs)
    by_customer: Dict[str, float] = {}
    for d in docs:
        by_customer[d["customer"]] = by_customer.get(d["customer"], 0) + d.get("balance", 0)
    return {"total_outstanding": round(total, 2),
            "by_customer": {k: round(v, 2) for k, v in by_customer.items()},
            "credits": docs}


# ----- Public Wallet -----
@api.get("/public/wallet/{customer_token}")
async def public_wallet(customer_token: str, workspace_id: Optional[str] = None):
    """Show everything a customer has: coupons redeemed, credits, gift cards on their email, loyalty."""
    # customer_token = email or opaque identifier used at redemption time
    customer = customer_token
    q_ws = {"workspace_id": workspace_id} if workspace_id else {}
    # Gift cards issued to this email
    gcs = await db.gift_cards.find(
        {**q_ws, "recipient_email": customer, "state": {"$ne": "cancelled"}}, {"_id": 0}
    ).to_list(50)
    # Store credits
    credits = await db.store_credits.find({**q_ws, "customer": customer}, {"_id": 0}).to_list(50)
    # Loyalty
    ml = await db.loyalty_members.find_one({**q_ws, "customer": customer}, {"_id": 0})
    # Recent redemptions
    reds = await db.redemptions.find(
        {**q_ws, "customer": customer}, {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    ws_name = ""
    if reds or gcs or credits or ml:
        wid = (reds[0]["workspace_id"] if reds else
               gcs[0]["workspace_id"] if gcs else
               credits[0]["workspace_id"] if credits else
               ml["workspace_id"] if ml else None)
        if wid:
            ws = await db.workspaces.find_one({"id": wid}, {"_id": 0}) or {}
            ws_name = ws.get("name", "")
    return {
        "customer": customer, "workspace_name": ws_name,
        "gift_cards": [{"code": g["code"], "amount": g["amount"], "balance": g["balance"],
                        "state": g["state"]} for g in gcs],
        "store_credits_total": round(sum(c.get("balance", 0) for c in credits), 2),
        "store_credits": credits,
        "loyalty": ml or None,
        "recent_redemptions": [{"code": r.get("code"), "discount": r.get("discount", 0),
                                "created_at": r.get("created_at")} for r in reds[:10]],
    }


# ---------------- Bundle C: Campaign Journeys ----------------
class JourneyIn(BaseModel):
    name: str
    trigger: str = "signup"      # signup | purchase | inactive_30d | birthday
    steps: List[dict] = []       # [{type: "wait"|"send_email"|"send_sms"|"send_coupon", ...}]
    enabled: bool = False


@api.post("/journeys")
async def create_journey(body: JourneyIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    doc = {"id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
           "name": body.name, "trigger": body.trigger, "steps": body.steps,
           "enabled": body.enabled, "stats": {"entered": 0, "completed": 0, "conversions": 0},
           "created_at": now_iso()}
    await db.journeys.insert_one({**doc})
    return doc


@api.get("/journeys")
async def list_journeys(user: dict = Depends(get_current_user)):
    docs = await db.journeys.find({"workspace_id": user["workspace_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@api.put("/journeys/{jid}")
async def update_journey(jid: str, body: JourneyIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    res = await db.journeys.update_one(
        {"id": jid, "workspace_id": user["workspace_id"]},
        {"$set": {**body.model_dump(), "updated_at": now_iso()}})
    if res.matched_count == 0:
        raise HTTPException(404, "Journey not found")
    return {"ok": True}


@api.delete("/journeys/{jid}")
async def delete_journey(jid: str, user: dict = Depends(get_current_user)):
    require_writer(user)
    await db.journeys.delete_one({"id": jid, "workspace_id": user["workspace_id"]})
    await db.journey_runs.update_many(
        {"journey_id": jid, "status": {"$in": ["pending", "waiting"]}},
        {"$set": {"status": "cancelled", "completed_at": now_iso()}})
    return {"ok": True}


class JourneyEnrollIn(BaseModel):
    customer: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


async def _enroll_customer_in_journey(journey: dict, customer: str,
                                      email: Optional[str] = None,
                                      phone: Optional[str] = None) -> dict:
    existing = await db.journey_runs.find_one({
        "journey_id": journey["id"], "customer": customer,
        "status": {"$in": ["pending", "waiting"]}})
    if existing:
        return {"skipped": True, "reason": "already enrolled"}
    run = {
        "id": str(uuid.uuid4()), "workspace_id": journey["workspace_id"],
        "journey_id": journey["id"], "customer": customer,
        "email": email, "phone": phone,
        "current_step": 0, "status": "pending",
        "next_at": now_iso(), "started_at": now_iso(),
        "log": [],
    }
    await db.journey_runs.insert_one({**run})
    await db.journeys.update_one({"id": journey["id"]},
                                 {"$inc": {"stats.entered": 1}})
    return {"ok": True, "run_id": run["id"]}


@api.post("/journeys/{jid}/enroll")
async def enroll_in_journey(jid: str, body: JourneyEnrollIn,
                            user: dict = Depends(get_current_user)):
    require_writer(user)
    j = await db.journeys.find_one({"id": jid, "workspace_id": user["workspace_id"]}, {"_id": 0})
    if not j:
        raise HTTPException(404, "Journey not found")
    if not j.get("enabled"):
        raise HTTPException(400, "Journey is disabled")
    return await _enroll_customer_in_journey(j, body.customer, body.email, body.phone)


@api.get("/journeys/{jid}/runs")
async def journey_runs(jid: str, user: dict = Depends(get_current_user)):
    runs = await db.journey_runs.find(
        {"journey_id": jid, "workspace_id": user["workspace_id"]},
        {"_id": 0}).sort("started_at", -1).to_list(200)
    return runs


async def _fire_trigger(workspace_id: str, trigger: str, customer: str,
                        email: Optional[str] = None, phone: Optional[str] = None):
    """Auto-enroll a customer into every enabled journey matching a trigger."""
    async for j in db.journeys.find({"workspace_id": workspace_id,
                                      "trigger": trigger, "enabled": True}, {"_id": 0}):
        try:
            await _enroll_customer_in_journey(j, customer, email, phone)
        except Exception as e:
            logger.warning("Journey enroll failed: %s", e)


async def _execute_journey_step(run: dict) -> None:
    """Perform a single step of a journey run. Advances current_step or schedules next_at."""
    j = await db.journeys.find_one({"id": run["journey_id"]}, {"_id": 0})
    if not j:
        await db.journey_runs.update_one({"id": run["id"]},
            {"$set": {"status": "cancelled", "completed_at": now_iso(),
                      "log": run.get("log", []) + ["journey deleted"]}})
        return
    steps = j.get("steps", [])
    idx = run["current_step"]
    if idx >= len(steps):
        await db.journey_runs.update_one({"id": run["id"]},
            {"$set": {"status": "completed", "completed_at": now_iso()}})
        await db.journeys.update_one({"id": j["id"]},
            {"$inc": {"stats.completed": 1}})
        return
    step = steps[idx]
    ws = await db.workspaces.find_one({"id": j["workspace_id"]}, {"_id": 0}) or {}
    log_entry = {"at": now_iso(), "step": idx, "type": step.get("type")}
    next_at = now_iso()
    try:
        if step["type"] == "wait":
            hours = float(step.get("hours", 1))
            next_at = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
            log_entry["waited_hours"] = hours
        elif step["type"] == "send_email":
            if not RESEND_API_KEY or not run.get("email"):
                log_entry["skipped"] = "email not configured or missing recipient"
            else:
                subject = step.get("subject", f"A message from {ws.get('name','us')}")
                body = step.get("body", "Thanks for being with us.")
                html = f"<div style='font-family:Helvetica,Arial,sans-serif;padding:24px;background:#0A0A0A;color:#fff'><h2>{subject}</h2><p style='color:#A1A1AA'>{body}</p></div>"
                r = await asyncio.to_thread(resend.Emails.send, {
                    "from": SENDER_EMAIL, "to": [run["email"]],
                    "subject": subject, "html": html})
                log_entry["email_id"] = r.get("id") if isinstance(r, dict) else None
        elif step["type"] == "send_sms":
            if not twilio_client or not run.get("phone") or not TWILIO_FROM_SMS:
                log_entry["skipped"] = "sms not configured or missing recipient"
            else:
                sid = await _twilio_send_one(run["phone"], step.get("body", "Hi from us!"), "sms")
                log_entry["sms_sid"] = sid
        elif step["type"] == "send_coupon":
            # Auto-create a coupon and record the code
            disc = float(step.get("discount", 15))
            code = "JRN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            new_cp = {
                "id": str(uuid.uuid4()), "workspace_id": j["workspace_id"],
                "code": code, "codes": [code],
                "name": f"Journey reward — {j['name']}"[:80],
                "type": step.get("type_coupon", "percentage"),
                "discount_value": disc, "headline": step.get("headline", f"{int(disc)}% just for you"),
                "description": step.get("description", ""),
                "terms": "One-time use. Journey-generated.",
                "cta": "Claim", "audience": run.get("customer"),
                "state": "active",
                "image_url": "", "qr_code": gen_qr(f"{PUBLIC_APP_URL or ''}/c/{code}"),
                "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                          "usage_limit": 1, "per_customer_limit": 1, "stackable": False,
                          "start_date": None, "end_date": None,
                          "referral_enabled": False, "referral_credit_pct": 10},
                "stats": {"impressions": 0, "redemptions": 0, "revenue": 0.0, "referral_credit": 0.0},
                "created_at": now_iso(), "updated_at": now_iso(), "source": "journey",
            }
            await db.coupons.insert_one({**new_cp})
            log_entry["coupon_code"] = code
            # Also try to deliver by email if we can
            if RESEND_API_KEY and run.get("email"):
                try:
                    subject = f"A special reward: {int(disc)}% off"
                    landing = f"{PUBLIC_APP_URL or ''}/c/{code}"
                    html = render_coupon_email(new_cp, ws, landing)
                    await asyncio.to_thread(resend.Emails.send, {
                        "from": SENDER_EMAIL, "to": [run["email"]],
                        "subject": subject, "html": html})
                    log_entry["email_delivered"] = True
                except Exception as e:
                    log_entry["email_error"] = str(e)[:120]
        else:
            log_entry["skipped"] = f"unknown step type {step['type']}"
    except Exception as e:
        log_entry["error"] = str(e)[:200]
    # Advance
    new_idx = idx + 1
    new_status = "waiting" if step["type"] == "wait" else "pending"
    if new_idx >= len(steps):
        new_status = "completed"
        await db.journeys.update_one({"id": j["id"]}, {"$inc": {"stats.completed": 1}})
    await db.journey_runs.update_one({"id": run["id"]}, {
        "$set": {"current_step": new_idx, "status": new_status,
                 "next_at": next_at if new_status != "completed" else None,
                 "completed_at": now_iso() if new_status == "completed" else None},
        "$push": {"log": log_entry}})


async def journey_worker():
    """Background loop: process any due runs every 30 seconds."""
    while True:
        try:
            now = datetime.now(timezone.utc).isoformat()
            due = await db.journey_runs.find({
                "status": {"$in": ["pending", "waiting"]},
                "next_at": {"$lte": now}}).to_list(50)
            for run in due:
                await _execute_journey_step({k: v for k, v in run.items() if k != "_id"})
        except Exception as e:
            logger.exception("journey_worker crash: %s", e)
        await asyncio.sleep(30)


# ---------------- Bundle D: Customer CRM + AI Segmentation ----------------
async def _aggregate_customers(workspace_id: str) -> List[dict]:
    """Compute a per-customer summary from redemptions + loyalty + gift_cards + credits."""
    pipeline = [
        {"$match": {"workspace_id": workspace_id, "customer": {"$ne": None}}},
        {"$group": {
            "_id": "$customer",
            "orders": {"$sum": 1},
            "spend": {"$sum": "$revenue"},
            "discount": {"$sum": "$discount"},
            "last_at": {"$max": "$created_at"},
            "first_at": {"$min": "$created_at"},
        }},
        {"$sort": {"spend": -1}}, {"$limit": 500},
    ]
    reds = await db.redemptions.aggregate(pipeline).to_list(500)
    result = []
    for r in reds:
        member = await db.loyalty_members.find_one(
            {"workspace_id": workspace_id, "customer": r["_id"]}, {"_id": 0})
        credit_sum = 0.0
        async for c in db.store_credits.find(
                {"workspace_id": workspace_id, "customer": r["_id"]}, {"balance": 1}):
            credit_sum += c.get("balance", 0)
        result.append({
            "customer": r["_id"], "orders": r["orders"],
            "spend": round(r["spend"], 2), "discount": round(r["discount"], 2),
            "last_at": r["last_at"], "first_at": r["first_at"],
            "loyalty_points": (member or {}).get("points", 0),
            "loyalty_tier": (member or {}).get("tier", "—"),
            "store_credit": round(credit_sum, 2),
        })
    return result


def _segment_customer(c: dict, now: datetime) -> str:
    try:
        last = datetime.fromisoformat(c.get("last_at", "").replace("Z", "+00:00"))
    except Exception:
        last = now
    days_since = max(0, (now - last).days)
    orders = c.get("orders", 0)
    spend = c.get("spend", 0)
    if spend >= 500 and orders >= 5:
        return "vip"
    if orders == 1 and days_since <= 14:
        return "new"
    if days_since >= 30:
        return "at_risk"
    if orders >= 3:
        return "frequent"
    return "regular"


@api.get("/customers")
async def customers(user: dict = Depends(get_current_user)):
    rows = await _aggregate_customers(user["workspace_id"])
    now = datetime.now(timezone.utc)
    counts: Dict[str, int] = {}
    for r in rows:
        seg = _segment_customer(r, now)
        r["segment"] = seg
        counts[seg] = counts.get(seg, 0) + 1
    total_spend = sum(r.get("spend", 0) for r in rows)
    total_orders = sum(r.get("orders", 0) for r in rows)
    n = len(rows)
    # Aggregate CAC estimate — the workspace's own spend on discounts is a proxy cost per new customer
    total_discount = sum(r.get("discount", 0) for r in rows)
    new_n = counts.get("new", 0)
    cac = round(total_discount / new_n, 2) if new_n else 0.0
    clv = round((total_spend / n), 2) if n else 0.0
    avg_orders = round((total_orders / n), 2) if n else 0.0
    return {
        "total": n, "by_segment": counts,
        "metrics": {
            "cac": cac, "clv": clv, "avg_orders": avg_orders,
            "total_spend": round(total_spend, 2),
            "total_discount": round(total_discount, 2),
        },
        "customers": rows,
    }


@api.post("/customers/{customer}/message")
async def message_customer(customer: str, body: dict, user: dict = Depends(get_current_user)):
    """Convenience wrapper — sends the branded coupon email to the given customer using a coupon id."""
    require_writer(user)
    cid = body.get("coupon_id")
    if not cid:
        raise HTTPException(400, "coupon_id required")
    return await send_coupon_email(
        cid, SendCouponEmailIn(to=[customer], landing_url=body.get("landing_url")), user)


class SegmentPromoIn(BaseModel):
    segment: str          # vip | at_risk | new | frequent | regular


@api.post("/ai/segment-promo")
async def ai_segment_promo(body: SegmentPromoIn, user: dict = Depends(get_current_user)):
    """AI-generated promo copy tailored to a customer segment."""
    ap = (await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}).get("autopilot") or {}
    system = ("You write hyper-personalized promotional copy for a specific customer segment. "
              "Return ONLY a JSON object with keys: headline (max 10 words), description (1-2 sentences), "
              "cta (max 4 words), discount_value (int under the cap), type (percentage|flash_sale|first_time|vip).")
    prompt = f"Segment: {body.segment}. Cap: {ap.get('max_discount',25)}%. Voice: {ap.get('brand_voice','confident')}."
    return await _ai_json(system, prompt, f"seg-{uuid.uuid4()}")


# ---------------- Bundle E: Template Marketplace ----------------
DEFAULT_TEMPLATES = [
    {"id": "luxe-black", "name": "Luxe Black", "category": "Luxury",
     "primary": "#0A0A0A", "secondary": "#D4AF37",
     "headline_style": "aspirational", "example_headline": "An Invitation, Just For You",
     "cover": "linear-gradient(135deg,#0A0A0A,#3A2E12)"},
    {"id": "flash-neon", "name": "Neon Flash", "category": "Flash Sale",
     "primary": "#00E0A4", "secondary": "#FFEA00",
     "headline_style": "urgent", "example_headline": "24 HOURS ONLY — Move Fast",
     "cover": "linear-gradient(135deg,#00E0A4,#FFEA00)"},
    {"id": "playful-candy", "name": "Playful Candy", "category": "Retail",
     "primary": "#FF4EC7", "secondary": "#FFD9EC",
     "headline_style": "playful", "example_headline": "Treat Yourself, Silly Prices",
     "cover": "linear-gradient(135deg,#FF4EC7,#FFD9EC)"},
    {"id": "minimal-mono", "name": "Minimal Mono", "category": "Modern",
     "primary": "#FFFFFF", "secondary": "#0A0A0A",
     "headline_style": "clean", "example_headline": "Less is More.",
     "cover": "linear-gradient(135deg,#F5F5F5,#0A0A0A)"},
    {"id": "holiday-warm", "name": "Holiday Warm", "category": "Holiday",
     "primary": "#B8171A", "secondary": "#F4B942",
     "headline_style": "warm", "example_headline": "Home For The Holidays — Save Together",
     "cover": "linear-gradient(135deg,#B8171A,#F4B942)"},
    {"id": "vip-onyx", "name": "VIP Onyx", "category": "VIP",
     "primary": "#141414", "secondary": "#CCFF00",
     "headline_style": "exclusive", "example_headline": "Members Only — Reserved For You",
     "cover": "linear-gradient(135deg,#141414,#CCFF00)"},
]


@api.get("/templates")
async def list_templates():
    return DEFAULT_TEMPLATES


class RestyleIn(BaseModel):
    template_id: str
    coupon_id: Optional[str] = None


@api.post("/templates/apply")
async def apply_template(body: RestyleIn, user: dict = Depends(get_current_user)):
    require_writer(user)
    tpl = next((t for t in DEFAULT_TEMPLATES if t["id"] == body.template_id), None)
    if not tpl:
        raise HTTPException(404, "Template not found")
    # Update workspace brand kit to match template
    await db.workspaces.update_one(
        {"id": user["workspace_id"]},
        {"$set": {"primary_color": tpl["primary"], "secondary_color": tpl["secondary"],
                  "updated_at": now_iso()}})
    return {"ok": True, "applied": tpl["id"]}


# ---------------- Bundle F: API Keys ----------------
class ApiKeyIn(BaseModel):
    name: str
    scopes: List[str] = ["read", "write"]


def _api_key_str() -> str:
    return "pk_live_" + _pysecrets.token_urlsafe(24)


@api.post("/api-keys")
async def create_api_key(body: ApiKeyIn, user: dict = Depends(get_current_user)):
    if user.get("role") != "owner":
        raise HTTPException(403, "Only owners can create API keys")
    key = _api_key_str()
    # Store plaintext prefix (first 16 chars: "pk_live_" + 8 chars) for O(1) index lookup.
    # Remaining entropy still gated by bcrypt on the full token.
    doc = {"id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
           "name": body.name, "scopes": body.scopes, "key_preview": key[:14] + "…",
           "key_prefix": key[:16],
           "key_hash": bcrypt.hashpw(key.encode(), bcrypt.gensalt(rounds=10)).decode(),
           "created_by": user["id"], "created_at": now_iso(), "last_used_at": None,
           "revoked": False}
    await db.api_keys.insert_one({**doc})
    doc_out = {k: v for k, v in doc.items() if k != "key_hash"}
    doc_out["key"] = key   # only shown once
    return doc_out


@api.get("/api-keys")
async def list_api_keys(user: dict = Depends(get_current_user)):
    docs = await db.api_keys.find(
        {"workspace_id": user["workspace_id"]},
        {"_id": 0, "key_hash": 0}
    ).sort("created_at", -1).to_list(50)
    return docs


@api.post("/api-keys/{kid}/revoke")
async def revoke_api_key(kid: str, user: dict = Depends(get_current_user)):
    if user.get("role") != "owner":
        raise HTTPException(403, "Only owners can revoke API keys")
    res = await db.api_keys.update_one(
        {"id": kid, "workspace_id": user["workspace_id"]},
        {"$set": {"revoked": True, "revoked_at": now_iso()}})
    if res.matched_count == 0:
        raise HTTPException(404, "API key not found")
    return {"ok": True}


# ---------------- Exports (CSV / PDF) ----------------
import csv as _csv


async def _period_start(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def _export_report_rows(workspace_id: str, days: int) -> dict:
    since = await _period_start(days)
    reds = await db.redemptions.find(
        {"workspace_id": workspace_id, "created_at": {"$gt": since}},
        {"_id": 0}).to_list(20000)
    coupons = await db.coupons.find(
        {"workspace_id": workspace_id}, {"_id": 0, "qr_code": 0}).to_list(500)
    ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0}) or {}
    per_coupon: Dict[str, Dict[str, float]] = {}
    for r in reds:
        cid = r.get("coupon_id"); c = per_coupon.setdefault(cid, {
            "code": r.get("code"), "redemptions": 0, "revenue": 0.0, "discount": 0.0})
        c["redemptions"] += 1
        c["revenue"] += r.get("revenue", 0)
        c["discount"] += r.get("discount", 0)
    total_reds = len(reds)
    total_rev = sum(r.get("revenue", 0) for r in reds)
    total_disc = sum(r.get("discount", 0) for r in reds)
    return {
        "workspace_name": ws.get("name", ""),
        "period_days": days, "since": since,
        "total_redemptions": total_reds,
        "total_revenue": round(total_rev, 2),
        "total_discount": round(total_disc, 2),
        "avg_order_value": round(total_rev / total_reds, 2) if total_reds else 0.0,
        "top_coupons": sorted(per_coupon.values(),
                              key=lambda x: x["revenue"], reverse=True)[:20],
        "coupons": coupons,
        "generated_at": now_iso(),
    }


@api.get("/analytics/export")
async def export_report(format: str = "csv", period: int = 30,
                        user: dict = Depends(get_current_user)):
    if format not in ("csv", "pdf"):
        raise HTTPException(400, "format must be csv or pdf")
    if period not in (7, 14, 30, 60, 90, 180, 365):
        period = 30
    rpt = await _export_report_rows(user["workspace_id"], period)
    fname = f"promoos-report-{rpt['workspace_name'].lower().replace(' ','-') or 'workspace'}-{period}d"
    if format == "csv":
        buf = io.StringIO()
        w = _csv.writer(buf)
        w.writerow(["PromoOS Performance Report"])
        w.writerow(["Workspace", rpt["workspace_name"]])
        w.writerow(["Period", f"Last {period} days"])
        w.writerow(["Generated", rpt["generated_at"]])
        w.writerow([])
        w.writerow(["Total redemptions", rpt["total_redemptions"]])
        w.writerow(["Total revenue", rpt["total_revenue"]])
        w.writerow(["Total discount given", rpt["total_discount"]])
        w.writerow(["Avg order value", rpt["avg_order_value"]])
        w.writerow([])
        w.writerow(["--- Top coupons ---"])
        w.writerow(["Code", "Redemptions", "Revenue", "Discount"])
        for c in rpt["top_coupons"]:
            w.writerow([c["code"], c["redemptions"], round(c["revenue"], 2), round(c["discount"], 2)])
        w.writerow([])
        w.writerow(["--- All coupons ---"])
        w.writerow(["Code", "Name", "Type", "Discount", "State",
                    "Impressions", "Redemptions", "Revenue"])
        for c in rpt["coupons"]:
            stats = c.get("stats") or {}
            w.writerow([c.get("code"), c.get("name"), c.get("type"),
                        c.get("discount_value"), c.get("state"),
                        stats.get("impressions", 0),
                        stats.get("redemptions", 0),
                        round(stats.get("revenue", 0), 2)])
        return Response(content=buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{fname}.csv"'})
    # PDF branch
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER,
                            leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#0A0A0A"), spaceAfter=6)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#005CEE"), spaceBefore=12, spaceAfter=6)
    small = ParagraphStyle("s", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#71717A"))
    body = []
    body.append(Paragraph("PromoOS Performance Report", title))
    body.append(Paragraph(f"{rpt['workspace_name']} · Last {period} days", small))
    body.append(Paragraph(rpt["generated_at"][:19].replace("T", " ") + " UTC", small))
    body.append(Spacer(1, 12))
    kpi_data = [
        ["Total Redemptions", "Total Revenue", "Total Discount", "AOV"],
        [str(rpt["total_redemptions"]),
         f"${rpt['total_revenue']:,.2f}",
         f"${rpt['total_discount']:,.2f}",
         f"${rpt['avg_order_value']:,.2f}"],
    ]
    kt = Table(kpi_data, colWidths=[120, 120, 120, 120])
    kt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0A0A0A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 14),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
    ]))
    body.append(kt)
    body.append(Paragraph("Top coupons by revenue", h2))
    tbl = [["Code", "Redemptions", "Revenue", "Discount"]] + [
        [c["code"], str(c["redemptions"]),
         f"${round(c['revenue'], 2):,.2f}",
         f"${round(c['discount'], 2):,.2f}"] for c in rpt["top_coupons"][:15]]
    t = Table(tbl, colWidths=[120, 100, 140, 120])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#005CEE")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E4E4E7")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]))
    body.append(t)
    body.append(Spacer(1, 12))
    body.append(Paragraph("Generated by PromoOS · promoos.com", small))
    doc.build(body)
    pdf = buf.getvalue()
    buf.close()
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}.pdf"'})


# ---------------- POS Connectors (Shopify + WooCommerce) ----------------
def _hmac_ok(secret: str, raw: bytes, signature_header: Optional[str]) -> bool:
    """Compare base64(hmac-sha256(secret, raw)) with the provided signature header."""
    if not signature_header:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature_header.strip())


async def _get_workspace_secret(workspace_id: str, provider: str) -> Optional[str]:
    ws = await db.workspaces.find_one({"id": workspace_id}, {"_id": 0})
    if not ws:
        return None
    return (ws.get("webhook_secrets") or {}).get(provider)


class PublicValidateIn(BaseModel):
    code: str
    amount: float = 0
    customer: Optional[str] = None


@api.post("/public/coupons/validate")
async def public_validate(body: PublicValidateIn):
    """Public validation used by POS checkouts to preview a discount before finalizing."""
    code = body.code.upper()
    c = await db.coupons.find_one({"$or": [{"code": code}, {"codes": code}]}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Code not found")
    if c["state"] != "active":
        raise HTTPException(400, f"Coupon is {c['state']}")
    rules = c.get("rules") or {}
    end_date = rules.get("end_date")
    if end_date and end_date < now_iso():
        raise HTTPException(400, "Coupon has expired")
    if rules.get("min_cart", 0) and body.amount < rules["min_cart"]:
        raise HTTPException(400, f"Minimum cart of ${rules['min_cart']} required")
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
    return {"ok": True, "code": code, "discount": discount,
            "type": c["type"], "value": c["discount_value"],
            "headline": c.get("headline"), "terms": c.get("terms")}


async def _apply_from_pos(source: str, workspace_id: str, code: str, amount: float,
                          customer: Optional[str], order_id: Optional[str],
                          currency: Optional[str] = None) -> dict:
    c = await db.coupons.find_one({"$or": [{"code": code.upper()}, {"codes": code.upper()}],
                                   "workspace_id": workspace_id})
    if not c or c["state"] != "active":
        return {"applied": False, "reason": "coupon inactive or missing"}
    percent_types = {"percentage", "flash_sale", "seasonal", "vip",
                     "first_time", "birthday", "referral"}
    if c["type"] in percent_types:
        discount = amount * c["discount_value"] / 100
    elif c["type"] == "fixed":
        discount = min(c["discount_value"], amount)
    elif c["type"] == "bogo":
        discount = amount * 0.5
    else:
        discount = 0
    discount = round(min(discount, amount), 2)
    rev = round(max(amount - discount, 0), 2)
    await db.redemptions.insert_one({
        "id": str(uuid.uuid4()), "workspace_id": workspace_id, "coupon_id": c["id"],
        "code": code.upper(), "customer": customer or "pos", "amount": amount,
        "discount": discount, "revenue": rev, "source": source,
        "external_order_id": order_id, "currency": currency or "USD",
        "created_at": now_iso()})
    await db.coupons.update_one({"id": c["id"]},
        {"$inc": {"stats.redemptions": 1, "stats.revenue": rev}})
    if customer:
        await _fire_trigger(workspace_id, "purchase", customer,
                            email=customer if "@" in customer else None)
    return {"applied": True, "discount": discount, "revenue": rev, "order_id": order_id}


@api.get("/pos/legacy-removed", include_in_schema=False)
async def _pos_removed_marker(): return {"moved": "routers/pos.py"}


# ---------------- API Key auth helper (server-to-server) ----------------
async def verify_api_key(authorization: Optional[str] = None) -> dict:
    """Bearer-token verification for public v1 endpoints. Returns the key doc."""
    from fastapi import Header
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if not token.startswith("pk_live_") or len(token) < 16:
        raise HTTPException(401, "Not a PromoOS API key")
    prefix = token[:16]
    # O(1) index lookup by prefix; bcrypt only runs on candidates matching the prefix.
    async for k in db.api_keys.find({"key_prefix": prefix, "revoked": {"$ne": True}}):
        try:
            if bcrypt.checkpw(token.encode(), k["key_hash"].encode()):
                await db.api_keys.update_one({"id": k["id"]},
                    {"$set": {"last_used_at": now_iso()}})
                return {k2: v for k2, v in k.items() if k2 not in ("_id", "key_hash")}
        except Exception:
            continue
    # Legacy fallback: older keys created without key_prefix (backfilled on next use).
    async for k in db.api_keys.find({"key_prefix": {"$exists": False}, "revoked": {"$ne": True}}):
        try:
            if bcrypt.checkpw(token.encode(), k["key_hash"].encode()):
                await db.api_keys.update_one({"id": k["id"]},
                    {"$set": {"last_used_at": now_iso(), "key_prefix": prefix}})
                return {k2: v for k2, v in k.items() if k2 not in ("_id", "key_hash")}
        except Exception:
            continue
    raise HTTPException(401, "Invalid or revoked API key")


from fastapi import Header


@api.post("/v1/coupons/redeem")
async def v1_redeem(body: PublicRedeemIn, authorization: Optional[str] = Header(None)):
    """Server-to-server redemption endpoint that requires a valid pk_live_ API key."""
    key = await verify_api_key(authorization)
    # scope check
    if "write" not in (key.get("scopes") or []):
        raise HTTPException(403, "Key lacks 'write' scope")
    return await public_redeem(body)


# ---------------- All 23 Coupon Types (Coupon Library) ----------------
COUPON_LIBRARY = [
    {"id": "percentage", "name": "Percentage Discount", "cat": "Discount",
     "desc": "Classic % off any order (10, 20, 25…).",
     "default_value": 20, "audience": "all"},
    {"id": "fixed", "name": "Fixed Amount", "cat": "Discount",
     "desc": "Flat dollar amount off ($5, $10, $25…).",
     "default_value": 10, "audience": "all"},
    {"id": "bogo", "name": "Buy One Get One", "cat": "Bundle",
     "desc": "Effectively 50% off — pair items at checkout.",
     "default_value": 50, "audience": "all"},
    {"id": "buy_x_get_y", "name": "Buy X Get Y", "cat": "Bundle",
     "desc": "Custom quantity thresholds (Buy 2, get 1 free).",
     "default_value": 33, "audience": "all"},
    {"id": "free_shipping", "name": "Free Shipping", "cat": "Perk",
     "desc": "Removes shipping at checkout.",
     "default_value": 0, "audience": "all"},
    {"id": "free_gift", "name": "Free Gift", "cat": "Perk",
     "desc": "Bundle a complimentary item with any purchase.",
     "default_value": 0, "audience": "all"},
    {"id": "free_service", "name": "Free Service", "cat": "Perk",
     "desc": "Complimentary consultation, install, or repair.",
     "default_value": 0, "audience": "all"},
    {"id": "bundle", "name": "Bundle Discount", "cat": "Bundle",
     "desc": "% off when specific SKUs are purchased together.",
     "default_value": 15, "audience": "all"},
    {"id": "first_time", "name": "First-Time Customer", "cat": "Acquisition",
     "desc": "Only redeemable on the customer's first order.",
     "default_value": 15, "audience": "new"},
    {"id": "returning", "name": "Returning Customer", "cat": "Retention",
     "desc": "Rewards customers on their second and beyond.",
     "default_value": 10, "audience": "returning"},
    {"id": "referral", "name": "Referral Coupon", "cat": "Growth",
     "desc": "Given by an existing customer to a friend.",
     "default_value": 10, "audience": "new"},
    {"id": "birthday", "name": "Birthday Coupon", "cat": "Lifecycle",
     "desc": "Auto-fires in the customer's birthday month.",
     "default_value": 20, "audience": "returning"},
    {"id": "anniversary", "name": "Anniversary Coupon", "cat": "Lifecycle",
     "desc": "Celebrates the customer's first purchase date.",
     "default_value": 15, "audience": "returning"},
    {"id": "abandoned_cart", "name": "Abandoned Cart", "cat": "Retention",
     "desc": "Recovers customers who left with items in cart.",
     "default_value": 10, "audience": "returning"},
    {"id": "vip", "name": "VIP Coupon", "cat": "Loyalty",
     "desc": "Reserved for top-spending customers.",
     "default_value": 25, "audience": "vip"},
    {"id": "flash_sale", "name": "Flash Sale", "cat": "Urgency",
     "desc": "Time-boxed steep discount (a few hours).",
     "default_value": 25, "audience": "all"},
    {"id": "seasonal", "name": "Seasonal Coupon", "cat": "Urgency",
     "desc": "Holiday or seasonal moment (Summer, BFCM…).",
     "default_value": 20, "audience": "all"},
    {"id": "location_based", "name": "Location-Based", "cat": "Geo",
     "desc": "Fires when customer is inside a geofence.",
     "default_value": 15, "audience": "all"},
    {"id": "event", "name": "Event Coupon", "cat": "Campaign",
     "desc": "Tied to a specific event (launch, pop-up, tour).",
     "default_value": 15, "audience": "all"},
    {"id": "subscription", "name": "Subscription Coupon", "cat": "Recurring",
     "desc": "Applies to a recurring plan or bill cycle.",
     "default_value": 10, "audience": "all"},
    {"id": "membership", "name": "Membership Coupon", "cat": "Loyalty",
     "desc": "Perk for paid or free members only.",
     "default_value": 15, "audience": "vip"},
    {"id": "influencer", "name": "Influencer Coupon", "cat": "Attribution",
     "desc": "Unique code per creator with attribution.",
     "default_value": 15, "audience": "all"},
    {"id": "affiliate", "name": "Affiliate Coupon", "cat": "Attribution",
     "desc": "Track partner-driven redemptions + commissions.",
     "default_value": 10, "audience": "all"},
]


@api.get("/library/coupon-types")
async def coupons_library_route():
    return COUPON_LIBRARY


# ---------------- Superadmin / Platform Admin Portal ----------------
def require_superadmin(user: dict):
    if user.get("role") != "superadmin":
        raise HTTPException(403, "Superadmin only")


@api.get("/admin/stats-legacy-removed", include_in_schema=False)
async def _admin_removed_marker(): return {"moved": "routers/admin.py"}


async def _admin_log(actor: dict, action: str, target: Optional[str] = None,
                     meta: Optional[dict] = None):
    await db.admin_logs.insert_one({
        "id": str(uuid.uuid4()), "actor_id": actor["id"], "actor_email": actor["email"],
        "action": action, "target": target, "meta": meta or {},
        "created_at": now_iso()})


@api.get("/pos/legacy-removed-2", include_in_schema=False)
async def _pos_removed_marker_2(): return {"moved": "routers/pos.py"}


# ---------------- Phase 1 extras: Stripe billing, storage, currencies, fonts, share/download ----------------
from routers.billing import register_extras
from routers.giftcards import register as register_giftcards
from routers.oauth_hub import register as register_oauth
from routers.funnels import register as register_funnels
from routers.qr import register as register_qr
from routers.admin import register as register_admin
from routers.payments_alt import register as register_payments_alt
from routers.pos import register as register_pos
from routers.iter14 import register as register_iter14
extras_ctx = register_extras(api, db, EMERGENT_LLM_KEY, PUBLIC_APP_URL, now_iso,
                          get_current_user, require_writer, _admin_log)
register_giftcards(api, db, EMERGENT_LLM_KEY, now_iso, get_current_user, require_writer)
register_oauth(api, db, PUBLIC_APP_URL, now_iso, get_current_user, require_writer)
register_funnels(api, db, PUBLIC_APP_URL, now_iso, get_current_user, require_writer)
register_qr(api, db, now_iso, get_current_user, require_writer)
register_admin(api, db, now_iso, get_current_user, require_superadmin, hash_password, _admin_log)
register_payments_alt(api, db, now_iso, get_current_user)
register_pos(api, db, PUBLIC_APP_URL, now_iso, get_current_user,
             encrypt_str, decrypt_str, _hmac_ok, _apply_from_pos)
register_iter14(api, db, now_iso, get_current_user, require_writer,
                hash_password, verify_password, PUBLIC_APP_URL)

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
    # Superadmin (platform-level, always ensured; password rotated to match env)
    sa_email = os.environ.get("SUPERADMIN_EMAIL", "superadmin@promoos.com").lower()
    sa_pass = os.environ.get("SUPERADMIN_PASSWORD", "superadmin123")
    existing_sa = await db.users.find_one({"email": sa_email})
    if not existing_sa:
        pw = await db.workspaces.find_one({"is_platform": True}, {"_id": 0})
        pwid = pw["id"] if pw else str(uuid.uuid4())
        if not pw:
            await db.workspaces.insert_one({
                "id": pwid, "name": "PromoOS Platform", "is_platform": True,
                "primary_color": "#005CEE", "secondary_color": "#CCFF00",
                "created_at": now_iso()})
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "name": "Platform Admin", "email": sa_email,
            "password_hash": hash_password(sa_pass), "role": "superadmin",
            "workspace_id": pwid, "created_at": now_iso(),
            "suspended": False, "deleted_at": None})
    else:
        # Rotate password to match current env (idempotent).
        if not verify_password(sa_pass, existing_sa.get("password_hash", "")):
            await db.users.update_one({"id": existing_sa["id"]},
                {"$set": {"password_hash": hash_password(sa_pass), "role": "superadmin",
                          "suspended": False, "deleted_at": None}})
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
        await db.journey_runs.create_index([("status", 1), ("next_at", 1)])
        await db.api_keys.create_index("key_prefix")
        await db.uploads.create_index([("workspace_id", 1), ("is_deleted", 1)])
        await db.payment_transactions.create_index("session_id", unique=True)
        # OAuth state tokens expire after 10 minutes to prevent unbounded accumulation.
        await db.oauth_states.create_index("created_at", expireAfterSeconds=600)
        # Initialize object storage (best-effort).
        try:
            extras_ctx["init_storage"]()
        except Exception:
            pass
        await seed()
        asyncio.create_task(journey_worker())
    except Exception as e:
        logger.error(f"Seed error: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
