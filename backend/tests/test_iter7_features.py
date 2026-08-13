"""Iteration 7 tests: encrypted webhook secrets + API-key auth on v1 endpoints
+ Admin Portal (superadmin) + 23-type Coupon Library + Privacy/Terms.

Covers:
- POST /api/pos/rotate-secret returns whsec_... (>=40 chars); GET /api/pos/secrets
  exposes preview + rotated_at only; HMAC still works after rotate (Fernet-encrypted at rest);
  DELETE /api/pos/secret/{provider} returns webhooks to trust-mode.
- POST /api/v1/coupons/redeem gate: missing bearer → 401 "Missing bearer token",
  invalid → 401 "Invalid or revoked API key", revoked → 401, valid without 'write' → 403,
  valid with 'write' → 200 + discount+revenue.
- Superadmin auth + RBAC on /api/admin/* (403 for non-superadmin).
- /api/admin/stats numeric shape.
- /api/admin/users includes superadmin@promoos.com with state=active; workspace_name populated.
- /api/admin/users lifecycle: create → suspend (login 403) → activate (login 200) → delete (login 403 "deleted") → restore.
- /api/admin/workspaces per-workspace counts numeric.
- /api/admin/logs contains an entry per admin action.
- /api/admin/payments {total_collected, count, payments} — empty list valid.
- GET /api/library/coupon-types → 23 items with id/name/cat/desc/default_value/audience and category coverage.
- Iter 1-6 regression smokes.
"""
import base64
import hashlib
import hmac as _hmac
import json
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


# ---------------- fixtures ----------------
def _login(email: str, password: str, expect_ok: bool = True):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    if expect_ok:
        assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
        return r.json()
    return r


@pytest.fixture(scope="module")
def superadmin():
    return _login("superadmin@promoos.com", "superadmin123")


@pytest.fixture(scope="module")
def sa_headers(superadmin):
    return {"Authorization": f"Bearer {superadmin['token']}"}


@pytest.fixture(scope="module")
def owner():
    return _login("admin@promoos.com", "admin123")


@pytest.fixture(scope="module")
def owner_headers(owner):
    return {"Authorization": f"Bearer {owner['token']}"}


@pytest.fixture(scope="module")
def marketer_headers():
    return {"Authorization": f"Bearer {_login('marketer@promoos.com', 'marketer123')['token']}"}


@pytest.fixture(scope="module")
def viewer_headers():
    return {"Authorization": f"Bearer {_login('viewer@promoos.com', 'viewer123')['token']}"}


@pytest.fixture(scope="module")
def workspace_id(owner_headers):
    r = requests.get(f"{API}/workspace", headers=owner_headers, timeout=10)
    assert r.status_code == 200
    return r.json()["id"]


# ================================================================
# Section 1 — Encrypted webhook secrets (Fernet at rest)
# ================================================================
class TestWebhookSecretsEncrypted:
    def test_rotate_returns_whsec_token(self, owner_headers):
        r = requests.post(f"{API}/pos/rotate-secret",
                          json={"provider": "shopify"}, headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["provider"] == "shopify"
        assert data["secret"].startswith("whsec_")
        assert len(data["secret"]) >= 40, f"whsec length {len(data['secret'])} < 40"

    def test_get_secrets_shape_no_plaintext(self, owner_headers, workspace_id):
        # ensure a secret is set
        r0 = requests.post(f"{API}/pos/rotate-secret",
                           json={"provider": "shopify"}, headers=owner_headers, timeout=10)
        assert r0.status_code == 200
        r = requests.get(f"{API}/pos/secrets", headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "shopify" in data and "woocommerce" in data
        sh = data["shopify"]
        assert sh["configured"] is True
        assert sh["rotated_at"] is not None
        # preview is short and not the full secret
        assert sh["preview"] and len(sh["preview"]) <= 20
        # Preview should not be a full whsec_ token
        assert not sh["preview"].startswith("whsec_") or "…" in sh["preview"]

    def test_hmac_works_after_rotation(self, owner_headers, workspace_id):
        # Create a test coupon (active) to redeem via shopify webhook
        code = f"TEST_ITER7_HMAC_{uuid.uuid4().hex[:6].upper()}"
        cp = requests.post(f"{API}/coupons",
                           json={"name": f"TEST_ITER7 hmac {code}", "type": "percentage",
                                 "discount_value": 15, "code": code, "state": "active"},
                           headers=owner_headers, timeout=10)
        assert cp.status_code == 200, cp.text
        # rotate to get fresh plaintext (Fernet-encrypted at rest)
        rot = requests.post(f"{API}/pos/rotate-secret",
                            json={"provider": "shopify"}, headers=owner_headers, timeout=10)
        assert rot.status_code == 200
        secret = rot.json()["secret"]

        payload = {"id": 12345, "total_price": "100.00",
                   "email": "buyer@example.com",
                   "note_attributes": [{"name": "promoos", "value": code}]}
        raw = json.dumps(payload).encode("utf-8")
        sig = base64.b64encode(
            _hmac.new(secret.encode(), raw, hashlib.sha256).digest()).decode()

        # correct sig → 200 applied
        r_ok = requests.post(f"{API}/pos/{workspace_id}/shopify",
                             data=raw,
                             headers={"Content-Type": "application/json",
                                      "X-Shopify-Hmac-Sha256": sig},
                             timeout=10)
        assert r_ok.status_code == 200, r_ok.text
        body_ok = r_ok.json()
        assert body_ok.get("applied") is True
        assert body_ok.get("discount", 0) > 0

        # bad sig → 401
        r_bad = requests.post(f"{API}/pos/{workspace_id}/shopify",
                              data=raw,
                              headers={"Content-Type": "application/json",
                                       "X-Shopify-Hmac-Sha256": "AAAAinvalidsig=="},
                              timeout=10)
        assert r_bad.status_code == 401

    def test_delete_secret_restores_trust_mode(self, owner_headers, workspace_id):
        # rotate to ensure there is a secret first
        requests.post(f"{API}/pos/rotate-secret",
                      json={"provider": "shopify"}, headers=owner_headers, timeout=10)
        d = requests.delete(f"{API}/pos/secret/shopify", headers=owner_headers, timeout=10)
        assert d.status_code == 200, d.text
        # confirm secrets shape shows not configured
        r = requests.get(f"{API}/pos/secrets", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        sh = r.json()["shopify"]
        assert sh["configured"] is False
        assert sh["preview"] is None
        assert sh["rotated_at"] is None

        # trust-mode now accepts unsigned webhook (with a valid code)
        code = f"TEST_ITER7_TRUST_{uuid.uuid4().hex[:6].upper()}"
        cp = requests.post(f"{API}/coupons",
                           json={"name": f"TEST_ITER7 trust {code}", "type": "percentage",
                                 "discount_value": 10, "code": code, "state": "active"},
                           headers=owner_headers, timeout=10)
        assert cp.status_code == 200
        payload = {"id": 99999, "total_price": "50.00",
                   "email": "b@e.com",
                   "note_attributes": [{"name": "promoos", "value": code}]}
        raw = json.dumps(payload).encode()
        r_ok = requests.post(f"{API}/pos/{workspace_id}/shopify", data=raw,
                             headers={"Content-Type": "application/json"}, timeout=10)
        # No secret set → no HMAC required → applies successfully
        assert r_ok.status_code == 200
        assert r_ok.json().get("applied") is True


# ================================================================
# Section 2 — v1/coupons/redeem API-key auth
# ================================================================
class TestV1CouponRedeemApiKeyAuth:
    @pytest.fixture(scope="class")
    def active_coupon_code(self, owner_headers):
        code = f"TEST_ITER7_V1_{uuid.uuid4().hex[:6].upper()}"
        r = requests.post(f"{API}/coupons",
                          json={"name": f"TEST_ITER7 v1 {code}", "type": "percentage",
                                "discount_value": 20, "code": code, "state": "active"},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        return code

    @pytest.fixture(scope="class")
    def write_key(self, owner_headers):
        r = requests.post(f"{API}/api-keys",
                          json={"name": "TEST_ITER7_write", "scopes": ["read", "write"]},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        return r.json()

    @pytest.fixture(scope="class")
    def read_only_key(self, owner_headers):
        r = requests.post(f"{API}/api-keys",
                          json={"name": "TEST_ITER7_readonly", "scopes": ["read"]},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 200, r.text
        return r.json()

    def test_missing_bearer_returns_401(self, active_coupon_code):
        r = requests.post(f"{API}/v1/coupons/redeem",
                          json={"code": active_coupon_code, "amount": 100},
                          timeout=10)
        assert r.status_code == 401
        detail = r.json().get("detail", "")
        assert "Missing bearer token" in detail

    def test_invalid_key_returns_401(self, active_coupon_code):
        r = requests.post(f"{API}/v1/coupons/redeem",
                          json={"code": active_coupon_code, "amount": 100},
                          headers={"Authorization": "Bearer pk_live_totally_not_a_real_key_xyz"},
                          timeout=10)
        assert r.status_code == 401
        assert "Invalid or revoked API key" in r.json().get("detail", "")

    def test_non_pk_live_token_returns_401(self, active_coupon_code):
        r = requests.post(f"{API}/v1/coupons/redeem",
                          json={"code": active_coupon_code, "amount": 100},
                          headers={"Authorization": "Bearer sk_test_xyz"},
                          timeout=10)
        assert r.status_code == 401

    def test_readonly_scope_returns_403(self, active_coupon_code, read_only_key):
        r = requests.post(f"{API}/v1/coupons/redeem",
                          json={"code": active_coupon_code, "amount": 100,
                                "customer": f"ro-{uuid.uuid4().hex[:6]}"},
                          headers={"Authorization": f"Bearer {read_only_key['key']}"},
                          timeout=10)
        assert r.status_code == 403
        assert "write" in r.json().get("detail", "").lower()

    def test_write_key_success(self, active_coupon_code, write_key):
        r = requests.post(f"{API}/v1/coupons/redeem",
                          json={"code": active_coupon_code, "amount": 200,
                                "customer": f"w-{uuid.uuid4().hex[:6]}"},
                          headers={"Authorization": f"Bearer {write_key['key']}"},
                          timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert data["discount"] == 40.0    # 20% of 200
        assert data["revenue"] == 160.0

    def test_revoked_key_returns_401(self, owner_headers, active_coupon_code):
        # create + revoke a key
        c = requests.post(f"{API}/api-keys",
                          json={"name": "TEST_ITER7_revoke", "scopes": ["read", "write"]},
                          headers=owner_headers, timeout=10).json()
        rv = requests.post(f"{API}/api-keys/{c['id']}/revoke",
                           headers=owner_headers, timeout=10)
        assert rv.status_code == 200
        r = requests.post(f"{API}/v1/coupons/redeem",
                          json={"code": active_coupon_code, "amount": 100,
                                "customer": f"rev-{uuid.uuid4().hex[:6]}"},
                          headers={"Authorization": f"Bearer {c['key']}"},
                          timeout=10)
        assert r.status_code == 401
        assert "Invalid or revoked API key" in r.json().get("detail", "")


# ================================================================
# Section 3 — Superadmin auth & RBAC on /api/admin/*
# ================================================================
class TestSuperadminAuthAndRBAC:
    def test_superadmin_login_role(self, superadmin):
        assert superadmin["user"]["role"] == "superadmin"
        assert superadmin["user"]["email"] == "superadmin@promoos.com"

    @pytest.mark.parametrize("path", [
        "/admin/stats", "/admin/users", "/admin/workspaces",
        "/admin/logs", "/admin/payments"])
    def test_admin_endpoints_403_for_owner(self, owner_headers, path):
        r = requests.get(f"{API}{path}", headers=owner_headers, timeout=10)
        assert r.status_code == 403

    @pytest.mark.parametrize("path", [
        "/admin/stats", "/admin/users", "/admin/workspaces",
        "/admin/logs", "/admin/payments"])
    def test_admin_endpoints_403_for_marketer(self, marketer_headers, path):
        r = requests.get(f"{API}{path}", headers=marketer_headers, timeout=10)
        assert r.status_code == 403

    @pytest.mark.parametrize("path", [
        "/admin/stats", "/admin/users", "/admin/workspaces",
        "/admin/logs", "/admin/payments"])
    def test_admin_endpoints_403_for_viewer(self, viewer_headers, path):
        r = requests.get(f"{API}{path}", headers=viewer_headers, timeout=10)
        assert r.status_code == 403


# ================================================================
# Section 4 — Admin stats / users / workspaces / logs / payments
# ================================================================
class TestAdminEndpoints:
    def test_admin_stats_numeric_shape(self, sa_headers):
        r = requests.get(f"{API}/admin/stats", headers=sa_headers, timeout=10)
        assert r.status_code == 200, r.text
        d = r.json()
        assert set(d.keys()) >= {"users", "workspaces", "coupons", "redemptions"}
        for k in ("active", "suspended", "deleted"):
            assert isinstance(d["users"][k], int)
        for k in ("workspaces", "coupons", "redemptions"):
            assert isinstance(d[k], int)
        assert d["users"]["active"] >= 1  # at least superadmin

    def test_admin_users_lists_superadmin(self, sa_headers):
        r = requests.get(f"{API}/admin/users", headers=sa_headers, timeout=10)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list) and len(rows) >= 4
        sa = next((u for u in rows if u["email"] == "superadmin@promoos.com"), None)
        assert sa is not None, "superadmin missing from /admin/users"
        assert sa["state"] == "active"
        assert sa["role"] == "superadmin"
        # workspace_name populated
        for u in rows:
            assert "workspace_name" in u
            assert u.get("state") in ("active", "suspended", "deleted")

    def test_admin_workspaces_counts(self, sa_headers):
        r = requests.get(f"{API}/admin/workspaces", headers=sa_headers, timeout=10)
        assert r.status_code == 200
        docs = r.json()
        assert isinstance(docs, list) and len(docs) >= 1
        for d in docs:
            for k in ("user_count", "coupon_count", "redemption_count"):
                assert isinstance(d.get(k), int)

    def test_admin_logs_shape(self, sa_headers):
        r = requests.get(f"{API}/admin/logs", headers=sa_headers, timeout=10)
        assert r.status_code == 200
        docs = r.json()
        assert isinstance(docs, list)

    def test_admin_payments_shape(self, sa_headers):
        r = requests.get(f"{API}/admin/payments", headers=sa_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert set(d.keys()) >= {"total_collected", "count", "payments"}
        assert isinstance(d["total_collected"], (int, float))
        assert isinstance(d["count"], int)
        assert isinstance(d["payments"], list)


# ================================================================
# Section 5 — Admin user lifecycle: create, suspend, activate, delete, restore
# ================================================================
class TestAdminUserLifecycle:
    def test_full_lifecycle(self, sa_headers):
        # create
        email = f"test_iter7_{uuid.uuid4().hex[:8]}@example.com"
        password = "Test-Iter7-Pass-123"
        c = requests.post(f"{API}/admin/users",
                          json={"name": "T7 Lifecycle", "email": email,
                                "password": password, "role": "marketer",
                                "workspace_name": "T7 LifecycleWS"},
                          headers=sa_headers, timeout=10)
        assert c.status_code == 200, c.text
        uid = c.json()["user_id"]

        # login works
        r_login = _login(email, password, expect_ok=False)
        assert r_login.status_code == 200

        # suspend
        s = requests.post(f"{API}/admin/users/{uid}/suspend", headers=sa_headers, timeout=10)
        assert s.status_code == 200
        r_login = _login(email, password, expect_ok=False)
        assert r_login.status_code == 403
        assert "suspend" in r_login.json().get("detail", "").lower()

        # activate
        a = requests.post(f"{API}/admin/users/{uid}/activate", headers=sa_headers, timeout=10)
        assert a.status_code == 200
        r_login = _login(email, password, expect_ok=False)
        assert r_login.status_code == 200

        # delete
        d = requests.delete(f"{API}/admin/users/{uid}", headers=sa_headers, timeout=10)
        assert d.status_code == 200
        r_login = _login(email, password, expect_ok=False)
        assert r_login.status_code == 403
        assert "delet" in r_login.json().get("detail", "").lower()

        # restore
        rr = requests.post(f"{API}/admin/users/{uid}/restore", headers=sa_headers, timeout=10)
        assert rr.status_code == 200
        r_login = _login(email, password, expect_ok=False)
        assert r_login.status_code == 200

        # logs picked up at least one entry for this uid
        logs = requests.get(f"{API}/admin/logs", headers=sa_headers, timeout=10).json()
        actions_for_uid = [l for l in logs if l.get("target") == uid]
        assert len(actions_for_uid) >= 4, f"expected >=4 log entries for {uid}, got {len(actions_for_uid)}"
        actions = {l["action"] for l in actions_for_uid}
        assert {"user.create", "user.suspend", "user.activate", "user.delete", "user.restore"} <= actions

    def test_cannot_self_delete_superadmin(self, sa_headers, superadmin):
        sa_uid = superadmin["user"]["id"]
        r = requests.delete(f"{API}/admin/users/{sa_uid}", headers=sa_headers, timeout=10)
        assert r.status_code == 400
        assert "own account" in r.json().get("detail", "").lower()

    def test_create_user_duplicate_email_400(self, sa_headers):
        r = requests.post(f"{API}/admin/users",
                          json={"name": "Dup", "email": "admin@promoos.com",
                                "password": "Xxxxx-Pass-123", "role": "marketer"},
                          headers=sa_headers, timeout=10)
        assert r.status_code == 400


# ================================================================
# Section 6 — /api/library/coupon-types
# ================================================================
class TestCouponLibrary:
    def test_23_items_and_shape(self):
        r = requests.get(f"{API}/library/coupon-types", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        assert len(d) == 23, f"expected 23, got {len(d)}"
        needed = {"id", "name", "cat", "desc", "default_value", "audience"}
        for item in d:
            assert needed <= set(item.keys()), f"missing keys in {item}"
            assert isinstance(item["id"], str) and item["id"]
            assert isinstance(item["default_value"], (int, float))

    def test_category_coverage(self):
        r = requests.get(f"{API}/library/coupon-types", timeout=10)
        cats = {i["cat"] for i in r.json()}
        expected = {"Discount", "Bundle", "Perk", "Acquisition", "Retention",
                    "Growth", "Lifecycle", "Loyalty", "Urgency", "Geo",
                    "Campaign", "Recurring", "Attribution"}
        missing = expected - cats
        assert not missing, f"missing categories: {missing}"


# ================================================================
# Section 7 — Regression smokes (iter 1-6)
# ================================================================
class TestRegression:
    def test_auth_me(self, owner_headers):
        r = requests.get(f"{API}/auth/me", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert r.json().get("email") == "admin@promoos.com"

    def test_list_coupons(self, owner_headers):
        r = requests.get(f"{API}/coupons", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_public_redeem_still_works(self, owner_headers):
        code = f"TEST_ITER7_REG_{uuid.uuid4().hex[:6].upper()}"
        cp = requests.post(f"{API}/coupons",
                           json={"name": f"TEST_ITER7 reg {code}", "type": "percentage",
                                 "discount_value": 10, "code": code, "state": "active"},
                           headers=owner_headers, timeout=10)
        assert cp.status_code == 200
        r = requests.post(f"{API}/public/coupons/redeem",
                          json={"code": code, "amount": 100,
                                "customer": f"reg-{uuid.uuid4().hex[:6]}"}, timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["discount"] == 10.0
        assert d["revenue"] == 90.0

    def test_authenticated_redeem(self, owner_headers):
        code = f"TEST_ITER7_AR_{uuid.uuid4().hex[:6].upper()}"
        cp = requests.post(f"{API}/coupons",
                           json={"name": f"TEST_ITER7 authred {code}", "type": "percentage",
                                 "discount_value": 25, "code": code, "state": "active"},
                           headers=owner_headers, timeout=10)
        assert cp.status_code == 200
        r = requests.post(f"{API}/coupons/redeem",
                          json={"code": code, "amount": 80,
                                "customer": f"ar-{uuid.uuid4().hex[:6]}"},
                          headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert r.json()["discount"] == 20.0

    def test_gift_cards_list(self, owner_headers):
        r = requests.get(f"{API}/gift-cards", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        d = r.json()
        # v6+: endpoint returns aggregate dict with a "cards" list
        assert isinstance(d, dict) and "cards" in d and isinstance(d["cards"], list)

    def test_journeys_list(self, owner_headers):
        r = requests.get(f"{API}/journeys", headers=owner_headers, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_analytics_csv_export(self, owner_headers):
        r = requests.get(f"{API}/analytics/export?format=csv&period=30",
                         headers=owner_headers, timeout=15)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "") or \
               "PromoOS Performance Report" in r.text[:200]
        assert len(r.content) > 100

    def test_shopify_hmac_signed_still_works(self, owner_headers, workspace_id):
        # rotate a fresh secret, then post a signed webhook
        rot = requests.post(f"{API}/pos/rotate-secret",
                            json={"provider": "shopify"}, headers=owner_headers, timeout=10)
        assert rot.status_code == 200
        secret = rot.json()["secret"]
        code = f"TEST_ITER7_REGH_{uuid.uuid4().hex[:6].upper()}"
        cp = requests.post(f"{API}/coupons",
                           json={"name": f"TEST_ITER7 regh {code}", "type": "percentage",
                                 "discount_value": 5, "code": code, "state": "active"},
                           headers=owner_headers, timeout=10)
        assert cp.status_code == 200
        payload = {"id": 55555, "total_price": "40.00",
                   "email": "regh@e.com",
                   "note_attributes": [{"name": "promoos", "value": code}]}
        raw = json.dumps(payload).encode()
        sig = base64.b64encode(_hmac.new(secret.encode(), raw,
                                         hashlib.sha256).digest()).decode()
        r = requests.post(f"{API}/pos/{workspace_id}/shopify", data=raw,
                          headers={"Content-Type": "application/json",
                                   "X-Shopify-Hmac-Sha256": sig}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("applied") is True

    def test_ai_endpoint_soft_check_only(self, owner_headers):
        # AI budget may be exhausted; do NOT drive the model — verify status in expected set only.
        r = requests.post(f"{API}/ai/copy", json={"prompt": "20% off spring collection"},
                          headers=owner_headers, timeout=30)
        # Acceptable: 200 (works), 429 (budget), 502 (upstream)
        assert r.status_code in (200, 429, 502), r.text
