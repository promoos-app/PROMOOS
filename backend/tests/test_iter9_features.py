"""Iteration 9 tests — Phase 2 expansion.

Covers:
  * Gift Card Studio (20 templates + design + AI regeneration)
  * OAuth Hub (6 providers, SendGrid api_key mode, mailchimp not-configured)
  * Funnel Builder (6 templates, CRUD, publish, custom domain, public renderer)
  * Router split regression (billing/uploads/currencies/fonts/coupon share still work)
"""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

SUPERADMIN_EMAIL = "superadmin@promoos.com"
SUPERADMIN_PASS = "sZpRBNpLKypsQDURBQNqMIzE"
OWNER_EMAIL = "admin@promoos.com"
OWNER_PASS = "admin123"
MARKETER_EMAIL = "marketer@promoos.com"
MARKETER_PASS = "marketer123"


def _login(email, password, expect=200):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == expect, f"login {email} -> {r.status_code} {r.text}"
    return r.json() if r.status_code == 200 else r


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def owner_token():
    return _login(OWNER_EMAIL, OWNER_PASS)["token"]


@pytest.fixture(scope="module")
def superadmin_token():
    return _login(SUPERADMIN_EMAIL, SUPERADMIN_PASS)["token"]


# =========================================================================
# GIFT CARD STUDIO
# =========================================================================
class TestGiftCardTemplates:
    def test_list_templates(self):
        r = requests.get(f"{API}/giftcard-templates", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "templates" in d and "categories" in d
        assert len(d["templates"]) == 20, f"expected 20, got {len(d['templates'])}"
        assert len(d["categories"]) == 9, f"expected 9 categories, got {d['categories']}"
        # verify fields on each template
        for t in d["templates"]:
            for k in ("id", "name", "category", "background", "accent", "font", "headline", "subline"):
                assert k in t, f"template {t.get('id')} missing {k}"

    def test_get_single_template(self):
        r = requests.get(f"{API}/giftcard-templates/midnight-onyx", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == "midnight-onyx"
        assert d["category"] == "luxury"
        assert d["accent"] == "#CCFF00"

    def test_get_unknown_template_404(self):
        r = requests.get(f"{API}/giftcard-templates/does-not-exist", timeout=15)
        assert r.status_code == 404


class TestGiftCardDesign:
    def test_create_design_requires_auth(self):
        r = requests.post(f"{API}/giftcards/design",
                          json={"template_id": "midnight-onyx", "amount": 50}, timeout=15)
        assert r.status_code in (401, 403)

    def test_create_design_owner(self, owner_token):
        payload = {
            "template_id": "midnight-onyx",
            "amount": 100.0,
            "currency": "USD",
            "recipient_name": "TEST_ITER9_alice",
            "recipient_email": "alice@example.com",
            "headline": "TEST_ITER9 headline",
            "subline": "TEST_ITER9 subline",
            "accent_override": "#FF0000",
        }
        r = requests.post(f"{API}/giftcards/design",
                          headers=_hdr(owner_token), json=payload, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d and "code" in d
        assert d["code"].startswith("GC-")
        assert d["amount"] == 100.0
        assert d["template_id"] == "midnight-onyx"
        assert d["design"]["headline"] == "TEST_ITER9 headline"
        assert d["design"]["subline"] == "TEST_ITER9 subline"
        assert d["design"]["accent"] == "#FF0000"
        pytest.iter9_gc_id = d["id"]

    def test_create_design_invalid_template(self, owner_token):
        r = requests.post(f"{API}/giftcards/design",
                          headers=_hdr(owner_token),
                          json={"template_id": "nope", "amount": 10}, timeout=15)
        assert r.status_code == 400

    def test_list_designs(self, owner_token):
        r = requests.get(f"{API}/giftcards/designs", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        ids = [g["id"] for g in arr]
        assert getattr(pytest, "iter9_gc_id", None) in ids


class TestGiftCardRegenerate:
    """LLM budget-safe: 1 headline + 1 subline (text only). Skip image_bg."""

    def test_regen_headline(self, owner_token):
        r = requests.post(f"{API}/giftcards/regenerate",
                          headers=_hdr(owner_token),
                          json={"field": "headline",
                                "tone": "warm, premium",
                                "occasion": "birthday"},
                          timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["field"] == "headline"
        v = d["value"]
        assert isinstance(v, str) and 1 < len(v) < 200, f"got: {v!r}"

    def test_regen_subline(self, owner_token):
        r = requests.post(f"{API}/giftcards/regenerate",
                          headers=_hdr(owner_token),
                          json={"field": "subline",
                                "tone": "warm, premium",
                                "current_headline": "You are unstoppable"},
                          timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["field"] == "subline"
        v = d["value"]
        assert isinstance(v, str) and 5 < len(v) < 400

    def test_regen_unknown_field_400(self, owner_token):
        r = requests.post(f"{API}/giftcards/regenerate",
                          headers=_hdr(owner_token),
                          json={"field": "banana"}, timeout=15)
        assert r.status_code == 400


# =========================================================================
# OAUTH HUB
# =========================================================================
class TestOAuthHub:
    def test_list_providers(self):
        r = requests.get(f"{API}/oauth/providers", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "providers" in d
        by_id = {p["id"]: p for p in d["providers"]}
        for pid in ("mailchimp", "sendgrid", "facebook", "instagram", "linkedin", "tiktok"):
            assert pid in by_id, f"missing {pid}"
        assert by_id["sendgrid"]["mode"] == "api_key"
        assert by_id["sendgrid"]["configured"] is True
        for p in ("mailchimp", "facebook", "instagram", "linkedin", "tiktok"):
            assert by_id[p]["mode"] == "oauth2"
            assert by_id[p]["configured"] is False

    def test_mailchimp_start_501(self, owner_token):
        r = requests.get(f"{API}/oauth/mailchimp/start", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 501, r.text
        assert "MAILCHIMP_CLIENT_ID" in r.text and "MAILCHIMP_CLIENT_SECRET" in r.text

    def test_facebook_start_501(self, owner_token):
        r = requests.get(f"{API}/oauth/facebook/start", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 501
        assert "FACEBOOK_APP_ID" in r.text

    def test_sendgrid_start_rejected_as_api_key(self, owner_token):
        r = requests.get(f"{API}/oauth/sendgrid/start", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 400
        assert "api" in r.text.lower() or "connect" in r.text.lower()

    def test_unknown_provider_404(self, owner_token):
        r = requests.get(f"{API}/oauth/foobar/start", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 404

    def test_sendgrid_api_key_connect_and_list(self, owner_token):
        # connect
        r = requests.post(f"{API}/oauth/sendgrid/connect",
                          headers=_hdr(owner_token),
                          json={"api_key": "SG.TEST_ITER9_key1234567890",
                                "account_label": "TEST_ITER9_sg"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True and d["provider"] == "sendgrid"

        # list tokens
        r2 = requests.get(f"{API}/oauth/tokens", headers=_hdr(owner_token), timeout=15)
        assert r2.status_code == 200
        arr = r2.json()
        assert isinstance(arr, list)
        sg = next((x for x in arr if x["provider"] == "sendgrid"), None)
        assert sg is not None, arr
        # access token itself must NOT leak; only preview
        assert "access_token" not in sg
        assert "access_token_preview" in sg
        assert sg["access_token_preview"].startswith("SG.TES")
        assert sg["mode"] == "api_key"

        # disconnect
        r3 = requests.delete(f"{API}/oauth/sendgrid", headers=_hdr(owner_token), timeout=15)
        assert r3.status_code == 200
        assert r3.json()["ok"] is True

        # list again → sendgrid should be gone (or revoked)
        r4 = requests.get(f"{API}/oauth/tokens", headers=_hdr(owner_token), timeout=15)
        active = [x for x in r4.json() if x["provider"] == "sendgrid"]
        assert active == [], f"expected sendgrid removed after revoke, got {active}"

    def test_api_key_connect_rejects_short_key(self, owner_token):
        r = requests.post(f"{API}/oauth/sendgrid/connect",
                          headers=_hdr(owner_token),
                          json={"api_key": "short"}, timeout=15)
        assert r.status_code == 400

    def test_facebook_connect_rejects_because_oauth(self, owner_token):
        r = requests.post(f"{API}/oauth/facebook/connect",
                          headers=_hdr(owner_token),
                          json={"api_key": "SG.foo1234567890abcdefg"}, timeout=15)
        assert r.status_code == 400


# =========================================================================
# FUNNEL BUILDER
# =========================================================================
class TestFunnelTemplates:
    def test_list_templates(self):
        r = requests.get(f"{API}/funnels/templates", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "templates" in d
        assert len(d["templates"]) == 6
        ids = [t["id"] for t in d["templates"]]
        for want in ("diamond", "champagne", "noir", "emerald", "rose", "electric"):
            assert want in ids, f"missing {want}"
        for t in d["templates"]:
            assert "theme" in t and "blocks" in t
            assert isinstance(t["blocks"], list) and len(t["blocks"]) >= 1


class TestFunnelCrud:
    @pytest.fixture(scope="class")
    def funnel(self, owner_token):
        name = f"TEST_ITER9_funnel_{uuid.uuid4().hex[:6]}"
        r = requests.post(f"{API}/funnels", headers=_hdr(owner_token),
                          json={"name": name, "template_id": "diamond"}, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()

    def test_create_funnel_from_diamond(self, funnel):
        assert funnel["template_id"] == "diamond"
        assert funnel["published"] is False
        # Diamond template has 4 blocks (hero, coupon, features, cta)
        assert len(funnel["blocks"]) == 4
        types = [b["type"] for b in funnel["blocks"]]
        for t in ("hero", "coupon", "features", "cta"):
            assert t in types
        # each block has an id
        for b in funnel["blocks"]:
            assert "id" in b and isinstance(b["id"], str)
        assert funnel["theme"]["accent"] == "#CCFF00"

    def test_get_funnel(self, owner_token, funnel):
        r = requests.get(f"{API}/funnels/{funnel['id']}", headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200
        assert r.json()["id"] == funnel["id"]

    def test_update_funnel_blocks(self, owner_token, funnel):
        new_blocks = [
            {"type": "hero", "props": {"headline": "Iter9 updated hero"}, "anchor": "h"},
            {"type": "cta", "props": {"headline": "Iter9 buy now", "cta_label": "Buy"}, "anchor": "c"},
        ]
        r = requests.put(f"{API}/funnels/{funnel['id']}", headers=_hdr(owner_token),
                         json={"blocks": new_blocks,
                               "seo": {"title": "TEST_ITER9", "description": "iter9 seo"}}, timeout=15)
        assert r.status_code == 200, r.text
        # verify persisted
        g = requests.get(f"{API}/funnels/{funnel['id']}", headers=_hdr(owner_token), timeout=15).json()
        assert len(g["blocks"]) == 2
        assert g["blocks"][0]["props"]["headline"] == "Iter9 updated hero"
        assert g["seo"]["title"] == "TEST_ITER9"

    def test_publish_and_public_render(self, owner_token, funnel):
        r = requests.post(f"{API}/funnels/{funnel['id']}/publish",
                          headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["published"] is True
        assert "public_url" in d and "/f/" in d["public_url"]

        # public render — no auth
        slug = funnel["slug"]
        r2 = requests.get(f"{API}/public/f/{slug}", timeout=15)
        assert r2.status_code == 200, r2.text
        pub = r2.json()
        assert pub["published"] is True
        assert pub["slug"] == slug
        assert "workspace_id" not in pub  # projected out

    def test_public_render_unpublished_404(self, owner_token):
        # create fresh unpublished funnel and try to render
        r = requests.post(f"{API}/funnels", headers=_hdr(owner_token),
                          json={"name": f"TEST_ITER9_unpub_{uuid.uuid4().hex[:6]}",
                                "template_id": "noir"}, timeout=15)
        assert r.status_code == 200
        slug = r.json()["slug"]
        r2 = requests.get(f"{API}/public/f/{slug}", timeout=15)
        assert r2.status_code == 404
        # cleanup
        requests.delete(f"{API}/funnels/{r.json()['id']}", headers=_hdr(owner_token), timeout=10)

    def test_delete_soft(self, owner_token, funnel):
        r = requests.delete(f"{API}/funnels/{funnel['id']}",
                            headers=_hdr(owner_token), timeout=15)
        assert r.status_code == 200
        # get should now 404
        r2 = requests.get(f"{API}/funnels/{funnel['id']}",
                          headers=_hdr(owner_token), timeout=15)
        assert r2.status_code == 404


class TestFunnelDomain:
    @pytest.fixture
    def funnel_id(self, owner_token):
        r = requests.post(f"{API}/funnels", headers=_hdr(owner_token),
                          json={"name": f"TEST_ITER9_dom_{uuid.uuid4().hex[:6]}",
                                "template_id": "electric"}, timeout=15)
        assert r.status_code == 200
        fid = r.json()["id"]
        yield fid
        requests.delete(f"{API}/funnels/{fid}", headers=_hdr(owner_token), timeout=10)

    def test_set_domain(self, owner_token, funnel_id):
        domain = f"iter9-{uuid.uuid4().hex[:8]}.example.com"
        r = requests.post(f"{API}/funnels/{funnel_id}/domain",
                          headers=_hdr(owner_token),
                          json={"domain": domain}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["domain"] == domain
        assert "verification" in d
        assert d["verification"]["cname"]["host"] == domain
        assert d["verification"]["cname"]["value"]
        assert d["verification"]["txt"]["host"] == f"_promoos-verify.{domain}"
        assert d["verification"]["txt"]["value"] == funnel_id

    def test_set_domain_invalid_400(self, owner_token, funnel_id):
        r = requests.post(f"{API}/funnels/{funnel_id}/domain",
                          headers=_hdr(owner_token),
                          json={"domain": "not a domain"}, timeout=15)
        assert r.status_code == 400

    def test_set_domain_conflict_409(self, owner_token, funnel_id):
        # claim a domain on funnel_id, then try to claim same on new funnel → 409
        d1 = f"iter9-conf-{uuid.uuid4().hex[:8]}.example.com"
        r1 = requests.post(f"{API}/funnels/{funnel_id}/domain",
                           headers=_hdr(owner_token), json={"domain": d1}, timeout=15)
        assert r1.status_code == 200

        r_new = requests.post(f"{API}/funnels", headers=_hdr(owner_token),
                              json={"name": f"TEST_ITER9_conflict_{uuid.uuid4().hex[:4]}",
                                    "template_id": "noir"}, timeout=15)
        assert r_new.status_code == 200
        fid2 = r_new.json()["id"]
        try:
            r2 = requests.post(f"{API}/funnels/{fid2}/domain",
                               headers=_hdr(owner_token),
                               json={"domain": d1}, timeout=15)
            assert r2.status_code == 409, r2.text
        finally:
            requests.delete(f"{API}/funnels/{fid2}", headers=_hdr(owner_token), timeout=10)


class TestFunnelPublicHydration:
    def test_public_hydrates_coupon_and_giftcard(self, owner_token):
        # 1) create a coupon in the workspace so we can attach its code to a block
        code = f"ITER9F{uuid.uuid4().hex[:6].upper()}"
        cr = requests.post(f"{API}/coupons", headers=_hdr(owner_token), json={
            "name": "TEST_ITER9_funnel_coupon",
            "type": "percentage",
            "discount_value": 15,
            "code": code,
            "headline": "Save 15% with Iter9",
            "description": "iter9 hydrate test",
            "state": "active",
        }, timeout=15)
        assert cr.status_code in (200, 201), cr.text

        # 2) create funnel from champagne (has a giftcard block) + hero
        fr = requests.post(f"{API}/funnels", headers=_hdr(owner_token),
                           json={"name": f"TEST_ITER9_hydr_{uuid.uuid4().hex[:6]}",
                                 "template_id": "champagne"}, timeout=15)
        assert fr.status_code == 200, fr.text
        f = fr.json()
        fid = f["id"]
        slug = f["slug"]

        try:
            # 3) inject a coupon block referring to our coupon code
            new_blocks = [
                {"type": "hero", "props": {"headline": "Iter9 hydrate test"}, "anchor": "h"},
                {"type": "coupon", "props": {"coupon_code": code, "label": "Try this"}, "anchor": "cp"},
                {"type": "giftcard", "props": {"template_id": "champagne-gold", "amount": 100},
                 "anchor": "gc"},
            ]
            u = requests.put(f"{API}/funnels/{fid}", headers=_hdr(owner_token),
                             json={"blocks": new_blocks}, timeout=15)
            assert u.status_code == 200, u.text

            # 4) publish
            p = requests.post(f"{API}/funnels/{fid}/publish",
                              headers=_hdr(owner_token), timeout=15)
            assert p.status_code == 200

            # 5) public render — verify hydration
            pub = requests.get(f"{API}/public/f/{slug}", timeout=15)
            assert pub.status_code == 200, pub.text
            data = pub.json()
            coupon_block = next(b for b in data["blocks"] if b["type"] == "coupon")
            assert "coupon" in coupon_block["props"], f"coupon not hydrated: {coupon_block}"
            assert coupon_block["props"]["coupon"]["code"] == code
            assert coupon_block["props"]["coupon"]["discount_value"] == 15

            gc_block = next(b for b in data["blocks"] if b["type"] == "giftcard")
            assert "template" in gc_block["props"], f"gc template not hydrated: {gc_block}"
            assert gc_block["props"]["template"]["id"] == "champagne-gold"
            assert "background" in gc_block["props"]["template"]
        finally:
            requests.delete(f"{API}/funnels/{fid}", headers=_hdr(owner_token), timeout=10)


# =========================================================================
# ROUTER-SPLIT REGRESSION (iter-8 endpoints still work)
# =========================================================================
class TestRouterSplitRegression:
    def test_billing_plans(self):
        r = requests.get(f"{API}/billing/plans", timeout=15)
        assert r.status_code == 200
        assert len(r.json()["plans"]) == 2

    def test_currencies(self):
        r = requests.get(f"{API}/currencies", timeout=15)
        assert r.status_code == 200
        assert 140 <= len(r.json()) <= 160

    def test_fonts(self):
        r = requests.get(f"{API}/fonts", timeout=15)
        assert r.status_code == 200
        assert len(r.json()["fonts"]) >= 80

    def test_admin_stripe_onboarding_superadmin(self, superadmin_token):
        r = requests.get(f"{API}/admin/stripe-onboarding",
                         headers=_hdr(superadmin_token), timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "onboarding_url" in d and "publishable_key" in d

    def test_old_superadmin_password_still_rejected(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": SUPERADMIN_EMAIL, "password": "superadmin123"},
                          timeout=15)
        assert r.status_code == 401
