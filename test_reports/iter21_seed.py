import json
import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE}/api"
s = requests.Session()
r = s.post(f"{API}/auth/login", json={"email": "admin@promoos.com", "password": "admin123"})
tok = r.json().get("access_token") or r.json().get("token")
s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})

SLUG = "test-iter21-ui"
# reuse existing
funnels = s.get(f"{API}/funnels").json()
fl = funnels if isinstance(funnels, list) else funnels.get("items", [])
existing = next((f for f in fl if f["slug"] == SLUG), None)
if existing:
    fid = existing["id"]
else:
    prod = s.post(f"{API}/products", json={"name": "TEST_EUR Widget", "price": 29.5,
                                           "currency": "EUR", "description": "iter21 ui"}).json()
    f = s.post(f"{API}/funnels", json={"name": "TEST_Iter21 UI", "template_id": "blank", "slug": SLUG}).json()
    fid = f["id"]
    s.put(f"{API}/funnels/{fid}", json={
        "blocks": [{"type": "heading", "props": {"text": "MAIN PAGE HEADING"}},
                   {"type": "product", "props": {"product_id": prod["id"]}}],
        "steps": [{"name": "Upsell", "slug_suffix": "upsell",
                   "blocks": [{"type": "heading", "props": {"text": "UPSELL STEP"}}]},
                  {"name": "Thanks", "slug_suffix": "thanks",
                   "blocks": [{"type": "heading", "props": {"text": "THANKS STEP"}}]}]})
    s.post(f"{API}/funnels/{fid}/publish")

pub = requests.get(f"{API}/public/f/{SLUG}").json()
print(json.dumps({"funnel_id": fid, "slug": SLUG,
                  "steps_meta": pub.get("steps_meta"),
                  "active_step": pub.get("active_step")}, indent=1))
