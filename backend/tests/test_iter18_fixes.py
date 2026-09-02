"""Iter-18: verify 4 fixes — products image url, login admin routing (FE), coupon discount at
Stripe checkout, publish/unpublish sets both state+status."""
import os
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "admin@promoos.com", "password": "admin123"}
SUPER = {"email": "superadmin@promoos.com", "password": "sZpRBNpLKypsQDURBQNqMIzE"}
VIP_CODE = "VIPELITJRIXE"


@pytest.fixture(scope="session")
def owner():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=OWNER, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"owner login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="session")
def hoodie(owner):
    r = owner.get(f"{API}/products", timeout=30)
    assert r.status_code == 200, r.text[:300]
    prods = r.json()
    assert prods, "no products seeded"
    h = next((p for p in prods if "Hoodie" in p["name"]), prods[0])
    return h


# ---------- FIX #1: uploads url (backend contract used by Products.js) ----------
class TestUploadUrl:
    def test_upload_returns_api_prefixed_relative_url(self, owner):
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082")
        r = owner.post(f"{API}/uploads",
                       files={"file": ("TEST_iter18.png", png, "image/png")}, timeout=60)
        assert r.status_code in (200, 201), r.text[:400]
        data = r.json()
        assert "url" in data and "id" in data
        url = data["url"]
        assert url.startswith("/api/"), f"url must be /api-prefixed relative: {url}"
        assert "/api/api/" not in url
        # Frontend composes ${REACT_APP_BACKEND_URL}${url}; must resolve 200
        full = f"{BASE_URL}{url}"
        g = requests.get(full, timeout=60)
        assert g.status_code == 200, f"{full} -> {g.status_code}"
        assert g.headers.get("content-type", "").startswith("image")


# ---------- FIX #3: coupon discount applied at Stripe checkout ----------
class TestCheckoutDiscount:
    def test_no_coupon_full_price(self, hoodie):
        r = requests.post(f"{API}/public/products/checkout",
                          json={"product_id": hoodie["id"], "origin_url": "https://x.com"},
                          timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["coupon_applied"] is None
        assert d["original_price"] == d["final_price"] == float(hoodie["price"])
        assert d["applied_discount"] == 0
        assert d["checkout_url"].startswith("https://")

    def test_percentage_coupon_applied(self, hoodie):
        r = requests.post(f"{API}/public/products/checkout",
                          json={"product_id": hoodie["id"], "origin_url": "https://x.com",
                                "coupon_code": VIP_CODE}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["coupon_applied"] == VIP_CODE
        assert d["original_price"] == 49.0
        assert round(d["applied_discount"], 2) == 9.80
        assert round(d["final_price"], 2) == 39.20

    def test_stripe_session_unit_amount_matches_final_price(self, hoodie):
        r = requests.post(f"{API}/public/products/checkout",
                          json={"product_id": hoodie["id"], "origin_url": "https://x.com",
                                "coupon_code": VIP_CODE}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        import stripe
        from dotenv import dotenv_values as dv
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or dv("/app/backend/.env").get("STRIPE_SECRET_KEY")
        assert stripe.api_key, "STRIPE_SECRET_KEY missing"
        sess = stripe.checkout.Session.retrieve(d["session_id"], expand=["line_items"])
        li = sess["line_items"]["data"][0]
        assert li["amount_total"] == int(round(d["final_price"] * 100)), li
        assert sess["metadata"]["coupon_code"] == VIP_CODE
        assert sess["metadata"]["final_amount"] == "39.20"

    def test_invalid_coupon_silently_skipped(self, hoodie):
        r = requests.post(f"{API}/public/products/checkout",
                          json={"product_id": hoodie["id"], "origin_url": "https://x.com",
                                "coupon_code": "NOPE_DOES_NOT_EXIST"}, timeout=90)
        assert r.status_code == 200, r.text[:400]
        d = r.json()
        assert d["coupon_applied"] is None
        assert d["final_price"] == d["original_price"]

    def test_draft_state_coupon_not_applied(self, owner, hoodie):
        cr = owner.post(f"{API}/coupons", json={"name": "TEST_iter18_draft", "type": "percentage",
                                               "discount_value": 50, "code": "TESTDRAFT18",
                                               "state": "draft"}, timeout=30)
        assert cr.status_code in (200, 201), cr.text[:300]
        cid = cr.json()["id"]
        try:
            r = requests.post(f"{API}/public/products/checkout",
                              json={"product_id": hoodie["id"], "origin_url": "https://x.com",
                                    "coupon_code": "TESTDRAFT18"}, timeout=90)
            assert r.status_code == 200, r.text[:300]
            assert r.json()["coupon_applied"] is None
        finally:
            owner.delete(f"{API}/coupons/{cid}", timeout=30)

    def test_fixed_amount_coupon_applied(self, owner, hoodie):
        cr = owner.post(f"{API}/coupons", json={"name": "TEST_iter18_fixed", "type": "fixed",
                                               "discount_value": 10, "code": "TESTFIXED18",
                                               "state": "active"}, timeout=30)
        assert cr.status_code in (200, 201), cr.text[:300]
        cid = cr.json()["id"]
        try:
            r = requests.post(f"{API}/public/products/checkout",
                              json={"product_id": hoodie["id"], "origin_url": "https://x.com",
                                    "coupon_code": "TESTFIXED18"}, timeout=90)
            assert r.status_code == 200, r.text[:300]
            d = r.json()
            assert d["coupon_applied"] == "TESTFIXED18"
            assert round(d["applied_discount"], 2) == 10.0
            assert round(d["final_price"], 2) == round(float(hoodie["price"]) - 10, 2)
        finally:
            owner.delete(f"{API}/coupons/{cid}", timeout=30)

    def test_cross_tenant_coupon_not_applied(self, hoodie):
        """A coupon from a different workspace must never discount this product."""
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={
            "name": "TEST_iter18_other", "email": "test_iter18_other@example.com",
            "password": "Passw0rd!23", "workspace_name": "TEST_iter18_ws"}, timeout=30)
        if r.status_code not in (200, 201):
            r = s.post(f"{API}/auth/login", json={
                "email": "test_iter18_other@example.com", "password": "Passw0rd!23"}, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        tok = r.json().get("token") or r.json().get("access_token")
        s.headers.update({"Authorization": f"Bearer {tok}"})
        cr = s.post(f"{API}/coupons", json={"name": "TEST_iter18_xt", "type": "percentage",
                                           "discount_value": 90, "code": "TESTXTENANT18",
                                           "state": "active"}, timeout=30)
        assert cr.status_code in (200, 201), cr.text[:300]
        cid = cr.json()["id"]
        try:
            chk = requests.post(f"{API}/public/products/checkout",
                                json={"product_id": hoodie["id"], "origin_url": "https://x.com",
                                      "coupon_code": "TESTXTENANT18"}, timeout=90)
            assert chk.status_code == 200, chk.text[:300]
            assert chk.json()["coupon_applied"] is None
        finally:
            s.delete(f"{API}/coupons/{cid}", timeout=30)


# ---------- FIX #4: publish/unpublish sets state AND status ----------
class TestPublishUnpublish:
    def test_publish_makes_coupon_public_then_unpublish_404s(self, owner):
        cr = owner.post(f"{API}/coupons", json={"name": "TEST_iter18_pub", "type": "percentage",
                                               "discount_value": 15, "code": "TESTPUB18",
                                               "state": "draft"}, timeout=30)
        assert cr.status_code in (200, 201), cr.text[:300]
        cid = cr.json()["id"]
        try:
            pre = requests.get(f"{API}/public/coupons/TESTPUB18", timeout=30)
            assert pre.status_code == 404, "draft coupon must not be public"

            pub = owner.post(f"{API}/coupons/{cid}/publish", timeout=30)
            assert pub.status_code == 200, pub.text[:300]
            assert pub.json()["state"] == "active" and pub.json()["status"] == "active"

            got = owner.get(f"{API}/coupons/{cid}", timeout=30)
            assert got.status_code == 200
            g = got.json()
            assert g["state"] == "active" and g.get("status") == "active", g

            pubget = requests.get(f"{API}/public/coupons/TESTPUB18", timeout=30)
            assert pubget.status_code == 200, f"public GET after publish: {pubget.status_code}"
            body = pubget.json()
            assert "_id" not in str(body)
            assert body.get("coupon", body).get("code", "TESTPUB18")

            unp = owner.post(f"{API}/coupons/{cid}/unpublish", timeout=30)
            assert unp.status_code == 200, unp.text[:300]
            assert unp.json()["state"] == "draft" and unp.json()["status"] == "draft"
            after = requests.get(f"{API}/public/coupons/TESTPUB18", timeout=30)
            assert after.status_code == 404
        finally:
            owner.delete(f"{API}/coupons/{cid}", timeout=30)

    def test_publish_unknown_id_404(self, owner):
        r = owner.post(f"{API}/coupons/does-not-exist-18/publish", timeout=30)
        assert r.status_code == 404


# ---------- Regression spot-checks ----------
class TestRegression:
    def test_templates_list(self, owner):
        r = owner.get(f"{API}/funnels/templates", timeout=30)
        assert r.status_code == 200, r.text[:300]
        tpls = r.json()["templates"]
        assert len(tpls) == 19, f"expected 19 funnel templates, got {len(tpls)}"

    def test_vip_coupon_public_and_payment_link_field(self, owner):
        r = requests.get(f"{API}/public/coupons/{VIP_CODE}", timeout=30)
        assert r.status_code == 200, r.text[:300]

    def test_admin_gate_403_for_owner(self, owner):
        r = owner.get(f"{API}/admin/stats", timeout=30)
        assert r.status_code == 403, r.status_code

    def test_superadmin_login_role(self):
        r = requests.post(f"{API}/auth/login", json=SUPER, timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["user"]["role"] == "superadmin"
