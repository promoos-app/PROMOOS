"""Iter22 backend batch — Compliance / DSAR / CSV / Mapping / Ratings / Unsubscribe / security.txt"""
import os, io, hashlib, uuid, json
import pytest, requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://campaign-hub-436.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
JWT_SECRET = "7f3d9a2c8b1e4f6a0d5c7e9b2a4f6d8c1e3a5b7d9f0c2e4a6b8d0f1c3e5a7b9d"

OWNER = {"email": "admin@promoos.com", "password": "admin123"}
SUPER = {"email": "superadmin@promoos.com", "password": "sZpRBNpLKypsQDURBQNqMIzE"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def owner_token():
    return _login(OWNER)


@pytest.fixture(scope="module")
def super_token():
    return _login(SUPER)


def H(tok): return {"Authorization": f"Bearer {tok}"}


# ---------- security.txt ----------
def test_security_txt():
    r = requests.get(f"{API}/.well-known/security.txt", timeout=15)
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")
    body = r.text
    assert "Contact:" in body and "Expires:" in body and "Policy:" in body


# ---------- error reporter ----------
def test_errors_anonymous():
    r = requests.post(f"{API}/errors",
                      json={"message": "TEST_anon crash", "stack": "at foo", "route": "/x", "user_agent": "pytest"},
                      timeout=15)
    assert r.status_code == 200
    assert r.json().get("ok") is True


def test_errors_authenticated(owner_token):
    r = requests.post(f"{API}/errors", headers=H(owner_token),
                      json={"message": "TEST_auth crash", "stack": "at bar", "route": "/y"}, timeout=15)
    assert r.status_code == 200 and r.json().get("ok") is True


def test_admin_errors_requires_superadmin(owner_token, super_token):
    r1 = requests.get(f"{API}/admin/errors", headers=H(owner_token), timeout=15)
    assert r1.status_code == 403
    r2 = requests.get(f"{API}/admin/errors", headers=H(super_token), timeout=15)
    assert r2.status_code == 200
    assert "reports" in r2.json()
    assert isinstance(r2.json()["reports"], list)


# ---------- DSAR ----------
def test_dsar_export_owner_workspace_scope(owner_token):
    r = requests.get(f"{API}/me/export", headers=H(owner_token), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d.get("scope") == "workspace"
    for k in ("coupons", "gift_cards", "redemptions", "customers", "journeys", "funnels"):
        assert k in d and isinstance(d[k], list), f"missing key {k}"


def test_dsar_delete_wrong_email_rejected(owner_token):
    r = requests.post(f"{API}/me/data/delete", headers=H(owner_token),
                      json={"confirm_email": "wrong@nope.com", "reason": "test"}, timeout=15)
    assert r.status_code == 400


def test_dsar_delete_queued(owner_token):
    r = requests.post(f"{API}/me/data/delete", headers=H(owner_token),
                      json={"confirm_email": OWNER["email"], "reason": "TEST_delete"}, timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("ok") is True and d.get("request_id")


# ---------- CSV delimiter + mapping presets ----------
def _upload_csv(tok, content, dry_run=True):
    files = {"file": ("t.csv", io.BytesIO(content.encode()), "text/csv")}
    return requests.post(f"{API}/coupons/import-csv",
                         headers=H(tok), files=files,
                         params={"dry_run": str(dry_run).lower()}, timeout=30)


def test_csv_delimiter_semicolon(owner_token):
    r = _upload_csv(owner_token, "promo_code;offer_name;pct\nSUMMER10;Summer;10\n")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("delimiter") == "semicolon"
    assert len(d.get("csv_headers", [])) == 3


def test_csv_delimiter_tab(owner_token):
    r = _upload_csv(owner_token, "promo_code\toffer_name\tpct\nWINTER5\tWinter\t5\n")
    assert r.status_code == 200
    assert r.json().get("delimiter") == "tab"


def test_mapping_preset_save_and_get(owner_token):
    headers = ["promo_code", "offer_name", "pct"]
    # signature must match backend: sha256 of sorted lowercased header pipe-join, first 16 chars
    norm = sorted(h.strip().lower() for h in headers)
    sig = hashlib.sha256("|".join(norm).encode()).hexdigest()[:16]
    mapping = {"promo_code": "code", "offer_name": "name", "pct": "discount_value"}
    r = requests.post(f"{API}/coupons/import-mapping", headers=H(owner_token),
                      json={"signature": sig, "mapping": mapping, "csv_headers": headers}, timeout=15)
    assert r.status_code == 200 and r.json().get("ok") is True

    r2 = requests.get(f"{API}/coupons/import-mapping", headers=H(owner_token),
                      params={"signature": sig}, timeout=15)
    assert r2.status_code == 200
    d = r2.json()
    assert d.get("mapping", {}).get("promo_code") == "code"


def test_preflight_returns_saved_mapping(owner_token):
    # After presets saved above, a dry-run upload with same headers should return saved_mapping populated
    r = _upload_csv(owner_token, "promo_code;offer_name;pct\nABC;Zzz;12\n", dry_run=True)
    assert r.status_code == 200
    d = r.json()
    sm = d.get("saved_mapping")
    assert sm and sm.get("promo_code") == "code"


# ---------- Journey template rating comments ----------
def _get_marketplace_template(super_tok, owner_tok):
    r = requests.get(f"{API}/journey-templates", headers=H(super_tok), timeout=15)
    if r.status_code == 200:
        for t in r.json().get("templates", []):
            if t.get("source") == "marketplace":
                return t["id"]
    # Seed one: superadmin creates a journey -> saves as template -> publishes
    j = requests.post(f"{API}/journeys", headers=H(super_tok),
                      json={"name": "TEST_j", "trigger": "manual",
                            "steps": [], "enabled": False}, timeout=15)
    if j.status_code != 200:
        return None
    jid = j.json()["id"]
    save = requests.post(f"{API}/journey-templates/save", headers=H(super_tok),
                         json={"journey_id": jid, "name": "TEST tmpl", "description": "t"}, timeout=15)
    if save.status_code != 200:
        return None
    tid = save.json()["id"]
    pub = requests.post(f"{API}/admin/journey-templates/{tid}/publish",
                        headers=H(super_tok), timeout=15)
    return tid if pub.status_code == 200 else None


def test_rating_with_comment(owner_token, super_token):
    tid = _get_marketplace_template(super_token, owner_token)
    if not tid:
        pytest.skip("No marketplace template available to rate")
    r = requests.post(f"{API}/journey-templates/{tid}/rate", headers=H(owner_token),
                      json={"stars": 5, "comment": "TEST_great template"}, timeout=15)
    assert r.status_code == 200, r.text
    r2 = requests.get(f"{API}/journey-templates/{tid}/comments", headers=H(owner_token), timeout=15)
    assert r2.status_code == 200
    comments = r2.json().get("comments", [])
    assert any(c.get("comment") == "TEST_great template" for c in comments)


# ---------- Unsubscribe (RFC 8058) ----------
def _unsub_token(email):
    return hashlib.sha256(f"{JWT_SECRET}::{email.strip().lower()}".encode()).hexdigest()[:32]


def test_unsubscribe_invalid_token():
    r = requests.post(f"{API}/unsubscribe/deadbeef" + "0" * 24, timeout=15)
    assert r.status_code == 404


def test_unsubscribe_valid_then_already():
    tok = _unsub_token(OWNER["email"])
    r1 = requests.post(f"{API}/unsubscribe/{tok}", timeout=20)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1.get("ok") is True
    assert d1.get("status") in ("unsubscribed", "already")
    r2 = requests.post(f"{API}/unsubscribe/{tok}", timeout=20)
    assert r2.status_code == 200
    assert r2.json().get("status") == "already"


def test_unsubscribe_get_html():
    tok = _unsub_token(OWNER["email"])
    r = requests.get(f"{API}/unsubscribe/{tok}", timeout=15)
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "unsubscribed" in r.text.lower()


# ---------- AI image metadata (allow skip on 502) ----------
def test_ai_image_metadata_shape(owner_token):
    r = requests.post(f"{API}/ai/image", headers=H(owner_token),
                      json={"prompt": "TEST minimal red square coupon background"}, timeout=90)
    if r.status_code in (502, 503, 429):
        pytest.skip(f"AI provider unavailable ({r.status_code})")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("ai_generated") is True
    assert d.get("provider")
    assert d.get("generated_at")
