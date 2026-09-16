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

    @api.post("/admin/preset-packs/import")
    async def import_pack(body: dict, user: dict = Depends(get_current_user)):
        """Bulk-import a preset pack from a raw JSON blob (partner/agency handoff)."""
        require_superadmin(user)
        name = (body.get("name") or "").strip()
        scope = body.get("scope", "both")
        if not name:
            raise HTTPException(400, "JSON must include a 'name'")
        if scope not in ("coupon", "gift_card", "both"):
            raise HTTPException(400, "'scope' must be coupon | gift_card | both")
        raw_presets = body.get("presets") or []
        if not isinstance(raw_presets, list) or not raw_presets:
            raise HTTPException(400, "JSON must include a non-empty 'presets' array")
        cleaned = []
        seen_keys = set()
        for i, p in enumerate(raw_presets):
            if not isinstance(p, dict):
                raise HTTPException(400, f"preset[{i}] must be an object")
            key = str(p.get("key") or "").strip().lower()
            label = str(p.get("label") or "").strip()
            accent = str(p.get("accent") or "#CCFF00").strip()
            prompt = str(p.get("prompt") or "").strip()
            if not key or not label or not prompt:
                raise HTTPException(400, f"preset[{i}] needs key, label, and prompt")
            if key in seen_keys:
                raise HTTPException(400, f"duplicate preset key '{key}'")
            seen_keys.add(key)
            cleaned.append({"key": key, "label": label, "accent": accent, "prompt": prompt})
        doc = {
            "id": str(uuid.uuid4()),
            "name": name[:80],
            "scope": scope,
            "presets": cleaned,
            "is_public": bool(body.get("is_public", True)),
            "created_by": user["id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "source": "import",
        }
        await db.preset_packs.insert_one({**doc})
        return doc


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
            "rating_avg": d.get("rating_avg", 0.0),
            "rating_count": d.get("rating_count", 0),
        } for d in docs]

    class PresetRateIn(BaseModel):
        stars: int  # 1..5
        comment: Optional[str] = None  # optional one-line qualitative feedback

    @api.post("/preset-packs/{pid}/rate")
    async def rate_preset_pack(pid: str, body: PresetRateIn,
                                 user: dict = Depends(get_current_user)):
        """Marketplace rating for coupon/gift-card preset packs. One vote per workspace, overwritable."""
        if body.stars < 1 or body.stars > 5:
            raise HTTPException(400, "stars must be 1..5")
        pack = await db.preset_packs.find_one({"id": pid, "is_public": True},
                                              {"_id": 0, "id": 1})
        if not pack:
            raise HTTPException(404, "Preset pack not found")
        ws = await db.workspaces.find_one({"id": user["workspace_id"]},
                                          {"_id": 0, "name": 1}) or {}
        comment = (body.comment or "").strip()[:200] or None
        await db.preset_pack_ratings.update_one(
            {"pack_id": pid, "workspace_id": user["workspace_id"]},
            {"$set": {"pack_id": pid, "workspace_id": user["workspace_id"],
                      "workspace_name": ws.get("name", "Agency"),
                      "stars": int(body.stars), "comment": comment,
                      "rated_at": now_iso()}},
            upsert=True)
        agg = await db.preset_pack_ratings.aggregate([
            {"$match": {"pack_id": pid}},
            {"$group": {"_id": "$pack_id", "avg": {"$avg": "$stars"},
                         "count": {"$sum": 1}}},
        ]).to_list(1)
        avg = round(agg[0]["avg"], 2) if agg else 0.0
        cnt = agg[0]["count"] if agg else 0
        await db.preset_packs.update_one({"id": pid},
                                         {"$set": {"rating_avg": avg, "rating_count": cnt}})
        return {"ok": True, "avg": avg, "count": cnt}

    @api.get("/preset-packs/{pid}/comments")
    async def list_pack_comments(pid: str, user: dict = Depends(get_current_user)):
        """Return the most-recent qualitative notes for a preset pack."""
        rows = await db.preset_pack_ratings.find(
            {"pack_id": pid, "comment": {"$ne": None}},
            {"_id": 0, "stars": 1, "comment": 1, "workspace_name": 1, "rated_at": 1}
        ).sort("rated_at", -1).to_list(20)
        return {"comments": rows}
