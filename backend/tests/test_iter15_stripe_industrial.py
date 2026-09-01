"""Iteration 15 — Stripe payment links, industrial funnel templates/blocks, opt-in capture,
and regression on the 9 deferred fixes from iteration 14."""
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
SUPER = {"email": "superadmin@promoos.com", "password": "sZpRBNpLKypsQDURBQNqMIzE"}

BASIC_LINK = "https://buy.stripe.com/5kQ28qcDSfMK3ni5MD2kw0f"
PRO_LINK = "https://buy.stripe.com/eVqfZg33igQO9LG5MD2kw0e"

NEW_TEMPLATES = ["lead_magnet", "webinar_registration", "product_launch",
                 "application_funnel", "thankyou"]


@pytest.fixture(scope="session")
def anon():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _login(creds):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json=creds)
    if r.status_code != 200:
        pytest.fail(f"login failed {creds['email']}: {r.status_code} {r.text[:300]}")
    tok = r.json().get("access_token") or r.json().get("token")
    assert tok, f"no token in login response: {r.text[:300]}"
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s, r.json()


@pytest.fixture(scope="session")
def owner():
    return _login(OWNER)


@pytest.fixture(scope="session")
def superadmin():
    return _login(SUPER)


# ------------------------------------------------------------------ STRIPE
class TestStripePaymentLinks:
    def test_plans_expose_payment_links(self, anon):
        r = anon.get(f"{API}/billing/plans")
        assert r.status_code == 200, r.text[:300]
        plans = r.json()["plans"]
        assert len(plans) == 2, plans
        by_key = {p["lookup_key"]: p for p in plans}
        assert set(by_key) == {"basic_monthly", "pro_monthly"}, list(by_key)
        assert by_key["basic_monthly"]["payment_link"] == BASIC_LINK
        assert by_key["pro_monthly"]["payment_link"] == PRO_LINK
        assert by_key["basic_monthly"]["price"] == 49
        assert by_key["pro_monthly"]["price"] == 79

    def test_legacy_checkout_still_works_for_auth_user(self, owner):
        s, _ = owner
        r = s.post(f"{API}/billing/checkout",
                   json={"lookup_key": "basic_monthly", "origin_url": BASE_URL})
        assert r.status_code == 200, r.text[:400]
        data = r.json()
        assert "checkout_url" in data and data["checkout_url"].startswith("http"), data

    def test_checkout_requires_auth(self, anon):
        r = anon.post(f"{API}/billing/checkout",
                      json={"lookup_key": "basic_monthly", "origin_url": BASE_URL})
        assert r.status_code in (401, 403), f"{r.status_code} {r.text[:200]}"


# ------------------------------------------------------------ TEMPLATES
class TestIndustrialTemplates:
    def test_templates_include_five_new(self, anon):
        r = anon.get(f"{API}/funnels/templates")
        assert r.status_code == 200, r.text[:300]
        ids = [t["id"] for t in r.json()["templates"]]
        for t in NEW_TEMPLATES:
            assert t in ids, f"missing template {t}; got {ids}"

    @pytest.mark.parametrize("tpl", NEW_TEMPLATES)
    def test_create_publish_and_public_hydrate(self, owner, tpl, created_funnels):
        s, _ = owner
        r = s.post(f"{API}/funnels", json={"name": f"TEST_{tpl}_{uuid.uuid4().hex[:6]}",
                                           "template_id": tpl})
        assert r.status_code == 200, r.text[:400]
        f = r.json()
        created_funnels.append((s, f["id"]))
        assert f["template_id"] == tpl
        assert len(f["blocks"]) > 0, "template produced no blocks"
        assert f["theme"], "no theme"
        for b in f["blocks"]:
            assert b.get("id") and b.get("type") and isinstance(b.get("props"), dict)

        pub = s.post(f"{API}/funnels/{f['id']}/publish")
        assert pub.status_code == 200, pub.text[:300]
        assert pub.json()["published"] is True

        pr = requests.get(f"{API}/public/f/{f['slug']}")
        assert pr.status_code == 200, pr.text[:300]
        payload = pr.json()
        assert "workspace_id" not in payload
        assert len(payload["blocks"]) == len(f["blocks"])

    def test_new_block_types_present_in_templates(self, anon):
        r = anon.get(f"{API}/funnels/templates")
        tpls = {t["id"]: t for t in r.json()["templates"]}
        expected = {
            "lead_magnet": {"logo_bar", "optin", "stats", "guarantee"},
            "webinar_registration": {"optin", "guarantee", "countdown"},
            "product_launch": {"pricing_table", "order_bump", "upsell", "stats", "logo_bar", "guarantee"},
            "application_funnel": {"optin", "guarantee"},
            "thankyou": {"upsell", "guarantee"},
        }
        for tid, must in expected.items():
            types = {b["type"] for b in tpls[tid]["blocks"]}
            assert must.issubset(types), f"{tid} missing {must - types}"


# --------------------------------------------------------------- OPT-IN
class TestOptinCapture:
    @pytest.fixture(scope="class")
    def optin_funnel(self, owner, created_funnels):
        s, _ = owner
        r = s.post(f"{API}/funnels", json={"name": f"TEST_optin_{uuid.uuid4().hex[:6]}",
                                           "template_id": "lead_magnet"})
        assert r.status_code == 200, r.text[:300]
        f = r.json()
        created_funnels.append((s, f["id"]))
        assert s.post(f"{API}/funnels/{f['id']}/publish").status_code == 200
        return f

    def test_optin_creates_lead_and_upserts(self, owner, optin_funnel):
        s, _ = owner
        slug = optin_funnel["slug"]
        email = f"TEST_lead_{uuid.uuid4().hex[:8]}@example.com"
        r1 = requests.post(f"{API}/public/f/{slug}/optin",
                           json={"fields": {"email": email}, "lead_tag": "leadmagnet"})
        assert r1.status_code == 200, r1.text[:300]
        assert r1.json()["ok"] is True
        lead_id = r1.json()["lead_id"]

        # re-submit same email -> upsert, submits += 1
        r2 = requests.post(f"{API}/public/f/{slug}/optin",
                           json={"fields": {"email": email.upper()}, "lead_tag": "leadmagnet"})
        assert r2.status_code == 200, r2.text[:300]
        assert r2.json()["lead_id"] == lead_id, "duplicate lead created instead of upsert"

        leads = s.get(f"{API}/funnels/{optin_funnel['id']}/leads")
        assert leads.status_code == 200, leads.text[:300]
        rows = leads.json()
        mine = [l for l in rows if l["email"] == email.lower()]
        assert len(mine) == 1, f"expected 1 lead row, got {len(mine)}"
        assert mine[0]["submits"] == 2, mine[0]
        assert mine[0]["lead_tag"] == "leadmagnet"
        assert "workspace_id" not in mine[0]

    @pytest.mark.parametrize("body", [
        {"fields": {}},
        {"fields": {"email": ""}},
        {"fields": {"email": "not-an-email"}},
    ])
    def test_optin_invalid_email_400(self, optin_funnel, body):
        r = requests.post(f"{API}/public/f/{optin_funnel['slug']}/optin", json=body)
        assert r.status_code == 400, f"{r.status_code} {r.text[:200]}"

    def test_optin_unknown_funnel_404(self):
        r = requests.post(f"{API}/public/f/does-not-exist-{uuid.uuid4().hex[:6]}/optin",
                          json={"fields": {"email": "a@b.com"}})
        assert r.status_code == 404, r.status_code

    def test_leads_requires_auth(self, optin_funnel):
        r = requests.get(f"{API}/funnels/{optin_funnel['id']}/leads")
        assert r.status_code in (401, 403), r.status_code

    def test_cross_tenant_leads_404(self, superadmin, optin_funnel):
        s, me = superadmin
        r = s.get(f"{API}/funnels/{optin_funnel['id']}/leads")
        assert r.status_code == 404, f"cross-tenant leak: {r.status_code} {r.text[:200]}"

    def test_analytics_optin_counter(self, owner, optin_funnel):
        s, _ = owner
        email = f"TEST_an_{uuid.uuid4().hex[:8]}@example.com"
        a0 = s.get(f"{API}/funnels/{optin_funnel['id']}/analytics").json()
        requests.post(f"{API}/public/f/{optin_funnel['slug']}/optin",
                      json={"fields": {"email": email}})
        a1 = s.get(f"{API}/funnels/{optin_funnel['id']}/analytics").json()
        assert a1["optin_submits"] == a0["optin_submits"] + 1, (a0, a1)
        assert "optin_conversion_pct" in a1


# ----------------------------------------------------- ITER14 REGRESSIONS
class TestIter14Regressions:
    def test_coupon_put_partial_update_preserves_fields(self, owner, created_coupons):
        s, _ = owner
        code = f"TESTPARTIAL{uuid.uuid4().hex[:6].upper()}"
        payload = {"name": "TEST_Partial", "code": code, "type": "percent",
                   "discount_value": 15.0, "headline": "Keep me",
                   "description": "Do not wipe me"}
        c = s.post(f"{API}/coupons", json=payload)
        assert c.status_code in (200, 201), c.text[:400]
        cid = c.json()["id"]
        created_coupons.append((s, cid))

        p = s.put(f"{API}/coupons/{cid}", json={"design": {"bg": "#111111"}})
        assert p.status_code == 200, p.text[:400]

        g = s.get(f"{API}/coupons/{cid}")
        assert g.status_code == 200, g.text[:300]
        d = g.json()
        assert d["name"] == "TEST_Partial", d
        assert d["type"] == "percent", d
        assert d["discount_value"] == 15.0, d
        assert d["headline"] == "Keep me", d
        assert d["description"] == "Do not wipe me", d
        assert (d.get("design") or {}).get("bg") == "#111111", d.get("design")

    def test_vip_coupon_restored(self, owner):
        s, _ = owner
        r = s.get(f"{API}/coupons")
        assert r.status_code == 200
        rows = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        vip = next((c for c in rows if c["code"] == "VIPELITJRIXE"), None)
        assert vip is not None, "VIPELITJRIXE coupon missing"
        assert vip["state"] == "active", vip["state"]
        assert vip["type"] == "vip", vip["type"]
        assert vip["discount_value"] == 20.0, vip["discount_value"]
        assert vip["name"] == "VIP Launch Offer", vip["name"]

    def test_public_wallet_no_500(self):
        r = requests.get(f"{API}/public/wallet/wallet-nobody@example.com")
        assert r.status_code != 500, r.text[:300]
        assert r.status_code in (200, 404), r.status_code
        if r.status_code == 200:
            assert isinstance(r.json(), (list, dict))

    def test_public_wallet_with_real_email(self, owner):
        # seed a coupon assignment path is complex; just assert admin email works w/o 500
        r = requests.get(f"{API}/public/wallet/{OWNER['email']}")
        assert r.status_code != 500, r.text[:300]

    def test_journeys_no_workspace_id(self, owner):
        s, _ = owner
        r = s.get(f"{API}/journeys")
        assert r.status_code == 200, r.text[:300]
        rows = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
        for j in rows:
            assert "workspace_id" not in j, f"workspace_id leaked: {j}"
            assert "_id" not in j

    def test_review_delete_idempotent(self, owner):
        s, _ = owner
        c = s.post(f"{API}/reviews", json={"customer_name": "TEST_Reviewer",
                                           "quote": "TEST idempotency", "rating": 5})
        assert c.status_code in (200, 201), c.text[:300]
        rid = c.json()["id"]
        d1 = s.delete(f"{API}/reviews/{rid}")
        assert d1.status_code in (200, 204), d1.text[:200]
        d2 = s.delete(f"{API}/reviews/{rid}")
        assert d2.status_code == 404, f"second delete returned {d2.status_code} (not idempotent)"

    def test_qa_storefront_live_hydrated(self):
        r = requests.get(f"{API}/public/f/qa-storefront-live")
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert "workspace_id" not in d
        prod = next((b for b in d["blocks"] if b["type"] == "product"), None)
        assert prod is not None, "no product block on qa-storefront-live"
        cpn = (prod["props"] or {}).get("coupon")
        assert cpn, "product block coupon not hydrated"
        assert cpn["code"] == "VIPELITJRIXE", cpn.get("code")
        assert cpn["state"] == "active", cpn.get("state")
        assert cpn["discount_value"] == 20.0
        p = (prod["props"] or {}).get("product")
        assert p, "product not hydrated"
        assert float(p["price"]) == 49.0, p.get("price")

    def test_track_view_event_accepted(self):
        r = requests.post(f"{API}/public/f/qa-storefront-live/track", json={"event": "view"})
        assert r.status_code == 200, r.text[:200]
        assert r.json().get("ok") is True
        bad = requests.post(f"{API}/public/f/qa-storefront-live/track", json={"event": "bogus"})
        assert bad.status_code == 400


# ------------------------------------------------------------ AUTH PLAYBOOK
class TestAuthPlaybook:
    def test_login_sets_httponly_cookie(self, anon):
        r = requests.post(f"{API}/auth/login", json=OWNER)
        assert r.status_code == 200, r.text[:300]
        ck = r.cookies.get("access_token")
        raw = r.headers.get("set-cookie", "")
        assert ck or "access_token" in raw, f"no access_token cookie: {raw[:200]}"
        assert "httponly" in raw.lower(), f"cookie not HttpOnly: {raw[:200]}"

    def test_bad_password_401(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": OWNER["email"], "password": "definitely-wrong"})
        assert r.status_code in (401, 429), r.status_code

    def test_me_requires_token(self, owner):
        s, _ = owner
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200, r.text[:300]
        assert r.json()["email"] == OWNER["email"]
        r2 = requests.get(f"{API}/auth/me")
        assert r2.status_code in (401, 403)


# --------------------------------------------------------------- CLEANUP
@pytest.fixture(scope="session")
def created_funnels():
    items = []
    yield items
    for s, fid in items:
        s.delete(f"{API}/funnels/{fid}")


@pytest.fixture(scope="session")
def created_coupons():
    items = []
    yield items
    for s, cid in items:
        s.delete(f"{API}/coupons/{cid}")
