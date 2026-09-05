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
        "id": "storefront",
        "name": "Storefront",
        "aesthetic": "full product landing page — video hero, countdown, testimonials, high-conversion",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#CCFF00",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "New drop · limited stock",
                                        "headline": "The product everyone's talking about.",
                                        "subline": "Real reviews below — grab yours before the launch offer ends.",
                                        "cta_label": "Shop now", "cta_scroll_to": "product-1"}},
            {"type": "video", "props": {"url": "", "poster_url": "", "autoplay": False}},
            {"type": "countdown", "props": {"ends_at": None, "label": "Launch offer ends in",
                                             "duration_hours": 72}},
            {"type": "product", "props": {"product_id": "", "coupon_code": ""}, "anchor": "product-1"},
            {"type": "features", "props": {"title": "Why customers keep coming back",
                                            "items": [
                                                {"title": "Free shipping", "text": "On every order, worldwide."},
                                                {"title": "60-day returns", "text": "Love it or send it back."},
                                                {"title": "Lifetime warranty", "text": "We stand behind every unit."},
                                            ]}},
            {"type": "testimonial", "props": {"title": "Real customers, real reviews",
                                                "items": [
                                                    {"quote": "Blew away my expectations — worth every dollar.",
                                                     "author": "Maya R.", "role": "Verified buyer",
                                                     "avatar_url": ""},
                                                    {"quote": "Shipping was fast and the quality is unreal.",
                                                     "author": "Jordan T.", "role": "Verified buyer",
                                                     "avatar_url": ""},
                                                    {"quote": "I already ordered a second one for my sister.",
                                                     "author": "Priya K.", "role": "Verified buyer",
                                                     "avatar_url": ""},
                                                ]}},
            {"type": "faq", "props": {"items": [
                {"q": "How long does shipping take?", "a": "3-5 business days in the US, 7-14 internationally."},
                {"q": "Can I use the coupon with other offers?", "a": "The launch coupon is standalone — no stacking."},
                {"q": "What's your return policy?", "a": "60 days from delivery, no questions asked."},
            ]}},
            {"type": "cta", "props": {"headline": "Ready to grab yours?",
                                        "cta_label": "Buy now", "cta_scroll_to": "product-1"}},
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
    # --------------------------------------------------------------------------------
    # Industrial funnel templates (systeme.io-style: opt-in / webinar / launch / etc.)
    # --------------------------------------------------------------------------------
    {
        "id": "lead_magnet",
        "name": "Lead Magnet Opt-in",
        "aesthetic": "conversion-optimized single-column opt-in for a free ebook / checklist / cheatsheet",
        "theme": {"bg": "#0B0F1A", "fg": "#FFFFFF", "muted": "#94A3B8", "accent": "#3B82F6",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "logo_bar", "props": {"label": "As featured in",
                                             "logos": ["Forbes", "TechCrunch", "Wired", "Fast Company", "Inc."]}},
            {"type": "hero", "props": {"eyebrow": "Free · Instant access",
                                        "headline": "The 7-step growth playbook top founders use.",
                                        "subline": "Enter your email and we'll send the PDF to your inbox in 30 seconds.",
                                        "cta_label": "Send me the playbook", "cta_scroll_to": "optin-1"}},
            {"type": "optin", "props": {"headline": "Where should we send it?",
                                          "sub": "No spam. Unsubscribe anytime.",
                                          "cta_label": "Send it now",
                                          "fields": [{"key": "email", "label": "Email address", "required": True}],
                                          "lead_tag": "leadmagnet"}, "anchor": "optin-1"},
            {"type": "stats", "props": {"items": [
                {"value": "12,400+", "label": "Founders enrolled"},
                {"value": "4.9/5", "label": "Average rating"},
                {"value": "30 sec", "label": "To first insight"},
            ]}},
            {"type": "testimonial", "props": {"title": "What readers are saying",
                                                "items": [
                                                    {"quote": "Read it in one sitting — implemented 3 things the same day.",
                                                     "author": "Jordan T.", "role": "Founder, Kettle", "rating": 5},
                                                    {"quote": "Refreshingly practical. No fluff.",
                                                     "author": "Aisha K.", "role": "Growth Lead", "rating": 5},
                                                    {"quote": "This is what every startup needs before series A.",
                                                     "author": "Miguel V.", "role": "Angel investor", "rating": 5},
                                                ]}},
            {"type": "guarantee", "props": {"title": "100% Free. Forever.",
                                              "text": "No credit card required. Unsubscribe with one click.",
                                              "icon": "shield"}},
        ],
    },
    {
        "id": "webinar_registration",
        "name": "Webinar Registration",
        "aesthetic": "high-conversion date-locked registration page with countdown + host bio",
        "theme": {"bg": "#0A0E1A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#F97316",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Live · Thursday 2pm ET",
                                        "headline": "The 45-minute masterclass founders wait months to attend.",
                                        "subline": "Learn the exact playbook we use to book 40+ demos a week — with zero paid ads.",
                                        "cta_label": "Save my seat", "cta_scroll_to": "optin-1"}},
            {"type": "countdown", "props": {"label": "Registration closes in", "duration_hours": 48}},
            {"type": "optin", "props": {"headline": "Reserve your spot — free",
                                          "sub": "You'll get a confirmation email + a calendar invite.",
                                          "cta_label": "Register now",
                                          "fields": [
                                              {"key": "first_name", "label": "First name", "required": True},
                                              {"key": "email", "label": "Work email", "required": True},
                                          ],
                                          "lead_tag": "webinar"}, "anchor": "optin-1"},
            {"type": "features", "props": {"title": "What you'll walk away with",
                                             "items": [
                                                {"title": "The 3-message cold sequence", "text": "Verbatim scripts you can send tonight."},
                                                {"title": "How to disqualify in 2 minutes", "text": "Stop wasting cycles on bad-fit leads."},
                                                {"title": "The $0 CRM stack", "text": "Free tools that outperform paid ones."},
                                             ]}},
            {"type": "testimonial", "props": {"title": "From past attendees",
                                                "items": [
                                                    {"quote": "Booked 6 demos the week after this session. Wild ROI on 45 minutes.",
                                                     "author": "Priya K.", "role": "Founder, Loop", "rating": 5},
                                                    {"quote": "The Q&A alone was worth attending.",
                                                     "author": "Nadia R.", "role": "Sales lead", "rating": 5},
                                                ]}},
            {"type": "guarantee", "props": {"title": "Can't make it live?",
                                              "text": "Register anyway — we'll send you the replay.",
                                              "icon": "clock"}},
        ],
    },
    {
        "id": "product_launch",
        "name": "Product Launch (Long-form sales)",
        "aesthetic": "long-form sales page with pricing table, order bump, guarantee, FAQ, and upsell teaser",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#CCFF00",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "logo_bar", "props": {"label": "Trusted by teams at",
                                             "logos": ["Stripe", "Notion", "Vercel", "Linear", "Ramp"]}},
            {"type": "hero", "props": {"eyebrow": "Now available",
                                        "headline": "The tool your competitors don't want you to find.",
                                        "subline": "Everything you need to launch a store in 5 minutes — with a 30-day money-back guarantee.",
                                        "cta_label": "See pricing", "cta_scroll_to": "pricing-1"}},
            {"type": "video", "props": {"url": "", "poster_url": "", "autoplay": False}},
            {"type": "stats", "props": {"items": [
                {"value": "27,000+", "label": "Active customers"},
                {"value": "99.98%", "label": "Uptime"},
                {"value": "$2.4B", "label": "Processed"},
            ]}},
            {"type": "features", "props": {"title": "Everything included",
                                             "items": [
                                                {"title": "Unlimited coupons", "text": "Never hit a cap. Ever."},
                                                {"title": "AI Copilot", "text": "Optimizes offers hourly."},
                                                {"title": "White-label", "text": "Your domain, your brand."},
                                                {"title": "24/7 support", "text": "Real humans, avg. 4-min reply."},
                                                {"title": "Global payments", "text": "100+ methods worldwide."},
                                                {"title": "SOC 2 Type II", "text": "Enterprise-grade security."},
                                             ]}},
            {"type": "pricing_table", "props": {"title": "Simple, honest pricing",
                                                  "tiers": [
                                                      {"name": "Basic", "price": 49, "period": "mo",
                                                       "features": ["Unlimited coupons", "Email + SMS", "Public API"],
                                                       "cta_label": "Start free", "highlight": False},
                                                      {"name": "Pro", "price": 79, "period": "mo",
                                                       "features": ["Everything in Basic", "Custom domain", "Advanced analytics"],
                                                       "cta_label": "Start free", "highlight": True},
                                                  ]}, "anchor": "pricing-1"},
            {"type": "order_bump", "props": {"title": "Add: Onboarding session",
                                                "text": "60-min 1:1 with a specialist who sets everything up for you.",
                                                "price": 149, "currency": "USD",
                                                "coupon_code": ""}},
            {"type": "testimonial", "props": {"title": "What customers say",
                                                "items": [
                                                    {"quote": "Paid for itself in the first week.", "author": "Sam L.", "role": "CMO", "rating": 5},
                                                    {"quote": "Support responds in minutes, not days.", "author": "Priya K.", "role": "Founder", "rating": 5},
                                                    {"quote": "The AI Copilot alone is worth 10x the price.", "author": "Miguel V.", "role": "Head of Growth", "rating": 5},
                                                ]}},
            {"type": "guarantee", "props": {"title": "30-day money-back guarantee",
                                              "text": "If it's not right for your business, we'll refund every cent — no questions asked.",
                                              "icon": "shield"}},
            {"type": "faq", "props": {"items": [
                {"q": "Do I need a card to start?", "a": "No — first 3 days are free with no card required."},
                {"q": "Can I cancel anytime?", "a": "One-click cancel from your dashboard. No lock-ins."},
                {"q": "Do you offer refunds?", "a": "Yes — 30-day money-back, no questions asked."},
                {"q": "What payment methods do you support?", "a": "Cards, Apple Pay, Google Pay, Klarna, Afterpay, SEPA, iDEAL, and more."},
            ]}},
            {"type": "upsell", "props": {"headline": "Wait — one more thing.",
                                           "text": "Add annual billing and save 2 months. Same everything, less spend.",
                                           "cta_label": "Switch to annual",
                                           "price": 790, "currency": "USD"}},
            {"type": "cta", "props": {"headline": "Ready to launch?",
                                        "cta_label": "Get started", "cta_scroll_to": "pricing-1"}},
        ],
    },
    {
        "id": "application_funnel",
        "name": "Application / Booking Funnel",
        "aesthetic": "high-ticket qualification page — application form + scheduling teaser",
        "theme": {"bg": "#0F0F0F", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#EAB308",
                  "font_display": "Playfair Display", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "By application only",
                                        "headline": "Ready to grow past $10K/mo?",
                                        "subline": "We work with a limited number of founders each quarter. Apply below.",
                                        "cta_label": "Apply now", "cta_scroll_to": "optin-1"}},
            {"type": "features", "props": {"title": "Who this is for",
                                             "items": [
                                                {"title": "You've hit $3K+ MRR", "text": "Product-market fit is close but not consistent."},
                                                {"title": "You need a system", "text": "Not more advice — a repeatable process."},
                                                {"title": "You'll do the work", "text": "Willing to execute daily for 90 days."},
                                             ]}},
            {"type": "optin", "props": {"headline": "Apply for a strategy call",
                                          "sub": "Takes about 90 seconds. We reply within 24 hours.",
                                          "cta_label": "Submit application",
                                          "fields": [
                                              {"key": "first_name", "label": "First name", "required": True},
                                              {"key": "email", "label": "Best email", "required": True},
                                              {"key": "company", "label": "Company / product", "required": False},
                                              {"key": "mrr", "label": "Current MRR", "required": False},
                                              {"key": "goal", "label": "What's your main goal?", "type": "textarea", "required": False},
                                          ],
                                          "lead_tag": "application"}, "anchor": "optin-1"},
            {"type": "testimonial", "props": {"title": "From past clients",
                                                "items": [
                                                    {"quote": "Went from $8K to $47K MRR in 6 months.", "author": "Rina S.", "role": "Founder, Beam", "rating": 5},
                                                    {"quote": "Best money I've spent on my business.", "author": "Ahmed K.", "role": "CEO, Loop", "rating": 5},
                                                ]}},
            {"type": "guarantee", "props": {"title": "Selective, honest fit",
                                              "text": "If we're not a match, we'll tell you on the call and point you elsewhere.",
                                              "icon": "handshake"}},
        ],
    },
    {
        "id": "thankyou",
        "name": "Thank You / Confirmation",
        "aesthetic": "post-purchase or post-optin confirmation with next-step upsell",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#22C55E",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "✓ You're in",
                                        "headline": "Check your inbox in the next 2 minutes.",
                                        "subline": "We've sent you a confirmation with next steps. While you wait — here's one more thing.",
                                        "cta_label": "See the upsell", "cta_scroll_to": "upsell-1"}},
            {"type": "upsell", "props": {"headline": "Only shown once: 60% off our flagship course.",
                                           "text": "Founders who take this course convert 3.4× more leads on average.",
                                           "cta_label": "Yes, add it to my order",
                                           "price": 197, "currency": "USD"}, "anchor": "upsell-1"},
            {"type": "guarantee", "props": {"title": "Anything not right?",
                                              "text": "Reply to the confirmation email and we'll fix it within an hour.",
                                              "icon": "shield"}},
        ],
    },
    # --- Sales-focused pages ---
    {
        "id": "sales_page",
        "name": "Sales Page (short-form)",
        "aesthetic": "single-CTA short-form sales page — one product, one price, one big button",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#F97316",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "One-page offer",
                                        "headline": "The upgrade that pays for itself in a week.",
                                        "subline": "Everything you need in one clean package.",
                                        "cta_label": "Buy now — $79", "cta_scroll_to": "product-1"}},
            {"type": "product", "props": {"product_id": "", "coupon_code": ""}, "anchor": "product-1"},
            {"type": "features", "props": {"title": "What's inside",
                                             "items": [
                                                {"title": "Lifetime access", "text": "Pay once, use forever."},
                                                {"title": "Instant delivery", "text": "Access within 60 seconds."},
                                                {"title": "Free updates", "text": "Every improvement, free."},
                                             ]}},
            {"type": "guarantee", "props": {"title": "30-day money-back guarantee",
                                              "text": "Not right for you? Full refund, no questions.", "icon": "shield"}},
            {"type": "cta", "props": {"headline": "Ready to upgrade?", "cta_label": "Buy now — $79", "cta_scroll_to": "product-1"}},
        ],
    },
    {
        "id": "order_form",
        "name": "Order Form",
        "aesthetic": "checkout-style single-page order form with order bump + guarantee",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#22C55E",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Step 2 of 2",
                                        "headline": "Complete your order.",
                                        "subline": "Secure checkout · 256-bit encryption · Cancel anytime."}},
            {"type": "product", "props": {"product_id": "", "coupon_code": ""}, "anchor": "product-1"},
            {"type": "order_bump", "props": {"title": "Add: 12-month priority support",
                                                "text": "Skip the queue, get answers in minutes not days.",
                                                "price": 47, "currency": "USD"}},
            {"type": "guarantee", "props": {"title": "60-day money-back",
                                              "text": "Every purchase is protected. If it's not right, we refund.",
                                              "icon": "shield"}},
            {"type": "testimonial", "props": {"title": "Recent buyers",
                                                "items": [
                                                    {"quote": "Best $79 I ever spent.", "author": "Sam L.", "role": "Verified buyer", "rating": 5},
                                                    {"quote": "Support answered in 4 minutes. Wild.", "author": "Priya K.", "role": "Verified buyer", "rating": 5},
                                                ]}},
        ],
    },
    {
        "id": "downsell",
        "name": "Downsell (After decline)",
        "aesthetic": "second-chance page shown when a customer declines the upsell — softer offer",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#EAB308",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Wait — one more thing",
                                        "headline": "Not ready for the full package? Try this instead.",
                                        "subline": "Same core value, gentler entry point.",
                                        "cta_label": "Yes, I'll take it", "cta_scroll_to": "upsell-1"}},
            {"type": "upsell", "props": {"headline": "Starter edition · 70% off",
                                           "text": "Same product, essentials only. Perfect if you're new.",
                                           "cta_label": "Add starter to my order",
                                           "price": 29, "currency": "USD"}, "anchor": "upsell-1"},
            {"type": "features", "props": {"title": "You still get",
                                             "items": [
                                                {"title": "Core lessons", "text": "The 8 essential modules."},
                                                {"title": "Community access", "text": "Ask questions any time."},
                                                {"title": "Upgrade later", "text": "Credit toward the full package."},
                                             ]}},
            {"type": "guarantee", "props": {"title": "Same 30-day guarantee",
                                              "text": "Try it — refund if it's not for you.", "icon": "shield"}},
        ],
    },
    {
        "id": "inline_form",
        "name": "Inline Form (Embedded lead-gen)",
        "aesthetic": "minimal — just a headline + one-field opt-in, designed to embed on a blog/newsletter",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#3B82F6",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "optin", "props": {"headline": "Get one growth tip every Tuesday.",
                                          "sub": "Read by 12,400+ founders. Unsubscribe anytime.",
                                          "cta_label": "Subscribe",
                                          "fields": [{"key": "email", "label": "Your email", "required": True}],
                                          "lead_tag": "newsletter"}},
        ],
    },
    {
        "id": "popup_form",
        "name": "Popup Form",
        "aesthetic": "exit-intent style opt-in with a discount incentive",
        "theme": {"bg": "#0A0A0A", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#EC4899",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Before you go —",
                                        "headline": "Save 15% on your first order.",
                                        "subline": "Drop your email and we'll send the code instantly."}},
            {"type": "optin", "props": {"headline": "Where should we send it?",
                                          "sub": "Discount code arrives in your inbox in seconds.",
                                          "cta_label": "Send me the code",
                                          "fields": [{"key": "email", "label": "Email", "required": True}],
                                          "lead_tag": "popup_discount"}},
            {"type": "countdown", "props": {"label": "Offer expires in", "duration_hours": 24}},
        ],
    },
    {
        "id": "link_in_bio",
        "name": "Link in Bio",
        "aesthetic": "phone-vertical stack of buttons — perfect for Instagram/TikTok bios",
        "theme": {"bg": "#0F0F0F", "fg": "#FFFFFF", "muted": "#A1A1AA", "accent": "#CCFF00",
                  "font_display": "Cabinet Grotesk", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "@yourhandle",
                                        "headline": "Everything in one place.",
                                        "subline": "Products · Free tools · Weekly newsletter."}},
            {"type": "cta", "props": {"headline": "Shop the latest drop",
                                        "cta_label": "Browse products", "cta_scroll_to": "product-1"}},
            {"type": "product", "props": {"product_id": "", "coupon_code": ""}, "anchor": "product-1"},
            {"type": "cta", "props": {"headline": "Get 15% off with code WELCOME",
                                        "cta_label": "Grab the coupon", "cta_scroll_to": "coupon-1"}},
            {"type": "coupon", "props": {"coupon_code": "", "label": "Instagram exclusive"}, "anchor": "coupon-1"},
            {"type": "optin", "props": {"headline": "Join the newsletter",
                                          "sub": "One email a week. Zero fluff.",
                                          "cta_label": "Subscribe",
                                          "fields": [{"key": "email", "label": "Email", "required": True}],
                                          "lead_tag": "bio_newsletter"}},
        ],
    },
    {
        "id": "info_page",
        "name": "Info Page",
        "aesthetic": "long-form article/announcement — no product, just information & credibility",
        "theme": {"bg": "#FFFFFF", "fg": "#0A0A0A", "muted": "#525252", "accent": "#000000",
                  "font_display": "Playfair Display", "font_body": "Inter"},
        "blocks": [
            {"type": "hero", "props": {"eyebrow": "Announcement",
                                        "headline": "What's new this quarter — and what's coming next.",
                                        "subline": "A short update on where we're headed."}},
            {"type": "heading", "props": {"text": "The 3 things we shipped this quarter"}},
            {"type": "paragraph", "props": {"text": "This quarter was about depth over breadth: we picked three areas that mattered most to customers and shipped them all the way to done."}},
            {"type": "features", "props": {"title": "The updates",
                                             "items": [
                                                {"title": "Faster load times", "text": "Every page 45% faster on median device."},
                                                {"title": "Better search", "text": "Fuzzy + semantic + saved queries."},
                                                {"title": "Reliability", "text": "99.99% uptime for the past 90 days."},
                                             ]}},
            {"type": "heading", "props": {"text": "What's next"}},
            {"type": "paragraph", "props": {"text": "Q2 is about integrations. Native connectors for the tools you already use, plus a public API to build your own."}},
            {"type": "cta", "props": {"headline": "Want product updates in your inbox?", "cta_label": "Subscribe", "cta_scroll_to": "optin-1"}},
            {"type": "optin", "props": {"headline": "Product updates",
                                          "sub": "1-2 emails per quarter. Zero marketing spam.",
                                          "cta_label": "Subscribe",
                                          "fields": [{"key": "email", "label": "Email", "required": True}],
                                          "lead_tag": "product_updates"}, "anchor": "optin-1"},
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
        steps: Optional[List[dict]] = None
        variants: Optional[List[dict]] = None

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
        # For the Storefront template, try to auto-attach an existing product + coupon so the
        # merchant lands in an editor that already looks like a real product page.
        auto_product_id = ""
        auto_coupon_code = ""
        if body.template_id == "storefront":
            prod = await db.products.find_one(
                {"workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
                {"_id": 0}, sort=[("created_at", -1)])
            if prod:
                auto_product_id = prod.get("id", "")
            cpn = await db.coupons.find_one(
                {"workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}, "state": {"$ne": "archived"}},
                {"_id": 0}, sort=[("created_at", -1)])
            if cpn:
                auto_coupon_code = cpn.get("code", "")
        import datetime as _dt
        blocks = []
        for i, b in enumerate((tpl or {}).get("blocks", [])):
            props = dict(b["props"])  # shallow copy so we don't mutate the shared template
            # Countdown: resolve duration_hours into a concrete ends_at at create time.
            if b["type"] == "countdown" and not props.get("ends_at"):
                hrs = int(props.pop("duration_hours", 72) or 72)
                props["ends_at"] = (_dt.datetime.now(_dt.timezone.utc)
                                    + _dt.timedelta(hours=hrs)).isoformat()
            # Storefront auto-attach: fill the product + coupon blocks if we found any.
            if body.template_id == "storefront":
                if b["type"] == "product":
                    if auto_product_id and not props.get("product_id"):
                        props["product_id"] = auto_product_id
                    if auto_coupon_code and not props.get("coupon_code"):
                        props["coupon_code"] = auto_coupon_code
                if b["type"] == "coupon" and auto_coupon_code and not props.get("coupon_code"):
                    props["coupon_code"] = auto_coupon_code
            blocks.append({"id": str(uuid.uuid4()), "type": b["type"], "props": props,
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
        if body.steps is not None:
            # Ensure every step has id + slug_suffix + blocks; auto-assign missing ids.
            steps_clean = []
            for s in body.steps:
                sid = s.get("id") or str(uuid.uuid4())
                suffix = _slugify(s.get("slug_suffix") or s.get("name") or f"step-{len(steps_clean)+1}")
                blks = []
                for b in (s.get("blocks") or []):
                    blks.append({"id": b.get("id") or str(uuid.uuid4()),
                                 "type": b.get("type"), "props": b.get("props") or {},
                                 "anchor": b.get("anchor")})
                steps_clean.append({"id": sid, "name": s.get("name") or "Untitled step",
                                    "slug_suffix": suffix, "blocks": blks})
            upd["steps"] = steps_clean
        if body.variants is not None:
            variants_clean = []
            for v in body.variants:
                vid = v.get("id") or str(uuid.uuid4())
                weight = max(0, int(v.get("weight") or 1))
                blks = []
                for b in (v.get("blocks") or []):
                    blks.append({"id": b.get("id") or str(uuid.uuid4()),
                                 "type": b.get("type"), "props": b.get("props") or {},
                                 "anchor": b.get("anchor")})
                variants_clean.append({"id": vid, "name": v.get("name") or f"Variant {len(variants_clean)+1}",
                                       "weight": weight, "blocks": blks})
            upd["variants"] = variants_clean
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
        if not d: raise HTTPException(404, "Not found")
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

    async def _hydrate_blocks(blocks, workspace_id):
        """Hydrate coupon/giftcard/product/testimonial blocks with real workspace-scoped data.
        Extracted so multi-step funnels can hydrate each step's blocks independently."""
        for block in blocks:
            if block["type"] == "coupon":
                code = (block.get("props") or {}).get("coupon_code")
                if code:
                    c = await db.coupons.find_one({"code": code, "workspace_id": workspace_id},
                                                    {"_id": 0, "workspace_id": 0})
                    if c: block["props"]["coupon"] = c
            elif block["type"] == "giftcard":
                tid = (block.get("props") or {}).get("template_id")
                if tid:
                    from routers.giftcards import TEMPLATES as GC_TEMPLATES
                    tpl = next((t for t in GC_TEMPLATES if t["id"] == tid), None)
                    if tpl: block["props"]["template"] = tpl
            elif block["type"] == "product":
                pid = (block.get("props") or {}).get("product_id")
                if pid:
                    prod = await db.products.find_one(
                        {"id": pid, "workspace_id": workspace_id, "is_deleted": {"$ne": True}},
                        {"_id": 0, "workspace_id": 0, "stripe_price_id": 0})
                    if prod: block["props"]["product"] = prod
                code = (block.get("props") or {}).get("coupon_code")
                if code:
                    c = await db.coupons.find_one({"code": code, "workspace_id": workspace_id},
                                                    {"_id": 0, "workspace_id": 0})
                    if c: block["props"]["coupon"] = c
            elif block["type"] == "testimonial":
                props = block.get("props") or {}
                if props.get("source") == "reviews":
                    q = {"workspace_id": workspace_id, "is_deleted": {"$ne": True}, "approved": True}
                    if props.get("product_id"): q["product_id"] = props["product_id"]
                    limit = int(props.get("limit") or 6)
                    reviews = await db.reviews.find(q,
                        {"_id": 0, "workspace_id": 0, "created_by": 0,
                         "is_deleted": 0, "approved": 0}).sort("created_at", -1).to_list(limit)
                    props["items"] = [{"quote": r["quote"], "author": r["customer_name"],
                        "role": r.get("role") or ("Verified buyer" if r.get("verified") else None),
                        "avatar_url": r.get("avatar_url"), "rating": r.get("rating", 5),
                    } for r in reviews]
                    block["props"] = props

    def _pick_variant(variants, visitor_bucket):
        """Deterministic A/B pick: hash visitor_bucket into a weighted variant."""
        if not variants: return None
        total = sum(max(0, int(v.get("weight", 1) or 1)) for v in variants) or len(variants)
        # simple hash-based bucket to number in [0, total)
        h = 0
        for ch in (visitor_bucket or "seed"):
            h = (h * 131 + ord(ch)) & 0xFFFFFFFF
        pick = h % total
        acc = 0
        for v in variants:
            acc += max(1, int(v.get("weight", 1) or 1))
            if pick < acc: return v
        return variants[-1]

    @api.get("/public/f/{slug}")
    async def public_funnel(slug: str, step: Optional[str] = None,
                              variant: Optional[str] = None, vb: Optional[str] = None):
        d = await db.funnels.find_one(
            {"slug": slug, "published": True, "is_deleted": {"$ne": True}},
            {"_id": 0, "created_by": 0})
        if not d: raise HTTPException(404, "Funnel not found or unpublished")
        try:
            await db.funnels.update_one({"slug": slug}, {"$inc": {"views": 1}})
        except Exception:
            pass
        workspace_id = d.get("workspace_id")
        # ------- Multi-step navigation -------
        # Main-page blocks are treated as a pseudo-step (slug_suffix=""). This keeps the
        # merchant's main page reachable even after they add extra steps.
        steps = d.get("steps") or []
        active_step = None
        if steps:
            main_meta = {"id": "main", "name": "Main", "slug_suffix": ""}
            if step is None or step == "" or step == "main":
                d["active_step"] = main_meta
                # keep d["blocks"] as-is (main page)
            else:
                active_step = next((s for s in steps if s.get("slug_suffix") == step), None)
                if not active_step: raise HTTPException(404, "Step not found")
                d["blocks"] = active_step.get("blocks") or []
                d["active_step"] = {"id": active_step.get("id"), "name": active_step.get("name"),
                                     "slug_suffix": active_step.get("slug_suffix", "")}
            d["steps_meta"] = [main_meta] + [{"id": s.get("id"), "name": s.get("name"),
                                                 "slug_suffix": s.get("slug_suffix", "")} for s in steps]
        # ------- A/B variant selection -------
        # Only apply variants when the merchant is viewing the main surface — variants clobbering
        # step blocks would render the wrong page for multi-step + A/B funnels.
        variants = d.get("variants") or []
        on_main = (not steps) or (d.get("active_step", {}).get("id") == "main")
        if variants and on_main:
            chosen = None
            if variant:
                chosen = next((v for v in variants if v.get("id") == variant), None)
            if not chosen:
                chosen = _pick_variant(variants, vb or slug)
            if chosen:
                d["blocks"] = chosen.get("blocks") or d.get("blocks", [])
                d["active_variant"] = {"id": chosen.get("id"), "name": chosen.get("name")}
                d["variants_meta"] = [{"id": v.get("id"), "name": v.get("name"),
                                          "weight": v.get("weight", 1)} for v in variants]
        await _hydrate_blocks(d.get("blocks", []), workspace_id)
        # drop workspace_id from response (not part of public payload)
        # Expose a non-sensitive workspace id echo so client-side flows like the
        # gift-card checkout know which workspace to attribute the sale to.
        d["public_workspace_id"] = workspace_id
        d.pop("workspace_id", None)
        return d

    class FunnelEvent(BaseModel):
        event: str  # view | buy_now_click | coupon_copy | cta_click | optin_submit
        block_id: Optional[str] = None
        block_type: Optional[str] = None
        variant_id: Optional[str] = None
        step_id: Optional[str] = None
        meta: Optional[dict] = None

    class OptinSubmit(BaseModel):
        block_id: Optional[str] = None
        fields: dict
        lead_tag: Optional[str] = None
        source_url: Optional[str] = None

    @api.post("/public/f/{slug}/optin")
    async def submit_optin(slug: str, body: OptinSubmit, request: Request = None):
        """Capture a lead from an opt-in block. Deduped by email per funnel."""
        f = await db.funnels.find_one({"slug": slug, "is_deleted": {"$ne": True}},
                                        {"id": 1, "workspace_id": 1, "name": 1})
        if not f: raise HTTPException(404, "Funnel not found")
        email = (body.fields.get("email") or "").strip().lower()
        if not email or "@" not in email:
            raise HTTPException(400, "A valid email is required")
        # Upsert by (workspace_id, email, funnel_id) so re-submits don't create dupes.
        existing = await db.funnel_leads.find_one({
            "workspace_id": f["workspace_id"], "email": email, "funnel_id": f["id"]})
        ua = ""
        ip = ""
        if request is not None:
            ua = (request.headers.get("user-agent") or "")[:200]
            ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                    or (request.client.host if request.client else ""))[:64]
        doc = {
            "workspace_id": f["workspace_id"], "funnel_id": f["id"], "funnel_name": f["name"],
            "slug": slug, "email": email, "fields": body.fields,
            "lead_tag": body.lead_tag or "", "block_id": body.block_id,
            "source_url": body.source_url or "", "ua": ua, "ip": ip,
        }
        if existing:
            await db.funnel_leads.update_one({"id": existing["id"]},
                {"$set": {**doc, "updated_at": now_iso()},
                 "$inc": {"submits": 1}})
            lead_id = existing["id"]
        else:
            doc["id"] = str(uuid.uuid4())
            doc["created_at"] = now_iso()
            doc["submits"] = 1
            await db.funnel_leads.insert_one(doc)
            lead_id = doc["id"]
        # Also emit an analytics event so it shows in the funnel dashboard.
        await db.funnel_events.insert_one({
            "id": str(uuid.uuid4()), "funnel_id": f["id"], "workspace_id": f["workspace_id"],
            "slug": slug, "event": "optin_submit", "block_id": body.block_id,
            "block_type": "optin", "meta": {"email": email, "lead_tag": body.lead_tag or ""},
            "ua": ua, "ip": ip, "created_at": now_iso()})
        # Enroll in any matching automation sequences (opt-in trigger).
        try:
            enroll = getattr(getattr(api, "state", None), "enroll_sequence_on_optin", None)
            if enroll:
                await enroll(f["workspace_id"], f["id"], body.lead_tag or "", email)
        except Exception:
            pass
        return {"ok": True, "lead_id": lead_id}

    @api.get("/funnels/{fid}/leads")
    async def funnel_leads(fid: str, user: dict = Depends(get_current_user)):
        f = await db.funnels.find_one({"id": fid, "workspace_id": user["workspace_id"],
                                         "is_deleted": {"$ne": True}}, {"id": 1})
        if not f: raise HTTPException(404, "Not found")
        docs = await db.funnel_leads.find(
            {"funnel_id": fid, "workspace_id": user["workspace_id"]},
            {"_id": 0, "workspace_id": 0, "ua": 0, "ip": 0}).sort("created_at", -1).to_list(500)
        return docs

    @api.post("/public/f/{slug}/track")
    async def track_funnel_event(slug: str, body: FunnelEvent, request: Request = None):
        """Public analytics event ingester — fired from PublicFunnel client-side."""
        ev = (body.event or "").strip().lower()
        if ev not in ("view", "buy_now_click", "coupon_copy", "cta_click", "optin_submit", "hyperlink_click"):
            raise HTTPException(400, "Unknown event")
        f = await db.funnels.find_one({"slug": slug, "is_deleted": {"$ne": True}},
                                        {"id": 1, "workspace_id": 1})
        if not f: return {"ok": False}
        ua = ""
        ip = ""
        if request is not None:
            ua = (request.headers.get("user-agent") or "")[:200]
            ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
                    or (request.client.host if request.client else ""))[:64]
        await db.funnel_events.insert_one({
            "id": str(uuid.uuid4()),
            "funnel_id": f["id"],
            "workspace_id": f["workspace_id"],
            "slug": slug,
            "event": ev,
            "block_id": body.block_id,
            "block_type": body.block_type,
            "variant_id": body.variant_id,
            "step_id": body.step_id,
            "meta": body.meta or {},
            "ua": ua, "ip": ip,
            "created_at": now_iso(),
        })
        return {"ok": True}

    @api.get("/funnels/{fid}/variants-analytics")
    async def variant_analytics(fid: str, user: dict = Depends(get_current_user)):
        """Per-variant conversion metrics for A/B split funnels."""
        f = await db.funnels.find_one(
            {"id": fid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"_id": 0, "id": 1, "slug": 1, "name": 1, "variants": 1})
        if not f: raise HTTPException(404, "Not found")
        variants = f.get("variants") or []
        if not variants:
            return {"variants": [], "note": "No variants configured for this funnel."}
        # Aggregate events grouped by (variant_id, event).
        pipeline = [
            {"$match": {"funnel_id": fid, "workspace_id": user["workspace_id"]}},
            {"$group": {"_id": {"variant": "$variant_id", "event": "$event"}, "count": {"$sum": 1}}},
        ]
        agg = {}
        async for r in db.funnel_events.aggregate(pipeline):
            vid = r["_id"].get("variant") or ""
            agg.setdefault(vid, {})[r["_id"]["event"]] = r["count"]
        rows = []
        best_conv = -1
        best_id = None
        for v in variants:
            m = agg.get(v["id"], {})
            views = m.get("view", 0)
            buys = m.get("buy_now_click", 0)
            optins = m.get("optin_submit", 0)
            copies = m.get("coupon_copy", 0)
            ctas = m.get("cta_click", 0)
            # Primary conversion = buys if any exist, otherwise optins.
            primary = buys if buys else optins
            conv = round((primary / views) * 100, 2) if views else 0.0
            rows.append({"id": v["id"], "name": v["name"], "weight": v.get("weight", 1),
                         "views": views, "buy_now_clicks": buys, "optin_submits": optins,
                         "coupon_copies": copies, "cta_clicks": ctas,
                         "conversion_pct": conv})
            if views >= 20 and conv > best_conv:
                best_conv = conv; best_id = v["id"]
        return {"variants": rows, "winning_variant_id": best_id,
                "note": None if best_id else "Need ≥20 views per variant before declaring a winner."}

    @api.post("/funnels/{fid}/promote-variant")
    async def promote_variant(fid: str, variant_id: str,
                                user: dict = Depends(get_current_user)):
        require_writer(user)
        f = await db.funnels.find_one({"id": fid, "workspace_id": user["workspace_id"]})
        if not f: raise HTTPException(404, "Not found")
        v = next((x for x in (f.get("variants") or []) if x.get("id") == variant_id), None)
        if not v: raise HTTPException(404, "Variant not found")
        # Promote variant's blocks to main blocks, then clear variants.
        await db.funnels.update_one({"id": fid},
            {"$set": {"blocks": v.get("blocks") or [], "variants": [],
                      "promoted_variant": {"id": variant_id, "name": v.get("name"), "at": now_iso()}}})
        return {"ok": True, "promoted": v.get("name")}

    @api.get("/funnels/{fid}/analytics")
    async def funnel_analytics(fid: str, user: dict = Depends(get_current_user)):
        f = await db.funnels.find_one(
            {"id": fid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"_id": 0, "id": 1, "slug": 1, "name": 1, "views": 1})
        if not f: raise HTTPException(404, "Not found")
        pipeline = [
            {"$match": {"funnel_id": fid, "workspace_id": user["workspace_id"]}},
            {"$group": {"_id": "$event", "count": {"$sum": 1}}},
        ]
        agg = {r["_id"]: r["count"] async for r in db.funnel_events.aggregate(pipeline)}
        views = agg.get("view", 0) or int(f.get("views") or 0)
        buy_clicks = agg.get("buy_now_click", 0)
        coupon_copies = agg.get("coupon_copy", 0)
        cta_clicks = agg.get("cta_click", 0)
        optin_submits = agg.get("optin_submit", 0)
        conv = round((buy_clicks / views) * 100, 2) if views else 0.0
        optin_conv = round((optin_submits / views) * 100, 2) if views else 0.0
        return {
            "funnel_id": fid, "slug": f["slug"], "name": f["name"],
            "views": views,
            "buy_now_clicks": buy_clicks,
            "coupon_copies": coupon_copies,
            "cta_clicks": cta_clicks,
            "optin_submits": optin_submits,
            "buy_now_conversion_pct": conv,
            "optin_conversion_pct": optin_conv,
        }

    @api.get("/funnels/{fid}/hyperlink-analytics")
    async def hyperlink_analytics(fid: str, user: dict = Depends(get_current_user)):
        """Per-block hyperlink click-through table for a funnel."""
        f = await db.funnels.find_one(
            {"id": fid, "workspace_id": user["workspace_id"], "is_deleted": {"$ne": True}},
            {"_id": 0, "id": 1, "slug": 1, "views": 1, "blocks": 1, "steps": 1, "variants": 1})
        if not f: raise HTTPException(404, "Not found")
        # Build a lookup: block_id -> {type, link_url}
        block_map: dict = {}
        for b in (f.get("blocks") or []):
            block_map[b.get("id")] = {"type": b.get("type"),
                                      "link_url": (b.get("props") or {}).get("link_url", "")}
        for s in (f.get("steps") or []):
            for b in (s.get("blocks") or []):
                block_map[b.get("id")] = {"type": b.get("type"),
                                          "link_url": (b.get("props") or {}).get("link_url", "")}
        for v in (f.get("variants") or []):
            for b in (v.get("blocks") or []):
                block_map[b.get("id")] = {"type": b.get("type"),
                                          "link_url": (b.get("props") or {}).get("link_url", "")}
        pipeline = [
            {"$match": {"funnel_id": fid, "workspace_id": user["workspace_id"],
                        "event": "hyperlink_click"}},
            {"$group": {"_id": "$block_id", "count": {"$sum": 1},
                        "last_at": {"$max": "$created_at"},
                        "sample_href": {"$last": "$meta.href"}}},
            {"$sort": {"count": -1}},
        ]
        rows = []
        views = int(f.get("views") or 0)
        async for r in db.funnel_events.aggregate(pipeline):
            info = block_map.get(r["_id"]) or {"type": "unknown", "link_url": ""}
            ctr = round((r["count"] / views) * 100, 2) if views else 0.0
            rows.append({
                "block_id": r["_id"],
                "block_type": info["type"],
                "href": info["link_url"] or r.get("sample_href", ""),
                "clicks": r["count"],
                "ctr_pct": ctr,
                "last_at": r.get("last_at"),
            })
        total_clicks = sum(r["clicks"] for r in rows)
        return {"funnel_id": fid, "views": views, "total_clicks": total_clicks, "rows": rows}
