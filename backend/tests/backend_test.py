"""Backend API regression tests for PromoOS.
Covers: Auth (login, register, /me, role gating), Workspace/Brand,
Team, Coupons CRUD + state + bulk codes, Validate/Redeem (fraud),
Dashboard stats, Analytics timeseries, AI copy (Claude) and AI image (Gemini).
"""
import os
import time
import uuid
import base64
import re
from pathlib import Path

import pytest
import requests

from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL is missing")
API = f"{BASE_URL}/api"

credentials_path = Path("/app/memory/test_credentials.md")
if not credentials_path.exists():
    raise RuntimeError("Missing /app/memory/test_credentials.md")
credentials_text = credentials_path.read_text(encoding="utf-8")

def _credential(role):
    match = re.search(rf"(?im)^\|\s*{role}\s*\|\s*([^|\s]+)\s*\|\s*([^|\s]+)\s*\|", credentials_text)
    if not match:
        raise RuntimeError(f"Missing {role} credentials in test_credentials.md")
    return match.group(1), match.group(2)

OWNER_EMAIL, OWNER_PW = _credential("Owner")
MARKETER_EMAIL, MARKETER_PW = _credential("Marketer")
VIEWER_EMAIL, VIEWER_PW = _credential("Viewer")


# ----- helpers -----
def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data["token"], data["user"]


@pytest.fixture(scope="session")
def owner_headers():
    tok, _ = _login(OWNER_EMAIL, OWNER_PW)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def viewer_headers():
    tok, _ = _login(VIEWER_EMAIL, VIEWER_PW)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def marketer_headers():
    tok, _ = _login(MARKETER_EMAIL, MARKETER_PW)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ----- Auth tests -----
class TestAuth:
    def test_login_owner_success(self):
        r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PW}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and isinstance(data["token"], str) and len(data["token"]) > 20
        assert data["user"]["email"] == OWNER_EMAIL
        assert data["user"]["role"] == "owner"

    def test_login_invalid_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_me_endpoint(self, owner_headers):
        r = requests.get(f"{API}/auth/me", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == OWNER_EMAIL
        assert "password_hash" not in u

    def test_me_without_token_fails(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_register_new_workspace(self):
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{API}/auth/register", json={
            "name": "Test User", "email": email, "password": "pw12345",
            "workspace_name": "TEST_WS"
        }, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["email"] == email
        assert data["user"]["role"] == "owner"
        # login should work
        r2 = requests.post(f"{API}/auth/login", json={"email": email, "password": "pw12345"}, timeout=15)
        assert r2.status_code == 200

    def test_register_duplicate_email_rejected(self):
        r = requests.post(f"{API}/auth/register", json={
            "name": "Dup", "email": OWNER_EMAIL, "password": "x"}, timeout=15)
        assert r.status_code == 400


# ----- Workspace / Team -----
class TestWorkspace:
    def test_get_workspace(self, owner_headers):
        r = requests.get(f"{API}/workspace", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        ws = r.json()
        assert ws["name"]
        assert "primary_color" in ws

    def test_update_brand_owner(self, owner_headers):
        r = requests.put(f"{API}/workspace/brand", headers=owner_headers,
                         json={"primary_color": "#123456", "font": "Inter"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["primary_color"] == "#123456"
        # revert
        requests.put(f"{API}/workspace/brand", headers=owner_headers,
                     json={"primary_color": "#005CEE"}, timeout=15)

    def test_update_brand_viewer_forbidden(self, viewer_headers):
        r = requests.put(f"{API}/workspace/brand", headers=viewer_headers,
                         json={"primary_color": "#000000"}, timeout=15)
        assert r.status_code == 403

    def test_team_list(self, owner_headers):
        r = requests.get(f"{API}/team", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        members = r.json()
        emails = [m["email"] for m in members]
        for e in (OWNER_EMAIL, MARKETER_EMAIL, VIEWER_EMAIL):
            assert e in emails, f"missing {e} in team"


# ----- Coupons -----
class TestCoupons:
    def test_list_seeded_coupons(self, owner_headers):
        r = requests.get(f"{API}/coupons", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        cs = r.json()
        assert isinstance(cs, list) and len(cs) >= 7
        codes = [c["code"] for c in cs]
        assert "SUMMER25" in codes

    def test_list_filter_state(self, owner_headers):
        r = requests.get(f"{API}/coupons?state=active", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        for c in r.json():
            assert c["state"] == "active"

    def test_create_update_delete_flow(self, owner_headers):
        payload = {
            "name": "TEST_Coupon", "type": "percentage", "discount_value": 10,
            "code": f"TESTC{uuid.uuid4().hex[:5].upper()}",
            "headline": "Test H", "description": "Test D", "terms": "T&C",
            "cta": "Buy", "state": "draft",
            "rules": {"min_cart": 50, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 2, "stackable": True,
                      "start_date": None, "end_date": None},
        }
        r = requests.post(f"{API}/coupons", headers=owner_headers, json=payload, timeout=15)
        assert r.status_code == 200
        created = r.json()
        cid = created["id"]
        assert created["name"] == "TEST_Coupon"
        assert created["rules"]["min_cart"] == 50
        assert created["rules"]["stackable"] is True
        assert "qr_code" in created and created["qr_code"].startswith("data:image/png;base64,")

        # GET
        r = requests.get(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert r.json()["code"] == payload["code"]

        # UPDATE
        payload["name"] = "TEST_Coupon_upd"
        payload["discount_value"] = 15
        r = requests.put(f"{API}/coupons/{cid}", headers=owner_headers, json=payload, timeout=15)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Coupon_upd"
        assert r.json()["discount_value"] == 15

        # STATE
        r = requests.post(f"{API}/coupons/{cid}/state", headers=owner_headers,
                         json={"state": "active"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["state"] == "active"

        # BULK CODES
        r = requests.post(f"{API}/coupons/{cid}/bulk-codes", headers=owner_headers,
                         json={"count": 5}, timeout=15)
        assert r.status_code == 200
        b = r.json()
        assert b["generated"] == 5 and len(b["codes"]) == 5

        # DELETE
        r = requests.delete(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        r = requests.get(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)
        assert r.status_code == 404

    def test_viewer_cannot_create_coupon(self, viewer_headers):
        r = requests.post(f"{API}/coupons", headers=viewer_headers,
                         json={"name": "no", "type": "percentage", "discount_value": 5}, timeout=15)
        assert r.status_code == 403


# ----- Validate / Redeem -----
class TestValidateRedeem:
    def test_validate_active(self, owner_headers):
        r = requests.post(f"{API}/coupons/validate", headers=owner_headers,
                         json={"code": "SUMMER25", "cart_value": 100}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["valid"] is True
        assert d["coupon"]["discount_value"] == 25

    def test_validate_unknown(self, owner_headers):
        r = requests.post(f"{API}/coupons/validate", headers=owner_headers,
                         json={"code": "NOPE" + uuid.uuid4().hex[:5]}, timeout=15)
        assert r.status_code == 200
        assert r.json()["valid"] is False

    def test_redeem_success_and_stats_increment(self, owner_headers):
        # Get before stats
        r = requests.get(f"{API}/coupons", headers=owner_headers, timeout=15)
        summer = [c for c in r.json() if c["code"] == "SUMMER25"][0]
        before_red = summer["stats"]["redemptions"]
        before_rev = summer["stats"]["revenue"]

        # Use a percentage-type seeded coupon: SPRING50 is expired, SUMMER25 is flash_sale.
        # Create a percentage coupon to validate discount math cleanly.
        create_payload = {
            "name": "TEST_RedeemMath", "type": "percentage", "discount_value": 20,
            "code": f"REDMATH{uuid.uuid4().hex[:4].upper()}",
            "state": "active",
        }
        r = requests.post(f"{API}/coupons", headers=owner_headers, json=create_payload, timeout=15)
        assert r.status_code == 200
        cid = r.json()["id"]
        the_code = r.json()["code"]

        cust = f"TEST_cust_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/coupons/redeem", headers=owner_headers,
                         json={"code": the_code, "amount": 100, "customer": cust}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["discount"] == 20.0
        assert d["revenue"] == 80.0

        # Verify persisted increment
        r = requests.get(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)
        c2 = r.json()
        assert c2["stats"]["redemptions"] == 1
        assert round(c2["stats"]["revenue"], 2) == 80.0

        # cleanup
        requests.delete(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)

    def test_redeem_duplicate_within_5s(self, owner_headers):
        cust = f"TEST_dup_{uuid.uuid4().hex[:6]}"
        r1 = requests.post(f"{API}/coupons/redeem", headers=owner_headers,
                          json={"code": "WELCOME15", "amount": 50, "customer": cust}, timeout=15)
        assert r1.status_code == 200
        # immediate second attempt
        r2 = requests.post(f"{API}/coupons/redeem", headers=owner_headers,
                          json={"code": "WELCOME15", "amount": 50, "customer": cust}, timeout=15)
        assert r2.status_code == 429

    def test_redeem_non_active_rejected(self, owner_headers):
        # SPRING50 is expired
        r = requests.post(f"{API}/coupons/redeem", headers=owner_headers,
                         json={"code": "SPRING50", "amount": 100,
                               "customer": f"TEST_{uuid.uuid4().hex[:5]}"}, timeout=15)
        assert r.status_code == 400


# ----- Dashboard / Analytics -----
class TestDashboardAnalytics:
    def test_dashboard_stats(self, owner_headers):
        r = requests.get(f"{API}/dashboard/stats", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("active_coupons", "total_coupons", "total_redemptions", "total_revenue",
                  "top_campaigns", "by_state"):
            assert k in d
        assert d["total_coupons"] >= 7
        assert isinstance(d["top_campaigns"], list) and len(d["top_campaigns"]) > 0
        assert "name" in d["top_campaigns"][0]

    def test_analytics_timeseries(self, owner_headers):
        r = requests.get(f"{API}/analytics/timeseries", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list) and len(arr) == 14
        for pt in arr:
            assert "date" in pt and "redemptions" in pt and "revenue" in pt


# ----- AI features -----
class TestAI:
    def test_ai_copy_generates_json(self, owner_headers):
        prompt = "Summer swimwear sale, 25% off, ends Sunday, target new customers"
        r = requests.post(f"{API}/ai/copy", headers=owner_headers,
                         json={"prompt": prompt}, timeout=90)
        assert r.status_code == 200, f"AI copy failed: {r.status_code} {r.text[:300]}"
        d = r.json()
        required = ["name", "type", "discount_value", "headline", "description", "terms", "cta"]
        for k in required:
            assert k in d and d[k] not in (None, ""), f"missing/empty {k} in AI copy {d}"
        # Sanity content check
        combined = (d["headline"] + " " + d["description"]).lower()
        assert any(w in combined for w in ["swim", "summer", "sale", "off", "%", "discount"]), \
            f"AI copy seems off-topic: {d}"
        print(f"AI COPY OUT: {d}")

    def test_ai_copy_viewer_forbidden(self, viewer_headers):
        r = requests.post(f"{API}/ai/copy", headers=viewer_headers,
                         json={"prompt": "test"}, timeout=30)
        assert r.status_code == 403

    def test_ai_image_generates_real_image(self, owner_headers):
        prompt = "A vibrant summer swimwear sale banner with tropical colors"
        r = requests.post(f"{API}/ai/image", headers=owner_headers,
                         json={"prompt": prompt}, timeout=90)
        assert r.status_code == 200, f"AI image failed: {r.status_code} {r.text[:300]}"
        d = r.json()
        assert "image_url" in d
        url = d["image_url"]
        assert url.startswith("data:image/"), f"expected data URL, got {url[:60]}"
        # Decode base64 and verify it's a real image
        b64 = url.split("base64,", 1)[1]
        raw = base64.b64decode(b64)
        assert len(raw) > 5000, f"image too small: {len(raw)} bytes"
        # PIL check
        try:
            from PIL import Image, ImageStat
            import io
            im = Image.open(io.BytesIO(raw))
            assert im.size[0] > 100 and im.size[1] > 100
            stddev = ImageStat.Stat(im.convert("L")).stddev[0]
            assert stddev > 5, f"image nearly blank stddev={stddev}"
            print(f"AI IMAGE OK: format={im.format} size={im.size} bytes={len(raw)} stddev={stddev:.1f}")
        except ImportError:
            print(f"PIL not available; bytes={len(raw)}")



# ----- Requested contract and authentication security checks -----
class TestRequestedContract:
    def test_validate_scheduled_coupon_is_invalid(self, owner_headers):
        active = requests.post(
            f"{API}/coupons/validate", headers=owner_headers,
            json={"code": "SUMMER25", "cart_value": 50}, timeout=15)
        assert active.status_code == 200
        assert active.json()["valid"] is True

        scheduled = requests.post(
            f"{API}/coupons/validate", headers=owner_headers,
            json={"code": "HOLIDAY40", "cart_value": 50}, timeout=15)
        assert scheduled.status_code == 200
        assert scheduled.json()["valid"] is False
        assert "scheduled" in scheduled.json()["reason"].lower()

    def test_seed_coupon_bulk_codes_are_five_unique_values(self, owner_headers):
        coupons = requests.get(f"{API}/coupons", headers=owner_headers, timeout=15).json()
        summer = next(c for c in coupons if c["code"] == "SUMMER25")
        response = requests.post(
            f"{API}/coupons/{summer['id']}/bulk-codes", headers=owner_headers,
            json={"count": 5}, timeout=15)
        assert response.status_code == 200
        data = response.json()
        assert data["generated"] == 5
        assert len(data["codes"]) == 5
        assert len(set(data["codes"])) == 5

    def test_exact_summer_redeem_then_duplicate(self, owner_headers):
        payload = {"code": "SUMMER25", "amount": 80, "customer": "x1"}
        first = requests.post(f"{API}/coupons/redeem", headers=owner_headers, json=payload, timeout=15)
        assert first.status_code == 200
        first_data = first.json()
        assert first_data["ok"] is True
        assert isinstance(first_data["discount"], (int, float))
        assert isinstance(first_data["revenue"], (int, float))

        duplicate = requests.post(f"{API}/coupons/redeem", headers=owner_headers, json=payload, timeout=15)
        assert duplicate.status_code == 429
        assert "duplicate" in duplicate.json()["detail"].lower()


class TestAuthSecurityPlaybook:
    def test_login_sets_httponly_auth_cookie(self):
        response = requests.post(
            f"{API}/auth/login",
            json={"email": OWNER_EMAIL, "password": OWNER_PW}, timeout=15)
        assert response.status_code == 200
        token = response.json()["token"]
        # Ignore infrastructure bot-management cookies; require an app auth cookie.
        auth_cookies = {
            cookie.name: cookie
            for cookie in response.cookies
            if cookie.name.lower() not in {"__cf_bm", "cf_clearance"}
        }
        assert auth_cookies, "Login did not set an application authentication cookie"
        assert any(cookie.value == token for cookie in auth_cookies.values())
        assert any(cookie.has_nonstandard_attr("HttpOnly") for cookie in auth_cookies.values())

    def test_cors_uses_explicit_origin_with_credentials(self):
        origin = "https://qa-origin.example.com"
        response = requests.options(
            f"{API}/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            }, timeout=15)
        assert response.status_code in (200, 204)
        assert response.headers.get("access-control-allow-credentials", "").lower() == "true"
        assert response.headers.get("access-control-allow-origin") == origin

    def test_account_locks_after_five_failed_logins(self):
        for _ in range(5):
            failed = requests.post(
                f"{API}/auth/login",
                json={"email": MARKETER_EMAIL, "password": "definitely-wrong"}, timeout=15)
            assert failed.status_code == 401
        locked = requests.post(
            f"{API}/auth/login",
            json={"email": MARKETER_EMAIL, "password": MARKETER_PW}, timeout=15)
        assert locked.status_code == 429, "Account accepted valid login immediately after five failures"

    def test_seeded_password_hash_uses_bcrypt_2b(self):
        try:
            from pymongo import MongoClient
        except ImportError:
            pytest.fail("pymongo is unavailable for bcrypt seed verification")
        backend_env = dotenv_values("/app/backend/.env")
        mongo = MongoClient(backend_env["MONGO_URL"])
        user = mongo[backend_env["DB_NAME"]].users.find_one({"email": OWNER_EMAIL})
        mongo.close()
        assert user is not None
        assert user["password_hash"].startswith("$2b$")
