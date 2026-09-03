import json
import requests
from dotenv import dotenv_values

BASE = dotenv_values("/app/frontend/.env")["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
s = requests.Session()
tok = s.post(f"{BASE}/auth/login", json={"email": "admin@promoos.com", "password": "admin123"}).json()["token"]
s.headers.update({"Authorization": f"Bearer {tok}"})
f = s.post(f"{BASE}/funnels", json={"name": "TEST_iter20 UI funnel"}).json()
s.post(f"{BASE}/funnels/{f['id']}/publish")
c = s.post(f"{BASE}/coupons", json={"name": "TEST_iter20 UI coupon", "type": "percentage",
                                    "discount_value": 15, "state": "active"}).json()
out = {"funnel_id": f["id"], "funnel_slug": f["slug"], "coupon_id": c["id"], "coupon_code": c.get("code")}
print(json.dumps(out))
open("/app/test_reports/iter20_seed.json", "w").write(json.dumps(out))
