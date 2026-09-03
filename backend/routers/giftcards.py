"""Gift Card Studio — 20 luxury design templates + AI Copilot regeneration.
Each template describes visual props consumed by the frontend renderer/editor.
"""
import uuid, os, base64, io, json
from typing import Optional, List
from fastapi import HTTPException, Depends
from pydantic import BaseModel


TEMPLATES = [
    # Luxury / Premium
    {"id":"midnight-onyx","name":"Midnight Onyx","category":"luxury",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#0A0A0A 0%,#1A1A1A 60%,#2B2B2B 100%)"},
     "accent":"#CCFF00","font":"Cabinet Grotesk","text_color":"#FFFFFF",
     "headline":"To someone remarkable","subline":"A little something, from the heart.",
     "pattern":"grain"},
    {"id":"champagne-gold","name":"Champagne Gold","category":"luxury",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#3A2E12 0%,#8B6914 50%,#D4AF37 100%)"},
     "accent":"#FFF8DC","font":"Playfair Display","text_color":"#FFFFFF",
     "headline":"Because you sparkle","subline":"Celebrate in style.","pattern":"foil"},
    {"id":"velvet-rouge","name":"Velvet Rouge","category":"luxury",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#2B0A0F 0%,#6B0F19 50%,#B01930 100%)"},
     "accent":"#FFD700","font":"Playfair Display","text_color":"#FFFFFF",
     "headline":"Made with love","subline":"Redeem when the moment is right.","pattern":"velvet"},
    {"id":"emerald-noir","name":"Emerald Noir","category":"luxury",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#04231A 0%,#0F5E43 60%,#1FB07E 100%)"},
     "accent":"#F5F5DC","font":"Cabinet Grotesk","text_color":"#FFFFFF",
     "headline":"A gift of good taste","subline":"For the discerning.","pattern":"marble"},
    {"id":"platinum-mist","name":"Platinum Mist","category":"luxury",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#E5E4E2 0%,#B8B8B8 60%,#7A7A7A 100%)"},
     "accent":"#0A0A0A","font":"Playfair Display","text_color":"#0A0A0A",
     "headline":"Timeless","subline":"Yours to spend, however you please.","pattern":"metallic"},
    # Occasions
    {"id":"birthday-neon","name":"Birthday Neon","category":"birthday",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#FF006E 0%,#8338EC 50%,#3A86FF 100%)"},
     "accent":"#FFBE0B","font":"Poppins","text_color":"#FFFFFF",
     "headline":"Happy Birthday!","subline":"Go make magic. 🎉","pattern":"confetti"},
    {"id":"birthday-pastel","name":"Birthday Pastel","category":"birthday",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#FDE2E4 0%,#FAD2E1 50%,#E2ECE9 100%)"},
     "accent":"#8E44AD","font":"Poppins","text_color":"#2C2C2C",
     "headline":"Happy Birthday","subline":"Wishing you a beautiful day.","pattern":"balloons"},
    {"id":"holiday-frost","name":"Holiday Frost","category":"holiday",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#0F2027 0%,#203A43 50%,#2C5364 100%)"},
     "accent":"#E8F1F2","font":"Playfair Display","text_color":"#FFFFFF",
     "headline":"Season's greetings","subline":"May your holidays sparkle.","pattern":"snow"},
    {"id":"holiday-warmth","name":"Holiday Warmth","category":"holiday",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#8B0000 0%,#B22222 50%,#DAA520 100%)"},
     "accent":"#FFFFF0","font":"Playfair Display","text_color":"#FFFFFF",
     "headline":"Warmest wishes","subline":"For someone who deserves the world.","pattern":"garland"},
    {"id":"anniversary-roses","name":"Anniversary Roses","category":"anniversary",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#8E354A 0%,#C0392B 50%,#F08080 100%)"},
     "accent":"#F5F5F5","font":"Playfair Display","text_color":"#FFFFFF",
     "headline":"Cheers to us","subline":"Another year of you and me.","pattern":"roses"},
    # Minimalist
    {"id":"minimal-ivory","name":"Minimal Ivory","category":"minimalist",
     "background":{"type":"solid","value":"#FAF7F0"},
     "accent":"#0A0A0A","font":"Cabinet Grotesk","text_color":"#0A0A0A",
     "headline":"Just for you","subline":"—","pattern":"none"},
    {"id":"minimal-charcoal","name":"Minimal Charcoal","category":"minimalist",
     "background":{"type":"solid","value":"#141414"},
     "accent":"#CCFF00","font":"Cabinet Grotesk","text_color":"#FFFFFF",
     "headline":"A little something","subline":"—","pattern":"none"},
    {"id":"minimal-blueprint","name":"Minimal Blueprint","category":"minimalist",
     "background":{"type":"solid","value":"#F5F5F5"},
     "accent":"#005CEE","font":"Inter","text_color":"#0A0A0A",
     "headline":"For you","subline":"Redeem anytime.","pattern":"grid"},
    # Corporate / B2B
    {"id":"corporate-slate","name":"Corporate Slate","category":"corporate",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#1E293B 0%,#334155 60%,#475569 100%)"},
     "accent":"#22D3EE","font":"Inter","text_color":"#FFFFFF",
     "headline":"Thank you for your partnership","subline":"With appreciation from the team.","pattern":"none"},
    {"id":"corporate-white","name":"Corporate White","category":"corporate",
     "background":{"type":"solid","value":"#FFFFFF"},
     "accent":"#0F172A","font":"Inter","text_color":"#0F172A",
     "headline":"With appreciation","subline":"A small token from the team.","pattern":"none"},
    # Playful
    {"id":"playful-citrus","name":"Playful Citrus","category":"playful",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#FFE066 0%,#FFA630 50%,#FF6B35 100%)"},
     "accent":"#2A1A00","font":"Poppins","text_color":"#2A1A00",
     "headline":"Sunshine, packaged","subline":"On me.","pattern":"citrus"},
    {"id":"playful-berry","name":"Playful Berry","category":"playful",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#7209B7 0%,#F72585 50%,#B5179E 100%)"},
     "accent":"#FFEB3B","font":"Poppins","text_color":"#FFFFFF",
     "headline":"Because you're a treat","subline":"Enjoy.","pattern":"sprinkles"},
    # Nature
    {"id":"nature-forest","name":"Nature Forest","category":"nature",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#1B4332 0%,#2D6A4F 50%,#52B788 100%)"},
     "accent":"#F1FAEE","font":"Playfair Display","text_color":"#FFFFFF",
     "headline":"A moment for you","subline":"Breathe. Enjoy. Repeat.","pattern":"leaves"},
    {"id":"nature-sunset","name":"Nature Sunset","category":"nature",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#FF6E7F 0%,#FEB47B 50%,#FDCB6E 100%)"},
     "accent":"#4A2545","font":"Playfair Display","text_color":"#4A2545",
     "headline":"Golden hour, all yours","subline":"Whenever you need it.","pattern":"gradient"},
    # Bold
    {"id":"bold-electric","name":"Bold Electric","category":"bold",
     "background":{"type":"gradient","value":"linear-gradient(135deg,#000000 0%,#005CEE 50%,#00F5FF 100%)"},
     "accent":"#CCFF00","font":"Cabinet Grotesk","text_color":"#FFFFFF",
     "headline":"Turn it up","subline":"Full-volume gifting.","pattern":"circuit"},
]


def register(api, db, EMERGENT_LLM_KEY, now_iso, get_current_user, require_writer):

    @api.get("/giftcard-templates")
    async def list_templates():
        return {"templates": TEMPLATES, "categories": sorted({t["category"] for t in TEMPLATES})}

    @api.get("/giftcard-templates/{tid}")
    async def get_template(tid: str):
        t = next((x for x in TEMPLATES if x["id"] == tid), None)
        if not t: raise HTTPException(404, "Template not found")
        return t

    class GiftCardDesignIn(BaseModel):
        template_id: str
        amount: float
        currency: str = "USD"
        recipient_name: Optional[str] = None
        recipient_email: Optional[str] = None
        headline: Optional[str] = None
        subline: Optional[str] = None
        message: Optional[str] = None
        logo_url: Optional[str] = None
        background_override: Optional[dict] = None
        accent_override: Optional[str] = None
        font_override: Optional[str] = None
        code: Optional[str] = None

    @api.post("/giftcards/design")
    async def create_gift_card_design(body: GiftCardDesignIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        tpl = next((x for x in TEMPLATES if x["id"] == body.template_id), None)
        if not tpl: raise HTTPException(400, "Unknown template")
        code = (body.code or f"GC-{uuid.uuid4().hex[:8].upper()}").upper()
        doc = {
            "id": str(uuid.uuid4()),
            "workspace_id": user["workspace_id"],
            "code": code,
            "amount": float(body.amount),
            "currency": body.currency,
            "balance": float(body.amount),
            "status": "active",
            "template_id": body.template_id,
            "design": {
                "headline": body.headline or tpl["headline"],
                "subline": body.subline or tpl["subline"],
                "background": body.background_override or tpl["background"],
                "accent": body.accent_override or tpl["accent"],
                "text_color": tpl.get("text_color", "#FFFFFF"),
                "font": body.font_override or tpl["font"],
                "pattern": tpl.get("pattern", "none"),
                "logo_url": body.logo_url,
            },
            "recipient_name": body.recipient_name,
            "recipient_email": body.recipient_email,
            "message": body.message,
            "created_by": user["id"],
            "created_at": now_iso(),
        }
        await db.gift_cards.insert_one({**doc})
        return {**{k: v for k, v in doc.items() if k != "_id"}}

    @api.get("/giftcards/designs")
    async def list_gift_card_designs(user: dict = Depends(get_current_user)):
        docs = await db.gift_cards.find(
            {"workspace_id": user["workspace_id"], "template_id": {"$exists": True}},
            {"_id": 0}
        ).sort("created_at", -1).to_list(200)
        return docs

    class RegenIn(BaseModel):
        field: str  # "headline" | "subline" | "message" | "background" | "image_bg"
        prompt: Optional[str] = None
        template_id: Optional[str] = None
        current_headline: Optional[str] = None
        current_subline: Optional[str] = None
        tone: Optional[str] = "warm, premium, gift-worthy"
        occasion: Optional[str] = None

    @api.post("/giftcards/regenerate")
    async def giftcard_regenerate(body: RegenIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        if not EMERGENT_LLM_KEY:
            raise HTTPException(501, "EMERGENT_LLM_KEY not configured")
        # Per-workspace rate limit — 30 AI regens per rolling hour. Image regens count 3x (nano-banana is pricier).
        from datetime import datetime, timezone, timedelta
        cost = 3 if body.field in ("background", "image_bg") else 1
        window_start = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        used = await db.llm_usage.aggregate([
            {"$match": {"workspace_id": user["workspace_id"], "at": {"$gte": window_start}}},
            {"$group": {"_id": None, "total": {"$sum": "$cost"}}},
        ]).to_list(1)
        used_amt = (used[0]["total"] if used else 0)
        LIMIT = 30
        if used_amt + cost > LIMIT:
            raise HTTPException(429, f"AI rate limit reached: {used_amt}/{LIMIT} credits used in the last hour. Wait a few minutes and try again.")
        await db.llm_usage.insert_one({
            "workspace_id": user["workspace_id"], "user_id": user["id"],
            "field": body.field, "cost": cost, "at": now_iso(),
        })
        field = body.field
        if field in ("headline", "subline", "message"):
            # Use Emergent LLM text (Claude sonnet-5) via emergentintegrations
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
            except Exception as e:
                raise HTTPException(502, f"emergentintegrations not installed: {e}")
            spec = {"headline": "a punchy 4-6 word gift-card headline",
                    "subline": "a warm 8-14 word gift-card subline that pairs with the headline",
                    "message": "a personal gift-card message of 20-40 words, warm and specific"}[field]
            prompt_ctx = f"Tone: {body.tone or 'premium'}. Occasion: {body.occasion or 'general gifting'}."
            if body.current_headline: prompt_ctx += f" Current headline: {body.current_headline!r}."
            if body.current_subline:  prompt_ctx += f" Current subline: {body.current_subline!r}."
            if body.prompt: prompt_ctx += f" User note: {body.prompt}."
            chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"gc-{uuid.uuid4()}",
                           system_message="You are a luxury brand copywriter for premium gift cards. Return ONLY the text, no quotes or explanation.").with_model("anthropic", "claude-sonnet-4-5-20250929")
            try:
                resp = await chat.send_message(UserMessage(text=f"Write {spec}. {prompt_ctx}"))
                return {"field": field, "value": (resp or "").strip().strip('"').strip("'")}
            except Exception as e:
                raise HTTPException(502, f"AI copy failed: {e}")
        elif field in ("background", "image_bg"):
            # Use Emergent Gemini nano-banana image generation via LlmChat multimodal
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
            except Exception as e:
                raise HTTPException(502, f"emergentintegrations not installed: {e}")
            desc = body.prompt or "abstract luxury gift-card background, soft gradient, premium, cinematic"
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"gc-img-{uuid.uuid4()}",
                system_message="You generate premium gift-card background artwork.",
            )
            chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
            prompt_text = (
                f"Gift card background art: {desc}. Widescreen 3:2 aspect, "
                "no text, no letters, tasteful, cinematic, premium, high quality."
            )
            try:
                _text, images = await chat.send_message_multimodal_response(UserMessage(text=prompt_text))
                if not images:
                    raise HTTPException(502, "No image returned")
                img = images[0]
                data_url = f"data:{img.get('mime_type', 'image/png')};base64,{img['data']}"
                return {"field": field, "value": {"type": "image", "value": data_url}}
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(502, f"AI image failed: {e}")
        else:
            raise HTTPException(400, f"Unknown field: {field}")
