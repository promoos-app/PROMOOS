"""Admin portal routes — superadmin only. Extracted from server.py in iter-11."""
import uuid
from typing import Optional
from fastapi import HTTPException, Depends
from pydantic import BaseModel, EmailStr


def register(api, db, now_iso, get_current_user, require_superadmin, hash_password, admin_log):

    @api.get("/admin/stats")
    async def admin_stats(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        users_active = await db.users.count_documents({"suspended": {"$ne": True}, "deleted_at": None})
        users_suspended = await db.users.count_documents({"suspended": True, "deleted_at": None})
        users_deleted = await db.users.count_documents({"deleted_at": {"$ne": None}})
        workspaces = await db.workspaces.count_documents({})
        coupons = await db.coupons.count_documents({})
        redemptions = await db.redemptions.count_documents({})
        return {
            "users": {"active": users_active, "suspended": users_suspended, "deleted": users_deleted},
            "workspaces": workspaces, "coupons": coupons, "redemptions": redemptions,
        }

    @api.get("/admin/users")
    async def admin_users(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(2000)
        ws_map = {w["id"]: w.get("name", "") for w in
                  await db.workspaces.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(500)}
        for r in rows:
            r["workspace_name"] = ws_map.get(r.get("workspace_id"), "")
            r["state"] = "deleted" if r.get("deleted_at") else ("suspended" if r.get("suspended") else "active")
        return rows

    class AdminUserCreateIn(BaseModel):
        name: str
        email: EmailStr
        password: str
        role: str = "marketer"
        workspace_id: Optional[str] = None
        workspace_name: Optional[str] = None

    @api.post("/admin/users")
    async def admin_create_user(body: AdminUserCreateIn, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        if body.role not in ("owner", "marketer", "viewer", "superadmin"):
            raise HTTPException(400, "invalid role")
        existing = await db.users.find_one({"email": body.email.lower()})
        if existing:
            raise HTTPException(400, "email already registered")
        wid = body.workspace_id
        if not wid:
            wid = str(uuid.uuid4())
            await db.workspaces.insert_one({
                "id": wid, "name": body.workspace_name or f"{body.name}'s workspace",
                "primary_color": "#005CEE", "secondary_color": "#CCFF00",
                "created_at": now_iso()})
        uid = str(uuid.uuid4())
        await db.users.insert_one({
            "id": uid, "name": body.name, "email": body.email.lower(),
            "password_hash": hash_password(body.password), "role": body.role,
            "workspace_id": wid, "suspended": False, "deleted_at": None,
            "created_at": now_iso(), "created_by_admin": user["id"]})
        await admin_log(user, "user.create", target=uid, meta={"email": body.email})
        return {"ok": True, "user_id": uid, "workspace_id": wid}

    @api.post("/admin/users/{uid}/suspend")
    async def admin_suspend(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        await db.users.update_one({"id": uid}, {"$set": {"suspended": True, "suspended_at": now_iso()}})
        await admin_log(user, "user.suspend", target=uid)
        return {"ok": True}

    @api.post("/admin/users/{uid}/activate")
    async def admin_activate(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        await db.users.update_one({"id": uid}, {"$set": {"suspended": False}, "$unset": {"suspended_at": ""}})
        await admin_log(user, "user.activate", target=uid)
        return {"ok": True}

    @api.post("/admin/users/{uid}/restore")
    async def admin_restore(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        await db.users.update_one({"id": uid}, {"$set": {"deleted_at": None, "suspended": False}})
        await admin_log(user, "user.restore", target=uid)
        return {"ok": True}

    @api.delete("/admin/users/{uid}")
    async def admin_delete(uid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        if uid == user["id"]:
            raise HTTPException(400, "Cannot delete your own account")
        await db.users.update_one({"id": uid}, {"$set": {"deleted_at": now_iso()}})
        await admin_log(user, "user.delete", target=uid)
        return {"ok": True}

    @api.get("/admin/workspaces")
    async def admin_workspaces(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        docs = await db.workspaces.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        for d in docs:
            d["user_count"] = await db.users.count_documents({"workspace_id": d["id"], "deleted_at": None})
            d["coupon_count"] = await db.coupons.count_documents({"workspace_id": d["id"]})
            d["redemption_count"] = await db.redemptions.count_documents({"workspace_id": d["id"]})
        return docs

    @api.get("/admin/logs")
    async def admin_logs(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        docs = await db.admin_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
        return docs

    @api.get("/admin/payments")
    async def admin_payments(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        docs = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        total = sum(d.get("amount", 0) for d in docs if d.get("status") == "succeeded")
        return {"total_collected": round(total, 2), "count": len(docs), "payments": docs}
