"""Funnel Builder — luxury drag-drop funnels with coupon/gift-card blocks and custom-domain publishing.

Data model
----------
Funnel: { id, workspace_id, name, slug, blocks: [Block], theme, seo, custom_domain?, published, created_at }
Block: { id, type, props }

Block types: hero, features, coupon, giftcard, cta, testimonial, faq, footer, image, heading, paragraph, video, spacer
"""
import uuid, re, os
from typing import Optional, List
from fastapi import HTTPException, Depends, Request
from pydantic import BaseModel


TEMPLATES = [
    {
        "id": "diamond",
        "name": "Diamond",
        "aesthetic": "minimalist luxury, black+white with a single accent",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#CCFF00",
                  "font_display": "Playfair Display", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Limited-edition offer",
                                        "headline": "A little something, on us.",
                                        "subline": "Redeem your exclusive coupon below and enjoy premium savings.",
                                        "cta_label": "Claim now", "cta_scroll_to": "coupon-1"}},
            {"type": "coupon", "props": {"coupon_code": "", "label": "Your coupon", "style": "luxury"}, "anchor": "coupon-1"},
            {"type": "features", "props": {"title": "Why members love us",
                                            "items": [
                                                {"title": "Free returns", "text": "30 days, no questions."},
                                                {"title": "Priority support", "text": "24/7 humans, not bots."},
                                                {"title": "Lifetime updates", "text": "Every new release, free."},
                                            ]}},
            {"type": "cta", "props": {"headline": "Ready when you are.", "cta_label": "Redeem", "cta_scroll_to": "coupon-1"}},
        ],
    },
    {
        "id": "champagne",
        "name": "Champagne",
        "aesthetic": "gold + cream, editorial serif, warm",
        "theme": {"bg": "#FAF7F0", "fg": "#1A1305", "muted": "#5C5040", "accent": "#B8860B",
                  "font_display": "Playfair Display", "font_body": "DM Sans"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "For our best customers",
                                        "headline": "The gift of great taste.",
                                        "subline": "Redeem your Champagne-tier gift card at checkout.",
                                        "cta_label": "Redeem", "cta_scroll_to": "gc-1"}},
            {"type": "giftcard", "props": {"template_id": "champagne-gold", "amount": 100, "currency": "USD"}, "anchor": "gc-1"},
            {"type": "testimonial", "props": {"quote": "The most elegant customer experience I've had all year.",
                                                "author": "Ava L., Verified Buyer"}},
            {"type": "cta", "props": {"headline": "Redeem in seconds.", "cta_label": "Copy code", "cta_scroll_to": "gc-1"}},
        ],
    },
    {
        "id": "noir",
        "name": "Noir",
        "aesthetic": "dark, cinematic, bold",
        "theme": {"bg": "#000000", "fg": "#FFFFFF", "muted": "#71717A", "accent": "#FF006E",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "24 hours only",
                                        "headline": "Flash. Sale.",
                                        "subline": "Your invitation-only 40% off.",
                                        "cta_label": "Grab it", "cta_scroll_to": "coupon-1"}},
            {"type": "coupon", "props": {"coupon_code": "", "label": "Flash coupon", "style": "bold"}, "anchor": "coupon-1"},
            {"type": "faq", "props": {"items": [
                {"q": "How long is this active?", "a": "Exactly 24 hours from now."},
                {"q": "Can I stack it?", "a": "Not with other promo codes, no."},
            ]}},
        ],
    },
    {
        "id": "emerald",
        "name": "Emerald",
        "aesthetic": "nature, calm, botanical",
        "theme": {"bg": "#F1FAEE", "fg": "#04231A", "muted": "#4A6B5C", "accent": "#0F5E43",
                  "font_display": "Playfair Display", "font_body": "Nunito"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Rewards program",
                                        "headline": "Your loyalty, richly rewarded.",
                                        "subline": "Redeem points, use your reward coupon below.",
                                        "cta_label": "Redeem", "cta_scroll_to": "coupon-1"}},
            {"type": "coupon", "props": {"coupon_code": "", "label": "Loyalty reward", "style": "nature"}, "anchor": "coupon-1"},
            {"type": "features", "props": {"title": "Ways to earn more",
                                            "items": [
                                                {"title": "Refer a friend", "text": "500 points each."},
                                                {"title": "Complete profile", "text": "200 points."},
                                                {"title": "Review a product", "text": "100 points."},
                                            ]}},
        ],
    },
    {
        "id": "rose",
        "name": "Rosé",
        "aesthetic": "warm pinks, romantic, celebratory",
        "theme": {"bg": "#FDE2E4", "fg": "#3A0616", "muted": "#7C4A5A", "accent": "#C2185B",
                  "font_display": "Playfair Display", "font_body": "Poppins"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Anniversary sale",
                                        "headline": "Cheers to us — and to you.",
                                        "subline": "Use your Rosé gift card any time this month.",
                                        "cta_label": "See gift card", "cta_scroll_to": "gc-1"}},
            {"type": "giftcard", "props": {"template_id": "anniversary-roses", "amount": 50, "currency": "USD"}, "anchor": "gc-1"},
        ],
    },
    {
        "id": "electric",
        "name": "Electric",
        "aesthetic": "futuristic gradient, tech-forward",
        "theme": {"bg": "#000000", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#00F5FF",
                  "font_display": "Space Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Product launch",
                                        "headline": "Something new is live.",
                                        "subline": "First 100 buyers get 30% off with the coupon below.",
                                        "cta_label": "Get 30% off", "cta_scroll_to": "coupon-1"}},
            {"type": "coupon", "props": {"coupon_code": "", "label": "Launch coupon", "style": "electric"}, "anchor": "coupon-1"},
            {"type": "cta", "props": {"headline": "Move fast.", "cta_label": "Redeem now", "cta_scroll_to": "coupon-1"}},
        ],
    },
]


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:60] or "funnel"


def register(api, db, PUBLIC_APP_URL, now_iso, get_current_user, require_writer):

    class FunnelCreate(BaseModel):
        name: str
        template_id: Optional[str] = None
        slug: Optional[str] = None

    class BlockPatch(BaseModel):
        id: Optional[str] = None
        type: str
        props: dict
        anchor: Optional[str] = None

    class FunnelPatch(BaseModel):
        name: Optional[str] = None
        blocks: Optional[List[BlockPatch]] = None
        theme: Optional[dict] = None
        seo: Optional[dict] = None
        slug: Optional[str] = None

    class DomainSet(BaseModel):
        domain: str

    @api.get("/funnels/templates")
    async def funnel_templates():
        return {"templates": TEMPLATES}

    @api.get("/funnels")
    async def list_funnels(user: dict = Depends(get_current_user)):
        docs = await db.funnels.find(
            {"workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"_id": 0}).sort("created_at", -1).to_list(200)
        return docs

    @api.post("/funnels")
    async def create_funnel(body: FunnelCreate, user: dict = Depends(get_current_user)):
        require_writer(user)
        tpl = next((t for t in TEMPLATES if t["id"] == body.template_id), None) if body.template_id else None
        slug = body.slug or _slugify(body.name)
        # ensure unique slug within workspace
        while await db.funnels.find_one({"workspace_id": user["workspace_id"], "slug": slug}):
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        blocks = []
        for i, b in enumerate((tpl or {}).get("blocks", [])):
            blocks.append({"id": str(uuid.uuid4()), "type": b["type"], "props": b["props"],
                           "anchor": b.get("anchor")})
        doc = {
            "id": str(uuid.uuid4()),
            "workspace_id": user["workspace_id"],
            "name": body.name,
            "slug": slug,
            "template_id": body.template_id,
            "blocks": blocks,
            "theme": (tpl or {}).get("theme", {"bg": "#0A0A0A", "fg": "#FFFFFF", "accent": "#CCFF00",
                                                "font_display": "Cabinet Grotesk", "font_body": "Inter"}),
            "seo": {"title": body.name, "description": ""},
            "custom_domain": None,
            "domain_verified": False,
            "published": False,
            "views": 0,
            "created_by": user["id"],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "is_deleted": False,
        }
        await db.funnels.insert_one({**doc})
        return {**{k: v for k, v in doc.items() if k != "_id"}}

    @api.get("/funnels/{fid}")
    async def get_funnel(fid: str, user: dict = Depends(get_current_user)):
        d = await db.funnels.find_one(
            {"id": fid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"_id": 0})
        if not d: raise HTTPException(404, "Not found")
        return d

    @api.put("/funnels/{fid}")
    async def update_funnel(fid: str, body: FunnelPatch, user: dict = Depends(get_current_user)):
        require_writer(user)
        upd = {"updated_at": now_iso()}
        if body.name is not None: upd["name"] = body.name
        if body.slug is not None: upd["slug"] = _slugify(body.slug)
        if body.theme is not None: upd["theme"] = body.theme
        if body.seo is not None: upd["seo"] = body.seo
        if body.blocks is not None:
            upd["blocks"] = [{"id": b.id or str(uuid.uuid4()), "type": b.type,
                              "props": b.props, "anchor": b.anchor} for b in body.blocks]
        r = await db.funnels.update_one(
            {"id": fid, "workspace_id": user["workspace_id"]}, {"$set": upd})
        if r.matched_count == 0: raise HTTPException(404, "Not found")
        return {"ok": True}

    @api.post("/funnels/{fid}/publish")
    async def publish_funnel(fid: str, user: dict = Depends(get_current_user), request: Request = None):
        require_writer(user)
        d = await db.funnels.find_one({"id": fid, "workspace_id": user["workspace_id"]})
        if not d: raise HTTPException(404, "Not found")
        await db.funnels.update_one({"id": fid}, {"$set": {
            "published": True, "published_at": now_iso(), "updated_at": now_iso()}})
        base = (PUBLIC_APP_URL or "").rstrip("/")
        if not base and request is not None:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            host = request.headers.get("x-forwarded-host") or request.headers.get("host")
            base = f"{proto}://{host}"
        return {
            "published": True,
            "public_url": f"{base}/f/{d['slug']}" if base else f"/f/{d['slug']}",
            "custom_domain_url": f"https://{d['custom_domain']}" if d.get("custom_domain") else None,
        }

    @api.post("/funnels/{fid}/unpublish")
    async def unpublish_funnel(fid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.funnels.update_one(
            {"id": fid, "workspace_id": user["workspace_id"]},
            {"$set": {"published": False, "updated_at": now_iso()}})
        if r.matched_count == 0: raise HTTPException(404, "Not found")
        return {"ok": True}

    @api.delete("/funnels/{fid}")
    async def delete_funnel(fid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        r = await db.funnels.update_one(
            {"id": fid, "workspace_id": user["workspace_id"]},
            {"$set": {"is_deleted": True, "deleted_at": now_iso()}})
        if r.matched_count == 0: raise HTTPException(404, "Not found")
        return {"ok": True}

    def _cloudflare_ready():
        return bool(os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ZONE_ID"))

    async def _cloudflare_provision(domain: str, funnel_id: str):
        """Call Cloudflare-for-SaaS Custom Hostnames API to enroll the domain and issue SSL.
        Returns (cf_id, verification_status). Requires CLOUDFLARE_API_TOKEN + CLOUDFLARE_ZONE_ID env.
        """
        import requests as _rq
        token = os.environ["CLOUDFLARE_API_TOKEN"]
        zone = os.environ["CLOUDFLARE_ZONE_ID"]
        r = _rq.post(
            f"https://api.cloudflare.com/client/v4/zones/{zone}/custom_hostnames",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"hostname": domain,
                  "ssl": {"method": "http", "type": "dv",
                          "settings": {"http2": "on", "min_tls_version": "1.2"}},
                  "custom_metadata": {"funnel_id": funnel_id, "source": "promoos"}},
            timeout=30)
        if r.status_code >= 400:
            errs = r.json().get("errors", []) if r.headers.get("content-type", "").startswith("application/json") else []
            msg = "; ".join(str(e.get("message", "")) for e in errs) or r.text[:200]
            raise HTTPException(502, f"Cloudflare error: {msg}")
        data = r.json().get("result") or {}
        return data.get("id"), data.get("status", "pending")

    @api.post("/funnels/{fid}/domain")
    async def set_custom_domain(fid: str, body: DomainSet, user: dict = Depends(get_current_user)):
        require_writer(user)
        domain = body.domain.lower().strip().rstrip("/")
        if not re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$", domain):
            raise HTTPException(400, "Invalid domain format")
        other = await db.funnels.find_one({"custom_domain": domain, "id": {"$ne": fid}})
        if other:
            raise HTTPException(409, "Domain is already in use by another funnel")
        upd = {"custom_domain": domain, "domain_verified": False, "updated_at": now_iso()}
        # If Cloudflare-for-SaaS is configured, enroll the hostname immediately and let CF handle SSL.
        cf_status = None
        if _cloudflare_ready():
            try:
                cf_id, cf_status = await _cloudflare_provision(domain, fid)
                upd["cloudflare_hostname_id"] = cf_id
                upd["cloudflare_status"] = cf_status
            except HTTPException:
                raise
            except Exception as e:
                # non-fatal; user can still add DNS manually.
                upd["cloudflare_error"] = str(e)[:200]
        r = await db.funnels.update_one(
            {"id": fid, "workspace_id": user["workspace_id"]}, {"$set": upd})
        if r.matched_count == 0: raise HTTPException(404, "Not found")
        return {
            "domain": domain,
            "cloudflare_enrolled": bool(cf_status),
            "cloudflare_status": cf_status,
            "verification": {
                "cname": {"host": domain,
                          "value": "funnels.promoos.app" if not _cloudflare_ready() else "cname.promoos.app",
                          "note": ("Cloudflare-for-SaaS is enrolling your hostname. Add this CNAME and SSL will be issued automatically." if _cloudflare_ready()
                                    else "Point your domain's CNAME to funnels.promoos.app — SSL is provisioned once verified.")},
                "txt":   {"host": f"_promoos-verify.{domain}", "value": fid,
                          "note": "Add this TXT record to prove ownership."}
            }
        }

    @api.post("/funnels/{fid}/verify-domain")
    async def verify_domain(fid: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        d = await db.funnels.find_one({"id": fid, "workspace_id": user["workspace_id"]})
        if not d: raise HTTPException(400, "Not found") if False else HTTPException(404, "Not found")
        if not d.get("custom_domain"): raise HTTPException(400, "No custom domain set")
        fid_str = fid
        # If Cloudflare-for-SaaS is configured, poll the custom-hostname status.
        if _cloudflare_ready() and d.get("cloudflare_hostname_id"):
            import requests as _rq
            token = os.environ["CLOUDFLARE_API_TOKEN"]
            zone = os.environ["CLOUDFLARE_ZONE_ID"]
            try:
                r = _rq.get(
                    f"https://api.cloudflare.com/client/v4/zones/{zone}/custom_hostnames/{d['cloudflare_hostname_id']}",
                    headers={"Authorization": f"Bearer {token}"}, timeout=15)
                r.raise_for_status()
                res = r.json().get("result") or {}
                cf_status = res.get("status", "pending")
                ssl_status = (res.get("ssl") or {}).get("status", "pending")
                verified = cf_status == "active" and ssl_status == "active"
                await db.funnels.update_one({"id": fid},
                    {"$set": {"domain_verified": verified,
                              "cloudflare_status": cf_status,
                              "cloudflare_ssl_status": ssl_status,
                              "domain_verified_at": now_iso() if verified else None}})
                return {"verified": verified, "cloudflare_status": cf_status, "ssl_status": ssl_status,
                        "note": ("Domain is live with SSL." if verified
                                  else f"Cloudflare status: {cf_status}, SSL: {ssl_status}. Add the CNAME and re-check in a few minutes.")}
            except Exception as e:
                # fall through to DNS-only verification
                pass
        # Attempt DNS TXT lookup (best-effort).
        verified = False
        try:
            import dns.resolver
            answers = dns.resolver.resolve(f"_promoos-verify.{d['custom_domain']}", "TXT",
                                           lifetime=5.0)
            for a in answers:
                for s in a.strings:
                    txt_value = s.decode() if isinstance(s, bytes) else s
                    if fid_str in txt_value:
                        verified = True
                        break
                if verified: break
        except Exception:
            verified = False
        await db.funnels.update_one(
            {"id": fid},
            {"$set": {"domain_verified": verified, "domain_verified_at": now_iso() if verified else None}})
        return {"verified": verified,
                "note": "DNS propagation can take up to 48h. Retry after adding the TXT record." if not verified else "Domain verified! SSL will be provisioned within a few minutes."}

    @api.get("/public/f/{slug}")
    async def public_funnel(slug: str):
        d = await db.funnels.find_one(
            {"slug": slug, "published": True, "is_deleted": {"$ne": True}},
            {"_id": 0, "workspace_id": 0, "created_by": 0})
        if not d: raise HTTPException(404, "Funnel not found or unpublished")
        # increment view count (fire-and-forget best-effort)
        try:
            await db.funnels.update_one({"slug": slug}, {"$inc": {"views": 1}})
        except Exception:
            pass
        # hydrate coupon/gift-card blocks with real data (workspace-scoped for tenant isolation)
        workspace_id = d.get("workspace_id")
        for block in d.get("blocks", []):
            if block["type"] == "coupon":
                code = (block.get("props") or {}).get("coupon_code")
                if code:
                    # Scope coupon lookup to the funnel's own workspace to prevent cross-tenant leaks.
                    c = await db.coupons.find_one({"code": code, "workspace_id": workspace_id},
                                                    {"_id": 0, "workspace_id": 0})
                    if c: block["props"]["coupon"] = c
            elif block["type"] == "giftcard":
                tid = (block.get("props") or {}).get("template_id")
                if tid:
                    from routers.giftcards import TEMPLATES as GC_TEMPLATES
                    tpl = next((t for t in GC_TEMPLATES if t["id"] == tid), None)
                    if tpl: block["props"]["template"] = tpl
        # drop workspace_id from response (not part of public payload)
        d.pop("workspace_id", None)
        return d
