"""Seed a QA funnel containing all 9 industrial block types, published."""
import os, requests
from dotenv import dotenv_values

BASE = (os.environ.get("REACT_APP_BACKEND_URL")
        or dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE}/api"
s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "admin@promoos.com", "password": "admin123"})
tok = r.json().get("access_token") or r.json().get("token")
s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})

SLUG = "qa-industrial-all"
existing = next((f for f in s.get(f"{API}/funnels").json() if f["slug"] == SLUG), None)
if existing:
    fid = existing["id"]
else:
    fid = s.post(f"{API}/funnels", json={"name": "QA Industrial All", "slug": SLUG,
                                         "template_id": "product_launch"}).json()["id"]

blocks = [
    {"type": "logo_bar", "props": {"label": "As featured in",
                                   "logos": ["Forbes", "TechCrunch", "Wired"]}},
    {"type": "stats", "props": {"items": [{"value": "12,400+", "label": "Founders"},
                                          {"value": "4.9/5", "label": "Rating"}]}},
    {"type": "guarantee", "props": {"title": "30-day money-back",
                                    "text": "Full refund, no questions.", "icon": "shield"}},
    {"type": "pricing_table", "props": {"title": "Simple pricing", "tiers": [
        {"name": "Basic", "price": 49, "period": "mo", "features": ["A", "B"],
         "cta_label": "Start free", "highlight": False},
        {"name": "Pro", "price": 79, "period": "mo", "features": ["C", "D"],
         "cta_label": "Start free", "highlight": True}]}, "anchor": "pricing-1"},
    {"type": "order_bump", "props": {"title": "Add: Onboarding session",
                                     "text": "60-min 1:1.", "price": 149, "currency": "USD"}},
    {"type": "upsell", "props": {"headline": "One more thing.", "text": "60% off.",
                                 "cta_label": "Yes, add it", "price": 197,
                                 "currency": "USD"}, "anchor": "upsell-1"},
    {"type": "optin", "props": {"headline": "Where should we send it?",
                                "sub": "No spam.", "cta_label": "Send it now",
                                "fields": [{"key": "email", "label": "Email address",
                                            "required": True}],
                                "lead_tag": "qaleadmagnet"}, "anchor": "optin-1"},
    {"type": "spacer", "props": {"height": 48}},
    {"type": "divider", "props": {}},
]
print(s.put(f"{API}/funnels/{fid}", json={"blocks": blocks}).status_code)
print(s.post(f"{API}/funnels/{fid}/publish").json())
print("FUNNEL_ID", fid)
print("PUBLIC", f"{BASE}/f/{SLUG}")
print("EDIT", f"{BASE}/funnels/{fid}/edit")
