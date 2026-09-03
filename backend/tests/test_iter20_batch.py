"""Iteration 20 backend tests: multi-step funnels, A/B variant analytics + promote,
product currency, footer block persistence, coupon design bg_image."""
import os
import uuid

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE = base_url.rstrip("/") + "/api"

OWNER = {"email": "admin@promoos.com", "password": "admin123"}


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE}/auth/login", json=OWNER)
    if r.status_code != 200:
        pytest.fail(f"Owner login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in {r.json()}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def funnel(client):
    """Create a dedicated test funnel."""
    r = client.post(f"{BASE}/funnels", json={"name": "TEST_iter20 funnel"})
    assert r.status_code in (200, 201), r.text[:300]
    f = r.json()
    pb = client.post(f"{BASE}/funnels/{f['id']}/publish")
    assert pb.status_code == 200, pb.text[:300]
    yield f
    client.delete(f"{BASE}/funnels/{f['id']}")


# ---------- Multi-step funnels ----------
class TestSteps:
    def test_steps_persist_and_public_render(self, client, funnel):
        fid = funnel["id"]
        steps = [
            {"name": "Step One", "slug_suffix": "step-one",
             "blocks": [{"id": str(uuid.uuid4()), "type": "hero",
                         "props": {"headline": "STEP ONE HEADLINE"}}]},
            {"name": "Step Two", "slug_suffix": "step-two",
             "blocks": [{"id": str(uuid.uuid4()), "type": "hero",
                         "props": {"headline": "STEP TWO HEADLINE"}}]},
        ]
        r = client.put(f"{BASE}/funnels/{fid}", json={"steps": steps})
        assert r.status_code == 200, r.text[:300]

        g = client.get(f"{BASE}/funnels/{fid}")
        assert g.status_code == 200
        d = g.json()
        assert "_id" not in d
        assert len(d.get("steps") or []) == 2
        assert d["steps"][0]["name"] == "Step One"
        assert d["steps"][0]["slug_suffix"] == "step-one"
        assert d["steps"][0]["blocks"][0]["props"]["headline"] == "STEP ONE HEADLINE"

        slug = d["slug"]
        p = requests.get(f"{BASE}/public/f/{slug}?step=step-two")
        assert p.status_code == 200, p.text[:300]
        pj = p.json()
        assert any(b.get("props", {}).get("headline") == "STEP TWO HEADLINE"
                   for b in pj.get("blocks", [])), f"step blocks not served: {pj.get('blocks')}"
        assert len(pj.get("steps_meta") or []) == 2

    def test_public_default_step_is_first(self, client, funnel):
        slug = client.get(f"{BASE}/funnels/{funnel['id']}").json()["slug"]
        p = requests.get(f"{BASE}/public/f/{slug}")
        assert p.status_code == 200
        assert any(b.get("props", {}).get("headline") == "STEP ONE HEADLINE"
                   for b in p.json().get("blocks", []))


# ---------- A/B variants ----------
class TestVariants:
    def test_variant_analytics_and_promote(self, client):
        r = client.post(f"{BASE}/funnels", json={"name": "TEST_iter20 ab"})
        assert r.status_code in (200, 201)
        fid = r.json()["id"]
        try:
            va = {"id": str(uuid.uuid4()), "name": "Variant A", "weight": 1,
                  "blocks": [{"id": str(uuid.uuid4()), "type": "hero",
                              "props": {"headline": "A WINS"}}]}
            vb = {"id": str(uuid.uuid4()), "name": "Variant B", "weight": 1,
                  "blocks": [{"id": str(uuid.uuid4()), "type": "hero",
                              "props": {"headline": "B LOSES"}}]}
            up = client.put(f"{BASE}/funnels/{fid}", json={"variants": [va, vb]})
            assert up.status_code == 200, up.text[:300]
            client.post(f"{BASE}/funnels/{fid}/publish")
            got = client.get(f"{BASE}/funnels/{fid}").json()
            assert len(got.get("variants") or []) == 2, got.get("variants")

            slug = got["slug"]
            # A: 25 views, 5 buys ; B: 25 views, 1 buy
            for vid, buys in ((va["id"], 5), (vb["id"], 1)):
                for _ in range(25):
                    t = requests.post(f"{BASE}/public/f/{slug}/track",
                                      json={"event": "view", "variant_id": vid})
                    assert t.status_code == 200, t.text[:200]
                for _ in range(buys):
                    t = requests.post(f"{BASE}/public/f/{slug}/track",
                                      json={"event": "buy_now_click", "variant_id": vid,
                                            "block_type": "product"})
                    assert t.status_code == 200, t.text[:200]

            an = client.get(f"{BASE}/funnels/{fid}/variants-analytics")
            assert an.status_code == 200, an.text[:300]
            aj = an.json()
            rows = aj.get("variants")
            assert isinstance(rows, list) and len(rows) == 2, aj
            byid = {x["id"]: x for x in rows}
            assert byid[va["id"]]["views"] == 25, byid[va["id"]]
            assert byid[va["id"]]["buy_now_clicks"] == 5
            assert byid[va["id"]]["conversion_pct"] == 20.0
            assert byid[vb["id"]]["conversion_pct"] == 4.0
            assert aj.get("winning_variant_id") == va["id"], aj

            pr = client.post(f"{BASE}/funnels/{fid}/promote-variant",
                             params={"variant_id": va["id"]})
            assert pr.status_code == 200, pr.text[:300]
            after = client.get(f"{BASE}/funnels/{fid}").json()
            assert (after.get("variants") or []) == []
            assert after["blocks"][0]["props"]["headline"] == "A WINS"
        finally:
            client.delete(f"{BASE}/funnels/{fid}")

    def test_promote_unknown_variant_404(self, client, funnel):
        r = client.post(f"{BASE}/funnels/{funnel['id']}/promote-variant",
                        params={"variant_id": "nope"})
        assert r.status_code == 404


# ---------- Product currency ----------
class TestProductCurrency:
    def test_currency_persists(self, client):
        c = client.post(f"{BASE}/products", json={"name": "TEST_iter20 eur product",
                                                  "price": 42.5, "currency": "EUR"})
        assert c.status_code in (200, 201), c.text[:300]
        p = c.json()
        assert p["currency"] == "EUR"
        pid = p["id"]
        try:
            lst = client.get(f"{BASE}/products").json()
            mine = next((x for x in lst if x["id"] == pid), None)
            assert mine and mine["currency"] == "EUR"
            u = client.put(f"{BASE}/products/{pid}", json={"name": "TEST_iter20 eur product",
                                                           "price": 42.5, "currency": "INR"})
            assert u.status_code == 200
            lst = client.get(f"{BASE}/products").json()
            assert next(x for x in lst if x["id"] == pid)["currency"] == "INR"
        finally:
            client.delete(f"{BASE}/products/{pid}")


# ---------- Footer block ----------
class TestFooterBlock:
    def test_footer_block_persists_and_public(self, client, funnel):
        fid = funnel["id"]
        blocks = [{"id": str(uuid.uuid4()), "type": "footer",
                   "props": {"brand": "TEST Brand", "address": "1 Test St",
                             "phone": "+1 555 0100", "email": "hi@test.co",
                             "privacy_url": "/privacy", "terms_url": "/terms",
                             "show_unsubscribe": True}}]
        r = client.put(f"{BASE}/funnels/{fid}", json={"blocks": blocks, "steps": []})
        assert r.status_code == 200, r.text[:300]
        slug = client.get(f"{BASE}/funnels/{fid}").json()["slug"]
        p = requests.get(f"{BASE}/public/f/{slug}")
        assert p.status_code == 200
        fb = next((b for b in p.json()["blocks"] if b["type"] == "footer"), None)
        assert fb, p.json()["blocks"]
        assert fb["props"]["brand"] == "TEST Brand"
        t = requests.post(f"{BASE}/public/f/{slug}/track",
                          json={"event": "cta_click", "block_type": "footer_unsubscribe",
                                "meta": {"email": "unsub@test.co"}})
        assert t.status_code == 200, t.text[:300]


# ---------- Coupon design bg_image ----------
class TestCouponBgImage:
    def test_bg_image_persists_and_public(self, client):
        code = f"TESTBG{uuid.uuid4().hex[:6].upper()}"
        payload = {"name": "TEST_iter20 bg", "code": code, "type": "percentage",
                   "discount_value": 10, "state": "active", "design": {"bg": "#111111", "fg": "#ffffff",
                                           "bg_image": "https://images.unsplash.com/photo-confetti"}}
        c = client.post(f"{BASE}/coupons", json=payload)
        assert c.status_code in (200, 201), c.text[:400]
        cid = c.json()["id"]
        try:
            g = client.get(f"{BASE}/coupons/{cid}")
            assert g.status_code == 200
            assert g.json()["design"].get("bg_image") == "https://images.unsplash.com/photo-confetti"
            pub = requests.get(f"{BASE}/public/coupons/{c.json().get('code', code)}")
            assert pub.status_code == 200, pub.text[:300]
            assert pub.json().get("design", {}).get("bg_image") == \
                "https://images.unsplash.com/photo-confetti"
        finally:
            client.delete(f"{BASE}/coupons/{cid}")


# ---------- Regression sweep ----------
class TestRegression:
    @pytest.mark.parametrize("path", [
        "/funnels", "/coupons", "/products", "/reviews", "/sequences",
        "/funnels/templates", "/library/coupon-types",
    ])
    def test_list_endpoints_ok(self, client, path):
        r = client.get(f"{BASE}{path}")
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text[:200]}"
        assert '"_id"' not in r.text

    def test_public_coupon_active(self):
        r = requests.get(f"{BASE}/public/coupons/VIPELITJRIXE")
        assert r.status_code == 200, r.text[:200]

    def test_qa_storefront_live_funnel(self):
        r = requests.get(f"{BASE}/public/f/qa-storefront-live")
        assert r.status_code == 200, r.text[:200]
