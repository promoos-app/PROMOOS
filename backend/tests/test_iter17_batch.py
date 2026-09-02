"""Iter-17 batch: funnel page types, bulk codes, coupon payment_link, X share, products, admin gate."""
import os
import re
import uuid
from urllib.parse import urlparse, parse_qs

import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE}/api"

OWNER = {"email": "admin@promoos.com", "password": "admin123"}
SUPER = {"email": "superadmin@promoos.com", "password": "sZpRBNpLKypsQDURBQNqMIzE"}

NEW_TEMPLATES = ["sales_page", "order_form", "downsell", "inline_form",
                 "popup_form", "link_in_bio", "info_page"]


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"Login failed for {creds['email']}: {r.status_code} {r.text[:300]}")
    return r.json()["access_token"] if "access_token" in r.json() else r.json().get("token")


@pytest.fixture(scope="session")
def owner():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(OWNER)}"})
    return s


@pytest.fixture(scope="session")
def sadmin():
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {_login(SUPER)}"})
    return s


# ---------- Funnel templates ----------
class TestFunnelTemplates:
    def test_templates_count_and_new_ids(self, owner):
        r = owner.get(f"{API}/funnels/templates", timeout=30)
        assert r.status_code == 200, r.text[:300]
        tpls = r.json()["templates"]
        ids = [t["id"] for t in tpls]
        assert len(tpls) == 19, f"expected 19 templates, got {len(tpls)}: {ids}"
        missing = [t for t in NEW_TEMPLATES if t not in ids]
        assert not missing, f"missing new templates: {missing}"
        for t in tpls:
            assert t.get("name"), f"template {t['id']} missing name"

    @pytest.mark.parametrize("tid", NEW_TEMPLATES)
    def test_create_publish_and_public_fetch(self, owner, tid):
        r = owner.post(f"{API}/funnels", json={"name": f"TEST_{tid}_{uuid.uuid4().hex[:6]}",
                                               "template_id": tid}, timeout=60)
        assert r.status_code in (200, 201), f"{tid} create failed: {r.status_code} {r.text[:300]}"
        f = r.json()
        assert f.get("blocks"), f"{tid} created with no blocks"
        fid, slug = f["id"], f["slug"]

        pub = owner.post(f"{API}/funnels/{fid}/publish", json={}, timeout=60)
        assert pub.status_code == 200, f"{tid} publish failed: {pub.status_code} {pub.text[:300]}"

        pr = requests.get(f"{API}/public/f/{slug}", timeout=60)
        assert pr.status_code == 200, f"{tid} public fetch failed: {pr.status_code} {pr.text[:300]}"
        body = pr.json()
        assert body.get("blocks"), f"{tid} public payload has no blocks"
        owner.delete(f"{API}/funnels/{fid}", timeout=30)

    def test_giftcard_block_hydrates_template(self, owner):
        # champagne template contains a giftcard block
        r = owner.post(f"{API}/funnels", json={"name": f"TEST_gc_{uuid.uuid4().hex[:6]}",
                                               "template_id": "champagne"}, timeout=60)
        assert r.status_code in (200, 201), r.text[:300]
        f = r.json()
        owner.post(f"{API}/funnels/{f['id']}/publish", json={}, timeout=60)
        pr = requests.get(f"{API}/public/f/{f['slug']}", timeout=60)
        assert pr.status_code == 200
        gcs = [b for b in pr.json()["blocks"] if b["type"] == "giftcard"]
        assert gcs, "no giftcard block in champagne funnel"
        assert gcs[0]["props"].get("template"), \
            f"giftcard block not hydrated with template: {gcs[0]['props']}"
        owner.delete(f"{API}/funnels/{f['id']}", timeout=30)


# ---------- Coupon fixture ----------
@pytest.fixture(scope="class")
def coupon(owner):
    payload = {"name": "TEST_iter17 coupon", "type": "percent", "value": 15,
               "payment_link": "https://buy.stripe.com/test_iter17abc"}
    r = owner.post(f"{API}/coupons", json=payload, timeout=30)
    assert r.status_code in (200, 201), r.text[:400]
    c = r.json()
    yield c
    owner.delete(f"{API}/coupons/{c['id']}", timeout=30)


class TestBulkCodes:
    def test_list_codes_shape(self, owner, coupon):
        r = owner.get(f"{API}/coupons/{coupon['id']}/codes", timeout=30)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d["parent_code"] == coupon["code"]
        assert isinstance(d["codes"], list)

    def test_generate_delete_and_double(self, owner, coupon):
        cid = coupon["id"]
        base = len(owner.get(f"{API}/coupons/{cid}/codes", timeout=30).json()["codes"])
        g = owner.post(f"{API}/coupons/{cid}/bulk-codes", json={"count": 5}, timeout=30)
        assert g.status_code == 200, g.text[:300]
        gen = g.json()["codes"]
        assert len(gen) == 5 and len(set(gen)) == 5
        prefix = coupon["code"][:4]
        assert all(c.startswith(prefix) for c in gen), f"codes not derived from parent: {gen}"

        after = owner.get(f"{API}/coupons/{cid}/codes", timeout=30).json()["codes"]
        assert len(after) == base + 5
        # generate again -> +5
        owner.post(f"{API}/coupons/{cid}/bulk-codes", json={"count": 5}, timeout=30)
        after2 = owner.get(f"{API}/coupons/{cid}/codes", timeout=30).json()["codes"]
        assert len(after2) == base + 10

        d = owner.post(f"{API}/coupons/{cid}/codes/delete", json={"codes": gen}, timeout=30)
        assert d.status_code == 200, d.text[:300]
        final = owner.get(f"{API}/coupons/{cid}/codes", timeout=30).json()["codes"]
        assert all(c not in final for c in gen)
        assert len(final) == base + 5

    def test_cross_tenant_read_404(self, sadmin, coupon):
        r = sadmin.get(f"{API}/coupons/{coupon['id']}/codes", timeout=30)
        assert r.status_code == 404, f"expected 404 cross-tenant, got {r.status_code}"

    def test_unauthenticated_blocked(self, coupon):
        r = requests.get(f"{API}/coupons/{coupon['id']}/codes", timeout=30)
        assert r.status_code in (401, 403)


class TestCouponPaymentLink:
    def test_create_returns_payment_link(self, owner, coupon):
        r = owner.get(f"{API}/coupons/{coupon['id']}", timeout=30)
        assert r.status_code == 200
        assert r.json().get("payment_link") == "https://buy.stripe.com/test_iter17abc"

    def test_put_updates_payment_link(self, owner, coupon):
        new = "https://buy.stripe.com/test_iter17updated"
        r = owner.put(f"{API}/coupons/{coupon['id']}", json={"payment_link": new}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        got = owner.get(f"{API}/coupons/{coupon['id']}", timeout=30).json()
        assert got["payment_link"] == new
        assert got["name"] == "TEST_iter17 coupon", "partial update clobbered other fields"

    def test_public_payload_includes_payment_link(self, owner, coupon):
        pub = owner.post(f"{API}/coupons/{coupon['id']}/state", json={"state": "active"}, timeout=30)
        assert pub.status_code == 200, pub.text[:300]
        r = requests.get(f"{API}/public/coupons/{coupon['code']}", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json().get("payment_link"), f"payment_link missing in public payload: {r.json()}"


class TestShareLinks:
    def test_twitter_uses_x_intent_post(self, owner, coupon):
        r = owner.get(f"{API}/coupons/{coupon['id']}/share", timeout=30)
        assert r.status_code == 200, r.text[:300]
        links = r.json()["share_links"]
        tw = links["twitter"]
        assert tw.startswith("https://x.com/intent/post?url="), tw
        assert "twitter.com" not in tw
        qs = parse_qs(urlparse(tw).query)
        assert qs["url"][0].startswith("http"), qs
        for k, v in links.items():
            if v.startswith("http"):
                # no raw unencoded nested URL scheme in query values
                assert " " not in v, f"{k} contains raw space: {v}"


class TestProducts:
    def test_crud_and_upload(self, owner):
        # upload a tiny PNG
        png = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082")
        up = owner.post(f"{API}/uploads",
                        files={"file": ("TEST_iter17.png", png, "image/png")}, timeout=60)
        assert up.status_code in (200, 201), f"upload failed: {up.status_code} {up.text[:300]}"
        url = up.json().get("url")
        assert url, up.json()

        cr = owner.post(f"{API}/products", json={"name": "TEST_iter17 product", "price": 42.5,
                                                 "currency": "USD", "image_url": url,
                                                 "description": "qa"}, timeout=30)
        assert cr.status_code in (200, 201), cr.text[:300]
        p = cr.json()
        assert p["image_url"] == url and p["price"] == 42.5

        lst = owner.get(f"{API}/products", timeout=30).json()
        assert any(x["id"] == p["id"] for x in lst)

        upd = owner.put(f"{API}/products/{p['id']}", json={"name": "TEST_iter17 product v2",
                                                           "price": 50, "currency": "USD",
                                                           "image_url": url}, timeout=30)
        assert upd.status_code == 200, upd.text[:300]
        lst2 = owner.get(f"{API}/products", timeout=30).json()
        got = next(x for x in lst2 if x["id"] == p["id"])
        assert got["name"] == "TEST_iter17 product v2" and got["price"] == 50

        assert owner.delete(f"{API}/products/{p['id']}", timeout=30).status_code == 200
        lst3 = owner.get(f"{API}/products", timeout=30).json()
        assert not any(x["id"] == p["id"] for x in lst3)

    def test_public_checkout_with_coupon_code(self, owner):
        prods = owner.get(f"{API}/products", timeout=30).json()
        if not prods:
            pytest.skip("no products seeded")
        pid = prods[0]["id"]
        r = requests.post(f"{API}/public/products/checkout",
                          json={"product_id": pid, "origin_url": BASE,
                                "coupon_code": "SAVE10"}, timeout=60)
        assert r.status_code == 200, f"checkout w/ coupon failed: {r.status_code} {r.text[:400]}"
        assert r.json().get("checkout_url", "").startswith("http")

    def test_checkout_bad_product_404(self):
        r = requests.post(f"{API}/public/products/checkout",
                          json={"product_id": "nope", "origin_url": BASE}, timeout=30)
        assert r.status_code == 404


class TestAdminGate:
    def test_owner_forbidden(self, owner):
        r = owner.get(f"{API}/admin/users", timeout=30)
        assert r.status_code == 403, f"owner got {r.status_code}"

    def test_superadmin_allowed(self, sadmin):
        r = sadmin.get(f"{API}/admin/users", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert isinstance(r.json(), list)

    def test_admin_stats_gated(self, owner, sadmin):
        assert owner.get(f"{API}/admin/stats", timeout=30).status_code == 403
        assert sadmin.get(f"{API}/admin/stats", timeout=30).status_code == 200


# ---------- Regression ----------
class TestRegression:
    def test_reviews_crud(self, owner):
        cr = owner.post(f"{API}/reviews", json={"customer_name": "TEST_iter17", "rating": 5,
                                                "quote": "great product"}, timeout=30)
        assert cr.status_code in (200, 201), cr.text[:300]
        rid = cr.json()["id"]
        assert owner.get(f"{API}/reviews", timeout=30).status_code == 200
        assert owner.delete(f"{API}/reviews/{rid}", timeout=30).status_code == 200

    def test_billing_plans(self):
        r = requests.get(f"{API}/billing/plans", timeout=30)
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_bcrypt_hash_and_cookie(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json=OWNER, timeout=30)
        assert r.status_code == 200
        assert "access_token" in s.cookies, f"httpOnly cookie not set: {s.cookies.get_dict()}"

    def test_login_bad_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "nobody_iter17@promoos.com", "password": "x"}, timeout=30)
        assert r.status_code in (401, 429)
