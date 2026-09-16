"""Seeded marketplace preset packs — installed on startup if the marketplace is empty.

Kept in its own module so a superadmin can visually diff, add, or replace packs
without touching route handlers. Insert is idempotent by pack `name` — running
seed() twice never creates duplicates.
"""
import uuid
from typing import List


MARKETPLACE_PACKS: List[dict] = [
    # ---- Coupon-scope packs ----
    {
        "name": "Luxury Retail — Coupon",
        "scope": "coupon",
        "presets": [
            {"key": "champagne-noir", "label": "Champagne Noir", "accent": "#E7CB8E",
             "prompt": "dark editorial luxury coupon banner, champagne gold accents on matte black, silk drapery texture, cinematic rim light, ultra-premium boutique, no text"},
            {"key": "porcelain-blush", "label": "Porcelain Blush", "accent": "#F4C9C0",
             "prompt": "soft porcelain blush luxury coupon banner, marble texture, powder pink and warm cream palette, editorial fashion boutique aesthetic, no text"},
            {"key": "obsidian-jade", "label": "Obsidian Jade", "accent": "#12A47D",
             "prompt": "obsidian black luxury coupon banner with polished jade green accents, art-deco linework, high-contrast fine jewellery aesthetic, no text"},
            {"key": "onyx-copper", "label": "Onyx Copper", "accent": "#B96A3C",
             "prompt": "onyx and warm copper luxury coupon banner, brushed metal texture, moody spot lighting, premium menswear boutique, no text"},
        ],
    },
    {
        "name": "Streetwear + Drop Culture — Coupon",
        "scope": "coupon",
        "presets": [
            {"key": "acid-neon", "label": "Acid Neon", "accent": "#CCFF00",
             "prompt": "acid lime neon streetwear coupon banner, hi-vis chartreuse and black, graffiti spatter texture, high-contrast urban aesthetic, no text"},
            {"key": "vaporwave", "label": "Vaporwave", "accent": "#FF3CE0",
             "prompt": "vaporwave sunset streetwear coupon banner, hot pink and cyan gradient, retro grid horizon, chrome type feel, no text"},
            {"key": "concrete-crimson", "label": "Concrete Crimson", "accent": "#DC2626",
             "prompt": "raw concrete streetwear coupon banner with slashes of crimson red spray paint, gritty industrial texture, warehouse drop energy, no text"},
            {"key": "utility-graphite", "label": "Utility Graphite", "accent": "#404040",
             "prompt": "techwear utility streetwear coupon banner, graphite and gunmetal palette, ripstop fabric texture, muted cinematic lighting, no text"},
        ],
    },
    {
        "name": "Wellness & Beauty — Coupon",
        "scope": "coupon",
        "presets": [
            {"key": "sage-sand", "label": "Sage & Sand", "accent": "#8FA582",
             "prompt": "calm wellness coupon banner, sage green and warm sand palette, soft botanical shadow, linen texture, airy natural light, no text"},
            {"key": "peach-milk", "label": "Peach Milk", "accent": "#F5B598",
             "prompt": "peach and cream beauty coupon banner, soft studio gradient, dewy skin-glow aesthetic, minimalist clean beauty, no text"},
            {"key": "rose-quartz", "label": "Rose Quartz", "accent": "#DFA6B8",
             "prompt": "rose quartz beauty coupon banner, iridescent pink-lavender crystal facets, soft-focus dreamlike lighting, no text"},
            {"key": "eucalyptus", "label": "Eucalyptus", "accent": "#6E9482",
             "prompt": "eucalyptus wellness coupon banner, deep-green leaves on stone background, spa-day serene aesthetic, no text"},
        ],
    },
    {
        "name": "Food & Beverage — Coupon",
        "scope": "coupon",
        "presets": [
            {"key": "espresso-crema", "label": "Espresso Crema", "accent": "#7A4A2B",
             "prompt": "artisan espresso café coupon banner, warm crema swirl on dark espresso brown, steam rising, cozy specialty coffee aesthetic, no text"},
            {"key": "citrus-pop", "label": "Citrus Pop", "accent": "#F59E0B",
             "prompt": "citrus splash food and beverage coupon banner, vibrant tangerine and lemon, water droplets, high-energy fresh-squeezed aesthetic, no text"},
            {"key": "burgundy-cellar", "label": "Burgundy Cellar", "accent": "#7C1E33",
             "prompt": "wine cellar coupon banner, deep burgundy and oak tannin palette, moody candlelight, premium sommelier aesthetic, no text"},
            {"key": "mint-glass", "label": "Mint & Glass", "accent": "#A7E2CD",
             "prompt": "fresh cocktail coupon banner, mint green liquid in crystal glass, cool refracted light, upscale bar aesthetic, no text"},
        ],
    },
    # ---- Gift-card packs ----
    {
        "name": "Celebration — Gift Card",
        "scope": "gift_card",
        "presets": [
            {"key": "birthday-confetti", "label": "Birthday Confetti", "accent": "#F472B6",
             "prompt": "joyful birthday gift-card background, hand-painted confetti burst in pink, gold and mint, warm bokeh sparkle, no text"},
            {"key": "anniversary-ivory", "label": "Anniversary Ivory", "accent": "#E7CB8E",
             "prompt": "romantic anniversary gift-card background, ivory silk drapery with soft champagne bokeh, warm candlelight, timeless elegant, no text"},
            {"key": "graduation-navy", "label": "Graduation Navy", "accent": "#1E3A8A",
             "prompt": "graduation gift-card background, deep navy with gold constellation lines, foil star texture, ceremonial premium, no text"},
            {"key": "wedding-blush", "label": "Wedding Blush", "accent": "#F4C9C0",
             "prompt": "wedding gift-card background, soft blush pink watercolor florals fading into ivory, hand-painted botanical, ethereal, no text"},
        ],
    },
    {
        "name": "Seasonal — Gift Card",
        "scope": "gift_card",
        "presets": [
            {"key": "winter-frost", "label": "Winter Frost", "accent": "#94B8D4",
             "prompt": "winter gift-card background, icy blue and silver frost gradient, delicate snowflakes, aurora shimmer, cinematic cold light, no text"},
            {"key": "spring-bloom", "label": "Spring Bloom", "accent": "#93C572",
             "prompt": "spring gift-card background, watercolor cherry blossoms and fresh green shoots on warm cream, hopeful morning light, no text"},
            {"key": "summer-solstice", "label": "Summer Solstice", "accent": "#FBBF24",
             "prompt": "summer solstice gift-card background, golden hour sunbeams over ocean horizon, warm coral to teal gradient, no text"},
            {"key": "autumn-ember", "label": "Autumn Ember", "accent": "#C2410C",
             "prompt": "autumn gift-card background, ember orange and deep rust leaves on warm brown, soft-focus fall foliage, cozy fireside mood, no text"},
        ],
    },
    {
        "name": "Corporate Modern — Gift Card",
        "scope": "gift_card",
        "presets": [
            {"key": "slate-mono", "label": "Slate Mono", "accent": "#525252",
             "prompt": "corporate gift-card background, sophisticated slate grey monochrome with subtle brushed-metal linework, tasteful executive premium, no text"},
            {"key": "navy-teal", "label": "Navy & Teal", "accent": "#0F766E",
             "prompt": "corporate gift-card background, deep navy with teal accent gradient, geometric grid lines, modern fintech aesthetic, no text"},
            {"key": "ivory-onyx", "label": "Ivory Onyx", "accent": "#0A0A0A",
             "prompt": "corporate gift-card background, split ivory-and-onyx composition with a single gold hairline, minimalist luxury stationery aesthetic, no text"},
            {"key": "sage-linen", "label": "Sage Linen", "accent": "#8FA582",
             "prompt": "corporate gift-card background, soft sage green linen texture with taupe accent, natural understated premium aesthetic, no text"},
        ],
    },
]


async def install_marketplace_packs(db, now_iso, logger) -> int:
    """Insert seeded packs that don't already exist. Returns count inserted."""
    inserted = 0
    for pack in MARKETPLACE_PACKS:
        existing = await db.preset_packs.find_one({"name": pack["name"]}, {"_id": 0, "id": 1})
        if existing:
            continue
        doc = {
            "id": str(uuid.uuid4()),
            "name": pack["name"],
            "scope": pack["scope"],
            "presets": pack["presets"],
            "is_public": True,
            "source": "seed",
            "created_by": "system",
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "rating_avg": 0.0,
            "rating_count": 0,
        }
        await db.preset_packs.insert_one(doc)
        inserted += 1
    if inserted:
        logger.info(f"Marketplace seed: installed {inserted} preset pack(s)")
    return inserted
