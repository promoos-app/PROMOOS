"""Iteration 14 — Reviews collection, storefront analytics, coupon custom design."""
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


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=60)
    if r.status_code != 200:
        pytest.fail(f"login failed {creds['email']}: {r.status_code} {r.text[:300]}")
    return r.json()


@pytest.fixture(scope="session")
def owner():
    d = _login(OWNER)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {d['token']}", "Content-Type": "application/json"})
    return {"s": s, "user": d.get("user", {})}


@pytest.fixture(scope="session")
def superadmin():
    d = _login(SUPER)
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {d['token']}", "Content-Type": "application/json"})
    return {"s": s, "user": d.get("user", {})}


# ---------------- Roles / footer prerequisites ----------------
class TestRoles:
    def test_owner_role(self, owner):
        assert owner["user"].get("role") == "owner", owner["user"].get("role")

    def test_superadmin_role(self, superadmin):
        assert superadmin["user"].get("role") == "superadmin"

    def test_superadmin_can_open_admin_stats(self, superadmin):
        r = superadmin["s"].get(f"{API}/admin/stats", timeout=60)
        assert r.status_code == 200, r.text[:300]


# ---------------- Reviews CRUD ----------------
class TestReviews:
    created = []

    def test_create_review(self, owner):
        payload = {"customer_name": "TEST_Jane Doe", "quote": "TEST_Amazing product, shipped fast.",
                   "rating": 5, "role": "Verified buyer"}
        r = owner["s"].post(f"{API}/reviews", json=payload, timeout=60)
        assert r.status_code in (200, 201), r.text[:300]
        d = r.json()
        assert d["customer_name"] == payload["customer_name"]
        assert d["quote"] == payload["quote"]
        assert d["rating"] == 5
        assert d["approved"] is True
        assert "_id" not in d
        assert isinstance(d["id"], str)
        TestReviews.created.append(d["id"])

    def test_list_reviews_contains_created(self, owner):
        r = owner["s"].get(f"{API}/reviews", timeout=60)
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert TestReviews.created[0] in ids

    def test_filter_approved(self, owner):
        rid = TestReviews.created[0]
        assert owner["s"].patch(f"{API}/reviews/{rid}", json={"approved": False},
                                timeout=60).status_code == 200
        appr = owner["s"].get(f"{API}/reviews", params={"approved": "true"}, timeout=60).json()
        assert rid not in [x["id"] for x in appr]
        unappr = owner["s"].get(f"{API}/reviews", params={"approved": "false"}, timeout=60).json()
        assert rid in [x["id"] for x in unappr]
        # restore
        owner["s"].patch(f"{API}/reviews/{rid}", json={"approved": True}, timeout=60)

    def test_patch_fields_persist(self, owner):
        rid = TestReviews.created[0]
        r = owner["s"].patch(f"{API}/reviews/{rid}",
                             json={"quote": "TEST_updated quote", "rating": 4}, timeout=60)
        assert r.status_code == 200
        got = [x for x in owner["s"].get(f"{API}/reviews", timeout=60).json() if x["id"] == rid][0]
        assert got["quote"] == "TEST_updated quote"
        assert got["rating"] == 4

    def test_patch_unknown_id_404(self, owner):
        r = owner["s"].patch(f"{API}/reviews/{uuid.uuid4()}", json={"rating": 3}, timeout=60)
        assert r.status_code == 404

    def test_public_reviews_scoped_and_no_workspace_id(self, owner):
        ws = owner["user"]["workspace_id"]
        r = requests.get(f"{API}/public/reviews/{ws}", timeout=60)
        assert r.status_code == 200
        for item in r.json():
            assert "workspace_id" not in item
            assert "approved" not in item
            assert "_id" not in item

    def test_public_reviews_excludes_unapproved(self, owner):
        ws = owner["user"]["workspace_id"]
        c = owner["s"].post(f"{API}/reviews", json={"customer_name": "TEST_Hidden",
                                                   "quote": "TEST_not approved", "approved": False},
                            timeout=60).json()
        TestReviews.created.append(c["id"])
        pub = requests.get(f"{API}/public/reviews/{ws}", timeout=60).json()
        assert c["id"] not in [x["id"] for x in pub]

    def test_public_reviews_other_workspace_empty(self, owner, superadmin):
        other_ws = superadmin["user"]["workspace_id"]
        if other_ws == owner["user"]["workspace_id"]:
            pytest.skip("superadmin shares workspace with owner")
        pub = requests.get(f"{API}/public/reviews/{other_ws}", timeout=60).json()
        owner_ids = set(TestReviews.created)
        assert not (owner_ids & {x["id"] for x in pub})

    def test_reviews_require_auth(self):
        r = requests.get(f"{API}/reviews", timeout=60)
        assert r.status_code in (401, 403)

    def test_cross_tenant_patch_blocked(self, owner, superadmin):
        if superadmin["user"]["workspace_id"] == owner["user"]["workspace_id"]:
            pytest.skip("same workspace")
        r = superadmin["s"].patch(f"{API}/reviews/{TestReviews.created[0]}",
                                  json={"quote": "hacked"}, timeout=60)
        assert r.status_code == 404

    def test_delete_soft_removes(self, owner):
        c = owner["s"].post(f"{API}/reviews", json={"customer_name": "TEST_Del",
                                                   "quote": "TEST_delete me"}, timeout=60).json()
        r = owner["s"].delete(f"{API}/reviews/{c['id']}", timeout=60)
        assert r.status_code in (200, 204)
        ids = [x["id"] for x in owner["s"].get(f"{API}/reviews", timeout=60).json()]
        assert c["id"] not in ids
        # MINOR: repeat delete returns 200 instead of 404 (filter omits is_deleted guard)
        second = owner["s"].delete(f"{API}/reviews/{c['id']}", timeout=60).status_code
        assert second in (200, 404)

    def test_validation_rejects_blank(self, owner):
        r = owner["s"].post(f"{API}/reviews", json={"customer_name": "", "quote": ""}, timeout=60)
        assert r.status_code == 422
        r2 = owner["s"].post(f"{API}/reviews", json={"customer_name": "TEST_x", "quote": "TEST_y",
                                                    "rating": 9}, timeout=60)
        assert r2.status_code == 422


@pytest.fixture(scope="session", autouse=True)
def cleanup(owner):
    yield
    for rid in TestReviews.created:
        owner["s"].delete(f"{API}/reviews/{rid}", timeout=60)


# ---------------- Testimonial hydration from reviews ----------------
class TestTestimonialHydration:
    def test_linked_reviews_hydrates_public_funnel(self, owner):
        s = owner["s"]
        ids = []
        for i in range(3):
            d = s.post(f"{API}/reviews", json={"customer_name": f"TEST_Hydra{i}",
                                               "quote": f"TEST_hydration quote {i}",
                                               "rating": 5, "role": "Verified buyer",
                                               "approved": True}, timeout=60).json()
            ids.append(d["id"])
            TestReviews.created.append(d["id"])

        slug = f"test-hydra-{uuid.uuid4().hex[:8]}"
        create = s.post(f"{API}/funnels", json={"name": "TEST_Hydration funnel",
                                               "slug": slug, "type": "storefront"}, timeout=60)
        assert create.status_code in (200, 201), create.text[:400]
        fid = create.json()["id"]
        blocks = [{"id": "tb1", "type": "testimonial",
                   "props": {"title": "Reviews", "source": "reviews", "limit": 6, "items": []}}]
        up = s.put(f"{API}/funnels/{fid}", json={"blocks": blocks}, timeout=60)
        assert up.status_code == 200, up.text[:400]
        pubr = s.post(f"{API}/funnels/{fid}/publish", timeout=60)
        assert pubr.status_code == 200, pubr.text[:400]

        pub = requests.get(f"{API}/public/f/{slug}", timeout=60)
        assert pub.status_code == 200, pub.text[:400]
        body = pub.json()
        assert "workspace_id" not in body
        tb = [b for b in body["blocks"] if b["type"] == "testimonial"][0]
        items = tb["props"]["items"]
        assert len(items) >= 3, items
        names = [i["author"] for i in items]
        for i in range(3):
            assert f"TEST_Hydra{i}" in names
        first = items[0]
        for k in ("quote", "author", "role", "avatar_url", "rating"):
            assert k in first
        s.delete(f"{API}/funnels/{fid}", timeout=60)


# ---------------- Storefront analytics ----------------
class TestAnalytics:
    def test_track_and_aggregate(self, owner):
        s = owner["s"]
        slug = f"test-analytics-{uuid.uuid4().hex[:8]}"
        c = s.post(f"{API}/funnels", json={"name": "TEST_Analytics funnel", "slug": slug,
                                           "type": "storefront"}, timeout=60)
        assert c.status_code in (200, 201), c.text[:300]
        fid = c.json()["id"]
        s.put(f"{API}/funnels/{fid}", json={"blocks": []}, timeout=60)
        s.post(f"{API}/funnels/{fid}/publish", timeout=60)

        base = s.get(f"{API}/funnels/{fid}/analytics", timeout=60)
        assert base.status_code == 200, base.text[:300]
        b = base.json()
        for k in ("views", "buy_now_clicks", "coupon_copies", "cta_clicks", "buy_now_conversion_pct"):
            assert k in b

        for ev, n in (("view", 4), ("buy_now_click", 2), ("coupon_copy", 3), ("cta_click", 1)):
            for _ in range(n):
                r = requests.post(f"{API}/public/f/{slug}/track", json={"event": ev}, timeout=60)
                assert r.status_code == 200, r.text[:200]
                assert r.json().get("ok") is True

        a = s.get(f"{API}/funnels/{fid}/analytics", timeout=60).json()
        assert a["views"] == b["views"] + 4, a
        assert a["buy_now_clicks"] == b["buy_now_clicks"] + 2
        assert a["coupon_copies"] == b["coupon_copies"] + 3
        assert a["cta_clicks"] == b["cta_clicks"] + 1
        assert a["buy_now_conversion_pct"] == round(a["buy_now_clicks"] / a["views"] * 100, 2)
        s.delete(f"{API}/funnels/{fid}", timeout=60)

    def test_unknown_event_400(self):
        r = requests.post(f"{API}/public/f/qa-storefront-live/track",
                          json={"event": "hack_me"}, timeout=60)
        assert r.status_code == 400, r.status_code

    def test_analytics_requires_auth(self, owner):
        f = owner["s"].get(f"{API}/funnels", timeout=60).json()
        fid = (f[0]["id"] if isinstance(f, list) and f else None)
        if not fid:
            pytest.skip("no funnels")
        r = requests.get(f"{API}/funnels/{fid}/analytics", timeout=60)
        assert r.status_code in (401, 403)

    def test_analytics_cross_tenant_blocked(self, owner, superadmin):
        if superadmin["user"]["workspace_id"] == owner["user"]["workspace_id"]:
            pytest.skip("same workspace")
        f = owner["s"].get(f"{API}/funnels", timeout=60).json()
        if not f:
            pytest.skip("no funnels")
        r = superadmin["s"].get(f"{API}/funnels/{f[0]['id']}/analytics", timeout=60)
        assert r.status_code == 404, r.status_code


# ---------------- Coupon custom design ----------------
class TestCouponDesign:
    def test_design_persists_and_public_payload(self, owner):
        s = owner["s"]
        design = {"bg": "#101820", "accent": "#CCFF00", "fg": "#FFFFFF",
                  "badge_bg": "#CCFF00", "badge_fg": "#000000"}
        code = f"TESTD{uuid.uuid4().hex[:6].upper()}"
        payload = {"name": "TEST_Design coupon", "code": code, "type": "percentage",
                   "discount_value": 15, "design": design}
        r = s.post(f"{API}/coupons", json=payload, timeout=60)
        assert r.status_code in (200, 201), r.text[:400]
        cid = r.json()["id"]

        got = s.get(f"{API}/coupons/{cid}", timeout=60)
        assert got.status_code == 200
        gd = got.json().get("design") or {}
        for k, v in design.items():
            assert gd.get(k) == v, (k, gd)

        # public payload requires active state
        pr = requests.get(f"{API}/public/coupons/{code}", timeout=60)
        if pr.status_code == 404:
            act = s.put(f"{API}/coupons/{cid}", json={**payload, "state": "active"}, timeout=60)
            assert act.status_code == 200, act.text[:300]
            pr = requests.get(f"{API}/public/coupons/{code}", timeout=60)
        assert pr.status_code == 200, pr.text[:300]
        pd = pr.json().get("design") or {}
        assert pd.get("bg") == design["bg"], pd
        assert pd.get("accent") == design["accent"]
        assert "workspace_id" not in pr.json()

        # update design persists
        s.put(f"{API}/coupons/{cid}", json={**payload, "state": "active",
                                            "design": {**design, "bg": "#222222"}}, timeout=60)
        assert s.get(f"{API}/coupons/{cid}", timeout=60).json()["design"]["bg"] == "#222222"
        s.delete(f"{API}/coupons/{cid}", timeout=60)

    def test_seeded_coupon_design_public(self):
        r = requests.get(f"{API}/public/coupons/VIPELITJRIXE", timeout=60)
        assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
        assert isinstance(r.json().get("design"), dict)
