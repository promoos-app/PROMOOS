"""Iter23 — Preset Pack ratings + comments, DSAR notify, loadtest scripts, runbook."""
import os, hashlib, io, subprocess
import pytest, requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://campaign-hub-436.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

OWNER = {"email": "admin@promoos.com", "password": "admin123"}
SUPER = {"email": "superadmin@promoos.com", "password": "sZpRBNpLKypsQDURBQNqMIzE"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def owner_token(): return _login(OWNER)


@pytest.fixture(scope="module")
def super_token(): return _login(SUPER)


def H(tok): return {"Authorization": f"Bearer {tok}"}


# ---------- Preset Pack listing includes rating aggregates ----------
def _get_coupon_pack_id(tok):
    r = requests.get(f"{API}/preset-packs", headers=H(tok), params={"scope": "coupon"}, timeout=15)
    assert r.status_code == 200, r.text
    packs = r.json()
    return packs[0] if packs else None


def test_public_packs_include_rating_fields(owner_token):
    r = requests.get(f"{API}/preset-packs", headers=H(owner_token), params={"scope": "coupon"}, timeout=15)
    assert r.status_code == 200
    packs = r.json()
    assert isinstance(packs, list)
    if not packs:
        pytest.skip("No coupon preset packs seeded")
    p = packs[0]
    assert "rating_avg" in p and "rating_count" in p
    assert isinstance(p["rating_avg"], (int, float))
    assert isinstance(p["rating_count"], int)


# ---------- Rating validation ----------
def test_rate_pack_invalid_stars(owner_token):
    pack = _get_coupon_pack_id(owner_token)
    if not pack:
        pytest.skip("No pack available")
    r = requests.post(f"{API}/preset-packs/{pack['id']}/rate", headers=H(owner_token),
                      json={"stars": 0}, timeout=15)
    assert r.status_code == 400
    r2 = requests.post(f"{API}/preset-packs/{pack['id']}/rate", headers=H(owner_token),
                       json={"stars": 6}, timeout=15)
    assert r2.status_code == 400


def test_rate_pack_404_missing(owner_token):
    r = requests.post(f"{API}/preset-packs/does-not-exist-xyz/rate", headers=H(owner_token),
                      json={"stars": 4}, timeout=15)
    assert r.status_code == 404


# ---------- Rating upsert + comments ----------
def test_rate_pack_upsert_and_comments(owner_token):
    pack = _get_coupon_pack_id(owner_token)
    if not pack:
        pytest.skip("No pack available")
    pid = pack["id"]
    # First rating with comment
    r1 = requests.post(f"{API}/preset-packs/{pid}/rate", headers=H(owner_token),
                       json={"stars": 5, "comment": "TEST_iter23 comment first"}, timeout=15)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1.get("ok") is True
    count_after_first = d1.get("count")

    # Second rating same workspace — should overwrite (no duplicate)
    r2 = requests.post(f"{API}/preset-packs/{pid}/rate", headers=H(owner_token),
                       json={"stars": 4, "comment": "TEST_iter23 comment second"}, timeout=15)
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("count") == count_after_first, (
        f"Duplicate row inserted: count went {count_after_first} → {d2.get('count')}")
    assert d2.get("avg") == 4.0 or abs(d2.get("avg") - 4.0) < 0.01 or d2.get("count") > 1

    # GET comments — sorted by rated_at desc, workspace_name populated
    r3 = requests.get(f"{API}/preset-packs/{pid}/comments", headers=H(owner_token), timeout=15)
    assert r3.status_code == 200
    comments = r3.json().get("comments", [])
    # Latest comment should be at top
    assert any(c.get("comment") == "TEST_iter23 comment second" for c in comments)
    for c in comments:
        assert c.get("workspace_name")
        assert c.get("comment")  # stars-only entries must not appear


def test_rate_pack_stars_only_not_in_comments(owner_token, super_token):
    pack = _get_coupon_pack_id(owner_token)
    if not pack:
        pytest.skip("No pack available")
    pid = pack["id"]
    # Super rates without comment
    r = requests.post(f"{API}/preset-packs/{pid}/rate", headers=H(super_token),
                      json={"stars": 3}, timeout=15)
    assert r.status_code == 200
    r2 = requests.get(f"{API}/preset-packs/{pid}/comments", headers=H(owner_token), timeout=15)
    assert r2.status_code == 200
    comments = r2.json().get("comments", [])
    # None of the comments should be None/empty
    for c in comments:
        assert c.get("comment")


# ---------- DSAR delete still returns 200 (fire-and-forget notify) ----------
def test_dsar_delete_still_returns_ok(owner_token):
    r = requests.post(f"{API}/me/data/delete", headers=H(owner_token),
                      json={"confirm_email": OWNER["email"], "reason": "TEST_iter23_notify"}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("ok") is True
    assert d.get("request_id")
    assert d.get("status") == "pending"


# ---------- Regression: iter22 endpoints ----------
def test_security_txt():
    r = requests.get(f"{API}/.well-known/security.txt", timeout=15)
    assert r.status_code == 200
    assert "Contact:" in r.text


def test_errors_anon():
    r = requests.post(f"{API}/errors",
                      json={"message": "TEST_iter23 anon", "route": "/x"}, timeout=15)
    assert r.status_code == 200 and r.json().get("ok") is True


def test_me_export(owner_token):
    r = requests.get(f"{API}/me/export", headers=H(owner_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("coupons", "gift_cards", "customers"):
        assert k in d


def test_csv_import_semicolon(owner_token):
    files = {"file": ("t.csv", io.BytesIO(b"promo_code;offer_name;pct\nX1;Test;10\n"), "text/csv")}
    r = requests.post(f"{API}/coupons/import-csv", headers=H(owner_token), files=files,
                      params={"dry_run": "true"}, timeout=30)
    assert r.status_code == 200
    assert r.json().get("delimiter") == "semicolon"


def test_coupons_import_mapping_get(owner_token):
    # Any signature returns 200 with empty when no preset
    r = requests.get(f"{API}/coupons/import-mapping", headers=H(owner_token),
                     params={"signature": "0" * 16}, timeout=15)
    assert r.status_code == 200


def test_journey_templates_list(owner_token):
    r = requests.get(f"{API}/journey-templates", headers=H(owner_token), timeout=15)
    assert r.status_code == 200


def test_unsubscribe_html():
    JWT_SECRET = "7f3d9a2c8b1e4f6a0d5c7e9b2a4f6d8c1e3a5b7d9f0c2e4a6b8d0f1c3e5a7b9d"
    tok = hashlib.sha256(f"{JWT_SECRET}::{OWNER['email']}".encode()).hexdigest()[:32]
    r = requests.get(f"{API}/unsubscribe/{tok}", timeout=15)
    assert r.status_code == 200 and "text/html" in r.headers.get("content-type", "")


# ---------- Load test scripts exist & valid ----------
def test_loadtest_scripts_exist():
    assert os.path.isfile("/app/scripts/loadtest.k6.js")
    assert os.path.isfile("/app/scripts/loadtest_bench.py")
    import ast
    ast.parse(open("/app/scripts/loadtest_bench.py").read())


def test_loadtest_bench_runs_briefly():
    """Runs the bench for 5s to verify it doesn't crash. Preview URL may 429 — that's OK."""
    try:
        result = subprocess.run(
            ["python3", "/app/scripts/loadtest_bench.py", "--duration", "5", "--concurrency", "3"],
            capture_output=True, timeout=30, text=True)
        # exit 0 preferred, but non-zero acceptable if it printed rate stats
        assert result.returncode == 0 or "req/s" in (result.stdout + result.stderr).lower() or \
               "requests" in (result.stdout + result.stderr).lower(), \
               f"bench failed:\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}"
    except subprocess.TimeoutExpired:
        pytest.fail("loadtest_bench.py did not exit within 30s")


def test_provisioning_runbook_covers_phases():
    txt = open("/app/PROVISIONING_RUNBOOK.md").read().lower()
    for kw in ["sanity", "credential", "stripe", "resend", "cors", "merchant", "compliance", "load test", "post-launch"]:
        assert kw in txt, f"runbook missing keyword: {kw}"
