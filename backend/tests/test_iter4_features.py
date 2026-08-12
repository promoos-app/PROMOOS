"""
PromoOS iteration 4 backend tests — Bundles A (Autopilot / Today's Promo / Weekly / One-Click),
B (Gift Cards / Store Credits / Public Wallet), C (Journeys), D (Customers CRM + AI Segment),
E (Templates), F (API Keys).

Uses public preview URL. Real Emergent LLM (Claude sonnet-5) is exercised for AI endpoints.
Auth via Bearer token stored in module-level fixtures.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://campaign-hub-436.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def owner_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@promoos.com", "password": "admin123"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def marketer_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "marketer@promoos.com", "password": "marketer123"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def viewer_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "viewer@promoos.com", "password": "viewer123"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _h(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


# =========== Bundle A: Autopilot ===========
class TestAutopilotConfig:
    def test_put_and_get_autopilot(self, owner_token):
        payload = {"enabled": True, "goal": "grow_sales", "max_discount": 20,
                   "frequency": "daily", "require_approval": True,
                   "brand_voice": "confident, playful, benefit-led",
                   "audience": "all"}
        r = requests.put(f"{BASE_URL}/api/autopilot/config",
                         json=payload, headers=_h(owner_token), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["max_discount"] == 20
        # persistence
        r2 = requests.get(f"{BASE_URL}/api/autopilot/config",
                          headers=_h(owner_token), timeout=15)
        assert r2.status_code == 200
        got = r2.json()
        assert got["max_discount"] == 20
        assert got["enabled"] is True
        assert got["goal"] == "grow_sales"

    def test_viewer_cannot_put_autopilot(self, viewer_token):
        r = requests.put(f"{BASE_URL}/api/autopilot/config",
                         json={"enabled": False, "max_discount": 25},
                         headers=_h(viewer_token), timeout=15)
        assert r.status_code == 403


# =========== Bundle A: AI Today's Promo & Weekly Calendar & One-Click ===========
class TestAIPromoEndpoints:
    def test_todays_promo_discount_capped(self, owner_token):
        # ensure cap is 20
        requests.put(f"{BASE_URL}/api/autopilot/config",
                     json={"enabled": True, "goal": "grow_sales", "max_discount": 20,
                           "frequency": "daily", "require_approval": True,
                           "brand_voice": "confident", "audience": "all"},
                     headers=_h(owner_token), timeout=15)
        r = requests.post(f"{BASE_URL}/api/ai/todays-promo",
                          json={"hint": "midweek boost for regulars"},
                          headers=_h(owner_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("type", "discount_value", "name", "headline", "description",
                  "terms", "cta", "audience"):
            assert k in d, f"missing key {k}: {d}"
        assert isinstance(d["discount_value"], (int, float))
        assert d["discount_value"] <= 20, f"cap violated: {d['discount_value']}"

    def test_weekly_calendar_returns_7_days_capped(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/ai/weekly-calendar",
                          json={}, headers=_h(owner_token), timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "days" in d
        days = d["days"]
        assert len(days) == 7, len(days)
        for day in days:
            assert "day" in day and "type" in day and "discount_value" in day
            assert "headline" in day and "audience" in day and "cta" in day
            assert day["discount_value"] <= 20, day

    def test_one_click_campaign_assets(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/ai/one-click-campaign",
                          json={"prompt": "Launch a 20% off weekend flash sale for VIP swim shoppers"},
                          headers=_h(owner_token), timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "coupon" in d
        assert isinstance(d["coupon"], dict)
        for k in ("email", "sms", "whatsapp", "push", "social_caption",
                  "landing_headline", "ad_copy"):
            assert k in d, f"missing {k}"
        # discount cap
        assert d["coupon"]["discount_value"] <= 20

    def test_one_click_approve_creates_active_coupon(self, owner_token):
        # generate a package
        gen = requests.post(f"{BASE_URL}/api/ai/one-click-campaign",
                            json={"prompt": "Weekend flash sale for TEST_iter4 approve flow"},
                            headers=_h(owner_token), timeout=90)
        assert gen.status_code == 200
        pkg = gen.json()
        # Force test-tag in name so we can identify our coupon
        pkg["coupon"]["name"] = "TEST_iter4_approve"
        appr = requests.post(f"{BASE_URL}/api/ai/one-click-campaign/approve",
                             json={"package": pkg, "activate": True},
                             headers=_h(owner_token), timeout=30)
        assert appr.status_code == 200, appr.text
        result = appr.json()
        assert result["ok"] is True
        assert "coupon_id" in result
        assert "code" in result
        # Verify persisted
        lst = requests.get(f"{BASE_URL}/api/coupons",
                           headers=_h(owner_token), timeout=15)
        coupons = lst.json()
        match = [c for c in coupons if c["id"] == result["coupon_id"]]
        assert len(match) == 1, "coupon not persisted"
        c = match[0]
        assert c["state"] == "active"
        assert c["code"] == result["code"]
        assert "campaign_assets" in c
        assert set(c["campaign_assets"].keys()) & {"email", "sms", "whatsapp"}


# =========== Bundle B: Gift Cards, Store Credits, Wallet ===========
class TestGiftCards:
    _issued = {}

    def test_issue_gift_card(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/gift-cards",
                          json={"amount": 50, "recipient_email": "TEST_gc_alice@example.com",
                                "recipient_name": "Alice", "sender_name": "Owner",
                                "message": "Thanks for the ride"},
                          headers=_h(owner_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] and d["code"].startswith("GC-")
        TestGiftCards._issued["code"] = d["code"]

    def test_public_gift_card_balance(self):
        code = TestGiftCards._issued["code"]
        r = requests.get(f"{BASE_URL}/api/public/gift-cards/{code}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["balance"] == 50.0
        assert d["state"] == "active"

    def test_redeem_partial_and_full(self, owner_token):
        code = TestGiftCards._issued["code"]
        r1 = requests.post(f"{BASE_URL}/api/gift-cards/redeem",
                           json={"code": code, "amount": 20},
                           headers=_h(owner_token), timeout=15)
        assert r1.status_code == 200
        assert r1.json()["balance"] == 30.0
        assert r1.json()["state"] == "active"
        r2 = requests.post(f"{BASE_URL}/api/gift-cards/redeem",
                           json={"code": code, "amount": 30},
                           headers=_h(owner_token), timeout=15)
        assert r2.status_code == 200
        assert r2.json()["balance"] == 0.0
        assert r2.json()["state"] == "redeemed"

    def test_list_gift_cards_returns_totals(self, owner_token):
        r = requests.get(f"{BASE_URL}/api/gift-cards", headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "total_issued" in d and "total_balance" in d and "cards" in d
        assert isinstance(d["cards"], list) and len(d["cards"]) >= 1

    def test_marketer_can_issue_but_viewer_cannot(self, marketer_token, viewer_token):
        rm = requests.post(f"{BASE_URL}/api/gift-cards",
                           json={"amount": 15, "recipient_email": "TEST_gc_m@example.com"},
                           headers=_h(marketer_token), timeout=15)
        assert rm.status_code == 200
        rv = requests.post(f"{BASE_URL}/api/gift-cards",
                           json={"amount": 10, "recipient_email": "TEST_gc_v@example.com"},
                           headers=_h(viewer_token), timeout=15)
        assert rv.status_code == 403


class TestStoreCredits:
    _issued_id = None

    def test_issue_store_credit(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/store-credits",
                          json={"customer": "TEST_alice@example.com", "amount": 25,
                                "reason": "customer_appreciation", "note": "test"},
                          headers=_h(owner_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["balance"] == 25.0
        TestStoreCredits._issued_id = d["credit_id"]

    def test_list_and_filter(self, owner_token):
        r = requests.get(f"{BASE_URL}/api/store-credits",
                         headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "total_outstanding" in d and "by_customer" in d
        assert d["total_outstanding"] >= 25
        # filter
        r2 = requests.get(f"{BASE_URL}/api/store-credits?customer=TEST_alice@example.com",
                          headers=_h(owner_token), timeout=15)
        assert r2.status_code == 200
        rows = r2.json()["credits"]
        assert all(c["customer"] == "TEST_alice@example.com" for c in rows)
        assert len(rows) >= 1


class TestPublicWallet:
    def test_alice_seeded_wallet(self, owner_token):
        # Ensure alice has gift card + store credit + loyalty points
        # Issue gift card + credit for alice as a top-up
        requests.post(f"{BASE_URL}/api/gift-cards",
                      json={"amount": 25, "recipient_email": "alice@example.com",
                            "recipient_name": "Alice"},
                      headers=_h(owner_token), timeout=15)
        requests.post(f"{BASE_URL}/api/store-credits",
                      json={"customer": "alice@example.com", "amount": 15,
                            "reason": "loyalty"},
                      headers=_h(owner_token), timeout=15)
        r = requests.get(f"{BASE_URL}/api/public/wallet/alice@example.com", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["customer"] == "alice@example.com"
        assert "gift_cards" in d and "store_credits" in d and "loyalty" in d and "recent_redemptions" in d
        # should have at least one gift card and credit
        assert len(d["gift_cards"]) >= 1
        assert d["store_credits_total"] >= 15


# =========== Bundle C: Journeys ===========
class TestJourneys:
    _jid = None

    def test_create_journey(self, marketer_token):
        r = requests.post(f"{BASE_URL}/api/journeys",
                          json={"name": "TEST_iter4_welcome_series", "trigger": "signup",
                                "steps": [{"type": "send_email", "template": "welcome"},
                                          {"type": "wait", "days": 3},
                                          {"type": "send_coupon", "code": "WELCOME15"}],
                                "enabled": False},
                          headers=_h(marketer_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == "TEST_iter4_welcome_series"
        assert d["trigger"] == "signup"
        assert len(d["steps"]) == 3
        TestJourneys._jid = d["id"]

    def test_list_journeys(self, owner_token):
        r = requests.get(f"{BASE_URL}/api/journeys",
                         headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert any(j["id"] == TestJourneys._jid for j in arr)

    def test_update_journey_enabled(self, owner_token):
        r = requests.put(f"{BASE_URL}/api/journeys/{TestJourneys._jid}",
                         json={"name": "TEST_iter4_welcome_series", "trigger": "signup",
                               "steps": [{"type": "send_email"}], "enabled": True},
                         headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        # verify
        lst = requests.get(f"{BASE_URL}/api/journeys",
                           headers=_h(owner_token), timeout=15).json()
        j = next(x for x in lst if x["id"] == TestJourneys._jid)
        assert j["enabled"] is True

    def test_delete_journey(self, owner_token):
        r = requests.delete(f"{BASE_URL}/api/journeys/{TestJourneys._jid}",
                            headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        lst = requests.get(f"{BASE_URL}/api/journeys",
                           headers=_h(owner_token), timeout=15).json()
        assert not any(j["id"] == TestJourneys._jid for j in lst)


# =========== Bundle D: Customers + AI Segment Promo ===========
class TestCustomers:
    def test_customers_aggregation(self, owner_token):
        r = requests.get(f"{BASE_URL}/api/customers",
                         headers=_h(owner_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "total" in d and "by_segment" in d and "customers" in d
        # seed has cust1..cust300 randomly picked, expect >= 50 (loose lower bound)
        assert d["total"] >= 50, f"total customers {d['total']} < 50"
        # segments present
        segs = set(c["segment"] for c in d["customers"])
        # at least one segment key should be one of known values
        assert segs & {"vip", "frequent", "regular", "new", "at_risk"}

    def test_ai_segment_promo_vip(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/ai/segment-promo",
                          json={"segment": "vip"},
                          headers=_h(owner_token), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("headline", "description", "cta", "discount_value", "type"):
            assert k in d, f"missing {k}: {d}"
        # cap 20 currently
        assert d["discount_value"] <= 20


# =========== Bundle E: Templates ===========
class TestTemplates:
    def test_list_templates(self, owner_token):
        r = requests.get(f"{BASE_URL}/api/templates", timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert len(arr) >= 6
        ids = {t["id"] for t in arr}
        assert "luxe-black" in ids

    def test_apply_template_updates_workspace(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/templates/apply",
                          json={"template_id": "luxe-black"},
                          headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        # verify workspace primary_color changed
        ws = requests.get(f"{BASE_URL}/api/workspace",
                          headers=_h(owner_token), timeout=15).json()
        assert ws["primary_color"].upper() == "#0A0A0A"
        assert ws["secondary_color"].upper() == "#D4AF37"

    def test_apply_template_viewer_forbidden(self, viewer_token):
        r = requests.post(f"{BASE_URL}/api/templates/apply",
                          json={"template_id": "minimal-mono"},
                          headers=_h(viewer_token), timeout=15)
        assert r.status_code == 403


# =========== Bundle F: API Keys ===========
class TestApiKeys:
    _kid = None
    _key_str = None

    def test_owner_can_create_key(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/api-keys",
                          json={"name": "TEST_iter4_key", "scopes": ["read", "write"]},
                          headers=_h(owner_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["key"].startswith("pk_live_")
        assert len(d["key"]) > 20
        assert "key_hash" not in d
        TestApiKeys._kid = d["id"]
        TestApiKeys._key_str = d["key"]

    def test_list_keys_hides_secret(self, owner_token):
        r = requests.get(f"{BASE_URL}/api/api-keys",
                         headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        arr = r.json()
        row = next((k for k in arr if k["id"] == TestApiKeys._kid), None)
        assert row is not None
        # No full key in the listing
        assert "key" not in row
        assert "key_hash" not in row
        assert row["key_preview"].startswith("pk_live_")

    def test_marketer_cannot_create_key(self, marketer_token):
        r = requests.post(f"{BASE_URL}/api/api-keys",
                          json={"name": "TEST_iter4_forbidden"},
                          headers=_h(marketer_token), timeout=15)
        assert r.status_code == 403

    def test_owner_can_revoke(self, owner_token):
        r = requests.post(f"{BASE_URL}/api/api-keys/{TestApiKeys._kid}/revoke",
                          headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        # verify state
        arr = requests.get(f"{BASE_URL}/api/api-keys",
                           headers=_h(owner_token), timeout=15).json()
        row = next(k for k in arr if k["id"] == TestApiKeys._kid)
        assert row["revoked"] is True

    def test_viewer_cannot_revoke(self, viewer_token, owner_token):
        # Create with owner then try revoke with viewer
        create = requests.post(f"{BASE_URL}/api/api-keys",
                               json={"name": "TEST_iter4_viewer_probe"},
                               headers=_h(owner_token), timeout=15).json()
        r = requests.post(f"{BASE_URL}/api/api-keys/{create['id']}/revoke",
                          headers=_h(viewer_token), timeout=15)
        assert r.status_code == 403


# =========== Regression: iterations 1-3 ===========
class TestRegression:
    def test_login_sets_httponly_cookie(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "admin@promoos.com", "password": "admin123"}, timeout=15)
        assert r.status_code == 200
        assert "access_token" in r.cookies

    def test_send_email_400_when_not_configured(self, owner_token):
        # Pick any active coupon
        coupons = requests.get(f"{BASE_URL}/api/coupons",
                               headers=_h(owner_token), timeout=15).json()
        cid = coupons[0]["id"]
        r = requests.post(f"{BASE_URL}/api/coupons/{cid}/send-email",
                          json={"to": ["nobody@example.com"]},
                          headers=_h(owner_token), timeout=15)
        assert r.status_code == 400
        assert "Email not configured" in r.text or "RESEND_API_KEY" in r.text

    def test_send_message_400_when_not_configured(self, owner_token):
        coupons = requests.get(f"{BASE_URL}/api/coupons",
                               headers=_h(owner_token), timeout=15).json()
        cid = coupons[0]["id"]
        r = requests.post(f"{BASE_URL}/api/coupons/{cid}/send-message",
                          json={"to": ["+15555550100"], "channel": "sms"},
                          headers=_h(owner_token), timeout=15)
        assert r.status_code == 400
        assert "not configured" in r.text.lower() or "TWILIO" in r.text

    def test_public_summer25_still_works(self):
        r = requests.get(f"{BASE_URL}/api/public/coupons/SUMMER25", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["code"] == "SUMMER25"
        assert d["state"] == "active"

    def test_loyalty_get(self, owner_token):
        r = requests.get(f"{BASE_URL}/api/loyalty",
                         headers=_h(owner_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "config" in d and "members" in d
