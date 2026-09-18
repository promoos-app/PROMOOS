"""Newsletter System — Beehiiv-style publications, subscribers, posts, referrals, analytics.

Collections created lazily:
    publications, newsletter_subscribers, newsletter_posts, newsletter_events

Endpoints (all under /api/newsletter):
    Publications
        POST/GET   /publications
        GET/PUT/DELETE /publications/{pid}
    Subscribers (auth: workspace)
        GET /publications/{pid}/subscribers
        POST /publications/{pid}/subscribers                (owner-add, no double opt-in)
        POST /publications/{pid}/subscribers/import-csv
        DELETE /publications/{pid}/subscribers/{sid}
    Posts
        POST/GET   /publications/{pid}/posts
        GET/PUT/DELETE /publications/{pid}/posts/{post_id}
        POST /publications/{pid}/posts/{post_id}/schedule
        POST /publications/{pid}/posts/{post_id}/send-test
        POST /publications/{pid}/posts/{post_id}/send-now
    Analytics
        GET /publications/{pid}/analytics
    Public (no auth)
        GET  /public/{slug}                             pub info + published posts
        GET  /public/{slug}/p/{post_slug}               full rendered post
        POST /public/{slug}/subscribe                   starts double opt-in
        GET  /public/confirm/{token}                    HTML confirmation
        GET  /public/{slug}/referral/{referral_token}   subscriber referral progress
    Tracking
        GET /track/open/{post_id}/{sub_id}.gif          1x1 open pixel
        GET /track/click/{post_id}/{sub_id}             302 redirect + record
"""
import uuid
import hashlib
import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import HTTPException, Depends, Request, Response, UploadFile, File
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("promoos.newsletter")

# 1x1 transparent GIF for open tracking (43 bytes)
_PIXEL_GIF = bytes([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00, 0x80, 0x00, 0x00,
    0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x21, 0xf9, 0x04, 0x01, 0x00, 0x00, 0x00,
    0x00, 0x2c, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02,
    0x44, 0x01, 0x00, 0x3b,
])

BLOCK_TYPES = {"heading", "text", "image", "button", "divider",
               "coupon", "giftcard", "funnel", "subscribe_form", "referral_cta",
               "video", "audio", "spacer"}


def _safe_color(val, default):
    """Accept only #rgb/#rrggbb hex strings; fall back to ``default`` otherwise.

    Prevents CSS injection through user-supplied color props while still
    letting merchants use their brand palette in every block.
    """
    if not isinstance(val, str): return default
    import re as _re
    if _re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", val.strip()):
        return val.strip()
    return default


def _slugify(s: str, existing: set = None) -> str:
    import re
    base = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:60] or f"post-{secrets.token_hex(3)}"
    if not existing: return base
    slug = base; i = 2
    while slug in existing:
        slug = f"{base}-{i}"; i += 1
    return slug


class PublicationIn(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = ""
    sender_name: Optional[str] = ""
    sender_email: Optional[EmailStr] = None
    primary_color: Optional[str] = "#005CEE"
    subscribe_headline: Optional[str] = "Join the list"
    subscribe_body: Optional[str] = "Weekly-ish. Unsubscribe anytime."
    thanks_headline: Optional[str] = "You're in ✓"
    thanks_body: Optional[str] = "Check your inbox to confirm your address."
    referral_rewards: Optional[List[dict]] = None  # [{count: 3, coupon_percent: 10}, ...]


class SubscriberIn(BaseModel):
    email: EmailStr
    name: Optional[str] = ""
    phone: Optional[str] = ""
    tags: Optional[List[str]] = None
    source: Optional[str] = "owner_add"


class PublicSubscribeIn(BaseModel):
    email: EmailStr
    name: Optional[str] = ""
    ref: Optional[str] = None  # referral_token of referring subscriber


class PostIn(BaseModel):
    title: str
    subtitle: Optional[str] = ""
    slug: Optional[str] = None
    blocks: Optional[List[dict]] = None
    channels: Optional[List[str]] = None  # ["email", "sms", "whatsapp"]
    sms_body: Optional[str] = ""


class ScheduleIn(BaseModel):
    scheduled_at: str  # ISO


class SendTestIn(BaseModel):
    email: EmailStr


class AIDraftIn(BaseModel):
    brief: str
    tone: Optional[str] = "friendly, punchy, brand-aware"


class DomainIn(BaseModel):
    name: str  # e.g. mail.acme.com


def register(api, db, now_iso, get_current_user, require_writer, ctx):
    """
    ctx: {resend, sender_default, public_url, jwt_secret, unsubscribe_token_for}
    """
    resend = ctx["resend"]
    SENDER_DEFAULT = ctx["sender_default"]
    PUBLIC_URL = (ctx["public_url"] or "").rstrip("/")
    JWT_SECRET = ctx["jwt_secret"]
    unsub_token = ctx["unsubscribe_token_for"]
    EMERGENT_LLM_KEY = ctx.get("emergent_llm_key")
    twilio_send_one = ctx.get("twilio_send_one")

    def _sanitize_channels(chs):
        if not chs: return ["email"]
        allowed = {"email", "sms", "whatsapp"}
        out = [c for c in chs if c in allowed]
        return out or ["email"]

    async def _uniq_pub_slug(base: str) -> str:
        existing = {d["slug"] async for d in db.publications.find({}, {"_id": 0, "slug": 1})}
        return _slugify(base, existing)

    async def _get_pub(pid: str, workspace_id: str) -> dict:
        p = await db.publications.find_one(
            {"id": pid, "workspace_id": workspace_id}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Publication not found")
        return p

    def _sanitize_blocks(blocks: list) -> list:
        out = []
        for b in (blocks or []):
            if not isinstance(b, dict): continue
            t = b.get("type")
            if t not in BLOCK_TYPES: continue
            cleaned = {"id": b.get("id") or str(uuid.uuid4())[:8], "type": t,
                       "props": b.get("props") or {}}
            out.append(cleaned)
        return out

    # ============ Publications ============
    @api.post("/newsletter/publications")
    async def create_publication(body: PublicationIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        slug = await _uniq_pub_slug(body.slug or body.name)
        ws = await db.workspaces.find_one({"id": user["workspace_id"]}, {"_id": 0}) or {}
        doc = {
            "id": str(uuid.uuid4()),
            "workspace_id": user["workspace_id"],
            "name": body.name.strip()[:80],
            "slug": slug,
            "description": (body.description or "")[:280],
            "sender_name": (body.sender_name or ws.get("name") or "").strip()[:80],
            "sender_email": body.sender_email or None,
            "primary_color": body.primary_color or "#005CEE",
            "subscribe_headline": body.subscribe_headline,
            "subscribe_body": body.subscribe_body,
            "thanks_headline": body.thanks_headline,
            "thanks_body": body.thanks_body,
            "referral_rewards": body.referral_rewards or
                [{"count": 3, "coupon_percent": 10},
                 {"count": 10, "coupon_percent": 20},
                 {"count": 25, "coupon_percent": 30}],
            "created_by": user["id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.publications.insert_one({**doc})
        return doc

    @api.get("/newsletter/publications")
    async def list_publications(user: dict = Depends(get_current_user)):
        docs = await db.publications.find(
            {"workspace_id": user["workspace_id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        # Attach quick counts
        for d in docs:
            d["subscriber_count"] = await db.newsletter_subscribers.count_documents(
                {"publication_id": d["id"], "status": "subscribed"})
            d["post_count"] = await db.newsletter_posts.count_documents(
                {"publication_id": d["id"]})
        return docs

    @api.get("/newsletter/publications/{pid}")
    async def get_publication(pid: str, user: dict = Depends(get_current_user)):
        return await _get_pub(pid, user["workspace_id"])

    @api.put("/newsletter/publications/{pid}")
    async def update_publication(pid: str, body: PublicationIn,
                                   user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        upd = {k: v for k, v in body.model_dump().items() if v is not None}
        upd["updated_at"] = now_iso()
        upd.pop("slug", None)  # slug immutable to preserve archive URLs
        await db.publications.update_one({"id": pid}, {"$set": upd})
        return await _get_pub(pid, user["workspace_id"])

    @api.delete("/newsletter/publications/{pid}")
    async def delete_publication(pid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        await db.publications.delete_one({"id": pid})
        await db.newsletter_subscribers.delete_many({"publication_id": pid})
        await db.newsletter_posts.delete_many({"publication_id": pid})
        await db.newsletter_events.delete_many({"publication_id": pid})
        return {"ok": True}

    # ============ Subscribers ============
    @api.get("/newsletter/publications/{pid}/subscribers")
    async def list_subscribers(pid: str, status: Optional[str] = None,
                                 user: dict = Depends(get_current_user)):
        await _get_pub(pid, user["workspace_id"])
        q = {"publication_id": pid}
        if status: q["status"] = status
        rows = await db.newsletter_subscribers.find(q, {"_id": 0}
                                                     ).sort("subscribed_at", -1).to_list(2000)
        return rows

    async def _create_subscriber(pub: dict, email: str, name: str, source: str,
                                   tags: list, status: str, referred_by: Optional[str],
                                   phone: str = "") -> dict:
        email = email.strip().lower()
        phone = (phone or "").strip()[:32] or None
        existing = await db.newsletter_subscribers.find_one(
            {"publication_id": pub["id"], "email": email}, {"_id": 0})
        if existing:
            if existing["status"] == "unsubscribed":
                await db.newsletter_subscribers.update_one(
                    {"id": existing["id"]},
                    {"$set": {"status": status, "unsubscribed_at": None,
                              "subscribed_at": now_iso()}})
                existing["status"] = status
            if phone and not existing.get("phone"):
                await db.newsletter_subscribers.update_one(
                    {"id": existing["id"]}, {"$set": {"phone": phone}})
                existing["phone"] = phone
            return existing
        doc = {
            "id": str(uuid.uuid4()),
            "publication_id": pub["id"],
            "workspace_id": pub["workspace_id"],
            "email": email,
            "name": (name or "").strip()[:120],
            "phone": phone,
            "tags": tags or [],
            "source": source,
            "status": status,  # subscribed | pending | unsubscribed
            "confirmation_token": secrets.token_urlsafe(24),
            "referral_token": secrets.token_urlsafe(12),
            "referred_by": referred_by,
            "referral_count": 0,
            "subscribed_at": now_iso(),
            "confirmed_at": now_iso() if status == "subscribed" else None,
            "unsubscribed_at": None,
            "stats": {"opens": 0, "clicks": 0},
        }
        await db.newsletter_subscribers.insert_one({**doc})
        # Bump referrer's count + maybe issue milestone coupon.
        if referred_by:
            await _bump_referrer(pub, referred_by)
        return doc

    async def _bump_referrer(pub: dict, referral_token: str) -> None:
        r = await db.newsletter_subscribers.find_one_and_update(
            {"publication_id": pub["id"], "referral_token": referral_token},
            {"$inc": {"referral_count": 1}},
            return_document=True, projection={"_id": 0})
        if not r: return
        new_count = r.get("referral_count", 0)
        # Check milestones — issue coupon if just crossed a threshold.
        milestones = pub.get("referral_rewards") or []
        for m in milestones:
            if m.get("count") == new_count:
                await _issue_referral_coupon(pub, r, m.get("coupon_percent", 10))

    async def _issue_referral_coupon(pub: dict, subscriber: dict, percent: int) -> None:
        from routers.newsletter_helpers import gen_code  # avoid circular
        code = gen_code(prefix="REF")
        c = {
            "id": str(uuid.uuid4()), "workspace_id": pub["workspace_id"],
            "code": code, "codes": [code],
            "name": f"Referral reward — {subscriber['email']}"[:80],
            "type": "percentage", "discount_value": percent,
            "headline": f"{percent}% off — thanks for referring!",
            "description": f"Because you brought {subscriber.get('referral_count')} friends.",
            "terms": "One-time use. Referral milestone reward.",
            "cta": "Claim", "audience": subscriber["email"],
            "state": "active",
            "image_url": "",
            "qr_code": "",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 1, "per_customer_limit": 1, "stackable": False,
                      "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
            "stats": {"impressions": 0, "redemptions": 0, "revenue": 0.0},
            "created_at": now_iso(), "source": "newsletter_referral",
        }
        await db.coupons.insert_one({**c})
        # Send an email if Resend is configured.
        if getattr(resend, "api_key", None):
            landing = f"{PUBLIC_URL}/c/{code}" if PUBLIC_URL else "#"
            try:
                await asyncio.to_thread(resend.Emails.send, {
                    "from": pub.get("sender_email") or SENDER_DEFAULT,
                    "to": [subscriber["email"]],
                    "subject": f"You unlocked {percent}% off",
                    "html": f"<div style='font-family:Helvetica,Arial;padding:32px;background:#0A0A0A;color:#fff'>"
                            f"<h2>Thanks for spreading the word 🎉</h2>"
                            f"<p>You've referred {subscriber.get('referral_count')} people to <b>{pub['name']}</b>. "
                            f"Here's a code just for you.</p>"
                            f"<div style='margin:24px 0;padding:20px;border:2px dashed {pub.get('primary_color','#005CEE')};"
                            f"border-radius:8px;text-align:center;font-family:monospace;font-size:24px;letter-spacing:4px;"
                            f"color:{pub.get('primary_color','#005CEE')}'>{code}</div>"
                            f"<p><a href='{landing}' style='background:{pub.get('primary_color','#005CEE')};"
                            f"color:#fff;padding:12px 24px;text-decoration:none;border-radius:8px'>Redeem now</a></p>"
                            f"</div>",
                })
            except Exception:
                pass

    @api.post("/newsletter/publications/{pid}/subscribers")
    async def owner_add_subscriber(pid: str, body: SubscriberIn,
                                     user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        doc = await _create_subscriber(pub, body.email, body.name or "",
                                          body.source or "owner_add",
                                          body.tags or [], "subscribed", None,
                                          phone=body.phone or "")
        return doc

    @api.post("/newsletter/publications/{pid}/subscribers/import-csv")
    async def import_subscribers_csv(pid: str, file: UploadFile = File(...),
                                       user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(400, "Upload a .csv file")
        raw = (await file.read()).decode("utf-8-sig", errors="replace")
        import csv as _csv
        from io import StringIO
        reader = _csv.DictReader(StringIO(raw))
        created, skipped = 0, 0
        for row in reader:
            email = ((row.get("email") or row.get("Email") or "").strip().lower())
            if not email or "@" not in email: skipped += 1; continue
            name = (row.get("name") or row.get("Name") or "").strip()
            phone = (row.get("phone") or row.get("Phone") or row.get("mobile") or "").strip()
            try:
                await _create_subscriber(pub, email, name, "csv_import",
                                            [], "subscribed", None, phone=phone)
                created += 1
            except Exception:
                skipped += 1
        return {"created": created, "skipped": skipped}

    @api.delete("/newsletter/publications/{pid}/subscribers/{sid}")
    async def remove_subscriber(pid: str, sid: str,
                                  user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        r = await db.newsletter_subscribers.delete_one(
            {"id": sid, "publication_id": pid})
        if r.deleted_count == 0:
            raise HTTPException(404, "Subscriber not found")
        return {"ok": True}

    # ============ Posts ============
    async def _uniq_post_slug(pid: str, base: str) -> str:
        existing = {d["slug"] async for d in db.newsletter_posts.find(
            {"publication_id": pid}, {"_id": 0, "slug": 1})}
        return _slugify(base, existing)

    @api.post("/newsletter/publications/{pid}/posts")
    async def create_post(pid: str, body: PostIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        slug = await _uniq_post_slug(pid, body.slug or body.title)
        doc = {
            "id": str(uuid.uuid4()),
            "publication_id": pid,
            "workspace_id": pub["workspace_id"],
            "title": body.title.strip()[:200],
            "subtitle": (body.subtitle or "")[:280],
            "slug": slug,
            "blocks": _sanitize_blocks(body.blocks or [
                {"type": "heading", "props": {"level": "h1", "text": body.title.strip()}},
                {"type": "text", "props": {"text": "Start writing…"}},
            ]),
            "channels": _sanitize_channels(body.channels),
            "sms_body": (body.sms_body or "")[:300],
            "status": "draft",
            "scheduled_at": None,
            "sent_at": None,
            "created_by": user["id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "stats": {"sent": 0, "opens": 0, "unique_opens": 0,
                       "clicks": 0, "unique_clicks": 0, "unsubscribes": 0,
                       "sms_sent": 0, "whatsapp_sent": 0},
        }
        await db.newsletter_posts.insert_one({**doc})
        return doc

    @api.get("/newsletter/publications/{pid}/posts")
    async def list_posts(pid: str, user: dict = Depends(get_current_user)):
        await _get_pub(pid, user["workspace_id"])
        return await db.newsletter_posts.find(
            {"publication_id": pid}, {"_id": 0}
        ).sort("created_at", -1).to_list(500)

    @api.get("/newsletter/publications/{pid}/posts/{post_id}")
    async def get_post(pid: str, post_id: str, user: dict = Depends(get_current_user)):
        await _get_pub(pid, user["workspace_id"])
        p = await db.newsletter_posts.find_one(
            {"id": post_id, "publication_id": pid}, {"_id": 0})
        if not p: raise HTTPException(404, "Post not found")
        return p

    @api.put("/newsletter/publications/{pid}/posts/{post_id}")
    async def update_post(pid: str, post_id: str, body: PostIn,
                            user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        upd = {"title": body.title.strip()[:200],
               "subtitle": (body.subtitle or "")[:280],
               "blocks": _sanitize_blocks(body.blocks or []),
               "channels": _sanitize_channels(body.channels),
               "sms_body": (body.sms_body or "")[:300],
               "updated_at": now_iso()}
        r = await db.newsletter_posts.update_one(
            {"id": post_id, "publication_id": pid,
             "status": {"$in": ["draft", "scheduled"]}}, {"$set": upd})
        if r.matched_count == 0:
            raise HTTPException(404, "Post not found or already sent")
        return await get_post(pid, post_id, user)

    @api.delete("/newsletter/publications/{pid}/posts/{post_id}")
    async def delete_post(pid: str, post_id: str,
                            user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        r = await db.newsletter_posts.delete_one(
            {"id": post_id, "publication_id": pid,
             "status": {"$in": ["draft", "scheduled"]}})
        if r.deleted_count == 0:
            raise HTTPException(404, "Post not found or already sent")
        return {"ok": True}

    @api.post("/newsletter/publications/{pid}/posts/{post_id}/schedule")
    async def schedule_post(pid: str, post_id: str, body: ScheduleIn,
                              user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        r = await db.newsletter_posts.update_one(
            {"id": post_id, "publication_id": pid, "status": "draft"},
            {"$set": {"status": "scheduled", "scheduled_at": body.scheduled_at,
                      "updated_at": now_iso()}})
        if r.matched_count == 0:
            raise HTTPException(404, "Post not found or not in draft")
        return {"ok": True, "scheduled_at": body.scheduled_at}

    @api.post("/newsletter/publications/{pid}/posts/{post_id}/send-test")
    async def send_test(pid: str, post_id: str, body: SendTestIn,
                          user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        post = await db.newsletter_posts.find_one(
            {"id": post_id, "publication_id": pid}, {"_id": 0})
        if not post: raise HTTPException(404, "Post not found")
        if not getattr(resend, "api_key", None):
            raise HTTPException(400, "Resend not configured — set RESEND_API_KEY")
        html = await _render_post_html(pub, post, subscriber_id="test",
                                          for_email=True, test=True)
        try:
            await asyncio.to_thread(resend.Emails.send, {
                "from": pub.get("sender_email") or SENDER_DEFAULT,
                "to": [body.email],
                "subject": f"[TEST] {post['title']}",
                "html": html,
            })
        except Exception as e:
            raise HTTPException(502, f"Test send failed: {e}")
        return {"ok": True}

    @api.get("/newsletter/publications/{pid}/posts/{post_id}/preview",
             response_class=Response)
    async def preview_post(pid: str, post_id: str,
                             user: dict = Depends(get_current_user)):
        """Render the exact email HTML for in-app preview.

        Returns text/html so the frontend can drop the response straight into
        an ``<iframe srcDoc={...}>``. No tracking pixels, no unsubscribe
        footer — this is a WYSIWYG preview, not a send.
        """
        pub = await _get_pub(pid, user["workspace_id"])
        post = await db.newsletter_posts.find_one(
            {"id": post_id, "publication_id": pid}, {"_id": 0})
        if not post:
            raise HTTPException(404, "Post not found")
        html = await _render_post_html(pub, post, subscriber_id="preview",
                                          for_email=True, test=True)
        return Response(content=html, media_type="text/html")

    @api.get("/newsletter/templates")
    async def list_templates():
        """List curated starter templates for the post-creation flow."""
        from routers.newsletter_templates import TEMPLATES
        # Strip the block payload from the list view — clients get it on demand.
        return [{k: t[k] for k in ("id", "name", "category", "description",
                                     "preview_emoji", "accent")} for t in TEMPLATES]

    @api.get("/newsletter/templates/{template_id}")
    async def get_template_full(template_id: str):
        """Fetch full template payload (title/subtitle/blocks) for previewing before use."""
        from routers.newsletter_templates import get_template
        t = get_template(template_id)
        if not t:
            raise HTTPException(404, "Template not found")
        return t

    @api.get("/newsletter/templates/{template_id}/preview",
             response_class=Response)
    async def preview_template(template_id: str,
                                 user: dict = Depends(get_current_user)):
        """Render a curated template as HTML for the picker's inline preview.

        Uses the caller's first publication (for name/color) as scaffold; if
        the workspace has no publication yet, a synthetic default is used.
        """
        from routers.newsletter_templates import get_template
        t = get_template(template_id)
        if not t:
            raise HTTPException(404, "Template not found")
        pub = await db.publications.find_one(
            {"workspace_id": user["workspace_id"]}, {"_id": 0}) or {
            "name": "Your Newsletter", "primary_color": "#005CEE",
            "workspace_id": user["workspace_id"], "slug": "preview",
        }
        synthetic_post = {"title": t["post"]["title"], "subtitle": t["post"].get("subtitle"),
                          "blocks": t["post"].get("blocks") or []}
        html = await _render_post_html(pub, synthetic_post,
                                          subscriber_id="preview",
                                          for_email=True, test=True)
        return Response(content=html, media_type="text/html")

    # ---- Saved (personal) templates ---------------------------------------
    class SavedTemplateIn(BaseModel):
        name: str
        post_id: Optional[str] = None
        # Snapshot fields — required if post_id not provided
        title: Optional[str] = None
        subtitle: Optional[str] = None
        blocks: Optional[List[dict]] = None

    @api.post("/newsletter/saved-templates")
    async def create_saved_template(body: SavedTemplateIn,
                                       user: dict = Depends(get_current_user)):
        """Save a post (or arbitrary blocks) as a reusable per-workspace template."""
        require_writer(user)
        if body.post_id:
            post = await db.newsletter_posts.find_one(
                {"id": body.post_id, "workspace_id": user["workspace_id"]},
                {"_id": 0, "title": 1, "subtitle": 1, "blocks": 1})
            if not post:
                raise HTTPException(404, "Post not found")
            title = post.get("title", ""); subtitle = post.get("subtitle") or ""
            blocks = post.get("blocks") or []
        else:
            title = (body.title or "").strip()
            subtitle = (body.subtitle or "").strip()
            blocks = body.blocks or []
        if not (body.name and title and blocks):
            raise HTTPException(400, "name, title, and at least one block are required")
        doc = {"id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
               "name": body.name.strip()[:80],
               "title": title[:200], "subtitle": subtitle[:280],
               "blocks": _sanitize_blocks(blocks),
               "created_by": user["id"], "created_at": now_iso()}
        await db.newsletter_saved_templates.insert_one({**doc})
        return doc

    @api.get("/newsletter/saved-templates")
    async def list_saved_templates(user: dict = Depends(get_current_user)):
        return await db.newsletter_saved_templates.find(
            {"workspace_id": user["workspace_id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(200)

    @api.delete("/newsletter/saved-templates/{tid}")
    async def delete_saved_template(tid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.newsletter_saved_templates.delete_one(
            {"id": tid, "workspace_id": user["workspace_id"]})
        if r.deleted_count == 0:
            raise HTTPException(404, "Not found")
        return {"ok": True}

    @api.post("/newsletter/publications/{pid}/posts/from-saved/{tid}")
    async def create_post_from_saved(pid: str, tid: str,
                                       user: dict = Depends(get_current_user)):
        """Create a new draft from a workspace-owned saved template."""
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        st = await db.newsletter_saved_templates.find_one(
            {"id": tid, "workspace_id": user["workspace_id"]}, {"_id": 0})
        if not st:
            raise HTTPException(404, "Saved template not found")
        slug = await _uniq_post_slug(pid, st["title"])
        doc = {"id": str(uuid.uuid4()), "publication_id": pid,
                "workspace_id": pub["workspace_id"],
                "title": st["title"][:200], "subtitle": (st.get("subtitle") or "")[:280],
                "slug": slug, "blocks": _sanitize_blocks(st.get("blocks") or []),
                "channels": ["email"], "sms_body": "",
                "status": "draft", "scheduled_at": None, "sent_at": None,
                "created_by": user["id"], "created_from_saved_template": tid,
                "created_at": now_iso(), "updated_at": now_iso(),
                "stats": {"sent": 0, "opens": 0, "unique_opens": 0,
                           "clicks": 0, "unique_clicks": 0, "unsubscribes": 0,
                           "sms_sent": 0, "whatsapp_sent": 0}}
        await db.newsletter_posts.insert_one({**doc})
        return doc

    # ---- Shared preview + comments (team approval flow) -------------------
    def _share_token(pid: str, post_id: str, ttl_hours: int = 168) -> str:
        payload = {"pid": pid, "post_id": post_id, "kind": "nl_preview",
                    "exp": datetime.now(timezone.utc) + timedelta(hours=ttl_hours)}
        import jwt as _jwt
        return _jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    @api.post("/newsletter/publications/{pid}/posts/{post_id}/share")
    async def create_share_link(pid: str, post_id: str,
                                  user: dict = Depends(get_current_user)):
        """Return a public preview URL (valid 7 days) reviewers can visit to comment."""
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        post = await db.newsletter_posts.find_one(
            {"id": post_id, "publication_id": pid}, {"_id": 0, "id": 1})
        if not post: raise HTTPException(404, "Post not found")
        tok = _share_token(pid, post_id)
        base = PUBLIC_URL.rstrip("/") if PUBLIC_URL else ""
        return {"token": tok, "url": f"{base}/newsletter/review/{tok}" if base else f"/newsletter/review/{tok}",
                 "expires_in_hours": 168}

    @api.get("/newsletter/public/review/{token}", response_class=Response)
    async def public_review_html(token: str):
        """Public rendered HTML for reviewers who received a share link."""
        import jwt as _jwt
        try:
            payload = _jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except _jwt.ExpiredSignatureError:
            raise HTTPException(410, "This review link has expired")
        except _jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid review link")
        if payload.get("kind") != "nl_preview":
            raise HTTPException(401, "Not a review token")
        post = await db.newsletter_posts.find_one(
            {"id": payload["post_id"], "publication_id": payload["pid"]}, {"_id": 0})
        pub = await db.publications.find_one({"id": payload["pid"]}, {"_id": 0})
        if not (post and pub): raise HTTPException(404, "Not found")
        html = await _render_post_html(pub, post, subscriber_id="preview",
                                          for_email=True, test=True)
        return Response(content=html, media_type="text/html")

    class ReviewCommentIn(BaseModel):
        reviewer_name: str
        body: str

    @api.post("/newsletter/public/review/{token}/comments")
    async def public_review_comment(token: str, body: ReviewCommentIn, request: Request):
        """Reviewer posts a comment against the shared post — no auth required."""
        import jwt as _jwt
        try:
            payload = _jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            raise HTTPException(401, "Invalid or expired review link")
        if payload.get("kind") != "nl_preview":
            raise HTTPException(401, "Not a review token")
        name = (body.reviewer_name or "").strip()[:60]
        text = (body.body or "").strip()[:2000]
        if not (name and text):
            raise HTTPException(400, "reviewer_name and body are required")
        doc = {"id": str(uuid.uuid4()), "post_id": payload["post_id"],
                "publication_id": payload["pid"], "reviewer_name": name,
                "body": text, "resolved": False,
                "ip": (request.client.host if request.client else None),
                "created_at": now_iso()}
        await db.newsletter_comments.insert_one({**doc})
        return {"ok": True, "comment": {k: doc[k] for k in
                                            ("id", "reviewer_name", "body", "resolved", "created_at")}}

    @api.get("/newsletter/public/review/{token}/comments")
    async def public_review_list_comments(token: str):
        import jwt as _jwt
        try:
            payload = _jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            raise HTTPException(401, "Invalid or expired review link")
        if payload.get("kind") != "nl_preview":
            raise HTTPException(401, "Not a review token")
        return await db.newsletter_comments.find(
            {"post_id": payload["post_id"], "publication_id": payload["pid"]},
            {"_id": 0, "ip": 0}
        ).sort("created_at", 1).to_list(500)

    @api.get("/newsletter/publications/{pid}/posts/{post_id}/comments")
    async def list_post_comments(pid: str, post_id: str,
                                    user: dict = Depends(get_current_user)):
        await _get_pub(pid, user["workspace_id"])
        return await db.newsletter_comments.find(
            {"post_id": post_id, "publication_id": pid},
            {"_id": 0, "ip": 0}
        ).sort("created_at", -1).to_list(500)

    @api.post("/newsletter/publications/{pid}/posts/{post_id}/comments/{cid}/resolve")
    async def resolve_comment(pid: str, post_id: str, cid: str,
                                user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        r = await db.newsletter_comments.update_one(
            {"id": cid, "post_id": post_id, "publication_id": pid},
            {"$set": {"resolved": True,
                        "resolved_at": now_iso(), "resolved_by": user["id"]}})
        if r.matched_count == 0:
            raise HTTPException(404, "Comment not found")
        return {"ok": True}


    class FromTemplateIn(BaseModel):
        template_id: str

    @api.post("/newsletter/publications/{pid}/posts/from-template")
    async def create_post_from_template(pid: str, body: FromTemplateIn,
                                          user: dict = Depends(get_current_user)):
        """Create a new draft post pre-filled with the chosen template."""
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        from routers.newsletter_templates import get_template
        t = get_template(body.template_id)
        if not t:
            raise HTTPException(404, "Template not found")
        tpost = t["post"]
        slug = await _uniq_post_slug(pid, tpost["title"])
        doc = {
            "id": str(uuid.uuid4()),
            "publication_id": pid,
            "workspace_id": pub["workspace_id"],
            "title": tpost["title"][:200],
            "subtitle": (tpost.get("subtitle") or "")[:280],
            "slug": slug,
            "blocks": _sanitize_blocks(tpost.get("blocks") or []),
            "channels": ["email"],
            "sms_body": "",
            "status": "draft",
            "scheduled_at": None,
            "sent_at": None,
            "created_by": user["id"],
            "created_from_template": body.template_id,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "stats": {"sent": 0, "opens": 0, "unique_opens": 0,
                       "clicks": 0, "unique_clicks": 0, "unsubscribes": 0,
                       "sms_sent": 0, "whatsapp_sent": 0},
        }
        await db.newsletter_posts.insert_one({**doc})
        return doc

    @api.post("/newsletter/publications/{pid}/posts/{post_id}/send-now")
    async def send_now(pid: str, post_id: str,
                         user: dict = Depends(get_current_user)):
        require_writer(user)
        await _get_pub(pid, user["workspace_id"])
        r = await db.newsletter_posts.update_one(
            {"id": post_id, "publication_id": pid, "status": "draft"},
            {"$set": {"status": "scheduled", "scheduled_at": now_iso(),
                      "updated_at": now_iso()}})
        if r.matched_count == 0:
            raise HTTPException(404, "Post not found or not draft")
        return {"ok": True, "queued": True}

    # ============ Rendering & sending ============
    async def _hydrate_block(block: dict, workspace_id: str) -> dict:
        t = block["type"]; p = block.get("props") or {}
        if t == "coupon" and p.get("code"):
            c = await db.coupons.find_one(
                {"workspace_id": workspace_id, "code": p["code"].upper()}, {"_id": 0})
            if c: p["_hydrated"] = {"headline": c.get("headline") or c["name"],
                                       "description": c.get("description", ""),
                                       "code": c["code"], "cta": c.get("cta", "Redeem")}
        elif t == "giftcard" and p.get("giftcard_id"):
            gc = await db.gift_cards.find_one(
                {"workspace_id": workspace_id, "id": p["giftcard_id"]}, {"_id": 0})
            if gc: p["_hydrated"] = {"headline": gc.get("template_id", "Gift Card"),
                                        "message": gc.get("message", ""),
                                        "amount": gc.get("amount"), "code": gc.get("code")}
        elif t == "funnel" and p.get("slug"):
            f = await db.funnels.find_one(
                {"workspace_id": workspace_id, "slug": p["slug"]}, {"_id": 0})
            if f: p["_hydrated"] = {"name": f["name"], "slug": f["slug"]}
        block["props"] = p
        return block

    async def _render_post_html(pub: dict, post: dict, subscriber_id: str,
                                  for_email: bool, test: bool = False) -> str:
        primary = pub.get("primary_color", "#005CEE")
        pieces = [f"""<!doctype html><html><head><meta charset="utf-8">
<title>{post['title']}</title></head>
<body style="margin:0;padding:0;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#0A0A0A">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:32px 12px">
<tr><td align="center">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border-radius:12px;overflow:hidden;max-width:640px">
<tr><td style="padding:24px 32px;background:{primary};color:#fff;font-weight:700;font-size:14px;letter-spacing:1px;text-transform:uppercase">{pub['name']}</td></tr>
<tr><td style="padding:32px 32px 8px">
<h1 style="margin:0 0 8px;font-size:28px;line-height:1.15;color:#0A0A0A">{post['title']}</h1>
{f'<p style="margin:0 0 24px;color:#71717A;font-size:14px">{post["subtitle"]}</p>' if post.get('subtitle') else ''}
"""]
        for b in post.get("blocks", []):
            await _hydrate_block(b, pub["workspace_id"])
            pieces.append(_render_block(b, pub, subscriber_id, for_email))
        # Footer with unsubscribe link (only for real sends).
        footer_html = ""
        if for_email and not test and subscriber_id != "test":
            unsub_url = f"{PUBLIC_URL}/api/newsletter/track/unsubscribe/{post['id']}/{subscriber_id}" if PUBLIC_URL else "#"
            footer_html = f"""
<tr><td style="padding:24px 32px;background:#FAFAFA;border-top:1px solid #E4E4E7;font-size:11px;color:#71717A;text-align:center">
<div>Sent by {pub.get('sender_name') or pub['name']} · <a href="{unsub_url}" style="color:#71717A">Unsubscribe</a></div>
<div style="margin-top:6px">Powered by PromoOS Newsletters</div>
</td></tr>"""
        # Open pixel (email only)
        pixel = ""
        if for_email and not test and subscriber_id != "test":
            px_url = f"{PUBLIC_URL}/api/newsletter/track/open/{post['id']}/{subscriber_id}.gif" if PUBLIC_URL else ""
            pixel = f'<img src="{px_url}" alt="" width="1" height="1" style="display:block;border:0" />'
        pieces.append(f"</td></tr>{footer_html}</table>{pixel}</td></tr></table></body></html>")
        return "\n".join(pieces)

    def _wrap_link(url: str, post_id: str, subscriber_id: str, for_email: bool) -> str:
        if not for_email or subscriber_id in ("test", ""): return url
        if not PUBLIC_URL: return url
        from urllib.parse import quote
        return f"{PUBLIC_URL}/api/newsletter/track/click/{post_id}/{subscriber_id}?u={quote(url, safe='')}"

    def _render_block(b: dict, pub: dict, subscriber_id: str, for_email: bool) -> str:
        t = b["type"]; p = b.get("props") or {}
        primary = pub.get("primary_color", "#005CEE")
        # Common presentational helpers — every block honors these props.
        align = p.get("align") or "left"
        align = align if align in ("left", "center", "right") else "left"
        text_color = _safe_color(p.get("color"), "#0A0A0A")
        bg = _safe_color(p.get("background"), None)
        bg_style = f"background:{bg};" if bg else ""
        pad = int(p.get("padding") if str(p.get("padding") or "").isdigit() else 0)
        pad_style = f"padding:{max(0, min(64, pad))}px;" if pad else ""
        wrap_open = wrap_close = ""
        if bg or pad:
            wrap_open = f'<div style="{bg_style}{pad_style}border-radius:8px">'
            wrap_close = "</div>"
        if t == "heading":
            level = p.get("level", "h2")
            tag = level if level in ("h1", "h2", "h3", "h4") else "h2"
            size = {"h1": 30, "h2": 24, "h3": 19, "h4": 16}[tag]
            sz = int(p.get("font_size") or size)
            return (f'{wrap_open}<{tag} style="margin:20px 0 8px;text-align:{align};'
                    f'font-size:{max(12, min(64, sz))}px;line-height:1.2;color:{text_color}">'
                    f'{p.get("text","")}</{tag}>{wrap_close}')
        if t == "text":
            sz = int(p.get("font_size") or 15)
            return (f'{wrap_open}<p style="margin:0 0 16px;text-align:{align};'
                    f'font-size:{max(10, min(28, sz))}px;line-height:1.6;color:{text_color};'
                    f'white-space:pre-wrap">{p.get("text","")}</p>{wrap_close}')
        if t == "image":
            src = p.get("url", "")
            if not src: return ""
            w = p.get("width")
            width_css = f"width:{int(w)}px;max-width:100%;" if str(w or "").isdigit() else "width:100%;"
            radius = int(p.get("radius") or 8)
            link = (p.get("link") or "").strip()
            img = (f'<img src="{src}" alt="{p.get("alt","")}" '
                   f'style="display:block;{width_css}border-radius:{max(0, min(48, radius))}px;'
                   f'margin:0 auto" />')
            if link:
                img = f'<a href="{link}" style="text-decoration:none">{img}</a>'
            return f'<div style="margin:16px 0;text-align:{align}">{img}</div>'
        if t == "button":
            url = p.get("url", "#"); label = p.get("label", "Learn more")
            btn_bg = _safe_color(p.get("background"), primary)
            btn_color = _safe_color(p.get("color"), "#FFFFFF")
            radius = int(p.get("radius") or 8)
            return (f'<div style="margin:24px 0;text-align:{align}"><a href="{url}" '
                    f'style="display:inline-block;background:{btn_bg};color:{btn_color};'
                    f'text-decoration:none;padding:12px 24px;border-radius:{max(0, min(48, radius))}px;'
                    f'font-weight:700">{label}</a></div>')
        if t == "divider":
            color = _safe_color(p.get("color"), "#E4E4E7")
            thick = int(p.get("thickness") or 1)
            return f'<hr style="border:0;border-top:{max(1, min(8, thick))}px solid {color};margin:24px 0" />'
        if t == "spacer":
            h = int(p.get("height") or 24)
            return f'<div style="height:{max(4, min(120, h))}px" aria-hidden="true"></div>'
        if t == "video":
            url = (p.get("url") or "").strip()
            if not url: return ""
            poster = (p.get("poster") or "").strip()
            # Email clients ignore <video> — render a poster + play badge that links to the video URL.
            if for_email:
                if not poster:
                    poster = ("https://via.placeholder.com/640x360/0A0A0A/CCFF00?text=%E2%96%B6")
                return (f'<div style="margin:16px 0;text-align:{align}">'
                        f'<a href="{url}" style="display:inline-block;position:relative;text-decoration:none">'
                        f'<img src="{poster}" alt="Watch video" style="display:block;width:100%;max-width:640px;border-radius:10px" />'
                        f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
                        f'width:64px;height:64px;background:{primary};border-radius:50%;color:#fff;'
                        f'font-size:24px;line-height:64px;text-align:center">▶</div></a></div>')
            poster_attr = f' poster="{poster}"' if poster else ""
            return (f'<div style="margin:16px 0;text-align:{align}">'
                    f'<video controls style="width:100%;max-width:640px;border-radius:10px"'
                    f'{poster_attr}>'
                    f'<source src="{url}" /></video></div>')
        if t == "audio":
            url = (p.get("url") or "").strip()
            if not url: return ""
            title = p.get("title") or "Listen"
            if for_email:
                return (f'<div style="margin:16px 0;padding:20px;border:1px solid #E4E4E7;border-radius:10px;'
                        f'display:flex;align-items:center;gap:12px">'
                        f'<div style="width:44px;height:44px;background:{primary};border-radius:50%;'
                        f'color:#fff;font-size:18px;line-height:44px;text-align:center">▶</div>'
                        f'<div style="flex:1"><div style="font-weight:700;color:#0A0A0A">{title}</div>'
                        f'<a href="{url}" style="color:{primary};font-size:12px;text-decoration:none">Open audio →</a>'
                        f'</div></div>')
            return (f'<div style="margin:16px 0"><div style="font-weight:700;margin-bottom:8px">{title}</div>'
                    f'<audio controls style="width:100%"><source src="{url}" /></audio></div>')
        if t == "coupon":
            h = p.get("_hydrated") or {}
            code = h.get("code") or p.get("code", "CODE")
            landing = f"{PUBLIC_URL}/c/{code}" if PUBLIC_URL else "#"
            return f"""<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:16px 0"><tr><td style="padding:20px;border:2px dashed {primary};border-radius:10px;text-align:center">
<div style="font-size:13px;color:#71717A;text-transform:uppercase;letter-spacing:2px;margin-bottom:8px">Reader-only offer</div>
<div style="font-size:20px;font-weight:800;margin-bottom:12px;color:#0A0A0A">{h.get('headline') or 'A gift for you'}</div>
<div style="font-family:monospace;font-size:22px;font-weight:800;letter-spacing:4px;color:{primary};margin-bottom:16px">{code}</div>
<a href="{landing}" style="display:inline-block;background:{primary};color:#fff;text-decoration:none;padding:10px 20px;border-radius:8px;font-weight:700">{h.get('cta') or 'Redeem'}</a>
</td></tr></table>"""
        if t == "giftcard":
            h = p.get("_hydrated") or {}
            return f"""<div style="margin:16px 0;padding:24px;background:#0A0A0A;color:#fff;border-radius:12px;text-align:center">
<div style="font-size:12px;letter-spacing:3px;text-transform:uppercase;opacity:0.6">Gift Card</div>
<div style="font-size:36px;font-weight:800;margin:12px 0">${h.get('amount') or 25}</div>
<div style="font-size:13px;opacity:0.8">{h.get('message') or 'Redeem at checkout.'}</div>
</div>"""
        if t == "funnel":
            h = p.get("_hydrated") or {}
            slug = h.get("slug") or p.get("slug", "")
            landing = f"{PUBLIC_URL}/f/{slug}" if (PUBLIC_URL and slug) else "#"
            return (f'<div style="margin:16px 0;padding:20px;border:1px solid #E4E4E7;border-radius:10px">'
                    f'<div style="font-size:12px;color:#71717A;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px">Featured</div>'
                    f'<div style="font-size:18px;font-weight:700;margin-bottom:12px">{h.get("name","Take a look")}</div>'
                    f'<a href="{landing}" style="color:{primary};font-weight:700;text-decoration:none">Explore →</a></div>')
        if t == "subscribe_form":
            url = f"{PUBLIC_URL}/n/{pub['slug']}" if PUBLIC_URL else "#"
            return (f'<div style="margin:24px 0;padding:24px;background:#F4F4F5;border-radius:10px;text-align:center">'
                    f'<div style="font-size:16px;font-weight:700;margin-bottom:6px">Enjoying this?</div>'
                    f'<div style="font-size:13px;color:#71717A;margin-bottom:12px">Share the link so friends can subscribe.</div>'
                    f'<a href="{url}" style="color:{primary};font-weight:700;text-decoration:none">{url}</a></div>')
        if t == "referral_cta":
            if subscriber_id in ("test", ""):
                return ""  # can only render for a real subscriber
            ref_url = f"{PUBLIC_URL}/n/{pub['slug']}?ref={subscriber_id}" if PUBLIC_URL else "#"
            return (f'<div style="margin:24px 0;padding:20px;background:{primary}10;border:1px solid {primary}44;border-radius:10px;text-align:center">'
                    f'<div style="font-size:14px;font-weight:700;color:{primary};margin-bottom:6px">Refer 3 friends → 10% off coupon</div>'
                    f'<div style="font-size:12px;color:#3F3F46;margin-bottom:12px">Share your link — every signup unlocks bigger rewards.</div>'
                    f'<div style="font-family:monospace;font-size:11px;background:#fff;padding:8px;border-radius:6px;border:1px solid #E4E4E7">{ref_url}</div></div>')
        return ""

    async def _send_scheduled_posts() -> None:
        """Worker — every 30s pick up scheduled posts whose time has arrived and send."""
        while True:
            try:
                now = datetime.now(timezone.utc).isoformat()
                cursor = db.newsletter_posts.find(
                    {"status": "scheduled", "scheduled_at": {"$lte": now}},
                    {"_id": 0}).limit(5)
                due = await cursor.to_list(5)
                for post in due:
                    await _fanout_post(post)
            except Exception as e:
                logger.exception(f"newsletter worker: {e}")
            await asyncio.sleep(30)

    async def _fanout_post(post: dict) -> None:
        pub = await db.publications.find_one(
            {"id": post["publication_id"]}, {"_id": 0})
        if not pub:
            await db.newsletter_posts.update_one(
                {"id": post["id"]}, {"$set": {"status": "cancelled"}})
            return
        channels = post.get("channels") or ["email"]
        want_email = "email" in channels
        want_sms = "sms" in channels
        want_whatsapp = "whatsapp" in channels
        if want_email and not getattr(resend, "api_key", None):
            logger.warning(f"Resend not configured — email channel skipped for post {post['id']}")
            want_email = False
        if (want_sms or want_whatsapp) and not twilio_send_one:
            logger.warning(f"Twilio not configured — sms/whatsapp channels skipped for post {post['id']}")
            want_sms = want_whatsapp = False
        if not (want_email or want_sms or want_whatsapp):
            # nothing to do — mark sent so we don't loop forever, but with a zero count.
            await db.newsletter_posts.update_one(
                {"id": post["id"]},
                {"$set": {"status": "sent", "sent_at": now_iso(), "stats.sent": 0,
                          "delivery_note": "No configured channels available"}})
            return
        subs = await db.newsletter_subscribers.find(
            {"publication_id": pub["id"], "status": "subscribed"},
            {"_id": 0, "id": 1, "email": 1, "phone": 1}).to_list(50000)
        sent_email = sent_sms = sent_wa = 0
        # SMS body — fallback derived from title if not provided.
        sms_text = (post.get("sms_body") or "").strip() or _derive_sms(post, pub)
        for s in subs:
            # Email
            if want_email and s.get("email"):
                try:
                    html = await _render_post_html(pub, post, subscriber_id=s["id"],
                                                     for_email=True, test=False)
                    headers = {}
                    try:
                        tok = unsub_token(s["email"], JWT_SECRET)
                        if PUBLIC_URL:
                            headers = {
                                "List-Unsubscribe": f"<{PUBLIC_URL}/api/unsubscribe/{tok}>",
                                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                            }
                    except Exception: pass
                    await asyncio.to_thread(resend.Emails.send, {
                        "from": pub.get("sender_email") or SENDER_DEFAULT,
                        "to": [s["email"]], "subject": post["title"],
                        "html": html, "headers": headers,
                    })
                    sent_email += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
            # SMS
            if want_sms and (s.get("phone") or "").strip():
                try:
                    await twilio_send_one(s["phone"].strip(), sms_text, "sms")
                    sent_sms += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
            # WhatsApp
            if want_whatsapp and (s.get("phone") or "").strip():
                try:
                    await twilio_send_one(s["phone"].strip(), sms_text, "whatsapp")
                    sent_wa += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
        await db.newsletter_posts.update_one(
            {"id": post["id"]},
            {"$set": {"status": "sent", "sent_at": now_iso(),
                       "stats.sent": sent_email,
                       "stats.sms_sent": sent_sms,
                       "stats.whatsapp_sent": sent_wa}})

    def _derive_sms(post: dict, pub: dict) -> str:
        """When merchant doesn't supply an sms_body, synthesise a compact one from title
        + a permalink to the web archive. Keeps under ~150 chars so carriers don't split it."""
        base = post["title"][:80]
        if PUBLIC_URL:
            url = f"{PUBLIC_URL}/n/{pub['slug']}/p/{post.get('slug', '')}"
            return f"{pub['name']}: {base} — {url}"
        return f"{pub['name']}: {base}"

    # ============ Analytics ============
    @api.get("/newsletter/publications/{pid}/analytics")
    async def analytics(pid: str, user: dict = Depends(get_current_user)):
        pub = await _get_pub(pid, user["workspace_id"])
        subs_total = await db.newsletter_subscribers.count_documents(
            {"publication_id": pid})
        subs_active = await db.newsletter_subscribers.count_documents(
            {"publication_id": pid, "status": "subscribed"})
        posts_sent = await db.newsletter_posts.count_documents(
            {"publication_id": pid, "status": "sent"})
        # Growth: subscribers per day for last 30 days.
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        growth_rows = await db.newsletter_subscribers.aggregate([
            {"$match": {"publication_id": pid, "subscribed_at": {"$gte": cutoff}}},
            {"$group": {"_id": {"$substr": ["$subscribed_at", 0, 10]},
                          "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(60)
        growth = [{"date": r["_id"], "count": r["count"]} for r in growth_rows]
        # Top posts.
        top_posts = await db.newsletter_posts.find(
            {"publication_id": pid, "status": "sent"},
            {"_id": 0, "id": 1, "title": 1, "sent_at": 1, "stats": 1}
        ).sort("stats.unique_opens", -1).to_list(5)
        # Top referrers.
        top_refs = await db.newsletter_subscribers.find(
            {"publication_id": pid, "referral_count": {"$gt": 0}},
            {"_id": 0, "email": 1, "referral_count": 1, "referral_token": 1}
        ).sort("referral_count", -1).to_list(10)
        return {
            "subscribers_total": subs_total,
            "subscribers_active": subs_active,
            "posts_sent": posts_sent,
            "growth": growth,
            "top_posts": top_posts,
            "top_referrers": top_refs,
        }

    # ============ Public endpoints ============
    @api.get("/newsletter/public/{slug}")
    async def public_pub(slug: str):
        pub = await db.publications.find_one({"slug": slug}, {"_id": 0})
        if not pub: raise HTTPException(404, "Publication not found")
        posts = await db.newsletter_posts.find(
            {"publication_id": pub["id"], "status": "sent"},
            {"_id": 0, "id": 1, "title": 1, "subtitle": 1, "slug": 1, "sent_at": 1}
        ).sort("sent_at", -1).to_list(50)
        return {
            "name": pub["name"], "slug": pub["slug"],
            "description": pub.get("description", ""),
            "primary_color": pub.get("primary_color", "#005CEE"),
            "subscribe_headline": pub.get("subscribe_headline"),
            "subscribe_body": pub.get("subscribe_body"),
            "thanks_headline": pub.get("thanks_headline"),
            "thanks_body": pub.get("thanks_body"),
            "referral_rewards": pub.get("referral_rewards", []),
            "posts": posts,
        }

    @api.get("/newsletter/public/{slug}/p/{post_slug}")
    async def public_post(slug: str, post_slug: str):
        pub = await db.publications.find_one({"slug": slug}, {"_id": 0})
        if not pub: raise HTTPException(404, "Publication not found")
        post = await db.newsletter_posts.find_one(
            {"publication_id": pub["id"], "slug": post_slug, "status": "sent"},
            {"_id": 0})
        if not post: raise HTTPException(404, "Post not found")
        # Hydrate blocks for the archive page.
        for b in post.get("blocks", []):
            await _hydrate_block(b, pub["workspace_id"])
        return {"pub": {"name": pub["name"], "slug": pub["slug"],
                          "primary_color": pub.get("primary_color", "#005CEE")},
                "post": post}

    @api.post("/newsletter/public/{slug}/subscribe")
    async def public_subscribe(slug: str, body: PublicSubscribeIn, request: Request):
        pub = await db.publications.find_one({"slug": slug}, {"_id": 0})
        if not pub: raise HTTPException(404, "Publication not found")
        # Double opt-in status = pending → send confirmation email.
        doc = await _create_subscriber(pub, body.email, body.name or "",
                                          "public_form", [], "pending",
                                          body.ref if body.ref else None)
        confirm_url = f"{PUBLIC_URL}/api/newsletter/public/confirm/{doc['confirmation_token']}" if PUBLIC_URL else ""
        if getattr(resend, "api_key", None) and confirm_url:
            primary = pub.get("primary_color", "#005CEE")
            try:
                await asyncio.to_thread(resend.Emails.send, {
                    "from": pub.get("sender_email") or SENDER_DEFAULT,
                    "to": [doc["email"]],
                    "subject": f"Confirm your subscription to {pub['name']}",
                    "html": f"""<div style="font-family:Helvetica,Arial,sans-serif;padding:32px;background:#fff;color:#0A0A0A">
<h2 style="color:{primary};margin:0 0 12px">One more click, please</h2>
<p>Confirm your email so we can start sending you {pub['name']}.</p>
<p style="margin:24px 0"><a href="{confirm_url}" style="background:{primary};color:#fff;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:700">Confirm subscription</a></p>
<p style="font-size:12px;color:#71717A">Or paste this link: {confirm_url}</p>
</div>""",
                })
            except Exception:
                pass
        return {"ok": True, "status": doc["status"],
                "thanks_headline": pub.get("thanks_headline"),
                "thanks_body": pub.get("thanks_body")}

    @api.get("/newsletter/public/confirm/{token}")
    async def public_confirm(token: str):
        s = await db.newsletter_subscribers.find_one_and_update(
            {"confirmation_token": token, "status": "pending"},
            {"$set": {"status": "subscribed", "confirmed_at": now_iso()}},
            return_document=True, projection={"_id": 0})
        message = "You're subscribed ✓" if s else "Link expired or already confirmed"
        html = f"""<!doctype html><html><head><title>{message}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>body{{background:#0A0A0A;color:#fff;font-family:system-ui;margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh}}
.card{{max-width:440px;padding:40px;text-align:center;background:#141414;border:1px solid #27272A;border-radius:12px}}
h1{{font-size:22px;margin:0 0 8px}}p{{color:#A1A1AA;font-size:14px}}</style></head>
<body><div class="card"><h1>{message}</h1>
<p>You can close this tab.</p></div></body></html>"""
        return Response(content=html, media_type="text/html")

    @api.get("/newsletter/public/{slug}/referral/{referral_token}")
    async def public_referral_progress(slug: str, referral_token: str):
        pub = await db.publications.find_one({"slug": slug}, {"_id": 0})
        if not pub: raise HTTPException(404, "Publication not found")
        s = await db.newsletter_subscribers.find_one(
            {"publication_id": pub["id"], "referral_token": referral_token},
            {"_id": 0, "email": 1, "referral_count": 1, "referral_token": 1})
        if not s: raise HTTPException(404, "Unknown referral token")
        rewards = pub.get("referral_rewards", [])
        next_reward = next((r for r in rewards if r.get("count") > s["referral_count"]), None)
        share_url = f"{PUBLIC_URL}/n/{slug}?ref={referral_token}" if PUBLIC_URL else ""
        return {
            "email": s["email"],
            "referral_count": s["referral_count"],
            "next_reward": next_reward,
            "all_rewards": rewards,
            "share_url": share_url,
        }

    # ============ Tracking ============
    @api.get("/newsletter/track/open/{post_id}/{sub_id}.gif")
    async def track_open(post_id: str, sub_id: str, request: Request):
        try:
            # Record only if not previously recorded for this pair.
            existing = await db.newsletter_events.find_one(
                {"post_id": post_id, "subscriber_id": sub_id, "type": "open"},
                {"_id": 0, "id": 1})
            await db.newsletter_events.insert_one({
                "id": str(uuid.uuid4()),
                "post_id": post_id, "subscriber_id": sub_id,
                "type": "open",
                "at": now_iso(),
                "ip": request.client.host if request.client else None,
            })
            await db.newsletter_posts.update_one(
                {"id": post_id},
                {"$inc": {"stats.opens": 1,
                           **({"stats.unique_opens": 1} if not existing else {})}})
        except Exception:
            pass
        return Response(content=_PIXEL_GIF, media_type="image/gif",
                         headers={"Cache-Control": "no-store"})

    @api.get("/newsletter/track/click/{post_id}/{sub_id}")
    async def track_click(post_id: str, sub_id: str, u: str, request: Request):
        target = u or "/"
        try:
            existing = await db.newsletter_events.find_one(
                {"post_id": post_id, "subscriber_id": sub_id, "type": "click"},
                {"_id": 0, "id": 1})
            await db.newsletter_events.insert_one({
                "id": str(uuid.uuid4()),
                "post_id": post_id, "subscriber_id": sub_id,
                "type": "click", "url": target[:400], "at": now_iso(),
                "ip": request.client.host if request.client else None,
            })
            await db.newsletter_posts.update_one(
                {"id": post_id},
                {"$inc": {"stats.clicks": 1,
                           **({"stats.unique_clicks": 1} if not existing else {})}})
        except Exception:
            pass
        return RedirectResponse(url=target, status_code=302)

    @api.get("/newsletter/track/unsubscribe/{post_id}/{sub_id}")
    async def track_unsubscribe(post_id: str, sub_id: str):
        await db.newsletter_subscribers.update_one(
            {"id": sub_id},
            {"$set": {"status": "unsubscribed", "unsubscribed_at": now_iso()}})
        await db.newsletter_posts.update_one(
            {"id": post_id}, {"$inc": {"stats.unsubscribes": 1}})
        html = """<!doctype html><html><head><title>Unsubscribed</title>
<style>body{background:#0A0A0A;color:#fff;font-family:system-ui;margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{max-width:440px;padding:40px;text-align:center;background:#141414;border:1px solid #27272A;border-radius:12px}
h1{font-size:22px;margin:0 0 8px}p{color:#A1A1AA;font-size:14px}</style></head>
<body><div class="card"><h1>You're unsubscribed</h1><p>We won't email you again from this list.</p></div></body></html>"""
        return Response(content=html, media_type="text/html")

    # ============ Import customers → subscribers ============
    @api.post("/newsletter/publications/{pid}/import-customers")
    async def import_from_customers(pid: str,
                                      user: dict = Depends(get_current_user)):
        """Bulk-import every customer in this workspace as a subscriber.

        Idempotent — existing subscribers are updated (not duplicated) and any
        who previously unsubscribed stay unsubscribed unless they resubscribe themselves.
        Adds tag ["customer_import"] so merchants can segment later.
        """
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        created, skipped, resubbed = 0, 0, 0
        async for c in db.customers.find(
                {"workspace_id": user["workspace_id"]},
                {"_id": 0, "email": 1, "name": 1}):
            email = ((c.get("email") or "").strip().lower())
            if not email or "@" not in email:
                skipped += 1; continue
            existing = await db.newsletter_subscribers.find_one(
                {"publication_id": pid, "email": email},
                {"_id": 0, "id": 1, "status": 1, "tags": 1})
            if existing:
                if existing["status"] == "unsubscribed":
                    skipped += 1  # respect their prior choice
                    continue
                # ensure the tag is present without duplicating
                if "customer_import" not in (existing.get("tags") or []):
                    await db.newsletter_subscribers.update_one(
                        {"id": existing["id"]},
                        {"$addToSet": {"tags": "customer_import"}})
                skipped += 1
                continue
            await _create_subscriber(pub, email, c.get("name", "") or "",
                                        "customer_import", ["customer_import"],
                                        "subscribed", None)
            created += 1
        return {"created": created, "skipped": skipped, "resubbed": resubbed}

    # ============ AI post drafter ============
    @api.post("/newsletter/publications/{pid}/ai-draft")
    async def ai_draft_post(pid: str, body: AIDraftIn,
                              user: dict = Depends(get_current_user)):
        """Turn a one-line brief into a full post draft with title + blocks.

        Returns the SAME shape as GET /posts/{id} so the frontend can preview
        or overwrite an existing draft. Does NOT persist — caller decides.
        """
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        if not EMERGENT_LLM_KEY:
            raise HTTPException(400, "EMERGENT_LLM_KEY not configured")
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        system = (
            "You are an elite email newsletter writer for e-commerce brands. "
            "Given a one-line brief, produce a JSON object matching this exact schema:\n"
            '{ "title": "<punchy subject line, max 60 chars>",\n'
            '  "subtitle": "<one-sentence preheader, max 120 chars>",\n'
            '  "blocks": [\n'
            '    {"type":"heading","props":{"level":"h2","text":"..."}},\n'
            '    {"type":"text","props":{"text":"..."}},\n'
            '    {"type":"button","props":{"label":"...","url":"https://"}},\n'
            '    ... (5-9 blocks total)\n'
            '  ]\n'
            '}\n'
            "Rules: use only these block types: heading, text, image, button, "
            "subscribe_form, referral_cta, divider. Do NOT include coupon/giftcard/funnel "
            "blocks — merchants will add those manually. Alternate heading/text/button. "
            "Include one subscribe_form and one referral_cta near the end. "
            f"Tone: {body.tone}. Respond with ONLY the JSON object.")
        import uuid as _uuid
        chat = LlmChat(api_key=EMERGENT_LLM_KEY,
                       session_id=f"nl-draft-{_uuid.uuid4()}",
                       system_message=system).with_model("anthropic", "claude-sonnet-5")
        try:
            resp = await chat.send_message(UserMessage(text=body.brief))
        except Exception as e:
            raise HTTPException(502, f"AI draft failed: {e}")
        import re as _re, json as _json
        text = resp if isinstance(resp, str) else str(resp)
        m = _re.search(r"\{[\s\S]*\}", text)
        if not m:
            raise HTTPException(502, "AI returned unparseable response")
        try:
            data = _json.loads(m.group(0))
        except Exception:
            raise HTTPException(502, "AI returned invalid JSON")
        data["blocks"] = _sanitize_blocks(data.get("blocks", []))
        # Normalize AI-produced quirks so the render matches expectations.
        for b in data["blocks"]:
            b["id"] = b.get("id") or str(_uuid.uuid4())[:8]
            pr = b.get("props") or {}
            if b["type"] == "image" and "src" in pr and "url" not in pr:
                pr["url"] = pr.pop("src")
            if b["type"] == "button" and "text" in pr and "label" not in pr:
                pr["label"] = pr.pop("text")
            if b["type"] == "button" and "buttonLabel" in pr and "label" not in pr:
                pr["label"] = pr.pop("buttonLabel")
            b["props"] = pr
        return data

    # ============ Custom sending domain (Resend) ============
    def _resend_configured():
        return bool(getattr(resend, "api_key", None))

    @api.get("/newsletter/publications/{pid}/domain")
    async def get_domain_status(pid: str,
                                  user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        d = pub.get("sending_domain")
        if not d: return {"configured": False}
        if not _resend_configured():
            return {"configured": True, **d,
                    "warning": "Resend API key not present — cannot refresh status"}
        # Poll Resend for current status.
        try:
            resp = await asyncio.to_thread(resend.Domains.get, d.get("resend_id"))
            info = getattr(resp, "data", resp) or {}
            status = (info.get("status") if isinstance(info, dict) else None) or d.get("status")
            records = (info.get("records") if isinstance(info, dict) else None) or d.get("records")
            await db.publications.update_one(
                {"id": pid},
                {"$set": {"sending_domain.status": status,
                          "sending_domain.records": records,
                          "sending_domain.last_checked_at": now_iso()}})
            return {"configured": True, "name": d["name"], "resend_id": d.get("resend_id"),
                    "status": status, "records": records}
        except Exception as e:
            return {"configured": True, **d,
                    "warning": f"Could not fetch fresh status: {str(e)[:200]}"}

    @api.post("/newsletter/publications/{pid}/domain")
    async def add_domain(pid: str, body: DomainIn,
                          user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        if not _resend_configured():
            raise HTTPException(400, "Resend API key not configured — set RESEND_API_KEY")
        name = body.name.strip().lower()
        if not name or "." not in name:
            raise HTTPException(400, "Invalid domain")
        try:
            resp = await asyncio.to_thread(resend.Domains.create, {"name": name})
            info = getattr(resp, "data", resp) or {}
            if not isinstance(info, dict):
                raise HTTPException(502, "Unexpected Resend response")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, f"Resend add-domain failed: {e}")
        domain_doc = {
            "name": name,
            "resend_id": info.get("id"),
            "status": info.get("status", "pending"),
            "records": info.get("records", []),
            "created_at": now_iso(),
            "last_checked_at": now_iso(),
        }
        await db.publications.update_one(
            {"id": pid}, {"$set": {"sending_domain": domain_doc,
                                     "updated_at": now_iso()}})
        return {"configured": True, **domain_doc}

    @api.post("/newsletter/publications/{pid}/domain/verify")
    async def verify_domain(pid: str,
                              user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        d = pub.get("sending_domain")
        if not d or not d.get("resend_id"):
            raise HTTPException(400, "No domain to verify")
        if not _resend_configured():
            raise HTTPException(400, "Resend API key not configured")
        try:
            await asyncio.to_thread(resend.Domains.verify, d["resend_id"])
        except Exception as e:
            raise HTTPException(502, f"Verify request failed: {e}")
        return await get_domain_status(pid, user)

    @api.delete("/newsletter/publications/{pid}/domain")
    async def remove_domain(pid: str,
                              user: dict = Depends(get_current_user)):
        require_writer(user)
        pub = await _get_pub(pid, user["workspace_id"])
        d = pub.get("sending_domain")
        if d and d.get("resend_id") and _resend_configured():
            try: await asyncio.to_thread(resend.Domains.remove, d["resend_id"])
            except Exception: pass  # remove locally even if Resend fails
        await db.publications.update_one(
            {"id": pid}, {"$unset": {"sending_domain": ""},
                           "$set": {"updated_at": now_iso()}})
        return {"ok": True}

    return {"worker": _send_scheduled_posts}
