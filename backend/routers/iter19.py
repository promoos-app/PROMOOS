"""Iter-19 batch: Automation Sequences + Gift Card purchase flow."""
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def register(api, db, get_current_user, require_writer, PUBLIC_APP_URL: str, now_iso):
    # =========================================================================
    # AUTOMATION SEQUENCES
    # =========================================================================
    class SequenceStep(BaseModel):
        delay_hours: int = 0
        subject: str
        body: str  # HTML/text — Resend handles both

    class SequenceIn(BaseModel):
        name: str
        trigger: str = "optin"  # optin | funnel_view | coupon_redeem
        lead_tag_filter: Optional[str] = None
        funnel_id: Optional[str] = None
        steps: List[SequenceStep] = Field(default_factory=list)
        enabled: bool = True

    @api.get("/sequences")
    async def list_sequences(user: dict = Depends(get_current_user)):
        docs = await db.sequences.find(
            {"workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"_id": 0, "workspace_id": 0}).sort("created_at", -1).to_list(200)
        return docs

    @api.post("/sequences")
    async def create_sequence(body: SequenceIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        doc = {"id": str(uuid.uuid4()), "workspace_id": user["workspace_id"],
               **body.model_dump(), "created_at": _iso(), "is_deleted": False,
               "stats": {"enrolled": 0, "delivered": 0, "opened": 0}}
        await db.sequences.insert_one(doc)
        doc.pop("_id", None); doc.pop("workspace_id", None)
        return doc

    @api.put("/sequences/{sid}")
    async def update_sequence(sid: str, body: SequenceIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        upd = {**body.model_dump(), "updated_at": _iso()}
        r = await db.sequences.update_one(
            {"id": sid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"$set": upd})
        if r.matched_count == 0: raise HTTPException(404, "Sequence not found")
        return {"ok": True}

    @api.delete("/sequences/{sid}")
    async def delete_sequence(sid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.sequences.update_one(
            {"id": sid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"$set": {"is_deleted": True, "deleted_at": _iso()}})
        if r.matched_count == 0: raise HTTPException(404, "Sequence not found")
        return {"ok": True}

    @api.get("/sequences/{sid}/enrollments")
    async def sequence_enrollments(sid: str, user: dict = Depends(get_current_user)):
        # Verify workspace ownership.
        s = await db.sequences.find_one({"id": sid, "workspace_id": user["workspace_id"]}, {"id": 1})
        if not s: raise HTTPException(404, "Sequence not found")
        docs = await db.sequence_enrollments.find(
            {"sequence_id": sid, "workspace_id": user["workspace_id"]},
            {"_id": 0, "workspace_id": 0}).sort("enrolled_at", -1).to_list(500)
        return docs

    async def enroll_sequence_on_optin(workspace_id: str, funnel_id: str, lead_tag: str, email: str):
        """Called by the opt-in submit handler. Finds matching sequences and schedules the emails."""
        q = {"workspace_id": workspace_id, "trigger": "optin",
             "enabled": True, "is_deleted": {"$ne": True}}
        seqs = await db.sequences.find(q).to_list(50)
        for s in seqs:
            tag = s.get("lead_tag_filter") or ""
            fid = s.get("funnel_id") or ""
            if tag and tag != lead_tag: continue
            if fid and fid != funnel_id: continue
            enrollment_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            schedule = []
            for i, step in enumerate(s.get("steps") or []):
                send_at = now + timedelta(hours=int(step.get("delay_hours") or 0))
                schedule.append({"idx": i, "subject": step.get("subject", ""),
                                 "body": step.get("body", ""),
                                 "send_at": send_at.isoformat(), "status": "scheduled"})
            await db.sequence_enrollments.insert_one({
                "id": enrollment_id, "workspace_id": workspace_id,
                "sequence_id": s["id"], "sequence_name": s.get("name", ""),
                "email": email, "funnel_id": funnel_id,
                "lead_tag": lead_tag, "enrolled_at": _iso(),
                "schedule": schedule, "status": "active",
            })
            await db.sequences.update_one({"id": s["id"]}, {"$inc": {"stats.enrolled": 1}})

    # ---- Sequence delivery worker ----
    async def deliver_due_sequence_emails():
        """Poll for scheduled sequence emails whose send_at <= now and send via Resend.
        Idempotent — marks each step with status=sent + resend_id + sent_at."""
        try:
            import resend
        except ImportError:
            return
        resend_key = os.environ.get("RESEND_API_KEY", "")
        sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
        if not resend_key: return
        resend.api_key = resend_key
        now_iso_str = _iso()
        # Find enrollments with at least one due scheduled step.
        cursor = db.sequence_enrollments.find(
            {"status": "active", "schedule.status": "scheduled",
             "schedule.send_at": {"$lte": now_iso_str}})
        async for enr in cursor:
            changed = False
            for step in enr.get("schedule", []):
                if step.get("status") != "scheduled": continue
                if step.get("send_at", "9999") > now_iso_str: continue
                try:
                    import asyncio
                    result = await asyncio.to_thread(resend.Emails.send, {
                        "from": sender, "to": enr["email"],
                        "subject": step.get("subject", "(no subject)"),
                        "html": step.get("body", ""),
                    })
                    step["status"] = "sent"
                    step["resend_id"] = (result or {}).get("id") if isinstance(result, dict) else None
                    step["sent_at"] = _iso()
                    await db.sequences.update_one({"id": enr["sequence_id"]},
                                                    {"$inc": {"stats.delivered": 1}})
                    changed = True
                except Exception as e:
                    step["status"] = "failed"
                    step["error"] = str(e)[:200]
                    step["failed_at"] = _iso()
                    changed = True
            if changed:
                # Auto-complete when all steps sent/failed.
                if all(s.get("status") in ("sent", "failed") for s in enr.get("schedule", [])):
                    await db.sequence_enrollments.update_one({"id": enr["id"]},
                        {"$set": {"schedule": enr["schedule"], "status": "completed",
                                  "completed_at": _iso()}})
                else:
                    await db.sequence_enrollments.update_one({"id": enr["id"]},
                        {"$set": {"schedule": enr["schedule"]}})

    async def _sequence_delivery_loop():
        import asyncio
        while True:
            try:
                await deliver_due_sequence_emails()
            except Exception:
                pass
            await asyncio.sleep(60)  # every minute

    @api.post("/sequences/deliver-now")
    async def trigger_delivery(user: dict = Depends(get_current_user)):
        """Manual delivery kick — useful for testing without waiting on the loop."""
        require_writer(user)
        await deliver_due_sequence_emails()
        return {"ok": True}

    # Kick off the background loop on startup.
    api.state = getattr(api, "state", type("_", (), {})())
    api.state.enroll_sequence_on_optin = enroll_sequence_on_optin
    api.state.deliver_due_sequence_emails = deliver_due_sequence_emails
    # Register startup task — FastAPI's add_event_handler works on the app, not the router,
    # so callers can wire this in via server.py.
    api.state.sequence_delivery_loop = _sequence_delivery_loop

    # =========================================================================
    # GIFT CARD PURCHASE FLOW (public Stripe checkout)
    # =========================================================================
    class GiftCardBuyIn(BaseModel):
        workspace_id: str
        template_id: str
        amount: float
        currency: str = "USD"
        purchaser_email: str
        recipient_email: Optional[str] = None
        recipient_name: Optional[str] = None
        message: Optional[str] = None
        origin_url: str

    @api.post("/public/giftcards/checkout")
    async def public_giftcard_checkout(body: GiftCardBuyIn):
        """Public — Stripe checkout for buying a gift card. On success, the webhook
        (or the success-page recovery flow) mints the actual gift card. Amount must
        be > 0. Currency defaults to USD."""
        if body.amount <= 0: raise HTTPException(400, "Amount must be positive")
        try:
            import stripe
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
            if not stripe.api_key: raise HTTPException(501, "Stripe not configured")
            product_data = {"name": f"Gift Card · ${body.amount:.0f} {body.currency}"}
            if body.recipient_name:
                product_data["description"] = f"For {body.recipient_name}"
            session = stripe.checkout.Session.create(
                line_items=[{"price_data": {
                    "currency": body.currency.lower(),
                    "product_data": product_data,
                    "unit_amount": int(round(body.amount * 100)),
                }, "quantity": 1}],
                mode="payment",
                customer_email=body.purchaser_email,
                success_url=f"{body.origin_url}/gift-thank-you?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=body.origin_url,
                metadata={
                    "kind": "giftcard",
                    "workspace_id": body.workspace_id,
                    "template_id": body.template_id,
                    "amount": f"{body.amount:.2f}",
                    "currency": body.currency,
                    "purchaser_email": body.purchaser_email,
                    "recipient_email": body.recipient_email or "",
                    "recipient_name": body.recipient_name or "",
                    "message": (body.message or "")[:400],
                },
            )
            await db.giftcard_orders.insert_one({
                "id": str(uuid.uuid4()), "session_id": session.id,
                "workspace_id": body.workspace_id, "template_id": body.template_id,
                "amount": body.amount, "currency": body.currency,
                "purchaser_email": body.purchaser_email,
                "recipient_email": body.recipient_email,
                "recipient_name": body.recipient_name,
                "message": body.message, "status": "initiated",
                "created_at": _iso(),
            })
            return {"checkout_url": session.url, "session_id": session.id}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, f"Stripe error: {e}")

    @api.get("/public/giftcards/order/{session_id}")
    async def giftcard_order_status(session_id: str):
        """After Stripe redirect, poll here to find out if the gift card was minted.
        On first paid call, mint a real gift card and return the code."""
        order = await db.giftcard_orders.find_one({"session_id": session_id}, {"_id": 0})
        if not order: raise HTTPException(404, "Order not found")
        if order.get("status") == "completed" and order.get("code"):
            return {"status": "completed", "code": order["code"], "amount": order["amount"]}
        # Ask Stripe if session is paid
        try:
            import stripe
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
            sess = stripe.checkout.Session.retrieve(session_id)
            paid = sess.payment_status in ("paid", "no_payment_required")
        except Exception:
            paid = False
        if not paid:
            return {"status": "pending"}
        # Mint the gift card now (idempotent on session_id).
        import secrets, string
        code = "GC-" + "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        gc = {
            "id": str(uuid.uuid4()), "workspace_id": order["workspace_id"],
            "template_id": order.get("template_id"), "code": code,
            "amount": order["amount"], "balance": order["amount"],
            "currency": order.get("currency", "USD"), "state": "active",
            "purchaser_email": order.get("purchaser_email"),
            "recipient_email": order.get("recipient_email"),
            "recipient_name": order.get("recipient_name"),
            "message": order.get("message"),
            "issued_via": "funnel_purchase", "session_id": session_id,
            "created_at": _iso(),
        }
        await db.gift_cards.insert_one(gc)
        await db.giftcard_orders.update_one(
            {"session_id": session_id},
            {"$set": {"status": "completed", "code": code, "completed_at": _iso()}})
        return {"status": "completed", "code": code, "amount": order["amount"]}
