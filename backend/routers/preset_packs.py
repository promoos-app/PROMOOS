"""Preset Packs — brandable one-tap style packs for the Coupon + Gift Card studios.

Superadmins CRUD packs; workspaces consume the union of built-in + public packs.
"""
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, Depends
from pydantic import BaseModel


class PresetItem(BaseModel):
    key: str
    label: str
    accent: str          # hex color like "#E7CB8E"
    prompt: str          # image generation prompt


class PresetPackIn(BaseModel):
    name: str
    scope: str           # "coupon" | "gift_card" | "both"
    presets: List[PresetItem] = []
    is_public: bool = True


def register(api, db, now_iso, get_current_user, require_superadmin):
    def _sanitize(doc: dict) -> dict:
        return {k: v for k, v in doc.items() if k != "_id"}

    @api.post("/admin/preset-packs")
    async def create_pack(body: PresetPackIn, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        if body.scope not in ("coupon", "gift_card", "both"):
            raise HTTPException(400, "scope must be coupon | gift_card | both")
        doc = {
            "id": str(uuid.uuid4()),
            "name": body.name.strip()[:80],
            "scope": body.scope,
            "presets": [p.model_dump() for p in body.presets],
            "is_public": bool(body.is_public),
            "created_by": user["id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        await db.preset_packs.insert_one({**doc})
        return doc

    @api.get("/admin/preset-packs")
    async def list_admin_packs(user: dict = Depends(get_current_user)):
        require_superadmin(user)
        docs = await db.preset_packs.find({}).sort("created_at", -1).to_list(200)
        return [_sanitize(d) for d in docs]

    @api.put("/admin/preset-packs/{pid}")
    async def update_pack(pid: str, body: PresetPackIn, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        if body.scope not in ("coupon", "gift_card", "both"):
            raise HTTPException(400, "scope must be coupon | gift_card | both")
        res = await db.preset_packs.update_one(
            {"id": pid},
            {"$set": {
                "name": body.name.strip()[:80],
                "scope": body.scope,
                "presets": [p.model_dump() for p in body.presets],
                "is_public": bool(body.is_public),
                "updated_at": now_iso(),
            }})
        if res.matched_count == 0:
            raise HTTPException(404, "Preset pack not found")
        return {"ok": True}

    @api.delete("/admin/preset-packs/{pid}")
    async def delete_pack(pid: str, user: dict = Depends(get_current_user)):
        require_superadmin(user)
        r = await db.preset_packs.delete_one({"id": pid})
        if r.deleted_count == 0:
            raise HTTPException(404, "Preset pack not found")
        return {"ok": True}

    @api.get("/preset-packs")
    async def public_packs(scope: Optional[str] = None,
                           user: dict = Depends(get_current_user)):
        """Any authenticated workspace user can read published packs."""
        q: dict = {"is_public": True}
        if scope in ("coupon", "gift_card"):
            q["scope"] = {"$in": [scope, "both"]}
        docs = await db.preset_packs.find(q).sort("created_at", -1).to_list(200)
        # Trim to what the studios need — never leak internal fields
        return [{
            "id": d["id"], "name": d["name"], "scope": d["scope"],
            "presets": d.get("presets", []),
        } for d in docs]
