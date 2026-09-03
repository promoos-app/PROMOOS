"""Iter21 verification: currency symbol localization data, main-page-in-steps, A/B clone context."""
import os
import uuid

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


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=OWNER)
    if r.status_code != 200:
        pytest.fail(f"Owner login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    assert token, f"no token in login response: {r.text[:300]}"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


@pytest.fixture(scope="module")
def artifacts(client):
    created = {"products": [], "funnels": []}
    yield created
    for pid in created["products"]:
        client.delete(f"{API}/products/{pid}")
    for fid in created["funnels"]:
        client.delete(f"{API}/funnels/{fid}")


@pytest.fixture(scope="module")
def eur_product(client, artifacts):
    r = client.post(f"{API}/products", json={
        "name": "TEST_EUR Product", "description": "iter21", "price": 29.5, "currency": "EUR"})
    assert r.status_code in (200, 201), r.text[:300]
    p = r.json()
    artifacts["products"].append(p["id"])
    assert p["currency"] == "EUR"
    assert p["price"] == 29.5
    # persistence check
    lst = client.get(f"{API}/products").json()
    got = next((x for x in lst if x["id"] == p["id"]), None)
    assert got and got["currency"] == "EUR" and got["price"] == 29.5
    assert "_id" not in got
    return p


@pytest.fixture(scope="module")
def funnel(client, artifacts, eur_product):
    slug = f"test-iter21-{uuid.uuid4().hex[:8]}"
    r = client.post(f"{API}/funnels", json={"name": "TEST_Iter21 Funnel",
                                            "template_id": "blank", "slug": slug})
    assert r.status_code in (200, 201), r.text[:400]
    f = r.json()
    artifacts["funnels"].append(f["id"])
    # main blocks: heading + product
    main_blocks = [
        {"type": "heading", "props": {"text": "MAIN PAGE HEADING"}},
        {"type": "product", "props": {"product_id": eur_product["id"]}},
    ]
    steps = [
        {"name": "Upsell", "slug_suffix": "upsell",
         "blocks": [{"type": "heading", "props": {"text": "UPSELL STEP"}}]},
        {"name": "Thanks", "slug_suffix": "thanks",
         "blocks": [{"type": "heading", "props": {"text": "THANKS STEP"}}]},
    ]
    r = client.put(f"{API}/funnels/{f['id']}", json={"blocks": main_blocks, "steps": steps})
    assert r.status_code == 200, r.text[:300]
    r = client.post(f"{API}/funnels/{f['id']}/publish")
    assert r.status_code == 200, r.text[:300]
    return {**f, "slug": slug}


# ---------- FIX #1: currency data reaches public payload for symbol rendering ----------
class TestCurrencyLocalization:
    def test_public_product_block_carries_currency(self, funnel, eur_product):
        r = requests.get(f"{API}/public/f/{funnel['slug']}")
        assert r.status_code == 200, r.text[:300]
        blocks = r.json()["blocks"]
        pb = next((b for b in blocks if b["type"] == "product"), None)
        assert pb, f"no product block in {[b['type'] for b in blocks]}"
        prod = pb["props"].get("product")
        assert prod, f"product not hydrated: {pb['props']}"
        assert prod["currency"] == "EUR"
        assert float(prod["price"]) == 29.5

    def test_fmtmoney_symbol_map(self):
        src = open("/app/frontend/src/pages/PublicFunnelBlocks.js").read()
        assert "export function fmtMoney" in src
        for code, sym in [("EUR", "€"), ("GBP", "£"), ("JPY", "¥"), ("INR", "₹")]:
            assert f'{code}: "{sym}"' in src, f"{code} symbol missing in map"
        assert "zeroDecimal" in src
        prod_src = open("/app/frontend/src/pages/Products.js").read()
        assert "fmtMoney(p.price, p.currency)" in prod_src


# ---------- FIX #2: main page is part of steps ----------
class TestMainPageInSteps:
    def test_no_step_param_returns_main(self, funnel):
        r = requests.get(f"{API}/public/f/{funnel['slug']}")
        assert r.status_code == 200
        d = r.json()
        assert d["active_step"] == {"id": "main", "name": "Main", "slug_suffix": ""}, d.get("active_step")
        texts = [b["props"].get("text") for b in d["blocks"] if b["type"] == "heading"]
        assert "MAIN PAGE HEADING" in texts, texts
        metas = d.get("steps_meta")
        assert metas and len(metas) == 3, metas
        assert metas[0]["id"] == "main"
        assert [m["slug_suffix"] for m in metas] == ["", "upsell", "thanks"]

    def test_step_param_returns_step_blocks(self, funnel):
        r = requests.get(f"{API}/public/f/{funnel['slug']}", params={"step": "thanks"})
        assert r.status_code == 200
        d = r.json()
        assert d["active_step"]["slug_suffix"] == "thanks"
        assert [b["props"].get("text") for b in d["blocks"]] == ["THANKS STEP"]
        assert len(d["steps_meta"]) == 3

    def test_step_main_alias(self, funnel):
        d = requests.get(f"{API}/public/f/{funnel['slug']}", params={"step": "main"}).json()
        assert d["active_step"]["id"] == "main"
        assert "MAIN PAGE HEADING" in [b["props"].get("text") for b in d["blocks"] if b["type"] == "heading"]

    def test_unknown_step_404(self, funnel):
        r = requests.get(f"{API}/public/f/{funnel['slug']}", params={"step": "nope-xyz"})
        assert r.status_code == 404


# ---------- FIX #3: addVariant clones active surface ----------
class TestVariantCloneContext:
    def test_addvariant_uses_currentblocks(self):
        src = open("/app/frontend/src/pages/Funnels.js").read()
        assert "const cloneBlocks = JSON.parse(JSON.stringify(currentBlocks() || []))" in src
        assert "JSON.stringify(funnel.blocks" not in src.split("const addVariant")[1][:400]

    def test_variant_persist_roundtrip(self, client, funnel):
        step_blocks = [{"type": "heading", "props": {"text": "STEP CLONE SRC"}}]
        r = client.put(f"{API}/funnels/{funnel['id']}", json={
            "variants": [{"name": "Variant A", "weight": 1, "blocks": step_blocks}]})
        assert r.status_code == 200, r.text[:300]
        d = client.get(f"{API}/funnels/{funnel['id']}").json()
        assert len(d["variants"]) == 1
        assert d["variants"][0]["blocks"][0]["type"] == "heading"
        assert d["variants"][0]["blocks"][0]["props"]["text"] == "STEP CLONE SRC"
        # cleanup variants so step nav test data stays clean
        client.put(f"{API}/funnels/{funnel['id']}", json={"variants": []})


# ---------- Light regression ----------
class TestRegression:
    def test_variants_analytics(self, client, funnel):
        r = client.get(f"{API}/funnels/{funnel['id']}/variants-analytics")
        assert r.status_code == 200, r.text[:300]
        assert "variants" in r.json()

    def test_currencies_and_coupon_types(self, client):
        r = client.get(f"{API}/library/coupon-types")
        assert r.status_code == 200
        assert len(r.json()) >= 20

    def test_live_storefront_funnel(self):
        r = requests.get(f"{API}/public/f/qa-storefront-live")
        assert r.status_code == 200, r.text[:200]
        assert "blocks" in r.json()
