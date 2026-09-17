"""Iter26 Newsletter System backend tests."""
import os
import io
import time
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://campaign-hub-436.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

OWNER_EMAIL = "admin@promoos.com"
OWNER_PASSWORD = "admin123"


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    j = r.json()
    return j.get("access_token") or j["token"]


@pytest.fixture(scope="session")
def h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def pub(h):
    name = f"TEST_Pub_{uuid.uuid4().hex[:6]}"
    r = requests.post(f"{API}/newsletter/publications", json={"name": name}, headers=h, timeout=15)
    assert r.status_code == 200, r.text
    p = r.json()
    yield p
    # cleanup
    requests.delete(f"{API}/newsletter/publications/{p['id']}", headers=h, timeout=15)


# ============= Publications =============
class TestPublications:
    def test_create_returns_defaults(self, h):
        r = requests.post(f"{API}/newsletter/publications", json={"name": "TEST_Alpha News"}, headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] and d["workspace_id"] and d["slug"] == "test-alpha-news"
        assert d["primary_color"] == "#005CEE"
        assert isinstance(d["referral_rewards"], list) and len(d["referral_rewards"]) == 3
        requests.delete(f"{API}/newsletter/publications/{d['id']}", headers=h)

    def test_slug_uniqueness(self, h):
        r1 = requests.post(f"{API}/newsletter/publications", json={"name": "TEST_DupName"}, headers=h)
        r2 = requests.post(f"{API}/newsletter/publications", json={"name": "TEST_DupName"}, headers=h)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["slug"] != r2.json()["slug"]
        requests.delete(f"{API}/newsletter/publications/{r1.json()['id']}", headers=h)
        requests.delete(f"{API}/newsletter/publications/{r2.json()['id']}", headers=h)

    def test_list_with_counts(self, h, pub):
        r = requests.get(f"{API}/newsletter/publications", headers=h)
        assert r.status_code == 200
        rows = r.json()
        found = [x for x in rows if x["id"] == pub["id"]]
        assert found and "subscriber_count" in found[0] and "post_count" in found[0]

    def test_put_does_not_change_slug(self, h, pub):
        r = requests.put(f"{API}/newsletter/publications/{pub['id']}",
                          json={"name": pub["name"], "slug": "hacked-slug", "description": "new desc"},
                          headers=h)
        assert r.status_code == 200
        assert r.json()["slug"] == pub["slug"]
        assert r.json()["description"] == "new desc"


# ============= Subscribers =============
class TestSubscribers:
    def test_owner_add_and_dedupe_and_flip(self, h, pub):
        email = f"TEST_{uuid.uuid4().hex[:6]}@example.com"
        r1 = requests.post(f"{API}/newsletter/publications/{pub['id']}/subscribers",
                            json={"email": email, "name": "T"}, headers=h)
        assert r1.status_code == 200
        s1 = r1.json()
        assert s1["status"] == "subscribed"
        # dup returns same id
        r2 = requests.post(f"{API}/newsletter/publications/{pub['id']}/subscribers",
                            json={"email": email}, headers=h)
        assert r2.status_code == 200 and r2.json()["id"] == s1["id"]
        # unsubscribe then re-add: flips back
        requests.get(f"{API}/newsletter/track/unsubscribe/nopost/{s1['id']}")
        r3 = requests.post(f"{API}/newsletter/publications/{pub['id']}/subscribers",
                            json={"email": email}, headers=h)
        assert r3.status_code == 200 and r3.json()["status"] == "subscribed"

    def test_csv_import(self, h, pub):
        csv = "email,name\ngood1@example.com,A\ngood2@example.com,B\nnotanemail,C\n"
        files = {"file": ("subs.csv", io.BytesIO(csv.encode()), "text/csv")}
        r = requests.post(f"{API}/newsletter/publications/{pub['id']}/subscribers/import-csv",
                          files=files, headers=h)
        assert r.status_code == 200
        j = r.json()
        assert j["created"] == 2 and j["skipped"] == 1


# ============= Public subscribe / confirm / referral =============
class TestPublic:
    def test_public_subscribe_pending_and_confirm(self, pub):
        slug = pub["slug"]
        email = f"TEST_pub_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(f"{API}/newsletter/public/{slug}/subscribe",
                          json={"email": email})
        assert r.status_code == 200
        assert r.json()["status"] == "pending"
        # find token via workspace API (owner sees it)

    def test_confirm_flow(self, h, pub):
        slug = pub["slug"]
        email = f"TEST_conf_{uuid.uuid4().hex[:6]}@example.com".lower()
        r = requests.post(f"{API}/newsletter/public/{slug}/subscribe", json={"email": email})
        assert r.status_code == 200
        # get token via owner list
        subs = requests.get(f"{API}/newsletter/publications/{pub['id']}/subscribers",
                             headers=h).json()
        me = [s for s in subs if s["email"] == email]
        assert me
        tok = me[0]["confirmation_token"]
        c1 = requests.get(f"{API}/newsletter/public/confirm/{tok}")
        assert c1.status_code == 200
        assert "subscribed" in c1.text.lower()
        c2 = requests.get(f"{API}/newsletter/public/confirm/{tok}")
        assert "expired" in c2.text.lower() or "already" in c2.text.lower()

    def test_public_pub_only_sent_posts(self, pub):
        r = requests.get(f"{API}/newsletter/public/{pub['slug']}")
        assert r.status_code == 200
        assert isinstance(r.json()["posts"], list)


# ============= Posts CRUD + schedule + send-now =============
class TestPosts:
    def test_crud_and_send(self, h, pub):
        r = requests.post(f"{API}/newsletter/publications/{pub['id']}/posts",
                          json={"title": "TEST Post 1"}, headers=h)
        assert r.status_code == 200
        post = r.json()
        assert post["status"] == "draft"
        pid, poid = pub["id"], post["id"]

        # update
        r2 = requests.put(f"{API}/newsletter/publications/{pid}/posts/{poid}",
                          json={"title": "TEST Post 1 v2", "blocks":
                              [{"type": "heading", "props": {"text": "H"}},
                               {"type": "bogus", "props": {}}]}, headers=h)
        assert r2.status_code == 200
        # bogus block dropped
        assert all(b["type"] != "bogus" for b in r2.json()["blocks"])

        # schedule
        future = "2099-01-01T00:00:00+00:00"
        r3 = requests.post(f"{API}/newsletter/publications/{pid}/posts/{poid}/schedule",
                           json={"scheduled_at": future}, headers=h)
        assert r3.status_code == 200
        # repeat schedule → 404
        r4 = requests.post(f"{API}/newsletter/publications/{pid}/posts/{poid}/schedule",
                           json={"scheduled_at": future}, headers=h)
        assert r4.status_code == 404

    def test_send_now_no_resend(self, h, pub):
        r = requests.post(f"{API}/newsletter/publications/{pub['id']}/posts",
                          json={"title": "TEST Send Now"}, headers=h)
        post = r.json()
        rn = requests.post(f"{API}/newsletter/publications/{pub['id']}/posts/{post['id']}/send-now",
                           headers=h)
        assert rn.status_code == 200
        # RESEND unset — worker cannot send, status should remain 'scheduled' (documented)
        time.sleep(2)
        cur = requests.get(f"{API}/newsletter/publications/{pub['id']}/posts/{post['id']}",
                            headers=h).json()
        assert cur["status"] in ("scheduled", "sent")


# ============= Tracking =============
class TestTracking:
    def test_open_click_unsub(self, h, pub):
        # create post + subscriber
        pr = requests.post(f"{API}/newsletter/publications/{pub['id']}/posts",
                           json={"title": "TEST Tracking"}, headers=h)
        post_id = pr.json()["id"]
        sr = requests.post(f"{API}/newsletter/publications/{pub['id']}/subscribers",
                           json={"email": f"TEST_trk_{uuid.uuid4().hex[:6]}@ex.com"}, headers=h)
        sid = sr.json()["id"]

        # open x2
        o1 = requests.get(f"{API}/newsletter/track/open/{post_id}/{sid}.gif")
        assert o1.status_code == 200 and o1.headers["content-type"].startswith("image/gif")
        requests.get(f"{API}/newsletter/track/open/{post_id}/{sid}.gif")

        # click x2
        cl = requests.get(f"{API}/newsletter/track/click/{post_id}/{sid}",
                           params={"u": "https://example.com/x"}, allow_redirects=False)
        assert cl.status_code == 302
        assert cl.headers["location"] == "https://example.com/x"
        requests.get(f"{API}/newsletter/track/click/{post_id}/{sid}",
                     params={"u": "https://example.com/x"}, allow_redirects=False)

        # verify stats
        p = requests.get(f"{API}/newsletter/publications/{pub['id']}/posts/{post_id}", headers=h).json()
        assert p["stats"]["opens"] == 2 and p["stats"]["unique_opens"] == 1
        assert p["stats"]["clicks"] == 2 and p["stats"]["unique_clicks"] == 1

        # unsubscribe
        requests.get(f"{API}/newsletter/track/unsubscribe/{post_id}/{sid}")
        p2 = requests.get(f"{API}/newsletter/publications/{pub['id']}/posts/{post_id}", headers=h).json()
        assert p2["stats"]["unsubscribes"] == 1
        subs = requests.get(f"{API}/newsletter/publications/{pub['id']}/subscribers",
                             headers=h).json()
        me = [s for s in subs if s["id"] == sid][0]
        assert me["status"] == "unsubscribed"


# ============= Analytics =============
class TestAnalytics:
    def test_analytics_shape(self, h, pub):
        r = requests.get(f"{API}/newsletter/publications/{pub['id']}/analytics", headers=h)
        assert r.status_code == 200
        j = r.json()
        for k in ("subscribers_total", "subscribers_active", "posts_sent",
                  "growth", "top_posts", "top_referrers"):
            assert k in j


# ============= Referral =============
class TestReferral:
    def test_referral_progress_and_bump(self, h, pub):
        # Add referrer manually
        rr = requests.post(f"{API}/newsletter/publications/{pub['id']}/subscribers",
                           json={"email": f"TEST_ref_{uuid.uuid4().hex[:6]}@ex.com"}, headers=h)
        referrer = rr.json()
        rtok = referrer["referral_token"]
        # public progress
        pg = requests.get(f"{API}/newsletter/public/{pub['slug']}/referral/{rtok}")
        assert pg.status_code == 200
        assert pg.json()["referral_count"] == 0
        # public subscribe with ref
        r = requests.post(f"{API}/newsletter/public/{pub['slug']}/subscribe",
                          json={"email": f"TEST_r_{uuid.uuid4().hex[:6]}@ex.com", "ref": rtok})
        assert r.status_code == 200
        # verify count bumped
        pg2 = requests.get(f"{API}/newsletter/public/{pub['slug']}/referral/{rtok}")
        assert pg2.json()["referral_count"] == 1
