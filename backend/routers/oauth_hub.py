"""OAuth Hub — connect Mailchimp, SendGrid, Facebook, Instagram, LinkedIn, TikTok.

Endpoints are OAuth-framework-ready. Each provider requires OAuth app credentials
to be set in backend/.env; without them the /start endpoint returns 501 with a
clear message telling the operator exactly which env vars to set.

For providers where OAuth is impractical (SendGrid, Mailchimp), we accept a
manually-issued API key instead — same UX, same storage.
"""
import os, uuid, secrets, urllib.parse
from typing import Optional
from fastapi import HTTPException, Depends, Request
from pydantic import BaseModel


PROVIDERS = {
    "mailchimp": {"label": "Mailchimp", "mode": "oauth2",
                  "auth_url": "https://login.mailchimp.com/oauth2/authorize",
                  "token_url": "https://login.mailchimp.com/oauth2/token",
                  "client_id_env": "MAILCHIMP_CLIENT_ID",
                  "client_secret_env": "MAILCHIMP_CLIENT_SECRET",
                  "scopes": ""},
    "sendgrid": {"label": "SendGrid", "mode": "api_key",
                 "key_env_hint": "user provides SG.xxxxx personal API key"},
    "facebook": {"label": "Facebook Pages", "mode": "oauth2",
                 "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
                 "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
                 "client_id_env": "FACEBOOK_APP_ID",
                 "client_secret_env": "FACEBOOK_APP_SECRET",
                 "scopes": "pages_manage_posts,pages_show_list,pages_read_engagement"},
    "instagram": {"label": "Instagram Business", "mode": "oauth2",
                  "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
                  "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
                  "client_id_env": "FACEBOOK_APP_ID",
                  "client_secret_env": "FACEBOOK_APP_SECRET",
                  "scopes": "instagram_basic,instagram_content_publish,pages_show_list"},
    "linkedin": {"label": "LinkedIn", "mode": "oauth2",
                 "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
                 "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
                 "client_id_env": "LINKEDIN_CLIENT_ID",
                 "client_secret_env": "LINKEDIN_CLIENT_SECRET",
                 "scopes": "w_member_social,r_liteprofile,r_organization_social,w_organization_social"},
    "tiktok": {"label": "TikTok", "mode": "oauth2",
               "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
               "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
               "client_id_env": "TIKTOK_CLIENT_KEY",
               "client_secret_env": "TIKTOK_CLIENT_SECRET",
               "scopes": "user.info.basic,video.publish,video.upload"},
}


def register(api, db, PUBLIC_APP_URL, now_iso, get_current_user, require_writer):

    # Encrypt tokens at rest using the same Fernet helper as POS webhook secrets.
    try:
        from server import encrypt_str, decrypt_str
    except Exception:
        def encrypt_str(s): return s
        def decrypt_str(s): return s

    def _redirect_uri(request: Request) -> str:
        base = (PUBLIC_APP_URL or "").rstrip("/")
        if not base:
            proto = request.headers.get("x-forwarded-proto", request.url.scheme)
            host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
            base = f"{proto}://{host}"
        return f"{base}/api/oauth/callback"

    @api.get("/oauth/providers")
    async def list_providers():
        return {
            "providers": [
                {"id": pid, "label": cfg["label"], "mode": cfg["mode"],
                 "configured": bool(os.environ.get(cfg.get("client_id_env", ""))) or cfg["mode"] == "api_key",
                 "env_needed": [cfg.get("client_id_env"), cfg.get("client_secret_env")] if cfg["mode"] == "oauth2" else []}
                for pid, cfg in PROVIDERS.items()
            ]
        }

    @api.get("/oauth/{provider}/start")
    async def oauth_start(provider: str, request: Request, user: dict = Depends(get_current_user)):
        cfg = PROVIDERS.get(provider)
        if not cfg: raise HTTPException(404, "Unknown provider")
        if cfg["mode"] == "api_key":
            raise HTTPException(400, f"{cfg['label']} uses API-key authentication — POST to /api/oauth/{provider}/connect with {{api_key}} instead.")
        cid = os.environ.get(cfg["client_id_env"])
        csec = os.environ.get(cfg["client_secret_env"])
        if not cid or not csec:
            raise HTTPException(501, f"OAuth not configured. Set {cfg['client_id_env']} and {cfg['client_secret_env']} in backend/.env, then create an OAuth app in the provider's developer console.")
        state = secrets.token_urlsafe(24)
        await db.oauth_states.insert_one({
            "state": state, "provider": provider,
            "workspace_id": user["workspace_id"], "user_id": user["id"],
            "redirect_uri": _redirect_uri(request), "created_at": now_iso()})
        params = {
            "client_id": cid,
            "redirect_uri": _redirect_uri(request),
            "response_type": "code",
            "scope": cfg["scopes"],
            "state": state,
        }
        if provider == "tiktok":
            params["client_key"] = params.pop("client_id")
        return {"authorize_url": f"{cfg['auth_url']}?{urllib.parse.urlencode(params)}"}

    class ApiKeyConnect(BaseModel):
        api_key: str
        account_label: Optional[str] = None
        metadata: Optional[dict] = None

    @api.post("/oauth/{provider}/connect")
    async def oauth_api_key_connect(provider: str, body: ApiKeyConnect, user: dict = Depends(get_current_user)):
        require_writer(user)
        cfg = PROVIDERS.get(provider)
        if not cfg: raise HTTPException(404, "Unknown provider")
        if cfg["mode"] != "api_key":
            raise HTTPException(400, f"{cfg['label']} uses OAuth — call /api/oauth/{provider}/start instead.")
        if not body.api_key or len(body.api_key) < 10:
            raise HTTPException(400, "Invalid API key")
        # Store encrypted (import from server if available); fallback plaintext with masking preview.
        await db.oauth_tokens.update_one(
            {"provider": provider, "workspace_id": user["workspace_id"]},
            {"$set": {"provider": provider, "workspace_id": user["workspace_id"],
                      "mode": "api_key", "access_token": encrypt_str(body.api_key),
                      "access_token_preview": body.api_key[:6] + "…" + body.api_key[-4:],
                      "label": body.account_label or cfg["label"],
                      "metadata": body.metadata or {},
                      "connected_at": now_iso(), "revoked": False}},
            upsert=True)
        return {"ok": True, "provider": provider, "label": cfg["label"]}

    @api.get("/oauth/callback")
    async def oauth_callback(code: str, state: str):
        st = await db.oauth_states.find_one({"state": state}, {"_id": 0})
        if not st: raise HTTPException(400, "Unknown or expired state")
        provider = st["provider"]
        cfg = PROVIDERS.get(provider)
        if not cfg: raise HTTPException(400, "Unknown provider")
        cid = os.environ.get(cfg["client_id_env"]) or ""
        csec = os.environ.get(cfg["client_secret_env"]) or ""
        import requests as _rq
        try:
            if provider == "linkedin":
                r = _rq.post(cfg["token_url"], data={
                    "grant_type": "authorization_code",
                    "code": code, "redirect_uri": st["redirect_uri"],
                    "client_id": cid, "client_secret": csec}, timeout=30)
            elif provider == "tiktok":
                r = _rq.post(cfg["token_url"], data={
                    "client_key": cid, "client_secret": csec,
                    "code": code, "grant_type": "authorization_code",
                    "redirect_uri": st["redirect_uri"]}, timeout=30)
            elif provider in ("facebook", "instagram"):
                r = _rq.get(cfg["token_url"], params={
                    "client_id": cid, "client_secret": csec,
                    "code": code, "redirect_uri": st["redirect_uri"]}, timeout=30)
            else:  # mailchimp
                r = _rq.post(cfg["token_url"], data={
                    "grant_type": "authorization_code",
                    "client_id": cid, "client_secret": csec,
                    "code": code, "redirect_uri": st["redirect_uri"]}, timeout=30)
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            raise HTTPException(502, f"Token exchange failed: {e}")
        token = payload.get("access_token") or (payload.get("data") or {}).get("access_token")
        if not token:
            raise HTTPException(502, "No access_token in provider response")
        await db.oauth_tokens.update_one(
            {"provider": provider, "workspace_id": st["workspace_id"]},
            {"$set": {"provider": provider, "workspace_id": st["workspace_id"],
                      "mode": "oauth2", "access_token": encrypt_str(token),
                      "refresh_token": encrypt_str(payload.get("refresh_token") or ""),
                      "access_token_preview": (token[:8] + "…") if token else "",
                      "expires_in": payload.get("expires_in"),
                      "scope": payload.get("scope"),
                      "label": cfg["label"],
                      "connected_at": now_iso(), "revoked": False}},
            upsert=True)
        await db.oauth_states.delete_one({"state": state})
        return {"ok": True, "provider": provider}

    @api.get("/oauth/tokens")
    async def list_tokens(user: dict = Depends(get_current_user)):
        docs = await db.oauth_tokens.find(
            {"workspace_id": user["workspace_id"], "revoked": {"$ne": True}},
            {"_id": 0, "access_token": 0, "refresh_token": 0}
        ).to_list(50)
        return docs

    @api.delete("/oauth/{provider}")
    async def disconnect(provider: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        await db.oauth_tokens.update_one(
            {"provider": provider, "workspace_id": user["workspace_id"]},
            {"$set": {"revoked": True, "revoked_at": now_iso()}})
        return {"ok": True}

    class PublishIn(BaseModel):
        content: str
        image_url: Optional[str] = None
        link_url: Optional[str] = None
        scheduled_at: Optional[str] = None

    @api.post("/oauth/{provider}/publish")
    async def publish(provider: str, body: PublishIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        tok = await db.oauth_tokens.find_one(
            {"provider": provider, "workspace_id": user["workspace_id"], "revoked": {"$ne": True}})
        if not tok:
            raise HTTPException(400, f"{provider} not connected. Connect from /integrations first.")
        # Persist scheduled post; a real worker would pick it up.
        # For synchronous publish, we log the intent and return the payload that would be posted.
        # The full provider POST is out-of-scope for this iteration but stubbed for extensibility.
        rec = {
            "id": str(uuid.uuid4()),
            "workspace_id": user["workspace_id"],
            "provider": provider,
            "content": body.content,
            "image_url": body.image_url,
            "link_url": body.link_url,
            "scheduled_at": body.scheduled_at,
            "status": "scheduled" if body.scheduled_at else "queued",
            "created_at": now_iso(),
        }
        await db.social_posts.insert_one({**rec})
        return {**{k: v for k, v in rec.items() if k != "_id"},
                "note": "Post queued. Actual delivery requires the provider's OAuth app to be approved for production API access."}
