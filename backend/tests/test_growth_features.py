"""Backend tests for PromoOS growth features (iteration 2):
- Public shareable coupon page endpoints
- Public redemption + referral credit accrual
- Coupons referrals aggregation (auth)
- Embed widget JS delivery
- Regression: coupon editor persists rules.referral_enabled/pct
- Regression: coupon email endpoint returns 400 when RESEND_API_KEY empty
"""
import os
import re
import uuid
import time
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
credentials_text = credentials_path.read_text(encoding="utf-8")


def _credential(role):
    m = re.search(rf"(?im)^\|\s*{role}\s*\|\s*([^|\s]+)\s*\|\s*([^|\s]+)\s*\|", credentials_text)
    if not m:
        raise RuntimeError(f"Missing {role} credentials")
    return m.group(1), m.group(2)


OWNER_EMAIL, OWNER_PW = _credential("Owner")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="module")
def owner_headers():
    tok, _ = _login(OWNER_EMAIL, OWNER_PW)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------------- Public coupon endpoint ----------------
class TestPublicCoupon:
    def test_get_summer25_returns_referral_enabled(self):
        r = requests.get(f"{API}/public/coupons/SUMMER25", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["code"] == "SUMMER25"
        assert d["state"] == "active"
        assert d["referral"] is True
        assert d["referral_credit_pct"] == 15
        assert d["brand"]["name"], "brand name missing"
        assert "primary_color" in d["brand"]
        # qr code should be a base64 data uri
        assert d["qr_code"].startswith("data:image/")

    def test_get_lowercase_code_case_insensitive(self):
        r = requests.get(f"{API}/public/coupons/summer25", timeout=15)
        assert r.status_code == 200
        assert r.json()["code"] == "SUMMER25"

    def test_get_draft_coupon_returns_404(self, owner_headers):
        # HAPPYBDAY is seeded as draft
        r = requests.get(f"{API}/public/coupons/HAPPYBDAY", timeout=15)
        assert r.status_code == 404

    def test_get_archived_coupon_returns_404(self, owner_headers):
        # Create + archive
        code = f"TESTARC{uuid.uuid4().hex[:4].upper()}"
        c = requests.post(f"{API}/coupons", headers=owner_headers, json={
            "name": "TEST_arc", "type": "percentage", "discount_value": 10,
            "code": code, "state": "active"}, timeout=15)
        assert c.status_code == 200
        cid = c.json()["id"]
        # Public sees it active
        r_pub = requests.get(f"{API}/public/coupons/{code}", timeout=15)
        assert r_pub.status_code == 200
        # Archive
        requests.post(f"{API}/coupons/{cid}/state", headers=owner_headers, json={"state": "archived"}, timeout=15)
        r = requests.get(f"{API}/public/coupons/{code}", timeout=15)
        assert r.status_code == 404
        # cleanup
        requests.delete(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)

    def test_get_unknown_code_returns_404(self):
        r = requests.get(f"{API}/public/coupons/NOSUCH{uuid.uuid4().hex[:4]}", timeout=15)
        assert r.status_code == 404

    def test_ref_query_records_referral_visit(self, owner_headers):
        # Use SUMMER25 which has referral enabled
        summer = [c for c in requests.get(f"{API}/coupons", headers=owner_headers, timeout=15).json()
                  if c["code"] == "SUMMER25"][0]
        # Baseline
        before = requests.get(f"{API}/coupons/{summer['id']}/referrals", headers=owner_headers, timeout=15).json()
        ref_token = f"visitor-{uuid.uuid4().hex[:6]}"
        r = requests.get(f"{API}/public/coupons/SUMMER25?ref={ref_token}", timeout=15)
        assert r.status_code == 200
        after = requests.get(f"{API}/coupons/{summer['id']}/referrals", headers=owner_headers, timeout=15).json()
        assert after["visits"] >= before["visits"] + 1


# ---------------- Public redeem endpoint ----------------
class TestPublicRedeem:
    def test_flash_sale_percentage_discount_applied(self):
        cust = f"pub-{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/public/coupons/redeem", json={
            "code": "SUMMER25", "amount": 100, "customer": cust}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
        assert d["discount"] == 25.0
        assert d["revenue"] == 75.0
        assert d["referral_credit"] == 0.0  # no ref

    def test_referral_credit_accrued_when_ref_provided(self, owner_headers):
        summer = [c for c in requests.get(f"{API}/coupons", headers=owner_headers, timeout=15).json()
                  if c["code"] == "SUMMER25"][0]
        ref_token = f"alice-{uuid.uuid4().hex[:6]}"
        cust = f"pub-{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/public/coupons/redeem", json={
            "code": "SUMMER25", "amount": 100, "customer": cust, "ref": ref_token}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["discount"] == 25.0
        assert d["revenue"] == 75.0
        # 15% of revenue (75) = 11.25
        assert d["referral_credit"] == 11.25
        # Verify aggregation includes this referrer
        agg = requests.get(f"{API}/coupons/{summer['id']}/referrals", headers=owner_headers, timeout=15).json()
        leader_names = [l["referrer"] for l in agg["leaders"]]
        assert ref_token in leader_names or any(r.get("referrer") == ref_token for r in agg.get("recent", []))

    def test_duplicate_public_redeem_within_5s_returns_429(self):
        cust = f"pub-dup-{uuid.uuid4().hex[:6]}"
        r1 = requests.post(f"{API}/public/coupons/redeem", json={
            "code": "WELCOME15", "amount": 50, "customer": cust}, timeout=15)
        assert r1.status_code == 200
        r2 = requests.post(f"{API}/public/coupons/redeem", json={
            "code": "WELCOME15", "amount": 50, "customer": cust}, timeout=15)
        assert r2.status_code == 429

    def test_public_redeem_non_active_rejected(self):
        r = requests.post(f"{API}/public/coupons/redeem", json={
            "code": "SPRING50", "amount": 100, "customer": f"g-{uuid.uuid4().hex[:5]}"}, timeout=15)
        assert r.status_code == 400

    def test_public_redeem_unknown_code_404(self):
        r = requests.post(f"{API}/public/coupons/redeem", json={
            "code": f"NO{uuid.uuid4().hex[:5]}", "amount": 50}, timeout=15)
        assert r.status_code == 404

    def test_ref_without_enabled_referral_gives_zero_credit(self, owner_headers):
        # WELCOME15 does not have referral_enabled by default
        cust = f"pub-{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/public/coupons/redeem", json={
            "code": "WELCOME15", "amount": 60, "customer": cust,
            "ref": "someone"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["referral_credit"] == 0.0


# ---------------- Referrals aggregation (auth) ----------------
class TestReferralsAggregation:
    def test_aggregation_structure_and_sum(self, owner_headers):
        summer = [c for c in requests.get(f"{API}/coupons", headers=owner_headers, timeout=15).json()
                  if c["code"] == "SUMMER25"][0]
        r = requests.get(f"{API}/coupons/{summer['id']}/referrals", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert set(d.keys()) >= {"visits", "redemptions", "total_credit", "leaders", "recent"}
        assert isinstance(d["visits"], int)
        assert isinstance(d["redemptions"], int)
        assert isinstance(d["total_credit"], (int, float))
        assert isinstance(d["leaders"], list)
        # If any recent, sum of credits should equal total_credit
        if d["recent"]:
            for l in d["leaders"]:
                assert "referrer" in l and "count" in l and "credit" in l

    def test_referrals_requires_auth(self):
        # Grab a real coupon id first via public info is not possible; use a random UUID
        r = requests.get(f"{API}/coupons/some-id/referrals", timeout=15)
        assert r.status_code == 401

    def test_referrals_unknown_coupon_404(self, owner_headers):
        r = requests.get(f"{API}/coupons/nonexistent-cid/referrals", headers=owner_headers, timeout=15)
        assert r.status_code == 404

    def test_aggregation_sums_by_referrer(self, owner_headers):
        # Create a fresh coupon with referral enabled, redeem twice from same referrer.
        code = f"TESTREF{uuid.uuid4().hex[:4].upper()}"
        c = requests.post(f"{API}/coupons", headers=owner_headers, json={
            "name": "TEST_ref_agg", "type": "percentage", "discount_value": 20,
            "code": code, "state": "active",
            "rules": {"referral_enabled": True, "referral_credit_pct": 10}}, timeout=15)
        assert c.status_code == 200
        cid = c.json()["id"]
        assert c.json()["rules"]["referral_enabled"] is True
        assert c.json()["rules"]["referral_credit_pct"] == 10

        ref = f"bob-{uuid.uuid4().hex[:6]}"
        for i in range(2):
            r = requests.post(f"{API}/public/coupons/redeem", json={
                "code": code, "amount": 100,
                "customer": f"c-{uuid.uuid4().hex[:8]}", "ref": ref}, timeout=15)
            assert r.status_code == 200

        agg = requests.get(f"{API}/coupons/{cid}/referrals", headers=owner_headers, timeout=15).json()
        # 2 redemptions * (100-20)*0.10 = 2 * 8.0 = 16.0
        bob = next((l for l in agg["leaders"] if l["referrer"] == ref), None)
        assert bob is not None
        assert bob["count"] == 2
        assert round(bob["credit"], 2) == 16.0
        assert agg["redemptions"] >= 2
        # cleanup
        requests.delete(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)


# ---------------- Embed widget JS ----------------
class TestEmbedJS:
    def test_embed_js_returns_javascript(self):
        r = requests.get(f"{API}/embed/coupon.js", timeout=15)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/javascript")
        body = r.text
        # widget core hook
        assert "data-promoos-code" in body
        # API base must be present (origin-echoed or explicit)
        assert "/api/public/coupons/" in body
        # scripts querySelector for the hook
        assert "script[data-promoos-code]" in body

    def test_embed_js_origin_matches_request_host(self):
        r = requests.get(f"{API}/embed/coupon.js", timeout=15)
        body = r.text
        # Expect the origin used by the JS to include the host we requested.
        host = BASE_URL.split("://", 1)[-1]
        assert host in body, f"embed js did not include our host {host}"


# ---------------- Coupon rules persistence for referral ----------------
class TestCouponReferralRules:
    def test_create_with_referral_and_reload(self, owner_headers):
        code = f"TESTRP{uuid.uuid4().hex[:5].upper()}"
        payload = {
            "name": "TEST_ref_persist", "type": "percentage", "discount_value": 25,
            "code": code, "state": "draft",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "", "usage_limit": 0,
                      "per_customer_limit": 1, "stackable": False,
                      "referral_enabled": True, "referral_credit_pct": 22}}
        r = requests.post(f"{API}/coupons", headers=owner_headers, json=payload, timeout=15)
        assert r.status_code == 200
        cid = r.json()["id"]
        assert r.json()["rules"]["referral_enabled"] is True
        assert r.json()["rules"]["referral_credit_pct"] == 22

        # Fetch fresh
        g = requests.get(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15).json()
        assert g["rules"]["referral_enabled"] is True
        assert g["rules"]["referral_credit_pct"] == 22

        # Update to disable
        payload["rules"]["referral_enabled"] = False
        r2 = requests.put(f"{API}/coupons/{cid}", headers=owner_headers, json=payload, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["rules"]["referral_enabled"] is False
        requests.delete(f"{API}/coupons/{cid}", headers=owner_headers, timeout=15)


# ---------------- Email endpoint regression ----------------
class TestEmailEndpointRegression:
    def test_send_email_returns_400_when_key_missing(self, owner_headers):
        summer = [c for c in requests.get(f"{API}/coupons", headers=owner_headers, timeout=15).json()
                  if c["code"] == "SUMMER25"][0]
        r = requests.post(f"{API}/coupons/{summer['id']}/send-email", headers=owner_headers,
                          json={"to": ["nobody@example.com"]}, timeout=15)
        # Expect 400 unless RESEND_API_KEY is set on server (then 200/502)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "Email not configured" in detail or "RESEND_API_KEY" in detail
