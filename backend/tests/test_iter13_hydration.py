"""Iteration 13 — re-verify the public_funnel hydration fix (workspace_id projection),
workspace_id stripping, positive cross-tenant isolation, and 7-template regression."""
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

SEED_SLUG = "qa-storefront-live"
ALL_TEMPLATES = ["diamond", "champagne", "noir", "emerald", "rose", "storefront", "electric"]

created_funnels = []


def _client(creds, label):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    if r.status_code != 200:
        pytest.fail(f"{label} login failed {r.status_code}: {r.text[:300]}")
    tok = r.json().get("token")
    if not tok:
        pytest.fail(f"{label} login response missing token: {r.text[:300]}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def oc():
    return _client(OWNER, "owner")


@pytest.fixture(scope="session")
def sc():
    return _client(SUPER, "superadmin")


@pytest.fixture(scope="session", autouse=True)
def cleanup(oc):
    yield
    for fid in created_funnels:
        try:
            oc.delete(f"{API}/funnels/{fid}", timeout=30)
        except Exception:
            pass


def _blocks_by_type(payload, btype):
    return [b for b in payload.get("blocks", []) if b.get("type") == btype]


# ---------- FIX #1: hydration on the seeded storefront funnel ----------
class TestSeedHydration:
    @pytest.fixture(scope="class")
    def seed_payload(self):
        r = requests.get(f"{API}/public/f/{SEED_SLUG}", timeout=30)
        if r.status_code != 200:
            pytest.fail(f"seed funnel {SEED_SLUG} GET returned {r.status_code}: {r.text[:300]}")
        return r.json()

    def test_product_block_hydrated(self, seed_payload):
        pb = _blocks_by_type(seed_payload, "product")
        assert pb, "no product block in seeded storefront funnel"
        props = pb[0]["props"]
        assert "product" in props, f"product NOT hydrated; props keys={list(props.keys())}"
        prod = props["product"]
        assert prod["name"] == "Signature Hoodie", prod.get("name")
        assert float(prod["price"]) == 49.0, prod.get("price")
        assert isinstance(prod.get("currency"), str) and prod["currency"], "missing currency"
        assert "id" in prod
        # internal fields must not leak
        assert "workspace_id" not in prod
        assert "_id" not in prod
        assert "stripe_price_id" not in prod

    def test_product_block_coupon_hydrated(self, seed_payload):
        props = _blocks_by_type(seed_payload, "product")[0]["props"]
        assert "coupon" in props, f"coupon NOT hydrated; props keys={list(props.keys())}"
        c = props["coupon"]
        assert c["code"] == "VIPELITJRIXE", c.get("code")
        assert c["type"] == "vip", c.get("type")
        assert float(c["discount_value"]) == 20.0, c.get("discount_value")
        assert "workspace_id" not in c and "_id" not in c

    def test_workspace_id_stripped_from_payload(self, seed_payload):
        assert "workspace_id" not in seed_payload, "workspace_id leaked in public payload"
        assert "_id" not in seed_payload
        assert "created_by" not in seed_payload

    def test_discounted_price_math(self, seed_payload):
        props = _blocks_by_type(seed_payload, "product")[0]["props"]
        price = float(props["product"]["price"])
        disc = float(props["coupon"]["discount_value"])
        assert round(price * (1 - disc / 100.0), 2) == 39.20


# ---------- FIX #1: coupon-block hydration on a fresh diamond funnel ----------
class TestCouponBlockHydration:
    def test_diamond_coupon_block_hydrates(self, oc):
        coupons = oc.get(f"{API}/coupons", timeout=30)
        assert coupons.status_code == 200, coupons.text[:200]
        cl = coupons.json()
        cl = cl.get("items", cl) if isinstance(cl, dict) else cl
        assert cl, "workspace has no coupons to test hydration with"
        coupon = cl[0]

        r = oc.post(f"{API}/funnels", json={"name": "TEST_iter13_diamond", "template_id": "diamond"}, timeout=30)
        assert r.status_code in (200, 201), r.text[:300]
        f = r.json()
        fid = f["id"]
        created_funnels.append(fid)

        blocks = f["blocks"]
        found = False
        for b in blocks:
            if b["type"] == "coupon":
                b.setdefault("props", {})["coupon_code"] = coupon["code"]
                found = True
        assert found, "diamond template has no coupon block"

        u = oc.put(f"{API}/funnels/{fid}", json={"blocks": blocks}, timeout=30)
        assert u.status_code == 200, u.text[:300]
        assert oc.post(f"{API}/funnels/{fid}/publish", timeout=30).status_code == 200

        pub = requests.get(f"{API}/public/f/{f['slug']}", timeout=30)
        assert pub.status_code == 200, f"{pub.status_code}: {pub.text[:300]}"
        payload = pub.json()
        assert "workspace_id" not in payload
        cb = _blocks_by_type(payload, "coupon")
        assert cb, "no coupon block returned"
        props = cb[0]["props"]
        assert "coupon" in props, f"coupon block NOT hydrated; keys={list(props.keys())}"
        assert props["coupon"]["code"] == coupon["code"]
        assert "workspace_id" not in props["coupon"]


# ---------- FIX #1: positive cross-tenant isolation ----------
class TestCrossTenantIsolation:
    def test_foreign_coupon_and_product_do_not_hydrate(self, oc, sc):
        """Owner's funnel referencing owner's own coupon hydrates (positive control),
        while the SAME funnel referencing a superadmin-workspace coupon must NOT hydrate."""
        # own coupon (positive control proving hydration is live)
        own = oc.get(f"{API}/coupons", timeout=30).json()
        own = own.get("items", own) if isinstance(own, dict) else own
        assert own, "owner workspace has no coupons"
        own_code = own[0]["code"]

        # create a coupon in the superadmin (other) workspace
        sr = sc.post(f"{API}/coupons", json={
            "name": "TEST_iter13_foreign", "type": "vip", "discount_value": 55.0,
        }, timeout=30)
        if sr.status_code not in (200, 201):
            pytest.fail(f"could not create foreign coupon: {sr.status_code} {sr.text[:300]}")
        foreign = sr.json()
        foreign_code = foreign["code"]
        foreign_id = foreign.get("id")
        assert foreign_code != own_code

        try:
            r = oc.post(f"{API}/funnels", json={"name": "TEST_iter13_xtenant", "template_id": "diamond"}, timeout=30)
            assert r.status_code in (200, 201), r.text[:300]
            f = r.json()
            fid = f["id"]
            created_funnels.append(fid)

            # POSITIVE: own coupon hydrates
            blocks = f["blocks"]
            for b in blocks:
                if b["type"] == "coupon":
                    b.setdefault("props", {})["coupon_code"] = own_code
            assert oc.put(f"{API}/funnels/{fid}", json={"blocks": blocks},
                          timeout=30).status_code == 200
            assert oc.post(f"{API}/funnels/{fid}/publish", timeout=30).status_code == 200
            p1 = requests.get(f"{API}/public/f/{f['slug']}", timeout=30).json()
            props1 = _blocks_by_type(p1, "coupon")[0]["props"]
            assert props1.get("coupon", {}).get("code") == own_code, \
                "positive control failed — hydration not working, isolation test would be vacuous"

            # NEGATIVE: foreign coupon must NOT hydrate
            for b in blocks:
                if b["type"] == "coupon":
                    b["props"]["coupon_code"] = foreign_code
                    b["props"].pop("coupon", None)
            assert oc.put(f"{API}/funnels/{fid}", json={"blocks": blocks},
                          timeout=30).status_code == 200
            p2 = requests.get(f"{API}/public/f/{f['slug']}", timeout=30).json()
            props2 = _blocks_by_type(p2, "coupon")[0]["props"]
            assert props2["coupon_code"] == foreign_code
            assert "coupon" not in props2, \
                f"CROSS-TENANT LEAK: foreign coupon hydrated -> {props2.get('coupon')}"
        finally:
            if foreign_id:
                sc.delete(f"{API}/coupons/{foreign_id}", timeout=30)

    def test_foreign_product_does_not_hydrate(self, oc, sc):
        # find a product in the owner workspace (positive control)
        op = oc.get(f"{API}/products", timeout=30).json()
        op = op.get("items", op) if isinstance(op, dict) else op
        assert op, "owner workspace has no products"
        own_pid = op[0]["id"]

        pr = sc.post(f"{API}/products", json={
            "name": "TEST_iter13_foreign_product", "price": 99.0, "currency": "USD",
        }, timeout=30)
        if pr.status_code not in (200, 201):
            pytest.fail(f"could not create foreign product: {pr.status_code} {pr.text[:300]}")
        foreign_pid = pr.json()["id"]

        try:
            r = oc.post(f"{API}/funnels", json={"name": "TEST_iter13_xprod", "template_id": "storefront"}, timeout=30)
            assert r.status_code in (200, 201), r.text[:300]
            f = r.json()
            fid = f["id"]
            created_funnels.append(fid)
            blocks = f["blocks"]

            # POSITIVE control
            for b in blocks:
                if b["type"] == "product":
                    b.setdefault("props", {})["product_id"] = own_pid
            assert oc.put(f"{API}/funnels/{fid}", json={"blocks": blocks},
                          timeout=30).status_code == 200
            assert oc.post(f"{API}/funnels/{fid}/publish", timeout=30).status_code == 200
            p1 = requests.get(f"{API}/public/f/{f['slug']}", timeout=30).json()
            pp1 = _blocks_by_type(p1, "product")[0]["props"]
            assert pp1.get("product", {}).get("id") == own_pid, "positive control failed"

            # NEGATIVE
            for b in blocks:
                if b["type"] == "product":
                    b["props"]["product_id"] = foreign_pid
                    b["props"].pop("product", None)
            assert oc.put(f"{API}/funnels/{fid}", json={"blocks": blocks},
                          timeout=30).status_code == 200
            p2 = requests.get(f"{API}/public/f/{f['slug']}", timeout=30).json()
            pp2 = _blocks_by_type(p2, "product")[0]["props"]
            assert pp2["product_id"] == foreign_pid
            assert "product" not in pp2, \
                f"CROSS-TENANT LEAK: foreign product hydrated -> {pp2.get('product')}"
        finally:
            sc.delete(f"{API}/products/{foreign_pid}", timeout=30)


# ---------- REGRESSION: all 7 templates ----------
@pytest.mark.parametrize("tpl", ALL_TEMPLATES)
def test_all_templates_create_publish_public_get(oc, tpl):
    r = oc.post(f"{API}/funnels", json={"name": f"TEST_iter13_{tpl}", "template_id": tpl}, timeout=30)
    assert r.status_code in (200, 201), f"{tpl} create failed {r.status_code}: {r.text[:300]}"
    f = r.json()
    created_funnels.append(f["id"])
    assert f.get("blocks"), f"{tpl} created with no blocks"
    u = oc.post(f"{API}/funnels/{f['id']}/publish", timeout=30)
    assert u.status_code == 200, u.text[:300]
    pub = requests.get(f"{API}/public/f/{f['slug']}", timeout=30)
    assert pub.status_code == 200, f"{tpl} public GET {pub.status_code}: {pub.text[:300]}"
    payload = pub.json()
    assert "workspace_id" not in payload, f"{tpl}: workspace_id leaked"
    assert len(payload["blocks"]) == len(f["blocks"])


# ---------- REGRESSION: customers list still works ----------
def test_customers_list(oc):
    r = oc.get(f"{API}/customers", timeout=30)
    assert r.status_code == 200, r.text[:200]
