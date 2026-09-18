"""Curated newsletter starter templates — inspired by Beehiiv's template library.

Each template contains a full post scaffold (title + subtitle + blocks) so
merchants can pick one, click "Use", and immediately have a well-structured
draft to customize instead of starting from an empty page.

To add a new template: append to TEMPLATES with a unique id.
"""

TEMPLATES = [
    {
        "id": "welcome_series",
        "name": "Welcome to the family",
        "category": "onboarding",
        "description": "Warm welcome for brand-new subscribers with your story + a first-order coupon slot.",
        "preview_emoji": "👋",
        "accent": "#CCFF00",
        "post": {
            "title": "Welcome to the family 👋",
            "subtitle": "You're in — here's what to expect (plus a little thank-you inside).",
            "blocks": [
                {"type": "heading", "props": {"level": "h2", "text": "Hey, so glad you're here"}},
                {"type": "text", "props": {"text": "We started this brand because we couldn't find what we were looking for. Now, you get a front-row seat to every drop, story, and exclusive we send out."}},
                {"type": "coupon", "props": {"code": "WELCOME10", "cta": "Redeem your welcome gift"}},
                {"type": "heading", "props": {"level": "h3", "text": "What to expect from us"}},
                {"type": "text", "props": {"text": "Two emails a month, tops. Never spam. Always a story, a drop, or a limited perk you won't find on the site."}},
                {"type": "button", "props": {"label": "Explore the collection", "url": "https://example.com/shop"}},
                {"type": "divider", "props": {}},
                {"type": "referral_cta", "props": {}},
            ],
        },
    },
    {
        "id": "product_drop",
        "name": "Product drop announcement",
        "category": "commerce",
        "description": "Announce a new collection with hero image, story, and prominent CTA. Great for launches.",
        "preview_emoji": "🚀",
        "accent": "#F472B6",
        "post": {
            "title": "It's here: the [Name] drop",
            "subtitle": "Six months in the making. Available Friday at 9 AM.",
            "blocks": [
                {"type": "image", "props": {"url": "", "alt": "Hero image of the drop"}},
                {"type": "heading", "props": {"level": "h1", "text": "The [Name] drop"}},
                {"type": "text", "props": {"text": "We rebuilt this from the ground up. New fabric, new fit, same obsession with the details you can only feel in your hands."}},
                {"type": "heading", "props": {"level": "h3", "text": "What's inside"}},
                {"type": "text", "props": {"text": "• Three colorways, launch-exclusive\n• Sizes XS–XXL\n• Ships in recycled packaging\n• Limited to 500 units"}},
                {"type": "button", "props": {"label": "Shop the drop", "url": "https://example.com/drop"}},
                {"type": "divider", "props": {}},
                {"type": "text", "props": {"text": "Not into this one? Reply and tell us what you'd want next — we read every message."}},
            ],
        },
    },
    {
        "id": "flash_sale",
        "name": "Flash sale — 48 hours",
        "category": "commerce",
        "description": "Urgent, coupon-forward layout for time-boxed promotions. Punchy copy + clear discount.",
        "preview_emoji": "⚡",
        "accent": "#F97316",
        "post": {
            "title": "48 hours only: 25% off everything",
            "subtitle": "Our biggest offer of the season. Ends Sunday midnight.",
            "blocks": [
                {"type": "heading", "props": {"level": "h1", "text": "25% off everything, everywhere"}},
                {"type": "text", "props": {"text": "No exclusions, no tiny print. Every color, every size, every category. Just use the code below at checkout."}},
                {"type": "coupon", "props": {"code": "FLASH25", "cta": "Copy code & shop"}},
                {"type": "heading", "props": {"level": "h3", "text": "Why now?"}},
                {"type": "text", "props": {"text": "We overbought for a launch that got delayed. Our loss, your gain. Grab what you've been eyeing before it's gone."}},
                {"type": "button", "props": {"label": "Shop the sale", "url": "https://example.com/sale"}},
            ],
        },
    },
    {
        "id": "weekly_digest",
        "name": "Weekly digest",
        "category": "content",
        "description": "Editorial-style roundup with three story slots. Perfect for content-led brands.",
        "preview_emoji": "📰",
        "accent": "#005CEE",
        "post": {
            "title": "This week: three things worth reading",
            "subtitle": "Your Sunday digest of what we've been making, thinking, and shipping.",
            "blocks": [
                {"type": "heading", "props": {"level": "h2", "text": "1. The behind-the-scenes"}},
                {"type": "text", "props": {"text": "Every product starts with a story. This week we're pulling back the curtain on how we source our materials — and why it matters."}},
                {"type": "button", "props": {"label": "Read the story", "url": "https://example.com/story-1"}},
                {"type": "divider", "props": {}},
                {"type": "heading", "props": {"level": "h2", "text": "2. What we're loving"}},
                {"type": "text", "props": {"text": "A collection of things we've been reading, listening to, and stealing ideas from. Consider this our internal Slack, publicly leaked."}},
                {"type": "divider", "props": {}},
                {"type": "heading", "props": {"level": "h2", "text": "3. Reader question"}},
                {"type": "text", "props": {"text": "'How do you decide what to make next?' Great question. The short answer: we listen to you. The long answer is coming next week."}},
                {"type": "referral_cta", "props": {}},
            ],
        },
    },
    {
        "id": "abandoned_cart",
        "name": "You left something behind",
        "category": "commerce",
        "description": "Gentle nudge for abandoned carts with a soft discount to close the loop.",
        "preview_emoji": "🛒",
        "accent": "#8B5CF6",
        "post": {
            "title": "Still thinking about it?",
            "subtitle": "We saved your cart. Here's a little something to help you decide.",
            "blocks": [
                {"type": "heading", "props": {"level": "h2", "text": "Your cart is waiting"}},
                {"type": "text", "props": {"text": "Life gets in the way — we get it. Your cart is still here whenever you're ready. And if it's the price giving you pause, we've got you."}},
                {"type": "coupon", "props": {"code": "COMEBACK10", "cta": "Save 10% and check out"}},
                {"type": "button", "props": {"label": "Return to your cart", "url": "https://example.com/cart"}},
                {"type": "text", "props": {"text": "Not the right time? Totally fine. We'll be here whenever you are."}},
            ],
        },
    },
    {
        "id": "gift_guide",
        "name": "Holiday gift guide",
        "category": "seasonal",
        "description": "Curated seasonal gift guide with categories. Ideal for Q4 and gifting moments.",
        "preview_emoji": "🎁",
        "accent": "#EF4444",
        "post": {
            "title": "The 2026 gift guide is here",
            "subtitle": "13 hand-picked ideas from under $20 to under-the-tree impressive.",
            "blocks": [
                {"type": "heading", "props": {"level": "h1", "text": "Gifts they'll actually keep"}},
                {"type": "text", "props": {"text": "We spent three weeks debating this list so you don't have to. Every pick tested, wrapped, and rated by our team. Categorized by budget."}},
                {"type": "heading", "props": {"level": "h3", "text": "Under $25"}},
                {"type": "text", "props": {"text": "For the coworker who returns everything. Small, thoughtful, universally loved."}},
                {"type": "heading", "props": {"level": "h3", "text": "Under $75"}},
                {"type": "text", "props": {"text": "The sweet spot. Genuinely nice, not budget-busting."}},
                {"type": "heading", "props": {"level": "h3", "text": "Splurge picks"}},
                {"type": "text", "props": {"text": "For the person you actually love enough to spoil."}},
                {"type": "button", "props": {"label": "Browse the full guide", "url": "https://example.com/gift-guide"}},
                {"type": "divider", "props": {}},
                {"type": "giftcard", "props": {}},
            ],
        },
    },
    {
        "id": "announcement",
        "name": "Big news",
        "category": "brand",
        "description": "Simple, story-first layout for major brand announcements — funding, rebrands, milestones.",
        "preview_emoji": "📣",
        "accent": "#10B981",
        "post": {
            "title": "We have big news to share",
            "subtitle": "A letter from the founders about where we're headed next.",
            "blocks": [
                {"type": "heading", "props": {"level": "h1", "text": "Where we're headed next"}},
                {"type": "text", "props": {"text": "When we started this brand three years ago, we had one goal: to build something we'd be proud to hand our kids. Today, we're taking the biggest step yet toward that vision."}},
                {"type": "heading", "props": {"level": "h3", "text": "What's changing"}},
                {"type": "text", "props": {"text": "The tl;dr — we're growing, we're doubling down on what you love, and we're keeping everything that makes us us."}},
                {"type": "heading", "props": {"level": "h3", "text": "What stays the same"}},
                {"type": "text", "props": {"text": "The people, the product, the promise. All of it. You're the reason we're here."}},
                {"type": "text", "props": {"text": "— The founders"}},
                {"type": "divider", "props": {}},
                {"type": "referral_cta", "props": {}},
            ],
        },
    },
    {
        "id": "reengagement",
        "name": "We've missed you",
        "category": "onboarding",
        "description": "Reactivate dormant subscribers with a soft offer + a chance to update preferences.",
        "preview_emoji": "💌",
        "accent": "#EC4899",
        "post": {
            "title": "We noticed you've been quiet",
            "subtitle": "Want to keep hearing from us? Here's a treat for saying yes.",
            "blocks": [
                {"type": "heading", "props": {"level": "h2", "text": "No hard feelings"}},
                {"type": "text", "props": {"text": "If our emails haven't been landing right for you, we get it. Inboxes are crowded. But before you slip away, we'd love one more shot."}},
                {"type": "coupon", "props": {"code": "COMEBACK20", "cta": "Yes, keep me on the list"}},
                {"type": "text", "props": {"text": "One click and you're back in — with 20% off your next order as a thank-you. No hoops, no fine print."}},
                {"type": "button", "props": {"label": "I'm in", "url": "https://example.com/reactivate"}},
                {"type": "divider", "props": {}},
                {"type": "text", "props": {"text": "Prefer to say goodbye? Totally fair — unsubscribe link is at the very bottom, no questions asked."}},
            ],
        },
    },
]


def get_template(template_id: str):
    """Return a template dict by id or None."""
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
