"""Iteration 8 tests — Phase 1 expansion (Stripe billing, uploads, currencies/fonts,
coupon share/download, rotated superadmin password, prefix-indexed API key auth).

Covers ONLY the new/changed endpoints for iter-8 per review_request.
"""
import io
import os
import re
import struct
import uuid
import zlib

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SUPERADMIN_EMAIL = "superadmin@promoos.com"
SUPERADMIN_PASS = "sZpRBNpLKypsQDURBQNqMIzE"
OLD_SUPERADMIN_PASS = "superadmin123"
OWNER_EMAIL = "admin@promoos.com"
OWNER_PASS = "admin123"
MARKETER_EMAIL = "marketer@promoos.com"
MARKETER_PASS = "marketer123"


# ---------------- helpers ----------------
def _login(email, password, expect=200):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == expect, f"login {email} -> {r.status_code} {r.text}"
    return r.json() if r.status_code == 200 else r


def _hdr(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def owner_token():
    return _login(OWNER_EMAIL, OWNER_PASS)["token"]


@pytest.fixture(scope="module")
def marketer_token():
    return _login(MARKETER_EMAIL, MARKETER_PASS)["token"]


@pytest.fixture(scope="module")
def superadmin_token():
    return _login(SUPERADMIN_EMAIL, SUPERADMIN_PASS)["token"]


# ---------------- Superadmin credentials rotation ----------------
class TestSuperadminAuth:
    def test_new_password_works(self):
        d = _login(SUPERADMIN_EMAIL, SUPERADMIN_PASS)
        assert d["user"]["role"] == "superadmin"
        assert isinstance(d.get("token"), str) and len(d["token"]) > 20

    def test_old_password_rejected(self):
        r = _login(SUPERADMIN_EMAIL, OLD_SUPERADMIN_PASS, expect=401)
        assert r.status_code == 401


# ---------------- Currencies + Fonts ----------------
class TestCurrenciesAndFonts:
    def test_currencies_shape_and_count(self):
        r = requests.get(f"{API}/currencies", timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        # review_request says ~145; extras.py file inspection shows 145
        assert 140 <= len(arr) <= 160, f"got {len(arr)} currencies"
        for c in arr[:3]:
            assert set(["code", "name", "symbol"]).issubset(c.keys())
        codes = [c["code"] for c in arr]
        for must in ("USD", "EUR", "GBP", "INR", "BTC", "USDC"):
            assert must in codes, f"missing {must}"

    def test_fonts_shape_and_count(self):
        r = requests.get(f"{API}/fonts", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "fonts" in d
        assert isinstance(d["fonts"], list)
        assert 80 <= len(d["fonts"]) <= 100, f"got {len(d['fonts'])} fonts"
        assert "Inter" in d["fonts"]
        assert "Cabinet Grotesk" in d["fonts"]


# ---------------- Billing ----------------
class TestBilling:
    def test_plans(self):
        r = requests.get(f"{API}/billing/plans", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "plans" in d and len(d["plans"]) == 2
        by_key = {p["lookup_key"]: p for p in d["plans"]}
        assert by_key["basic_monthly"]["price"] == 49.0
        assert by_key["basic_monthly"]["trial_days"] == 3
        assert by_key["pro_monthly"]["price"] == 79.0
        assert by_key["pro_monthly"]["trial_days"] == 3
        assert d.get("publishable_key", "").startswith("pk_"), "publishable_key missing"

    def test_checkout_requires_auth(self):
        r = requests.post(f"{API}/billing/checkout",
                          json={"lookup_key": "basic_monthly", "origin_url": BASE_URL},
                          timeout=15)
        assert r.status_code in (401, 403)

    def test_checkout_creates_stripe_session(self, owner_token):
        r = requests.post(f"{API}/billing/checkout",
                          headers=_hdr(owner_token),
                          json={"lookup_key": "basic_monthly", "origin_url": BASE_URL},
                          timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        d = r.json()
        assert "checkout_url" in d and "session_id" in d
        assert d["checkout_url"].startswith("https://checkout.stripe.com/"), d["checkout_url"]
        assert d["session_id"].startswith("cs_"), d["session_id"]
        # save for status
        pytest.session_id = d["session_id"]

    def test_checkout_pro_plan(self, owner_token):
        r = requests.post(f"{API}/billing/checkout",
                          headers=_hdr(owner_token),
                          json={"lookup_key": "pro_monthly", "origin_url": BASE_URL},
                          timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["checkout_url"].startswith("https://checkout.stripe.com/")

    def test_checkout_invalid_plan(self, owner_token):
        r = requests.post(f"{API}/billing/checkout",
                          headers=_hdr(owner_token),
                          json={"lookup_key": "gold_monthly", "origin_url": BASE_URL},
                          timeout=15)
        assert r.status_code == 400

    def test_status_returns_transaction(self, owner_token):
        sid = getattr(pytest, "session_id", None)
        assert sid, "prior checkout test must run first"
        r = requests.get(f"{API}/billing/status/{sid}", timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["session_id"] == sid
        assert d["payment_status"] in ("pending", "paid", "unpaid", "no_payment_required")
        assert d["lookup_key"] == "basic_monthly"

    def test_status_404(self):
        r = requests.get(f"{API}/billing/status/cs_test_doesnotexist", timeout=15)
        assert r.status_code == 404

    def test_subscription(self, owner_token):
        r = requests.get(f"{API}/billing/subscription",
                         headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "status" in d and "plan" in d


# ---------------- Admin Stripe onboarding ----------------
class TestStripeOnboarding:
    def test_superadmin_ok(self, superadmin_token):
        r = requests.get(f"{API}/admin/stripe-onboarding",
                         headers=_hdr(superadmin_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "onboarding_url" in d
        assert d["onboarding_url"].startswith("https://") or d["onboarding_url"] == ""
        assert "mode" in d and "account_id" in d and "publishable_key" in d

    def test_non_superadmin_forbidden(self, owner_token):
        r = requests.get(f"{API}/admin/stripe-onboarding",
                         headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 403

    def test_unauth_forbidden(self):
        r = requests.get(f"{API}/admin/stripe-onboarding", timeout=15)
        assert r.status_code in (401, 403)


# ---------------- Uploads ----------------
def _make_png_bytes(w=8, h=8):
    """Craft a tiny valid PNG in-memory (no PIL needed)."""
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * w for _ in range(h))
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


class TestUploads:
    def test_upload_png_and_download(self, owner_token):
        png = _make_png_bytes(16, 16)
        files = {"file": ("test_iter8.png", png, "image/png")}
        r = requests.post(f"{API}/uploads", headers=_hdr(owner_token),
                          files=files, timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        d = r.json()
        assert "id" in d and "url" in d and "size" in d and "content_type" in d
        assert d["content_type"] == "image/png"
        assert d["size"] == len(png)
        assert d["url"] == f"/api/uploads/{d['id']}"
        pytest.upload_id = d["id"]

        # download
        r2 = requests.get(f"{BASE_URL}{d['url']}", timeout=30)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/png")
        assert r2.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(r2.content) == len(png)

    def test_upload_rejects_bad_mime(self, owner_token):
        files = {"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")}
        r = requests.post(f"{API}/uploads", headers=_hdr(owner_token),
                          files=files, timeout=30)
        assert r.status_code == 400
        assert "Unsupported" in r.text or "type" in r.text.lower()

    def test_list_uploads(self, owner_token):
        r = requests.get(f"{API}/uploads", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        ids = [u["id"] for u in arr]
        assert getattr(pytest, "upload_id", None) in ids

    def test_upload_requires_auth(self):
        png = _make_png_bytes(2, 2)
        r = requests.post(f"{API}/uploads",
                          files={"file": ("x.png", png, "image/png")}, timeout=15)
        assert r.status_code in (401, 403)


# ---------------- Coupon share / download ----------------
class TestCouponShareDownload:
    @pytest.fixture(scope="class")
    def coupon_id(self, owner_token):
        # create fresh coupon so we always have something to share
        payload = {
            "name": "TEST_ITER8_share",
            "type": "percentage",
            "discount_value": 20,
            "code": f"ITER8SHARE{uuid.uuid4().hex[:6].upper()}",
            "headline": "Save 20% on your next order",
            "description": "Iter 8 share test",
            "state": "active",
        }
        r = requests.post(f"{API}/coupons", headers=_hdr(owner_token),
                          json=payload, timeout=30)
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]

    def test_share(self, owner_token, coupon_id):
        r = requests.get(f"{API}/coupons/{coupon_id}/share",
                         headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["landing_url"].startswith("http")
        assert "/c/" in d["landing_url"]
        embed = d["embed_snippets"]
        for v in ("inline", "popup", "bar", "wheel", "wallet"):
            assert v in embed and "<script" in embed[v] and "coupon.js" in embed[v]
        share = d["share_links"]
        for k in ("email", "twitter", "facebook", "linkedin", "whatsapp", "telegram", "pinterest"):
            assert k in share and share[k].startswith(("http", "mailto"))

    def test_share_requires_auth(self, coupon_id):
        r = requests.get(f"{API}/coupons/{coupon_id}/share", timeout=15)
        assert r.status_code in (401, 403)

    def test_share_404_wrong_workspace(self, owner_token):
        r = requests.get(f"{API}/coupons/does-not-exist/share",
                         headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 404

    def test_download_png(self, owner_token, coupon_id):
        r = requests.get(f"{API}/coupons/{coupon_id}/download.png",
                         headers=_hdr(owner_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("image/png")
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd and "coupon-" in cd
        # real PNG bytes
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert len(r.content) > 500


# ---------------- API key prefix indexing regression ----------------
class TestApiKeyPrefixIndex:
    def test_pk_live_key_still_works(self, owner_token):
        # first ensure there's an active coupon SUMMER25 or create one
        code = f"ITER8REDEEM{uuid.uuid4().hex[:6].upper()}"
        cr = requests.post(f"{API}/coupons", headers=_hdr(owner_token), json={
            "name": "TEST_ITER8_apikey", "type": "percentage", "discount_value": 20,
            "code": code, "headline": "20% off", "description": "iter8",
            "state": "active",
        }, timeout=30)
        assert cr.status_code in (200, 201), cr.text
        cid = cr.json()["id"]
        # ensure activated
        requests.post(f"{API}/coupons/{cid}/state", headers=_hdr(owner_token),
                      json={"state": "active"}, timeout=10)

        # create api key
        ak = requests.post(f"{API}/api-keys", headers=_hdr(owner_token),
                           json={"name": "TEST_ITER8_pk", "scopes": ["read", "write"]},
                           timeout=15)
        assert ak.status_code in (200, 201), ak.text
        key = ak.json().get("key") or ak.json().get("api_key") or ak.json().get("token")
        assert key and key.startswith("pk_live_"), f"expected pk_live_..., got {ak.json()}"

        # redeem via pk_live_ bearer
        r = requests.post(f"{API}/v1/coupons/redeem",
                          headers={"Authorization": f"Bearer {key}"},
                          json={"code": code, "amount": 100}, timeout=15)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        d = r.json()
        assert d.get("ok") is True
        # 20% of 100 = 20
        assert abs(d["discount"] - 20) < 0.01
        assert abs(d["revenue"] - 80) < 0.01

        # cleanup: revoke
        kid = ak.json().get("id")
        if kid:
            requests.delete(f"{API}/api-keys/{kid}", headers=_hdr(owner_token), timeout=10)

    def test_invalid_pk_live_rejected(self):
        r = requests.post(f"{API}/v1/coupons/redeem",
                          headers={"Authorization": "Bearer pk_live_zzzzzzzzzzzzzzzzzz"},
                          json={"code": "ANY", "amount": 100}, timeout=15)
        assert r.status_code == 401
        assert "Invalid" in r.text or "revoked" in r.text.lower()


# ---------------- Iter 1-7 regression smokes ----------------
class TestRegressionExisting:
    def test_auth_login(self):
        d = _login(OWNER_EMAIL, OWNER_PASS)
        assert d["user"]["role"] == "owner"

    def test_coupons_list(self, owner_token):
        r = requests.get(f"{API}/coupons", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_dashboard_stats(self, owner_token):
        r = requests.get(f"{API}/dashboard/stats", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("total_coupons", "active_coupons", "total_redemptions", "total_revenue"):
            assert k in d

    def test_admin_stats(self, superadmin_token):
        r = requests.get(f"{API}/admin/stats", headers=_hdr(superadmin_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "users" in d and "workspaces" in d

    def test_admin_users(self, superadmin_token):
        r = requests.get(f"{API}/admin/users", headers=_hdr(superadmin_token), timeout=15)
        assert r.status_code == 200
        arr = r.json()
        emails = [u["email"] for u in arr]
        assert SUPERADMIN_EMAIL in emails
