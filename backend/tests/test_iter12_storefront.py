"""Iteration 12 — Storefront funnel template lifecycle + REGISTRY refactor regression."""
import os
import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
base_url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
if not base_url:
    raise RuntimeError("REACT_APP_BACKEND_URL missing")
BASE_URL = base_url.rstrip("/")
API = f"{BASE_URL}/api"

OWNER = {"email": "admin@promoos.com", "password": "admin123"}
SUPER = {"email": "superadmin@promoos.com", "password": "sZpRBNpLKypsQDURBQNqMIzE"}


@pytest.fixture(scope="session")
def owner_token():
    r = requests.post(f"{API}/auth/login", json=OWNER, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"owner login failed {r.status_code}: {r.text[:300]}")
    return r.json()["token"]


@pytest.fixture(scope="session")
def super_token():
    r = requests.post(f"{API}/auth/login", json=SUPER, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"superadmin login failed {r.status_code}: {r.text[:300]}")
    return r.json()["token"]


@pytest.fixture(scope="session")
def oc(owner_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {owner_token}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def sc(super_token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {super_token}", "Content-Type": "application/json"})
    return s


created_funnels = []


@pytest.fixture(scope="session", autouse=True)
def cleanup(oc):
    yield
    for fid in created_funnels:
        oc.delete(f"{API}/funnels/{fid}", timeout=30)


# ---------- Templates ----------
class TestTemplates:
    def test_storefront_template_present_with_block_order(self):
        r = requests.get(f"{API}/funnels/templates", timeout=30)
        assert r.status_code == 200
        tpls = r.json()["templates"]
        ids = [t["id"] for t in tpls]
        for expected in ["diamond", "champagne", "noir", "emerald", "rose", "electric", "storefront"]:
            assert expected in ids, f"{expected} missing"
        sf = next(t for t in tpls if t["id"] == "storefront")
        assert [b["type"] for b in sf["blocks"]] == [
            "hero", "video", "countdown", "product", "features", "testimonial", "faq", "cta"]
        tb = next(b for b in sf["blocks"] if b["type"] == "testimonial")
        assert len(tb["props"]["items"]) == 3
        for it in tb["props"]["items"]:
            assert it["quote"] and it["author"] and it["role"]


# ---------- Storefront create ----------
class TestStorefrontCreate:
    def test_create_storefront_funnel(self, oc):
        r = oc.post(f"{API}/funnels", json={"name": "TEST_Storefront_A", "template_id": "storefront"}, timeout=30)
        assert r.status_code == 200, r.text[:400]
        f = r.json()
        created_funnels.append(f["id"])
        assert "_id" not in f
        blocks = f["blocks"]
        assert [b["type"] for b in blocks] == [
            "hero", "video", "countdown", "product", "features", "testimonial", "faq", "cta"]
        # countdown ends_at concrete ~72h
        cd = next(b for b in blocks if b["type"] == "countdown")["props"]
        assert cd.get("ends_at"), "countdown ends_at not resolved"
        assert "duration_hours" not in cd
        import datetime as dt
        ends = dt.datetime.fromisoformat(cd["ends_at"])
        delta_h = (ends - dt.datetime.now(dt.timezone.utc)).total_seconds() / 3600
        assert 71 < delta_h < 73, f"ends_at delta {delta_h}h"
        # testimonial items
        ti = next(b for b in blocks if b["type"] == "testimonial")["props"]["items"]
        assert len(ti) == 3
        # product block present
        pb = next(b for b in blocks if b["type"] == "product")
        assert pb["anchor"] == "product-1"
        assert "product_id" in pb["props"] and "coupon_code" in pb["props"]
        pytest.storefront_funnel = f

    def test_auto_attach_matches_workspace_data(self, oc):
        f = getattr(pytest, "storefront_funnel", None)
        assert f, "prior test failed"
        prods = oc.get(f"{API}/products", timeout=30)
        assert prods.status_code == 200, prods.text[:300]
        plist = prods.json()
        plist = plist if isinstance(plist, list) else plist.get("products", [])
        pb = next(b for b in f["blocks"] if b["type"] == "product")["props"]
        if plist:
            assert pb["product_id"], "product exists in workspace but not auto-attached"
            assert pb["product_id"] in [p["id"] for p in plist]
        else:
            assert pb["product_id"] == ""
        cps = oc.get(f"{API}/coupons", timeout=30)
        assert cps.status_code == 200
        cl = cps.json()
        cl = cl if isinstance(cl, list) else cl.get("coupons", [])
        if cl:
            assert pb["coupon_code"], "coupon exists but not auto-attached"
        else:
            assert pb["coupon_code"] == ""


# ---------- Publish + public hydration ----------
class TestPublicHydration:
    def test_publish_and_public_get_hydrates_product(self, oc):
        r0 = oc.post(f"{API}/funnels", json={"name": "TEST_Storefront_Pub", "template_id": "storefront"}, timeout=30)
        assert r0.status_code == 200, r0.text[:300]
        f = r0.json()
        created_funnels.append(f["id"])
        r = oc.post(f"{API}/funnels/{f['id']}/publish", timeout=30)
        assert r.status_code == 200, r.text[:300]
        assert r.json()["published"] is True
        pub = requests.get(f"{API}/public/f/{f['slug']}", timeout=30)
        assert pub.status_code == 200, pub.text[:300]
        d = pub.json()
        assert "workspace_id" not in d
        pb = next(b for b in d["blocks"] if b["type"] == "product")["props"]
        src = next(b for b in f["blocks"] if b["type"] == "product")["props"]
        if src.get("product_id"):
            assert "product" in pb, "product_id attached but props.product NOT hydrated"
            assert pb["product"].get("name")
            assert pb["product"].get("price") is not None
            assert pb["product"].get("currency")
        if src.get("coupon_code"):
            assert "coupon" in pb, "coupon_code attached but props.coupon NOT hydrated"

    def test_coupon_block_hydration_regression(self, oc):
        """Diamond template coupon block should hydrate when a real coupon code is set."""
        cps = oc.get(f"{API}/coupons", timeout=30)
        cl = cps.json()
        cl = cl if isinstance(cl, list) else cl.get("coupons", [])
        if not cl:
            pytest.skip("no coupons in workspace")
        code = cl[0]["code"]
        r = oc.post(f"{API}/funnels", json={"name": "TEST_Diamond_H", "template_id": "diamond"}, timeout=30)
        assert r.status_code == 200
        f = r.json()
        created_funnels.append(f["id"])
        blocks = f["blocks"]
        for b in blocks:
            if b["type"] == "coupon":
                b["props"]["coupon_code"] = code
        up = oc.put(f"{API}/funnels/{f['id']}", json={"blocks": blocks}, timeout=30)
        assert up.status_code == 200, up.text[:300]
        assert oc.post(f"{API}/funnels/{f['id']}/publish", timeout=30).status_code == 200
        pub = requests.get(f"{API}/public/f/{f['slug']}", timeout=30)
        assert pub.status_code == 200
        cb = next(b for b in pub.json()["blocks"] if b["type"] == "coupon")["props"]
        assert "coupon" in cb, "coupon block NOT hydrated on public funnel"
        assert cb["coupon"]["code"] == code

    def test_cross_tenant_isolation(self, oc, sc):
        """A product/coupon id from another workspace must not hydrate."""
        # get superadmin workspace product
        pr = sc.get(f"{API}/products", timeout=30)
        if pr.status_code != 200:
            pytest.skip("cannot list superadmin products")
        other = pr.json()
        other = other if isinstance(other, list) else other.get("products", [])
        op = oc.get(f"{API}/products", timeout=30).json()
        op = op if isinstance(op, list) else op.get("products", [])
        owner_ids = {p["id"] for p in op}
        foreign = next((p for p in other if p["id"] not in owner_ids), None)
        if not foreign:
            pytest.skip("no foreign product available")
        r = oc.post(f"{API}/funnels", json={"name": "TEST_XTenant", "template_id": "storefront"}, timeout=30)
        f = r.json()
        created_funnels.append(f["id"])
        blocks = f["blocks"]
        for b in blocks:
            if b["type"] == "product":
                b["props"]["product_id"] = foreign["id"]
                b["props"]["coupon_code"] = ""
        assert oc.put(f"{API}/funnels/{f['id']}", json={"blocks": blocks}, timeout=30).status_code == 200
        assert oc.post(f"{API}/funnels/{f['id']}/publish", timeout=30).status_code == 200
        pub = requests.get(f"{API}/public/f/{f['slug']}", timeout=30)
        assert pub.status_code == 200
        pb = next(b for b in pub.json()["blocks"] if b["type"] == "product")["props"]
        assert "product" not in pb, "CROSS-TENANT LEAK: foreign product hydrated"

    def test_unpublished_funnel_public_404(self, oc):
        r = oc.post(f"{API}/funnels", json={"name": "TEST_Unpub", "template_id": "storefront"}, timeout=30)
        f = r.json()
        created_funnels.append(f["id"])
        pub = requests.get(f"{API}/public/f/{f['slug']}", timeout=30)
        assert pub.status_code == 404


# ---------- Other templates regression ----------
@pytest.mark.parametrize("tpl", ["diamond", "champagne", "noir", "emerald", "rose", "electric"])
def test_other_templates_create_and_publish(oc, tpl):
    r = oc.post(f"{API}/funnels", json={"name": f"TEST_reg_{tpl}", "template_id": tpl}, timeout=30)
    assert r.status_code == 200, r.text[:300]
    f = r.json()
    created_funnels.append(f["id"])
    assert f["template_id"] == tpl
    assert len(f["blocks"]) > 0
    assert oc.post(f"{API}/funnels/{f['id']}/publish", timeout=30).status_code == 200
    pub = requests.get(f"{API}/public/f/{f['slug']}", timeout=30)
    assert pub.status_code == 200


# ---------- Customers page API ----------
class TestCustomers:
    def test_list_customers(self, oc):
        r = oc.get(f"{API}/customers", timeout=30)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert isinstance(data, (list, dict))
