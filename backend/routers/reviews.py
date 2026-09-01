"""Reviews collection — verified customer quotes merchants attach to storefronts."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewIn(BaseModel):
    product_id: Optional[str] = None
    customer_name: str = Field(min_length=1, max_length=120)
    role: Optional[str] = Field(default=None, max_length=120)
    quote: str = Field(min_length=1, max_length=2000)
    rating: int = Field(default=5, ge=1, le=5)
    avatar_url: Optional[str] = None
    verified: bool = True
    approved: bool = True


class ReviewPatch(BaseModel):
    product_id: Optional[str] = None
    customer_name: Optional[str] = None
    role: Optional[str] = None
    quote: Optional[str] = None
    rating: Optional[int] = None
    avatar_url: Optional[str] = None
    verified: Optional[bool] = None
    approved: Optional[bool] = None


def register(api, db, get_current_user, require_writer):

    @api.get("/reviews")
    async def list_reviews(product_id: Optional[str] = None,
                             approved: Optional[bool] = None,
                             user: dict = Depends(get_current_user)):
        q = {"workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}}
        if product_id: q["product_id"] = product_id
        if approved is not None: q["approved"] = approved
        docs = await db.reviews.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
        return docs

    @api.post("/reviews")
    async def create_review(body: ReviewIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        doc = {
            "id": str(uuid.uuid4()),
            "workspace_id": user["workspace_id"],
            "product_id": body.product_id,
            "customer_name": body.customer_name.strip(),
            "role": (body.role or "").strip() or None,
            "quote": body.quote.strip(),
            "rating": body.rating,
            "avatar_url": (body.avatar_url or "").strip() or None,
            "verified": bool(body.verified),
            "approved": bool(body.approved),
            "created_at": _iso(),
            "created_by": user["id"],
            "is_deleted": False,
        }
        await db.reviews.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @api.patch("/reviews/{rid}")
    async def update_review(rid: str, body: ReviewPatch,
                              user: dict = Depends(get_current_user)):
        require_writer(user)
        updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k in ("role", "avatar_url", "product_id")}
        if not updates: return {"ok": True}
        updates["updated_at"] = _iso()
        r = await db.reviews.update_one(
            {"id": rid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"$set": updates})
        if r.matched_count == 0: raise HTTPException(404, "Review not found")
        return {"ok": True}

    @api.delete("/reviews/{rid}")
    async def delete_review(rid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.reviews.update_one(
            {"id": rid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"$set": {"is_deleted": True, "deleted_at": _iso()}})
        if r.matched_count == 0: raise HTTPException(404, "Review not found")
        return {"ok": True}

    @api.get("/public/reviews/{workspace_id}")
    async def public_reviews(workspace_id: str,
                               product_id: Optional[str] = None,
                               limit: int = Query(6, ge=1, le=24)):
        q = {"workspace_id": workspace_id, "is_deleted": {"$ne": True}, "approved": True}
        if product_id: q["product_id"] = product_id
        docs = await db.reviews.find(q, {"_id": 0, "workspace_id": 0, "created_by": 0,
                                            "is_deleted": 0, "approved": 0}).sort("created_at", -1).to_list(limit)
        return docs
