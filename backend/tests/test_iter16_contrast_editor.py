"""Iteration 16 — contrast fix support (seed coupons) + funnel leads regression."""
import os
import json
import re
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")

SEED_OUT = Path("/app/test_reports/iter16_seed.json")


@pytest.fixture(scope="session")
def creds():
    content = Path("/app/memory/test_credentials.md").read_text()
    row = re.search(r"\|\s*Owner\s*\|\s*(\S+)\s*\|\s*(\S+)\s*\|", content)
    assert row, "owner creds not found"
    return {"email": row.group(1), "password": row.group(2)}


@pytest.fixture(scope="session")
def client(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text[:300]}"
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token in {r.json().keys()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


# --- workspace brand sanity ---
class TestBrand:
    def test_brand_colors(self, client):
        r = client.get(f"{BASE_URL}/api/workspace")
        assert r.status_code == 200, r.text[:300]
        w = r.json()
        assert "_id" not in json.dumps(w)
        print("BRAND primary=", w.get("primary_color"), "secondary=", w.get("secondary_color"))


# --- seed coupons with edge-case accents used by the Playwright contrast test ---
ACCENT_CASES = [
    ("white", "#FFFFFF", "#0A0A0A"),
    ("black", "#0A0A0A", "#FFFFFF"),
    ("lime", "#CCFF00", "#0A0A0A"),
    ("orange", "#F97316", None),
]


class TestSeedContrastCoupons:
    created = []

    @pytest.mark.parametrize("label,accent,expected", ACCENT_CASES)
    def test_create_coupon(self, client, label, accent, expected):
        payload = {
            "name": f"TEST_contrast_{label}",
            "type": "percentage",
            "discount_value": 15,
            "headline": f"Contrast {label}",
            "description": "QA contrast probe",
            "cta": "Claim Offer",
            "state": "active",
            "design": {"accent": accent},
        }
        r = client.post(f"{BASE_URL}/api/coupons", json=payload)
        assert r.status_code in (200, 201), f"{r.status_code} {r.text[:300]}"
        c = r.json()
        assert c["design"]["accent"] == accent
        code = c["code"]
        TestSeedContrastCoupons.created.append({"label": label, "code": code,
                                                "accent": accent, "expected": expected})
        # verify public endpoint serves it
        pr = requests.get(f"{BASE_URL}/api/public/coupons/{code}")
        assert pr.status_code == 200, pr.text[:200]
        assert pr.json()["design"]["accent"] == accent

    def test_create_no_design_coupon(self, client):
        r = client.post(f"{BASE_URL}/api/coupons", json={
            "name": "TEST_contrast_brandonly", "type": "percentage", "discount_value": 10,
            "headline": "Brand default", "cta": "Claim Offer", "state": "active"})
        assert r.status_code in (200, 201), r.text[:300]
        code = r.json()["code"]
        TestSeedContrastCoupons.created.append({"label": "brandonly", "code": code,
                                               "accent": None, "expected": None})
        SEED_OUT.write_text(json.dumps(TestSeedContrastCoupons.created, indent=2))
        print("SEEDED:", json.dumps(TestSeedContrastCoupons.created))


# --- VIPELITJRIXE still active with 20% off ---
class TestVipCoupon:
    def test_vip_public(self):
        r = requests.get(f"{BASE_URL}/api/public/coupons/VIPELITJRIXE")
        assert r.status_code == 200, r.text[:200]
        d = r.json()
        assert d["state"] == "active"
        assert d["discount_value"] == 20
        print("VIP design=", d.get("design"), "brand=", d.get("brand"))


# --- funnel leads regression ---
class TestFunnelLeads:
    def test_leads_owned_200(self, client):
        r = client.get(f"{BASE_URL}/api/funnels")
        assert r.status_code == 200
        funnels = r.json()
        target = next((f for f in funnels if f.get("slug") == "qa-industrial-all"), None)
        assert target, f"qa-industrial-all not found among {[f.get('slug') for f in funnels]}"
        lr = client.get(f"{BASE_URL}/api/funnels/{target['id']}/leads")
        assert lr.status_code == 200, f"{lr.status_code} {lr.text[:300]}"
        body = lr.json()
        assert isinstance(body, list)
        for d in body:
            assert "_id" not in d and "ip" not in d and "ua" not in d

    def test_leads_unknown_404(self, client):
        r = client.get(f"{BASE_URL}/api/funnels/00000000-0000-0000-0000-000000000000/leads")
        assert r.status_code == 404, r.status_code

    def test_leads_soft_deleted_404(self, client):
        cr = client.post(f"{BASE_URL}/api/funnels", json={
            "name": "TEST_iter16_softdel", "slug": "test-iter16-softdel", "blocks": []})
        assert cr.status_code in (200, 201), cr.text[:300]
        fid = cr.json()["id"]
        assert client.get(f"{BASE_URL}/api/funnels/{fid}/leads").status_code == 200
        dr = client.delete(f"{BASE_URL}/api/funnels/{fid}")
        assert dr.status_code in (200, 204), dr.text[:200]
        after = client.get(f"{BASE_URL}/api/funnels/{fid}/leads")
        assert after.status_code == 404, f"expected 404 after soft delete, got {after.status_code}"

    def test_leads_unauth_401(self):
        r = requests.get(f"{BASE_URL}/api/funnels/xyz/leads")
        assert r.status_code in (401, 403), r.status_code


# --- public wallet no 500 regression ---
class TestWallet:
    def test_public_wallet(self):
        r = requests.get(f"{BASE_URL}/api/public/wallet?email=qa@example.test")
        assert r.status_code in (200, 400, 404, 422), f"{r.status_code} {r.text[:200]}"
        assert r.status_code != 500
