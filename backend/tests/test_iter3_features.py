"""Backend tests for PromoOS iteration 3 features:
- Twilio SMS/WhatsApp send-message (graceful 400 with creds unset)
- A/B testing (AI variant generation with Claude, list, promote)
- Public coupon variant selection + variant stats increment
- Loyalty program config + points crediting via public redeem
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
VIEWER_EMAIL, VIEWER_PW = _credential("Viewer")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"], r.json()["user"]


@pytest.fixture(scope="module")
def owner_headers():
    tok, _ = _login(OWNER_EMAIL, OWNER_PW)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def viewer_headers():
    tok, _ = _login(VIEWER_EMAIL, VIEWER_PW)
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def test_coupon(owner_headers):
    """Create a throwaway active coupon for iteration 3 tests, cleanup after."""
    code = f"IT3{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "name": "TEST_iter3", "type": "percentage", "discount_value": 20,
        "code": code, "state": "active",
        "headline": "Base headline", "description": "Base description",
        "cta": "Base CTA", "terms": "test",
        "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                  "usage_limit": 0, "per_customer_limit": 0, "stackable": False,
                  "referral_enabled": False, "referral_credit_pct": 10}
    }
    r = requests.post(f"{API}/coupons", json=payload, headers=owner_headers, timeout=15)
    assert r.status_code in (200, 201), f"create coupon failed: {r.status_code} {r.text}"
    c = r.json()
    yield c
    # Cleanup
    try:
        requests.delete(f"{API}/coupons/{c['id']}", headers=owner_headers, timeout=10)
    except Exception:
        pass


# ---------------- Twilio SMS / WhatsApp graceful fallback ----------------
class TestSendMessage:
    def test_send_sms_returns_400_when_twilio_unset(self, owner_headers, test_coupon):
        r = requests.post(
            f"{API}/coupons/{test_coupon['id']}/send-message",
            json={"to": ["+15551234567"], "channel": "sms"},
            headers=owner_headers, timeout=15)
        assert r.status_code == 400, f"expected 400, got {r.status_code} {r.text}"
        assert "not configured" in r.json().get("detail", "").lower() or \
               "sms" in r.json().get("detail", "").lower()

    def test_send_whatsapp_returns_400_when_twilio_unset(self, owner_headers, test_coupon):
        r = requests.post(
            f"{API}/coupons/{test_coupon['id']}/send-message",
            json={"to": ["+15551234567"], "channel": "whatsapp"},
            headers=owner_headers, timeout=15)
        assert r.status_code == 400
        assert "not configured" in r.json().get("detail", "").lower() or \
               "whatsapp" in r.json().get("detail", "").lower()

    def test_unknown_channel_returns_400(self, owner_headers, test_coupon):
        r = requests.post(
            f"{API}/coupons/{test_coupon['id']}/send-message",
            json={"to": ["+15551234567"], "channel": "carrier-pigeon"},
            headers=owner_headers, timeout=15)
        assert r.status_code == 400
        assert "channel" in r.json().get("detail", "").lower()

    def test_missing_coupon_returns_400_or_404(self, owner_headers):
        # Since Twilio unset, endpoint returns 400 BEFORE looking up coupon
        # so unknown coupon still returns 400. Test that not configured wins.
        r = requests.post(
            f"{API}/coupons/does-not-exist/send-message",
            json={"to": ["+15551234567"], "channel": "sms"},
            headers=owner_headers, timeout=15)
        assert r.status_code in (400, 404), f"got {r.status_code} {r.text}"

    def test_viewer_forbidden(self, viewer_headers, test_coupon):
        r = requests.post(
            f"{API}/coupons/{test_coupon['id']}/send-message",
            json={"to": ["+15551234567"], "channel": "sms"},
            headers=viewer_headers, timeout=15)
        assert r.status_code == 403


# ---------------- A/B Testing (AI variant generation) ----------------
class TestExperiments:
    def test_create_experiment_with_ai_variants(self, owner_headers, test_coupon):
        r = requests.post(
            f"{API}/coupons/{test_coupon['id']}/experiments",
            json={"n": 3, "use_ai": True},
            headers=owner_headers, timeout=90)
        assert r.status_code == 200, f"experiment create failed: {r.status_code} {r.text}"
        exp = r.json()
        assert exp["status"] == "running"
        assert exp["coupon_id"] == test_coupon["id"]
        assert len(exp["variants"]) == 3, f"expected 3 variants, got {len(exp['variants'])}"
        # Each variant should have distinct headline/description/cta
        headlines = [v["headline"] for v in exp["variants"]]
        descriptions = [v["description"] for v in exp["variants"]]
        assert len(set(headlines)) == 3, f"headlines not distinct: {headlines}"
        assert len(set(descriptions)) >= 2, f"descriptions too similar: {descriptions}"
        for v in exp["variants"]:
            assert v["headline"] and v["description"] and v["cta"]
            assert v["impressions"] == 0
            assert v["redemptions"] == 0
        # Save for later tests
        pytest.experiment_id = exp["id"]
        pytest.variant_ids = [v["id"] for v in exp["variants"]]

    def test_list_experiments_with_cvr(self, owner_headers, test_coupon):
        r = requests.get(f"{API}/coupons/{test_coupon['id']}/experiments",
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        exps = r.json()
        assert len(exps) >= 1
        running = [e for e in exps if e["status"] == "running"]
        assert len(running) >= 1
        for e in exps:
            for v in e["variants"]:
                assert "cvr" in v
                assert isinstance(v["cvr"], (int, float))

    def test_public_coupon_returns_variant_id_when_experiment_running(self, test_coupon):
        r = requests.get(f"{API}/public/coupons/{test_coupon['code']}?ref=alice-t", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "variant_id" in d, f"variant_id missing: {d.keys()}"
        assert "experiment_id" in d
        assert d["variant_id"] in pytest.variant_ids

    def test_public_coupon_variant_override_via_v_param(self, test_coupon):
        target = pytest.variant_ids[1]
        r = requests.get(f"{API}/public/coupons/{test_coupon['code']}?v={target}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["variant_id"] == target

    def test_public_coupon_deterministic_variant_per_ref(self, test_coupon):
        r1 = requests.get(f"{API}/public/coupons/{test_coupon['code']}?ref=bob-token", timeout=15).json()
        r2 = requests.get(f"{API}/public/coupons/{test_coupon['code']}?ref=bob-token", timeout=15).json()
        assert r1["variant_id"] == r2["variant_id"], "variant assignment not deterministic per ref"

    def test_variant_impressions_incremented(self, owner_headers, test_coupon):
        # By now several requests have hit — impressions on chosen variants > 0
        r = requests.get(f"{API}/coupons/{test_coupon['id']}/experiments",
                         headers=owner_headers, timeout=15)
        exps = r.json()
        running = next(e for e in exps if e["status"] == "running")
        total_impr = sum(v.get("impressions", 0) for v in running["variants"])
        assert total_impr > 0, "no impressions recorded despite public GETs"

    def test_redeem_credits_variant_stats(self, test_coupon):
        target = pytest.variant_ids[0]
        r = requests.post(f"{API}/public/coupons/redeem",
                          json={"code": test_coupon["code"], "amount": 100,
                                "customer": f"TEST_var_{uuid.uuid4().hex[:6]}@example.com",
                                "variant_id": target},
                          timeout=15)
        assert r.status_code == 200, f"redeem failed: {r.status_code} {r.text}"
        d = r.json()
        assert d["discount"] == 20.0
        assert d["revenue"] == 80.0

    def test_variant_redemption_incremented(self, owner_headers, test_coupon):
        target = pytest.variant_ids[0]
        r = requests.get(f"{API}/coupons/{test_coupon['id']}/experiments",
                         headers=owner_headers, timeout=15)
        exps = r.json()
        running = next(e for e in exps if e["status"] == "running")
        v = next(x for x in running["variants"] if x["id"] == target)
        assert v["redemptions"] >= 1
        assert v["revenue"] >= 80.0

    def test_promote_specific_variant(self, owner_headers, test_coupon):
        eid = pytest.experiment_id
        winner_id = pytest.variant_ids[1]
        r = requests.post(f"{API}/experiments/{eid}/promote",
                          json={"variant_id": winner_id}, headers=owner_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["winner"]["id"] == winner_id
        # Base coupon copy should be updated
        rc = requests.get(f"{API}/coupons/{test_coupon['id']}", headers=owner_headers, timeout=15)
        c = rc.json()
        assert c["headline"] == d["winner"]["headline"]
        assert c["cta"] == d["winner"]["cta"]
        # Experiment marked complete
        el = requests.get(f"{API}/coupons/{test_coupon['id']}/experiments",
                          headers=owner_headers, timeout=15).json()
        exp = next(e for e in el if e["id"] == eid)
        assert exp["status"] == "complete"
        assert exp["winner_variant_id"] == winner_id

    def test_promote_auto_picks_highest_rate(self, owner_headers, test_coupon):
        # Create a fresh experiment
        r = requests.post(f"{API}/coupons/{test_coupon['id']}/experiments",
                          json={"n": 2, "use_ai": True}, headers=owner_headers, timeout=90)
        assert r.status_code == 200
        exp = r.json()
        eid = exp["id"]
        vids = [v["id"] for v in exp["variants"]]
        # Warm impressions on both variants via public GET override so denominator > 0
        for vid in vids:
            for _ in range(3):
                requests.get(f"{API}/public/coupons/{test_coupon['code']}?v={vid}", timeout=10)
        # Redeem twice against variant vids[1] to force higher redemption rate
        for _ in range(2):
            requests.post(f"{API}/public/coupons/redeem",
                          json={"code": test_coupon["code"], "amount": 50,
                                "customer": f"TEST_auto_{uuid.uuid4().hex[:6]}@example.com",
                                "variant_id": vids[1]}, timeout=15)
            time.sleep(0.1)
        # promote with empty body
        pr = requests.post(f"{API}/experiments/{eid}/promote", json={},
                           headers=owner_headers, timeout=15)
        assert pr.status_code == 200
        w = pr.json()["winner"]
        assert w["id"] == vids[1], f"expected auto-promote to pick vids[1], got {w['id']}"


# ---------------- Loyalty ----------------
class TestLoyalty:
    def test_put_loyalty_config(self, owner_headers):
        tiers = [
            {"name": "Bronze", "threshold": 0},
            {"name": "Silver", "threshold": 500},
            {"name": "Gold", "threshold": 2000},
        ]
        r = requests.put(f"{API}/workspace/loyalty",
                         json={"enabled": True, "points_per_dollar": 2, "tiers": tiers},
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_get_loyalty_config(self, owner_headers):
        r = requests.get(f"{API}/loyalty", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["config"]["enabled"] is True
        assert d["config"]["points_per_dollar"] == 2.0
        assert isinstance(d["config"]["tiers"], list)
        assert "total_members" in d
        assert "by_tier" in d
        assert isinstance(d["members"], list)

    def test_public_redeem_credits_loyalty_points_for_alice(self, owner_headers):
        # Use SUMMER25 (25% discount, active, referral_enabled=true, seeded coupon)
        # ppd=2, amount=100 -> discount=25, rev=75, points=150
        customer = "alice@example.com"
        r = requests.post(f"{API}/public/coupons/redeem",
                          json={"code": "SUMMER25", "amount": 100, "customer": customer},
                          timeout=15)
        assert r.status_code == 200, f"redeem failed: {r.status_code} {r.text}"
        d = r.json()
        # SUMMER25 is flash_sale (25%) -> discount=25, rev=75
        assert d["discount"] == 25.0
        assert d["revenue"] == 75.0
        # Loyalty enabled, ppd=2, so 75*2=150 points awarded
        assert d["loyalty_points_awarded"] == 150.0, \
            f"expected 150 points, got {d.get('loyalty_points_awarded')}"

    def test_get_loyalty_shows_alice(self, owner_headers):
        r = requests.get(f"{API}/loyalty", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        alice = next((m for m in d["members"] if m["customer"] == "alice@example.com"), None)
        assert alice is not None, "alice@example.com not in loyalty members"
        assert alice["points"] >= 150, f"alice points={alice['points']}"
        assert alice["tier"] == "Bronze", f"alice tier={alice['tier']} (should be Bronze < 500)"
        assert d["total_members"] >= 1
        assert d["by_tier"].get("Bronze", 0) >= 1

    def test_viewer_cannot_update_loyalty(self, viewer_headers):
        r = requests.put(f"{API}/workspace/loyalty",
                         json={"enabled": False, "points_per_dollar": 1},
                         headers=viewer_headers, timeout=15)
        assert r.status_code == 403


# ---------------- Regression: existing endpoints still work ----------------
class TestRegression:
    def test_auth_login_sets_cookie(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": OWNER_EMAIL, "password": OWNER_PW}, timeout=15)
        assert r.status_code == 200
        assert "access_token" in r.cookies

    def test_coupons_list(self, owner_headers):
        r = requests.get(f"{API}/coupons", headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_send_email_400_no_key(self, owner_headers, test_coupon):
        r = requests.post(f"{API}/coupons/{test_coupon['id']}/send-email",
                          json={"to": ["a@b.com"]}, headers=owner_headers, timeout=15)
        assert r.status_code == 400
        assert "email" in r.json().get("detail", "").lower() or \
               "not configured" in r.json().get("detail", "").lower()

    def test_embed_js_served(self):
        r = requests.get(f"{API}/embed/coupon.js", timeout=15)
        assert r.status_code == 200
        assert "javascript" in r.headers.get("content-type", "")
        assert "data-promoos-code" in r.text

    def test_public_summer25_still_shape(self):
        r = requests.get(f"{API}/public/coupons/SUMMER25", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["code"] == "SUMMER25"
        assert d["state"] == "active"
