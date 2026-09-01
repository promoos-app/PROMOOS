"""Iteration 12 — auth playbook checks + storefront empty-workspace fallback."""
import os
import subprocess
import uuid
import pytest
import requests
from dotenv import dotenv_values

fe = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or fe.get("REACT_APP_BACKEND_URL")).rstrip("/")
API = f"{BASE_URL}/api"
OWNER = {"email": "admin@promoos.com", "password": "admin123"}
SUPER = {"email": "superadmin@promoos.com", "password": "sZpRBNpLKypsQDURBQNqMIzE"}


# ---------- Auth playbook ----------
class TestAuthPlaybook:
    def test_bcrypt_hash_format(self):
        out = subprocess.run(
            ["python", "-c",
             "import asyncio,os;from motor.motor_asyncio import AsyncIOMotorClient;"
             "from dotenv import load_dotenv;load_dotenv('/app/backend/.env');"
             "c=AsyncIOMotorClient(os.environ['MONGO_URL']);d=c[os.environ['DB_NAME']];"
             "print(asyncio.get_event_loop().run_until_complete("
             "d.users.find_one({'email':'admin@promoos.com'}))['password_hash'][:4])"],
            capture_output=True, text=True, cwd="/app/backend")
        assert "$2b$" in out.stdout, f"bcrypt prefix not $2b$: {out.stdout} {out.stderr[-300:]}"

    def test_login_sets_httponly_cookie(self):
        r = requests.post(f"{API}/auth/login", json=OWNER, timeout=30)
        assert r.status_code == 200
        raw = r.headers.get("set-cookie", "")
        assert "access_token" in raw, f"no access_token cookie: {raw[:200]}"
        assert "HttpOnly" in raw or "httponly" in raw, f"cookie not HttpOnly: {raw[:200]}"

    def test_cors_credentials_explicit_origin(self):
        """The preview CDN edge rewrites CORS headers to '*', so assert the FastAPI
        CORSMiddleware config directly on the app-local port."""
        import socket
        try:
            r = requests.post("http://localhost:8001/api/auth/login", json=OWNER,
                              headers={"Origin": BASE_URL}, timeout=30)
        except (requests.ConnectionError, socket.error) as e:
            pytest.skip(f"app-local port unreachable: {e}")
        assert r.status_code == 200, r.text[:200]
        assert r.headers.get("access-control-allow-credentials") == "true"
        assert r.headers.get("access-control-allow-origin") == BASE_URL, r.headers.get("access-control-allow-origin")

    def test_brute_force_lockout_after_5_fails(self):
        # unique email per run so the 15-min lockout window from a previous run
        # does not poison the assertion
        email = f"TEST_bf_iter12_{uuid.uuid4().hex[:10]}@example.com"
        codes = []
        for _ in range(7):
            r = requests.post(f"{API}/auth/login", json={"email": email, "password": "nope"}, timeout=30)
            codes.append(r.status_code)
        assert 429 in codes, f"no lockout, codes={codes}"
        assert codes.index(429) >= 5, f"locked too early: {codes}"

    def test_invalid_password_401(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "admin@promoos.com", "password": "wrong-pw-iter12"}, timeout=30)
        assert r.status_code in (401, 429), r.status_code

    def test_seed_admin_password_still_valid_after_restart(self):
        """seed_admin must be idempotent — both accounts still log in."""
        for creds in (OWNER, SUPER):
            r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
            assert r.status_code == 200, f"{creds['email']} -> {r.status_code} {r.text[:200]}"


# ---------- Storefront in an empty workspace ----------
class TestStorefrontEmptyWorkspace:
    def test_empty_workspace_storefront_placeholders(self):
        s = requests.Session()
        t = requests.post(f"{API}/auth/login", json=SUPER, timeout=30).json()["token"]
        s.headers.update({"Authorization": f"Bearer {t}", "Content-Type": "application/json"})
        prods = s.get(f"{API}/products", timeout=30).json()
        prods = prods if isinstance(prods, list) else prods.get("products", [])
        cps = s.get(f"{API}/coupons", timeout=30).json()
        cps = cps if isinstance(cps, list) else cps.get("coupons", [])
        if prods or cps:
            pytest.skip(f"superadmin workspace not empty (products={len(prods)}, coupons={len(cps)})")
        r = s.post(f"{API}/funnels", json={"name": "TEST_Empty_SF", "template_id": "storefront"}, timeout=30)
        assert r.status_code == 200, r.text[:300]
        f = r.json()
        try:
            pb = next(b for b in f["blocks"] if b["type"] == "product")["props"]
            assert pb["product_id"] == ""
            assert pb["coupon_code"] == ""
            ti = next(b for b in f["blocks"] if b["type"] == "testimonial")["props"]["items"]
            assert len(ti) == 3
        finally:
            s.delete(f"{API}/funnels/{f['id']}", timeout=30)
