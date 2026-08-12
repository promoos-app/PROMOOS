"""Iteration 5 tests: Journey runtime + POS connectors.

Covers:
- POST /api/journeys/{jid}/enroll (idempotency + stats.entered increment)
- Background journey_worker executes wait/send_coupon steps
- GET /api/journeys/{jid}/runs contains current_step/status/log
- Public redeem auto-fires trigger=purchase
- POST /api/public/coupons/validate (no auth)
- POST /api/pos/{workspace_id}/shopify (X-PromoOS-Code + note_attributes fallback)
- POST /api/pos/{workspace_id}/woocommerce (meta_data + coupon_lines fallback)
- GET /api/pos/snippets (auth) — fully-qualified URLs
- Iter 1-4 regression smokes
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": "admin@promoos.com", "password": "admin123"},
                      timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def workspace_id(token):
    r = requests.get(f"{API}/workspace",
                     headers={"Authorization": f"Bearer {token}"}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["id"]


@pytest.fixture(scope="session")
def http(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}",
                      "Content-Type": "application/json"})
    return s


# ---------------- Iter 5.1: Journey enroll / runs ----------------
class TestJourneyEnroll:
    def _mkjourney(self, http, steps, trigger="signup", enabled=True, name=None):
        payload = {
            "name": name or f"TEST_iter5_{uuid.uuid4().hex[:6]}",
            "trigger": trigger, "enabled": enabled, "steps": steps,
        }
        r = http.post(f"{API}/journeys", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        # /journeys returns the doc; grab from list
        listr = http.get(f"{API}/journeys", timeout=15).json()
        for j in listr:
            if j["name"] == payload["name"]:
                return j
        raise AssertionError("Just-created journey not found in list")

    def test_enroll_creates_run_and_increments_entered(self, http):
        j = self._mkjourney(http, [{"type": "wait", "hours": 24}], trigger="signup")
        cust = f"TEST_enroll_{uuid.uuid4().hex[:6]}@example.com"
        r = http.post(f"{API}/journeys/{j['id']}/enroll",
                      json={"customer": cust, "email": cust}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("ok") is True and "run_id" in data

        # Verify stats.entered incremented
        listr = http.get(f"{API}/journeys", timeout=15).json()
        jj = next(x for x in listr if x["id"] == j["id"])
        assert jj["stats"]["entered"] >= 1

        # Idempotency: re-enroll same customer while pending/waiting
        r2 = http.post(f"{API}/journeys/{j['id']}/enroll",
                       json={"customer": cust, "email": cust}, timeout=15)
        assert r2.status_code == 200, r2.text
        assert r2.json().get("skipped") is True

    def test_runs_list_contains_current_step_status_log(self, http):
        j = self._mkjourney(http, [{"type": "wait", "hours": 24}])
        cust = f"TEST_runs_{uuid.uuid4().hex[:6]}@example.com"
        http.post(f"{API}/journeys/{j['id']}/enroll",
                  json={"customer": cust, "email": cust}, timeout=15)
        r = http.get(f"{API}/journeys/{j['id']}/runs", timeout=15)
        assert r.status_code == 200, r.text
        runs = r.json()
        assert isinstance(runs, list) and len(runs) >= 1
        row = next(x for x in runs if x["customer"] == cust)
        assert "current_step" in row and "status" in row and "log" in row

    def test_disabled_journey_rejects_enroll(self, http):
        j = self._mkjourney(http, [{"type": "wait", "hours": 24}], enabled=False)
        r = http.post(f"{API}/journeys/{j['id']}/enroll",
                      json={"customer": "TEST_off@example.com"}, timeout=15)
        assert r.status_code == 400, r.text


# ---------------- Iter 5.2: Background worker executes steps ----------------
class TestJourneyWorker:
    def test_worker_executes_wait_and_send_coupon(self, http):
        # steps: wait 0 hours (fires immediately) -> send_coupon 15%
        payload = {
            "name": f"TEST_worker_{uuid.uuid4().hex[:6]}",
            "trigger": "signup", "enabled": True,
            "steps": [
                {"type": "wait", "hours": 0},
                {"type": "send_coupon", "discount": 15},
            ],
        }
        r = http.post(f"{API}/journeys", json=payload, timeout=15)
        assert r.status_code == 200
        j = next(x for x in http.get(f"{API}/journeys").json() if x["name"] == payload["name"])
        cust = f"TEST_wrk_{uuid.uuid4().hex[:6]}@example.com"
        http.post(f"{API}/journeys/{j['id']}/enroll",
                  json={"customer": cust, "email": cust}, timeout=15)

        # Poll up to 95s (worker ticks every 30s; we need 2 ticks to run both steps)
        end = time.time() + 95
        status = None
        run = None
        while time.time() < end:
            runs = http.get(f"{API}/journeys/{j['id']}/runs").json()
            run = next((x for x in runs if x["customer"] == cust), None)
            if run and run.get("status") == "completed":
                status = "completed"
                break
            time.sleep(5)
        assert status == "completed", f"Run did not complete in 95s: {run}"

        # Log has entries per executed step (2)
        assert len(run["log"]) >= 2, run["log"]
        for entry in run["log"]:
            assert "at" in entry and "step" in entry and "type" in entry

        # A new coupon was created (source='journey', code starts with 'JRN-',
        # rules.usage_limit=1)
        cps = http.get(f"{API}/coupons").json()
        jrn = [c for c in cps if c.get("source") == "journey"
               and c["code"].startswith("JRN-")
               and c.get("rules", {}).get("usage_limit") == 1]
        assert len(jrn) >= 1, "No journey-sourced coupon in db.coupons"


# ---------------- Iter 5.3: Public redeem auto-fires purchase ----------------
class TestPublicRedeemFiresPurchase:
    def test_redeem_enrolls_in_purchase_journey(self, http):
        # Create a purchase-triggered journey
        payload = {
            "name": f"TEST_purchase_{uuid.uuid4().hex[:6]}",
            "trigger": "purchase", "enabled": True,
            "steps": [{"type": "wait", "hours": 24}],
        }
        r = http.post(f"{API}/journeys", json=payload, timeout=15)
        assert r.status_code == 200
        j = next(x for x in http.get(f"{API}/journeys").json() if x["name"] == payload["name"])

        # Create an active coupon
        cp = {
            "name": f"TEST_iter5_purchase_{uuid.uuid4().hex[:6]}",
            "type": "percentage", "discount_value": 10,
            "headline": "10% off", "description": "", "terms": "",
            "cta": "Buy", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        rc = http.post(f"{API}/coupons", json=cp, timeout=15)
        assert rc.status_code == 200, rc.text
        code = rc.json()["code"]
        # Activate
        http.post(f"{API}/coupons/{rc.json()['id']}/state",
                  json={"state": "active"}, timeout=15)

        cust = f"TEST_redeem_{uuid.uuid4().hex[:6]}@example.com"
        # No auth for public
        pub = requests.post(f"{API}/public/coupons/redeem",
                            json={"code": code, "amount": 100, "customer": cust},
                            timeout=15)
        assert pub.status_code == 200, pub.text

        # Poll runs for this journey
        end = time.time() + 15
        found = False
        while time.time() < end:
            runs = http.get(f"{API}/journeys/{j['id']}/runs").json()
            if any(r["customer"] == cust for r in runs):
                found = True
                break
            time.sleep(1)
        assert found, "purchase-trigger journey did not enroll the redeemer"


# ---------------- Iter 5.4: Public validate (no auth) ----------------
class TestPublicValidate:
    def test_validate_percentage(self, http):
        cp = {
            "name": f"TEST_val_pct_{uuid.uuid4().hex[:6]}",
            "type": "percentage", "discount_value": 20,
            "headline": "20% off", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]; cid = r.json()["id"]
        http.post(f"{API}/coupons/{cid}/state", json={"state": "active"})

        pub = requests.post(f"{API}/public/coupons/validate",
                            json={"code": code, "amount": 100}, timeout=15)
        assert pub.status_code == 200, pub.text
        d = pub.json()
        assert d["ok"] is True
        assert d["type"] == "percentage"
        assert d["value"] == 20
        assert d["discount"] == 20.0

    def test_validate_fixed(self, http):
        cp = {
            "name": f"TEST_val_fx_{uuid.uuid4().hex[:6]}",
            "type": "fixed", "discount_value": 30,
            "headline": "$30 off", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]; cid = r.json()["id"]
        http.post(f"{API}/coupons/{cid}/state", json={"state": "active"})
        pub = requests.post(f"{API}/public/coupons/validate",
                            json={"code": code, "amount": 100}, timeout=15)
        assert pub.status_code == 200
        assert pub.json()["discount"] == 30.0

    def test_validate_bogo_is_half(self, http):
        cp = {
            "name": f"TEST_val_bogo_{uuid.uuid4().hex[:6]}",
            "type": "bogo", "discount_value": 50,
            "headline": "BOGO", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]; cid = r.json()["id"]
        http.post(f"{API}/coupons/{cid}/state", json={"state": "active"})
        pub = requests.post(f"{API}/public/coupons/validate",
                            json={"code": code, "amount": 100}, timeout=15)
        assert pub.status_code == 200
        assert pub.json()["discount"] == 50.0

    def test_validate_404_for_missing(self):
        pub = requests.post(f"{API}/public/coupons/validate",
                            json={"code": "NOPE-XYZ-999", "amount": 100}, timeout=15)
        assert pub.status_code == 404

    def test_validate_400_for_inactive(self, http):
        cp = {
            "name": f"TEST_val_off_{uuid.uuid4().hex[:6]}",
            "type": "percentage", "discount_value": 10,
            "headline": "10% off", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]
        # NOT activating -> state is 'draft'
        pub = requests.post(f"{API}/public/coupons/validate",
                            json={"code": code, "amount": 100}, timeout=15)
        assert pub.status_code == 400


# ---------------- Iter 5.5: POS Shopify webhook ----------------
class TestPosShopify:
    def test_shopify_applies_with_header(self, http, workspace_id):
        cp = {
            "name": f"TEST_shopify_{uuid.uuid4().hex[:6]}",
            "type": "percentage", "discount_value": 20,
            "headline": "20% off", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]; cid = r.json()["id"]
        http.post(f"{API}/coupons/{cid}/state", json={"state": "active"})
        order_id = f"shopify-{uuid.uuid4().hex[:8]}"
        body = {
            "id": order_id, "total_price": "150.00", "currency": "USD",
            "email": f"TEST_sh_{uuid.uuid4().hex[:6]}@example.com",
        }
        r2 = requests.post(f"{API}/pos/{workspace_id}/shopify",
                           json=body,
                           headers={"X-PromoOS-Code": code,
                                    "Content-Type": "application/json"},
                           timeout=15)
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["applied"] is True
        assert d["discount"] > 0
        assert d["revenue"] > 0
        assert d["order_id"] == order_id

    def test_shopify_note_attributes_fallback(self, http, workspace_id):
        cp = {
            "name": f"TEST_shopify_na_{uuid.uuid4().hex[:6]}",
            "type": "percentage", "discount_value": 15,
            "headline": "15% off", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]; cid = r.json()["id"]
        http.post(f"{API}/coupons/{cid}/state", json={"state": "active"})
        body = {
            "id": f"shopify-{uuid.uuid4().hex[:8]}", "total_price": "80.00",
            "currency": "USD", "email": "TEST_na@example.com",
            "note_attributes": [{"name": "promoos", "value": code}],
        }
        r2 = requests.post(f"{API}/pos/{workspace_id}/shopify",
                           json=body, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["applied"] is True

    def test_shopify_no_code_returns_skip(self, workspace_id):
        r2 = requests.post(f"{API}/pos/{workspace_id}/shopify",
                           json={"id": "x", "total_price": "10"}, timeout=15)
        assert r2.status_code == 200
        d = r2.json()
        assert d["applied"] is False
        assert "no PromoOS code" in (d.get("reason") or "")

    def test_shopify_unknown_workspace_404(self):
        r2 = requests.post(f"{API}/pos/does-not-exist/shopify",
                           json={"id": "x", "total_price": "10"},
                           headers={"X-PromoOS-Code": "ANY"}, timeout=15)
        assert r2.status_code == 404


# ---------------- Iter 5.6: POS WooCommerce webhook ----------------
class TestPosWoocommerce:
    def test_woo_applies_with_meta_data(self, http, workspace_id):
        cp = {
            "name": f"TEST_woo_{uuid.uuid4().hex[:6]}",
            "type": "percentage", "discount_value": 25,
            "headline": "25% off", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]; cid = r.json()["id"]
        http.post(f"{API}/coupons/{cid}/state", json={"state": "active"})
        order_id = f"woo-{uuid.uuid4().hex[:8]}"
        body = {
            "id": order_id, "total": "200.00", "currency": "USD",
            "billing": {"email": f"TEST_woo_{uuid.uuid4().hex[:6]}@example.com"},
            "meta_data": [{"key": "promoos", "value": code}],
        }
        r2 = requests.post(f"{API}/pos/{workspace_id}/woocommerce",
                           json=body, timeout=15)
        assert r2.status_code == 200, r2.text
        d = r2.json()
        assert d["applied"] is True
        assert d["order_id"] == order_id

    def test_woo_coupon_lines_fallback(self, http, workspace_id):
        cp = {
            "name": f"TEST_woo_cl_{uuid.uuid4().hex[:6]}",
            "type": "percentage", "discount_value": 10,
            "headline": "10% off", "description": "", "terms": "",
            "cta": "Save", "audience": "all",
            "rules": {"min_cart": 0, "scope": "all", "scope_value": "",
                      "usage_limit": 100, "per_customer_limit": 100,
                      "stackable": False, "start_date": None, "end_date": None,
                      "referral_enabled": False, "referral_credit_pct": 10},
        }
        r = http.post(f"{API}/coupons", json=cp, timeout=15)
        code = r.json()["code"]; cid = r.json()["id"]
        http.post(f"{API}/coupons/{cid}/state", json={"state": "active"})
        body = {
            "id": f"woo-{uuid.uuid4().hex[:8]}", "total": "50.00",
            "currency": "USD", "billing": {"email": "TEST_woo_cl@example.com"},
            "coupon_lines": [{"code": code}],
        }
        r2 = requests.post(f"{API}/pos/{workspace_id}/woocommerce",
                           json=body, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["applied"] is True


# ---------------- Iter 5.7: /pos/snippets ----------------
class TestPosSnippets:
    def test_snippets_auth_required(self):
        r = requests.get(f"{API}/pos/snippets", timeout=15)
        # Middleware returns 401 or 403
        assert r.status_code in (401, 403)

    def test_snippets_returns_full_urls(self, http, workspace_id):
        r = http.get(f"{API}/pos/snippets", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "shopify" in d and "woocommerce" in d and "generic_curl" in d
        s = d["shopify"]; w = d["woocommerce"]
        assert s["topic"] == "orders/create"
        assert w["topic"] == "order.created"
        assert s["webhook_url"].startswith("https://")
        assert w["webhook_url"].startswith("https://")
        assert f"/api/pos/{workspace_id}/shopify" in s["webhook_url"]
        assert f"/api/pos/{workspace_id}/woocommerce" in w["webhook_url"]
        assert isinstance(s["instructions"], list) and len(s["instructions"]) >= 3
        assert isinstance(w["instructions"], list) and len(w["instructions"]) >= 3
        assert isinstance(d["generic_curl"], str) and "curl" in d["generic_curl"]


# ---------------- Iter 1-4 regression smokes ----------------
class TestRegression:
    def test_dashboard_stats(self, http):
        r = http.get(f"{API}/dashboard/stats", timeout=15)
        assert r.status_code == 200
        assert "total_redemptions" in r.json()

    def test_list_coupons(self, http):
        r = http.get(f"{API}/coupons", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_customers(self, http):
        r = http.get(f"{API}/customers", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "customers" in d and isinstance(d["customers"], list)

    def test_gift_cards(self, http):
        r = http.get(f"{API}/gift-cards", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "total_issued" in d

    def test_store_credits(self, http):
        r = http.get(f"{API}/store-credits", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "credits" in d and isinstance(d["credits"], list)

    def test_loyalty_members(self, http):
        r = http.get(f"{API}/loyalty", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "config" in d and "total_members" in d
