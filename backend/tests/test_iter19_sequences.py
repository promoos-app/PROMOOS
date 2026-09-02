"""Iteration 19 — funnel templates count, sequences CRUD, public funnel regression."""
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


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": "admin@promoos.com", "password": "admin123"})
    if r.status_code != 200:
        pytest.fail(f"Login failed {r.status_code}: {r.text[:300]}")
    token = r.json().get("access_token") or r.json().get("token")
    if not token:
        pytest.fail(f"No token in login response: {r.text[:300]}")
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s


# --- Funnel templates ---
def test_funnel_templates_19(client):
    r = client.get(f"{API}/funnels/templates")
    assert r.status_code == 200, r.text[:300]
    data = r.json()
    assert "templates" in data
    ids = [t["id"] for t in data["templates"]]
    assert len(ids) == 19, f"expected 19 templates, got {len(ids)}: {ids}"
    assert "info_page" in ids
    for t in data["templates"]:
        assert "theme" in t and "bg" in t["theme"]


# --- Sequences CRUD ---
def test_sequences_crud(client):
    payload = {
        "name": "TEST_Welcome seq",
        "trigger": "optin",
        "lead_tag_filter": "leadmagnet",
        "enabled": True,
        "steps": [{"delay_hours": 0, "subject": "Hi", "body": "Test"},
                  {"delay_hours": 24, "subject": "Day 1", "body": "More"}],
    }
    r = client.post(f"{API}/sequences", json=payload)
    assert r.status_code in (200, 201), r.text[:400]
    created = r.json()
    assert "_id" not in created
    sid = created["id"]
    assert created["name"] == payload["name"]
    assert len(created["steps"]) == 2

    # LIST persistence
    r = client.get(f"{API}/sequences")
    assert r.status_code == 200
    lst = r.json()
    assert all("_id" not in x for x in lst)
    match = [x for x in lst if x["id"] == sid]
    assert match, "created sequence not returned by list"
    assert match[0]["trigger"] == "optin"
    assert match[0]["lead_tag_filter"] == "leadmagnet"

    # UPDATE
    r = client.put(f"{API}/sequences/{sid}", json={**payload, "name": "TEST_Renamed", "enabled": False})
    assert r.status_code == 200, r.text[:300]
    lst = client.get(f"{API}/sequences").json()
    upd = [x for x in lst if x["id"] == sid][0]
    assert upd["name"] == "TEST_Renamed"
    assert upd["enabled"] is False

    # DELETE
    r = client.delete(f"{API}/sequences/{sid}")
    assert r.status_code in (200, 204), r.text[:300]
    lst = client.get(f"{API}/sequences").json()
    assert not [x for x in lst if x["id"] == sid], "sequence still listed after delete"


def test_sequences_requires_auth():
    r = requests.get(f"{API}/sequences")
    assert r.status_code in (401, 403), r.status_code


# --- Public funnel regression ---
def test_public_funnel_qa_storefront():
    r = requests.get(f"{API}/public/f/qa-storefront-live")
    if r.status_code == 404:
        pytest.skip("seed funnel qa-storefront-live not present")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert "_id" not in d
    assert d.get("slug") == "qa-storefront-live"
    assert isinstance(d.get("blocks"), list) and len(d["blocks"]) > 0
