"""Compliance & platform hygiene endpoints.

- POST /api/errors                    — silent front-end crash reporter (Error Boundary hook)
- GET  /api/me/export                 — GDPR Data Subject Access Request (user + workspace dump)
- POST /api/me/data/delete            — GDPR/CCPA right-to-erasure request (soft-marks + queues)
- GET  /api/unsubscribe/{token}       — one-click unsubscribe landing (RFC 8058 target)
- POST /api/unsubscribe/{token}       — programmatic unsubscribe (form POST)
- GET  /api/.well-known/security.txt  — RFC 9116 security disclosure

Kept in its own router so `server.py` stays lean and the compliance surface is auditable
by a security review.
"""
import uuid
import hashlib
from typing import Optional
from fastapi import HTTPException, Depends, Request, Response
from pydantic import BaseModel


class ErrorReportIn(BaseModel):
    message: str
    stack: Optional[str] = ""
    route: Optional[str] = ""
    component_stack: Optional[str] = ""
    user_agent: Optional[str] = ""


class DeleteRequestIn(BaseModel):
    reason: Optional[str] = ""
    confirm_email: str


def unsubscribe_token_for(email: str, secret: str) -> str:
    """Deterministic, non-guessable token derived from email + platform secret.
    RFC 8058 allows the header value to include a POST target; we bake in the
    token so the endpoint is idempotent and stateless.
    """
    h = hashlib.sha256(f"{secret}::{email.strip().lower()}".encode()).hexdigest()
    return h[:32]


def register(api, db, now_iso, get_current_user, jwt_secret: str):
    # ---------------- Error Boundary Reporter ----------------
    @api.post("/errors")
    async def report_error(body: ErrorReportIn, request: Request):
        """Silent front-end crash reporter. Auth optional — anonymous crashes are still valuable."""
        user_id, workspace_id = None, None
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                import jwt as _jwt
                payload = _jwt.decode(auth[7:], jwt_secret, algorithms=["HS256"])
                user_id = payload.get("sub")
                u = await db.users.find_one({"id": user_id},
                                            {"_id": 0, "workspace_id": 1})
                if u:
                    workspace_id = u.get("workspace_id")
            except Exception:
                pass
        doc = {
            "id": str(uuid.uuid4()),
            "message": (body.message or "")[:500],
            "stack": (body.stack or "")[:4000],
            "component_stack": (body.component_stack or "")[:4000],
            "route": (body.route or "")[:200],
            "user_agent": (body.user_agent or request.headers.get("user-agent", ""))[:280],
            "user_id": user_id,
            "workspace_id": workspace_id,
            "ip": (request.client.host if request.client else None),
            "created_at": now_iso(),
        }
        try:
            await db.error_reports.insert_one(doc)
        except Exception:
            # Never let a crash-reporter crash the app.
            pass
        return {"ok": True}

    @api.get("/admin/errors")
    async def list_error_reports(limit: int = 50, user: dict = Depends(get_current_user)):
        """Superadmin — recent front-end crash reports for regression spotting."""
        if user.get("role") != "superadmin":
            raise HTTPException(403, "Superadmin only")
        rows = await db.error_reports.find({}, {"_id": 0}).sort("created_at", -1).to_list(min(limit, 200))
        return {"reports": rows}

    # ---------------- DSAR: right of access ----------------
    @api.get("/me/export")
    async def dsar_export(user: dict = Depends(get_current_user)):
        """GDPR Art. 15 / CCPA §1798.110 — return a JSON dump of everything we hold on the caller.

        Includes the workspace they belong to, so an owner running this gets the
        merchant-scoped catalog too. Non-owners get their own user record + their events.
        """
        ws_id = user["workspace_id"]
        is_owner = user.get("role") in ("owner", "superadmin")
        payload = {"user": user, "generated_at": now_iso(), "scope": "user"}
        if is_owner:
            payload["scope"] = "workspace"
            payload["workspace"] = await db.workspaces.find_one({"id": ws_id}, {"_id": 0}) or {}
            payload["coupons"] = await db.coupons.find({"workspace_id": ws_id}, {"_id": 0}).to_list(2000)
            payload["gift_cards"] = await db.gift_cards.find({"workspace_id": ws_id}, {"_id": 0}).to_list(2000)
            payload["redemptions"] = await db.redemptions.find({"workspace_id": ws_id}, {"_id": 0}).to_list(5000)
            payload["customers"] = await db.customers.find({"workspace_id": ws_id}, {"_id": 0}).to_list(5000)
            payload["journeys"] = await db.journeys.find({"workspace_id": ws_id}, {"_id": 0}).to_list(500)
            payload["funnels"] = await db.funnels.find({"workspace_id": ws_id}, {"_id": 0}).to_list(200)
        else:
            payload["email_events"] = await db.email_events.find({"to": user.get("email")}, {"_id": 0}).to_list(500)
        return payload

    # ---------------- DSAR: right of erasure ----------------
    @api.post("/me/data/delete")
    async def dsar_delete(body: DeleteRequestIn, user: dict = Depends(get_current_user)):
        """GDPR Art. 17 / CCPA §1798.105 — queue a right-to-erasure request.

        We DO NOT hard-delete inline: a superadmin approves erasures via /admin so
        we don't accidentally torch tax-relevant redemption ledgers before their
        legally required retention window. This endpoint books the intent.
        """
        if (body.confirm_email or "").strip().lower() != (user.get("email") or "").lower():
            raise HTTPException(400, "confirm_email must match your account email")
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "email": user.get("email"),
            "workspace_id": user["workspace_id"],
            "reason": (body.reason or "")[:400],
            "status": "pending",
            "created_at": now_iso(),
        }
        await db.deletion_requests.insert_one(doc)
        # Soft-flag the account so we stop sending marketing while the request is queued.
        await db.users.update_one({"id": user["id"]},
                                  {"$set": {"deletion_requested_at": now_iso(),
                                            "marketing_optout": True}})
        return {"ok": True, "request_id": doc["id"], "status": "pending"}

    @api.get("/admin/deletion-requests")
    async def list_deletion_requests(user: dict = Depends(get_current_user)):
        if user.get("role") != "superadmin":
            raise HTTPException(403, "Superadmin only")
        rows = await db.deletion_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
        return {"requests": rows}

    # ---------------- Unsubscribe (RFC 8058) ----------------
    async def _do_unsubscribe(token: str) -> dict:
        # Token is deterministic — look up by hash across recent recipients.
        # Cheap linear scan bounded by email_events retention; adequate at MVP scale.
        # In practice we also accept the token as an already-stored suppression entry.
        row = await db.email_suppressions.find_one({"token": token}, {"_id": 0})
        if row:
            return {"ok": True, "email": row.get("email"), "status": "already"}
        # Otherwise scan the most recent 5000 email events + workspace users to find a match.
        candidates = set()
        async for e in db.email_events.find({}, {"_id": 0, "to": 1}).sort("created_at", -1).limit(5000):
            to = e.get("to")
            if isinstance(to, list):
                for t in to: candidates.add((t or "").strip().lower())
            elif isinstance(to, str):
                candidates.add(to.strip().lower())
        async for u in db.users.find({}, {"_id": 0, "email": 1}).limit(5000):
            if u.get("email"):
                candidates.add(u["email"].strip().lower())
        match = None
        for c in candidates:
            if unsubscribe_token_for(c, jwt_secret) == token:
                match = c
                break
        if not match:
            raise HTTPException(404, "Unknown unsubscribe token")
        await db.email_suppressions.insert_one({
            "id": str(uuid.uuid4()), "email": match, "token": token,
            "reason": "user_unsubscribed", "created_at": now_iso()})
        await db.users.update_one({"email": match},
                                  {"$set": {"marketing_optout": True}})
        return {"ok": True, "email": match, "status": "unsubscribed"}

    @api.post("/unsubscribe/{token}")
    async def unsubscribe_post(token: str):
        """RFC 8058 target — Gmail / Yahoo POST here when a user hits List-Unsubscribe."""
        return await _do_unsubscribe(token)

    @api.get("/unsubscribe/{token}")
    async def unsubscribe_get(token: str):
        """Human-visitable unsubscribe landing (link in email footer)."""
        result = await _do_unsubscribe(token)
        html = f"""<!doctype html><html><head><title>Unsubscribed</title>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<style>body{{background:#0A0A0A;color:#fff;font-family:system-ui;margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh}}
.card{{max-width:480px;padding:40px;text-align:center;background:#141414;border:1px solid #27272A;border-radius:12px}}
h1{{font-size:24px;margin:0 0 8px}}p{{color:#A1A1AA}}</style></head>
<body><div class="card"><h1>You're unsubscribed</h1>
<p>{result.get('email')} won't receive marketing emails from this workspace.</p>
<p style="font-size:12px;color:#71717A;margin-top:24px">You can still receive transactional messages (order receipts, security alerts) required by law.</p>
</div></body></html>"""
        return Response(content=html, media_type="text/html")

    # ---------------- RFC 9116 security.txt ----------------
    @api.get("/.well-known/security.txt")
    async def security_txt():
        """RFC 9116 — publish a canonical security-contact document."""
        import os
        contact = os.environ.get("SECURITY_CONTACT_EMAIL", "security@promoos.com")
        from datetime import datetime, timezone, timedelta
        expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")
        body = (
            f"Contact: mailto:{contact}\n"
            f"Expires: {expires}\n"
            f"Preferred-Languages: en\n"
            f"Canonical: /api/.well-known/security.txt\n"
            f"Policy: /privacy\n"
        )
        return Response(content=body, media_type="text/plain")
