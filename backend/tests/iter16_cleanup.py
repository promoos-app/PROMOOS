"""Restore seed funnel prop values changed during iteration-16 UI persistence checks
and remove TEST_ contrast coupons."""
import json
import re
from pathlib import Path

import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/")
FID = "110aa3a0-c961-456e-945e-04d63f0dde79"

content = Path("/app/memory/test_credentials.md").read_text()
m = re.search(r"\|\s*Owner\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|", content)
s = requests.Session()
r = s.post(f"{BASE}/api/auth/login", json={"email": m.group(1), "password": m.group(2)})
tok = r.json().get("access_token") or r.json().get("token")
s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})

f = s.get(f"{BASE}/api/funnels/{FID}").json()
changed = 0
for b in f.get("blocks", []):
    if b.get("type") == "optin" and b["props"].get("lead_tag") == "qa-iter16-tag":
        b["props"]["lead_tag"] = "qaleadmagnet"; changed += 1
    if b.get("type") == "spacer" and b["props"].get("height") == 72:
        b["props"]["height"] = 48; changed += 1
if changed:
    up = s.put(f"{BASE}/api/funnels/{FID}", json={"name": f["name"], "slug": f["slug"],
                                                  "blocks": f["blocks"]})
    print("restore funnel props:", up.status_code, changed)

seed = json.loads(Path("/app/test_reports/iter16_seed.json").read_text())
codes = {x["code"] for x in seed}
for c in s.get(f"{BASE}/api/coupons").json():
    if c.get("code") in codes or str(c.get("name", "")).startswith("TEST_contrast"):
        print("delete coupon", c["code"], s.delete(f"{BASE}/api/coupons/{c['id']}").status_code)
