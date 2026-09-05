"""Campaign Journeys — trigger-based automation runs.

Endpoints:
- POST/GET/PUT/DELETE /api/journeys[/{jid}]
- POST /api/journeys/{jid}/enroll
- GET  /api/journeys/{jid}/runs

Background worker `journey_worker()` processes due runs every 30s.
"""
import uuid
import random
import string
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import HTTPException, Depends
from pydantic import BaseModel, EmailStr

logger = logging.getLogger(__name__)


class JourneyIn(BaseModel):
    name: str
    trigger: str = "signup"           # signup | purchase | inactive_30d | birthday
    steps: List[dict] = []            # [{type: "wait"|"send_email"|"send_sms"|"send_coupon", ...}]
    enabled: bool = False


class JourneyEnrollIn(BaseModel):
    customer: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


def register(api, db, now_iso, get_current_user, require_writer, ctx):
    """Register journey endpoints + worker.

    `ctx` is a dict with:
        RESEND_API_KEY, SENDER_EMAIL, TWILIO_FROM_SMS, PUBLIC_APP_URL,
        twilio_client, resend, gen_qr, render_coupon_email, twilio_send_one
    """

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
                if not ctx["RESEND_API_KEY"] or not run.get("email"):
                    log_entry["skipped"] = "email not configured or missing recipient"
                else:
                    subject = step.get("subject", f"A message from {ws.get('name','us')}")
                    body = step.get("body", "Thanks for being with us.")
                    html = f"<div style='font-family:Helvetica,Arial,sans-serif;padding:24px;background:#0A0A0A;color:#fff'><h2>{subject}</h2><p style='color:#A1A1AA'>{body}</p></div>"
                    r = await asyncio.to_thread(ctx["resend"].Emails.send, {
                        "from": ctx["SENDER_EMAIL"], "to": [run["email"]],
                        "subject": subject, "html": html})
                    log_entry["email_id"] = r.get("id") if isinstance(r, dict) else None
            elif step["type"] == "send_sms":
                if not ctx["twilio_client"] or not run.get("phone") or not ctx["TWILIO_FROM_SMS"]:
                    log_entry["skipped"] = "sms not configured or missing recipient"
                else:
                    sid = await ctx["twilio_send_one"](run["phone"], step.get("body", "Hi from us!"), "sms")
                    log_entry["sms_sid"] = sid
            elif step["type"] == "send_coupon":
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
                    "image_url": "",
                    "qr_code": ctx["gen_qr"](f"{ctx['PUBLIC_APP_URL'] or ''}/c/{code}"),
                    "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                              "usage_limit": 1, "per_customer_limit": 1, "stackable": False,
                              "start_date": None, "end_date": None,
                              "referral_enabled": False, "referral_credit_pct": 10},
                    "stats": {"impressions": 0, "redemptions": 0, "revenue": 0.0, "referral_credit": 0.0},
                    "created_at": now_iso(), "updated_at": now_iso(), "source": "journey",
                }
                await db.coupons.insert_one({**new_cp})
                log_entry["coupon_code"] = code
                if ctx["RESEND_API_KEY"] and run.get("email"):
                    try:
                        subject = f"A special reward: {int(disc)}% off"
                        landing = f"{ctx['PUBLIC_APP_URL'] or ''}/c/{code}"
                        html = ctx["render_coupon_email"](new_cp, ws, landing)
                        await asyncio.to_thread(ctx["resend"].Emails.send, {
                            "from": ctx["SENDER_EMAIL"], "to": [run["email"]],
                            "subject": subject, "html": html})
                        log_entry["email_delivered"] = True
                    except Exception as e:
                        log_entry["email_error"] = str(e)[:120]
            else:
                log_entry["skipped"] = f"unknown step type {step['type']}"
        except Exception as e:
            log_entry["error"] = str(e)[:200]
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
        docs = await db.journeys.find({"workspace_id": user["workspace_id"]},
                                        {"_id": 0, "workspace_id": 0}).sort("created_at", -1).to_list(200)
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

    JOURNEY_TEMPLATES = [
        {
            "id": "welcome",
            "name": "Welcome flow",
            "description": "Greet new signups, wait a day, then send a 10% welcome coupon.",
            "trigger": "signup",
            "steps": [
                {"type": "send_email",
                 "subject": "Welcome to the family",
                 "body": "Hey! Thanks for joining us. We built a little gift to say hi — arriving tomorrow."},
                {"type": "wait", "hours": 24},
                {"type": "send_coupon", "discount": 10,
                 "headline": "10% off, on us", "type_coupon": "percentage",
                 "description": "A tiny welcome gift to start your journey with us."},
            ],
        },
        {
            "id": "cart_abandonment",
            "name": "Cart abandonment",
            "description": "Nudge shoppers 4h after they leave, then rescue with a 15% code the next day.",
            "trigger": "inactive_30d",
            "steps": [
                {"type": "wait", "hours": 4},
                {"type": "send_email",
                 "subject": "Still thinking it over?",
                 "body": "We saved your favourites. Come back anytime — they'll be waiting."},
                {"type": "wait", "hours": 20},
                {"type": "send_coupon", "discount": 15,
                 "headline": "15% off — come finish your order", "type_coupon": "percentage",
                 "description": "This one's just for you. Good for the next 48 hours."},
            ],
        },
        {
            "id": "birthday",
            "name": "Birthday reward",
            "description": "Wish customers a happy birthday and drop a 20% code they can spend all week.",
            "trigger": "birthday",
            "steps": [
                {"type": "send_email",
                 "subject": "Happy birthday from us",
                 "body": "Wishing you the best year yet. We put a little something aside for you."},
                {"type": "send_coupon", "discount": 20,
                 "headline": "Happy birthday — 20% off, all week", "type_coupon": "percentage",
                 "description": "Our birthday gift to you. Good for the next seven days."},
            ],
        },
    ]

    @api.get("/journey-templates")
    async def list_journey_templates(user: dict = Depends(get_current_user)):
        """Ready-to-run automation templates any workspace can install with one click.

        Union of:
        - Built-in templates (welcome / cart abandonment / birthday)
        - Templates saved by this workspace via the Journey Template Studio
        - Public templates promoted by superadmin (Template Marketplace)
        """
        own = await db.journey_templates.find(
            {"workspace_id": user["workspace_id"]},
            {"_id": 0}).sort("created_at", -1).to_list(100)
        public = await db.journey_templates.find(
            {"is_public": True, "workspace_id": {"$ne": user["workspace_id"]}},
            {"_id": 0}).sort("published_at", -1).to_list(100)
        # Attribution — resolve publishing workspace names in one round-trip
        ws_ids = list({c["workspace_id"] for c in public if c.get("workspace_id")})
        ws_names: dict = {}
        if ws_ids:
            async for ws in db.workspaces.find({"id": {"$in": ws_ids}}, {"_id": 0, "id": 1, "name": 1}):
                ws_names[ws["id"]] = ws.get("name", "")
        # Normalize into the same shape as builtin
        own_shaped = [{
            "id": c["id"], "name": c["name"], "description": c.get("description", ""),
            "trigger": c["trigger"], "steps": c["steps"], "source": "custom",
            "is_public": bool(c.get("is_public")),
        } for c in own]
        public_shaped = [{
            "id": c["id"], "name": c["name"], "description": c.get("description", ""),
            "trigger": c["trigger"], "steps": c["steps"], "source": "marketplace",
            "published_by_workspace": ws_names.get(c.get("workspace_id"), "Agency"),
        } for c in public]
        return {"templates": own_shaped + public_shaped + JOURNEY_TEMPLATES}

    class SaveTemplateIn(BaseModel):
        journey_id: str
        name: str
        description: Optional[str] = ""

    @api.post("/journey-templates/save")
    async def save_journey_as_template(body: SaveTemplateIn,
                                        user: dict = Depends(get_current_user)):
        """Journey Template Studio — snapshot an existing journey as a reusable template."""
        require_writer(user)
        j = await db.journeys.find_one(
            {"id": body.journey_id, "workspace_id": user["workspace_id"]},
            {"_id": 0})
        if not j:
            raise HTTPException(404, "Journey not found")
        doc = {
            "id": str(uuid.uuid4()),
            "workspace_id": user["workspace_id"],
            "name": body.name.strip()[:80],
            "description": (body.description or "").strip()[:280],
            "trigger": j["trigger"],
            "steps": j["steps"],
            "source_journey_id": body.journey_id,
            "created_by": user["id"],
            "created_at": now_iso(),
            "is_public": False,  # merchant-scoped by default; superadmin can promote
        }
        await db.journey_templates.insert_one({**doc})
        return doc

    @api.post("/admin/journey-templates/{tid}/publish")
    async def publish_custom_template(tid: str, user: dict = Depends(get_current_user)):
        """Template Marketplace — superadmin promotes a workspace-scoped template to the global catalog."""
        if user.get("role") != "superadmin":
            raise HTTPException(403, "Superadmin only")
        r = await db.journey_templates.update_one(
            {"id": tid}, {"$set": {"is_public": True, "published_at": now_iso(),
                                     "published_by": user["id"]}})
        if r.matched_count == 0:
            raise HTTPException(404, "Custom template not found")
        return {"ok": True}

    @api.post("/admin/journey-templates/{tid}/unpublish")
    async def unpublish_custom_template(tid: str, user: dict = Depends(get_current_user)):
        if user.get("role") != "superadmin":
            raise HTTPException(403, "Superadmin only")
        r = await db.journey_templates.update_one(
            {"id": tid}, {"$set": {"is_public": False}})
        if r.matched_count == 0:
            raise HTTPException(404, "Custom template not found")
        return {"ok": True}

    @api.delete("/journey-templates/custom/{tid}")
    async def delete_custom_template(tid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.journey_templates.delete_one(
            {"id": tid, "workspace_id": user["workspace_id"]})
        if r.deleted_count == 0:
            raise HTTPException(404, "Custom template not found")
        return {"ok": True}

    @api.post("/journey-templates/{tid}/apply")
    async def apply_journey_template(tid: str, user: dict = Depends(get_current_user)):
        """Copy a template into the merchant's workspace as an enabled journey.
        Accepts both builtin ids and workspace-scoped custom template ids."""
        require_writer(user)
        tpl = next((t for t in JOURNEY_TEMPLATES if t["id"] == tid), None)
        if tpl is None:
            custom = await db.journey_templates.find_one(
                {"id": tid, "$or": [
                    {"workspace_id": user["workspace_id"]},
                    {"is_public": True},
                ]}, {"_id": 0})
            if custom:
                tpl = custom
        if not tpl:
            raise HTTPException(404, f"Template '{tid}' not found")
        doc = {
            "id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
            "name": tpl["name"], "trigger": tpl["trigger"], "steps": tpl["steps"],
            "enabled": True,
            "stats": {"entered": 0, "completed": 0, "conversions": 0},
            "created_at": now_iso(),
            "source": f"template:{tid}",
        }
        await db.journeys.insert_one({**doc})
        return doc



    return {
        "fire_trigger": _fire_trigger,
        "enroll": _enroll_customer_in_journey,
        "worker": journey_worker,
    }
