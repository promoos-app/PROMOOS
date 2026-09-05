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
    "mailchimp": {"label": "Mailchimp", "mode": "oauth2", "category": "email",
                  "auth_url": "https://login.mailchimp.com/oauth2/authorize",
                  "token_url": "https://login.mailchimp.com/oauth2/token",
                  "client_id_env": "MAILCHIMP_CLIENT_ID",
                  "client_secret_env": "MAILCHIMP_CLIENT_SECRET",
                  "scopes": "",
                  "token_hint": "us1-xxxxxxxxxxxxxxxxxxxxxxxxxxxx-us1 · Mailchimp → Profile → Extras → API keys",
                  "token_docs": "https://mailchimp.com/help/about-api-keys/"},
    "sendgrid": {"label": "SendGrid", "mode": "api_key",
                 "key_env_hint": "user provides SG.xxxxx personal API key"},
    "facebook": {"label": "Facebook Pages", "mode": "oauth2", "category": "social",
                 "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
                 "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
                 "client_id_env": "FACEBOOK_APP_ID",
                 "client_secret_env": "FACEBOOK_APP_SECRET",
                 "scopes": "pages_manage_posts,pages_show_list,pages_read_engagement",
                 "token_hint": "Long-lived Page Access Token from Meta Graph API Explorer",
                 "token_docs": "https://developers.facebook.com/tools/explorer/"},
    "instagram": {"label": "Instagram Business", "mode": "oauth2", "category": "social",
                  "auth_url": "https://www.facebook.com/v18.0/dialog/oauth",
                  "token_url": "https://graph.facebook.com/v18.0/oauth/access_token",
                  "client_id_env": "FACEBOOK_APP_ID",
                  "client_secret_env": "FACEBOOK_APP_SECRET",
                  "scopes": "instagram_basic,instagram_content_publish,pages_show_list",
                  "token_hint": "IG Business long-lived access token (link IG to Page first)",
                  "token_docs": "https://developers.facebook.com/docs/instagram-api/getting-started"},
    "linkedin": {"label": "LinkedIn", "mode": "oauth2", "category": "social",
                 "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
                 "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
                 "client_id_env": "LINKEDIN_CLIENT_ID",
                 "client_secret_env": "LINKEDIN_CLIENT_SECRET",
                 "scopes": "w_member_social,r_liteprofile,r_organization_social,w_organization_social",
                 "token_hint": "3-legged OAuth access token from LinkedIn Developer Portal",
                 "token_docs": "https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow"},
    "tiktok": {"label": "TikTok", "mode": "oauth2", "category": "social",
               "auth_url": "https://www.tiktok.com/v2/auth/authorize/",
               "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
               "client_id_env": "TIKTOK_CLIENT_KEY",
               "client_secret_env": "TIKTOK_CLIENT_SECRET",
               "scopes": "user.info.basic,video.publish,video.upload",
               "token_hint": "TikTok Business access token from developers.tiktok.com",
               "token_docs": "https://developers.tiktok.com/doc/oauth-user-access-token-management"},

    # Email marketing / delivery (api_key mode — user pastes their own key)
    "resend":     {"label": "Resend",              "mode": "api_key", "category": "email", "key_hint": "re_xxxxxxxxxxxxxxxx"},
    "convertkit": {"label": "ConvertKit",          "mode": "api_key", "category": "email", "key_hint": "kit_xxxxxxxx"},
    "brevo":      {"label": "Brevo (Sendinblue)",  "mode": "api_key", "category": "email", "key_hint": "xkeysib-xxxxxxxxx"},
    "postmark":   {"label": "Postmark",            "mode": "api_key", "category": "email", "key_hint": "server-token uuid"},
    "mailgun":    {"label": "Mailgun",             "mode": "api_key", "category": "email", "key_hint": "key-xxxxxxxx (append domain via meta.domain later)"},
    "ses":        {"label": "AWS SES",             "mode": "api_key", "category": "email", "key_hint": "AKIA... (paste ACCESS:SECRET as one string)"},
    "klaviyo":    {"label": "Klaviyo",             "mode": "api_key", "category": "email", "key_hint": "pk_xxxxxxxx"},

    # Social (api_key fallbacks — OAuth apps optional)
    "twitter":    {"label": "X (Twitter)",         "mode": "api_key", "category": "social", "key_hint": "Bearer token"},
    "youtube":    {"label": "YouTube",             "mode": "api_key", "category": "social", "key_hint": "AIza…"},
    "pinterest":  {"label": "Pinterest",           "mode": "api_key", "category": "social", "key_hint": "pina_xxxxxxxx"},
    "threads":    {"label": "Threads",             "mode": "api_key", "category": "social", "key_hint": "Meta Graph long-lived token"},
    "snapchat":   {"label": "Snapchat Ads",        "mode": "api_key", "category": "social", "key_hint": "access token"},

    # Delivery / payments (api_key mode)
    "twilio":     {"label": "Twilio",              "mode": "api_key", "category": "delivery", "key_hint": "AC_SID:AUTH_TOKEN"},
    "paypal":     {"label": "PayPal",              "mode": "api_key", "category": "delivery", "key_hint": "CLIENT_ID:CLIENT_SECRET"},
    "razorpay":   {"label": "Razorpay",            "mode": "api_key", "category": "delivery", "key_hint": "rzp_KEY_ID:KEY_SECRET"},
    "paystack":   {"label": "Paystack",            "mode": "api_key", "category": "delivery", "key_hint": "sk_live_xxxxxxxx"},
    "telegram":   {"label": "Telegram Bot",        "mode": "api_key", "category": "delivery", "key_hint": "bot token from @BotFather"},
    "stripe":     {"label": "Stripe",              "mode": "api_key", "category": "delivery",
                    "key_hint": "sk_live_xxxxxxxx or sk_test_xxxxxxxx",
                    "token_docs": "https://dashboard.stripe.com/apikeys"},
}


# ---- Health-check helpers: light API probes to confirm a pasted token works ----
def _health_check(provider: str, token: str) -> dict:
    """Return {ok: bool, account: str, extra?: dict}. Never raises — returns ok:false on failure."""
    import requests as _rq
    try:
        if provider == "sendgrid":
            r = _rq.get("https://api.sendgrid.com/v3/user/profile",
                         headers={"Authorization": f"Bearer {token}"}, timeout=8)
            if r.ok:
                d = r.json()
                return {"ok": True, "account": f"{d.get('first_name','')} {d.get('last_name','')}".strip() or d.get("email") or "SendGrid account"}
        elif provider == "mailchimp":
            # Mailchimp keys end with -dcX (e.g. -us1). Use it to pick the datacenter.
            dc = token.rsplit("-", 1)[-1] if "-" in token else "us1"
            r = _rq.get(f"https://{dc}.api.mailchimp.com/3.0/",
                         auth=("anystring", token), timeout=8)
            if r.ok:
                d = r.json()
                return {"ok": True, "account": d.get("account_name") or "Mailchimp account"}
        elif provider in ("facebook", "instagram"):
            r = _rq.get("https://graph.facebook.com/v18.0/me",
                         params={"access_token": token, "fields": "name,id"}, timeout=8)
            if r.ok:
                d = r.json()
                return {"ok": True, "account": d.get("name") or f"ID {d.get('id')}"}
        elif provider == "linkedin":
            r = _rq.get("https://api.linkedin.com/v2/userinfo",
                         headers={"Authorization": f"Bearer {token}"}, timeout=8)
            if r.ok:
                d = r.json()
                return {"ok": True, "account": d.get("name") or d.get("email") or "LinkedIn user"}
        elif provider == "resend":
            r = _rq.get("https://api.resend.com/domains",
                         headers={"Authorization": f"Bearer {token}"}, timeout=8)
            if r.ok:
                data = r.json().get("data", [])
                return {"ok": True, "account": f"{len(data)} domain(s)"}
        elif provider == "stripe":
            r = _rq.get("https://api.stripe.com/v1/account",
                         auth=(token, ""), timeout=8)
            if r.ok:
                d = r.json()
                return {"ok": True, "account": d.get("business_profile", {}).get("name") or d.get("email") or d.get("id") or "Stripe account"}
        elif provider == "twilio":
            # Format: AC_SID:AUTH_TOKEN
            if ":" in token:
                sid, auth = token.split(":", 1)
                r = _rq.get(f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                             auth=(sid, auth), timeout=8)
                if r.ok:
                    d = r.json()
                    return {"ok": True, "account": d.get("friendly_name") or sid}
        elif provider == "telegram":
            r = _rq.get(f"https://api.telegram.org/bot{token}/getMe", timeout=8)
            if r.ok and r.json().get("ok"):
                b = r.json().get("result", {})
                return {"ok": True, "account": f"@{b.get('username')}" if b.get('username') else b.get("first_name", "Bot")}
        elif provider == "paystack":
            r = _rq.get("https://api.paystack.co/bank",
                         headers={"Authorization": f"Bearer {token}"}, timeout=8)
            if r.ok:
                return {"ok": True, "account": "Paystack account"}
        else:
            # No probe defined — accept the token but flag as unverified.
            return {"ok": True, "account": "Stored (not probed)"}
    except Exception as e:
        return {"ok": False, "account": "", "error": str(e)[:120]}
    return {"ok": False, "account": "", "error": "Provider rejected the token"}


def register(api, db, PUBLIC_APP_URL, now_iso, get_current_user, require_writer):

    # Encrypt tokens at rest using the same Fernet helper as POS webhook secrets.
    try:
        from server import encrypt_str, decrypt_str
    except Exception:
        import logging as _log
        _log.getLogger(__name__).warning(
            "OAuth token encryption DISABLED — encrypt_str/decrypt_str could not be imported from server. Tokens stored plaintext."
        )
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
                 "category": cfg.get("category", "email" if pid in ("mailchimp", "sendgrid") else "social"),
                 "key_hint": cfg.get("key_hint") or cfg.get("token_hint", ""),
                 "token_docs": cfg.get("token_docs", ""),
                 # `configured` = user CAN connect (either OAuth env is set OR paste-a-token is always allowed).
                 # Since we accept pasted access tokens for OAuth providers too, this is always True.
                 "configured": True,
                 # `oauth_configured` = the platform owner has set the OAuth app credentials.
                 "oauth_configured": (bool(os.environ.get(cfg.get("client_id_env", ""))) and
                                        bool(os.environ.get(cfg.get("client_secret_env", "")))
                                        if cfg["mode"] == "oauth2" else False),
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
        if not body.api_key or len(body.api_key) < 10:
            raise HTTPException(400, "Invalid API key or access token")
        # Store encrypted (import from server if available); fallback plaintext with masking preview.
        # Both API-key-native providers AND OAuth providers accept a pasted long-lived access token here
        # so merchants don't have to wait on platform-owner OAuth app credentials in backend/.env.
        stored_mode = "api_key" if cfg["mode"] == "api_key" else "access_token"
        # Publish-time health check — light probe to confirm the token actually works.
        health = _health_check(provider, body.api_key)
        metadata = {**(body.metadata or {})}
        if health.get("account"): metadata["account_name"] = health["account"]
        if health.get("error"):   metadata["last_health_error"] = health["error"]
        await db.oauth_tokens.update_one(
            {"provider": provider, "workspace_id": user["workspace_id"]},
            {"$set": {"provider": provider, "workspace_id": user["workspace_id"],
                      "mode": stored_mode, "access_token": encrypt_str(body.api_key),
                      "access_token_preview": body.api_key[:6] + "…" + body.api_key[-4:],
                      "label": body.account_label or health.get("account") or cfg["label"],
                      "metadata": metadata,
                      "health_ok": bool(health.get("ok")),
                      "connected_at": now_iso(), "revoked": False}},
            upsert=True)
        return {"ok": True, "provider": provider, "label": cfg["label"],
                "health": health}

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
        from datetime import datetime, timezone as _tz
        now = datetime.now(_tz.utc)
        for d in docs:
            connected = d.get("connected_at")
            if connected:
                try:
                    age = (now - datetime.fromisoformat(connected.replace("Z", "+00:00"))).days
                    d["age_days"] = age
                    # Rotation reminder — Meta long-lived tokens expire around day 60. Warn at 55.
                    d["expires_soon"] = age >= 55
                except Exception:
                    d["age_days"] = 0; d["expires_soon"] = False
        return docs

    @api.delete("/oauth/{provider}")
    async def disconnect(provider: str, user: dict = Depends(get_current_user)):
        require_writer(user)
        await db.oauth_tokens.update_one(
            {"provider": provider, "workspace_id": user["workspace_id"]},
            {"$set": {"revoked": True, "revoked_at": now_iso()}})
        return {"ok": True}


    @api.post("/oauth/{provider}/retest")
    async def retest_connection(provider: str, user: dict = Depends(get_current_user)):
        """Re-run the live health probe against the currently-stored token."""
        require_writer(user)
        tok = await db.oauth_tokens.find_one(
            {"provider": provider, "workspace_id": user["workspace_id"], "revoked": {"$ne": True}})
        if not tok:
            raise HTTPException(404, f"{provider} not connected")
        token = decrypt_str(tok.get("access_token", ""))
        health = _health_check(provider, token)
        metadata = tok.get("metadata") or {}
        if health.get("account"):
            metadata["account_name"] = health["account"]
        if health.get("error"):
            metadata["last_health_error"] = health["error"]
        else:
            metadata.pop("last_health_error", None)
        await db.oauth_tokens.update_one(
            {"_id": tok["_id"]},
            {"$set": {"health_ok": bool(health.get("ok")),
                      "metadata": metadata,
                      "last_retested_at": now_iso()}})
        return {"health": health, "last_retested_at": now_iso()}


    class PublishIn(BaseModel):
        content: str
        image_url: Optional[str] = None
        link_url: Optional[str] = None
        scheduled_at: Optional[str] = None

    @api.post("/oauth/{provider}/publish")
    async def publish(provider: str, body: PublishIn, user: dict = Depends(get_current_user)):
        require_writer(user)
        # TikTok publishing requires video upload + production API approval — surface this before the connection check.
        if provider == "tiktok":
            raise HTTPException(501, "TikTok publishing requires video content and production API approval. Coming in Phase 4.")
        tok = await db.oauth_tokens.find_one(
            {"provider": provider, "workspace_id": user["workspace_id"], "revoked": {"$ne": True}})
        if not tok:
            raise HTTPException(400, f"{provider} not connected. Connect from /integrations first.")
        access_token = decrypt_str(tok.get("access_token", ""))
        metadata = tok.get("metadata") or {}
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
        # If scheduled, just queue. Real dispatch happens when scheduled_at <= now.
        if body.scheduled_at:
            await db.social_posts.insert_one({**rec})
            return {**{k: v for k, v in rec.items() if k != "_id"}, "note": "Scheduled — worker will publish at scheduled_at."}

        # Live publish per provider
        import requests as _rq
        try:
            if provider == "facebook":
                page_id = metadata.get("page_id") or os.environ.get("FACEBOOK_PAGE_ID")
                if not page_id:
                    raise HTTPException(400, "Facebook page_id missing. Save the target Page ID in metadata or FACEBOOK_PAGE_ID env.")
                if body.image_url:
                    r = _rq.post(f"https://graph.facebook.com/v18.0/{page_id}/photos",
                                 data={"url": body.image_url, "caption": body.content,
                                       "access_token": access_token}, timeout=30)
                else:
                    r = _rq.post(f"https://graph.facebook.com/v18.0/{page_id}/feed",
                                 data={"message": body.content, "link": body.link_url or "",
                                       "access_token": access_token}, timeout=30)
                r.raise_for_status()
                rec["provider_post_id"] = r.json().get("id") or r.json().get("post_id")
                rec["status"] = "published"
            elif provider == "instagram":
                ig_user_id = metadata.get("ig_user_id") or os.environ.get("IG_BUSINESS_ACCOUNT_ID")
                if not ig_user_id: raise HTTPException(400, "IG_BUSINESS_ACCOUNT_ID missing.")
                if not body.image_url: raise HTTPException(400, "Instagram requires image_url.")
                cr = _rq.post(f"https://graph.facebook.com/v18.0/{ig_user_id}/media",
                              data={"image_url": body.image_url, "caption": body.content,
                                    "access_token": access_token}, timeout=30)
                cr.raise_for_status()
                creation_id = cr.json()["id"]
                pub = _rq.post(f"https://graph.facebook.com/v18.0/{ig_user_id}/media_publish",
                               data={"creation_id": creation_id, "access_token": access_token}, timeout=30)
                pub.raise_for_status()
                rec["provider_post_id"] = pub.json().get("id")
                rec["status"] = "published"
            elif provider == "linkedin":
                author_urn = metadata.get("author_urn") or os.environ.get("LINKEDIN_ORG_URN")
                if not author_urn:
                    # Look up user's own profile URN
                    me = _rq.get("https://api.linkedin.com/v2/userinfo",
                                 headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
                    me.raise_for_status()
                    author_urn = f"urn:li:person:{me.json()['sub']}"
                post_body = {
                    "author": author_urn,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": body.content},
                            "shareMediaCategory": "NONE" if not body.link_url else "ARTICLE",
                            **({"media": [{"status": "READY", "originalUrl": body.link_url}]} if body.link_url else {}),
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                }
                r = _rq.post("https://api.linkedin.com/v2/ugcPosts",
                             headers={"Authorization": f"Bearer {access_token}",
                                      "Content-Type": "application/json",
                                      "X-Restli-Protocol-Version": "2.0.0"},
                             json=post_body, timeout=30)
                r.raise_for_status()
                rec["provider_post_id"] = r.headers.get("x-restli-id") or r.json().get("id")
                rec["status"] = "published"
            elif provider == "mailchimp":
                dc = metadata.get("dc") or (access_token.split("-")[-1] if "-" in access_token else None)
                if not dc: raise HTTPException(400, "Mailchimp data-center (dc) missing in metadata (e.g. 'us14').")
                audience_id = metadata.get("audience_id") or body.link_url  # allow link_url slot to carry it
                if not audience_id: raise HTTPException(400, "audience_id required (save in oauth metadata or pass in link_url).")
                base = f"https://{dc}.api.mailchimp.com/3.0"
                # Create campaign then set content then send
                cr = _rq.post(f"{base}/campaigns",
                              headers={"Authorization": f"Bearer {access_token}"},
                              json={"type": "regular",
                                    "recipients": {"list_id": audience_id},
                                    "settings": {"subject_line": body.content[:150],
                                                 "title": body.content[:60],
                                                 "from_name": "PromoOS",
                                                 "reply_to": "noreply@promoos.app"}},
                              timeout=30)
                cr.raise_for_status()
                campaign_id = cr.json()["id"]
                html = f"<html><body><p>{body.content}</p>" + (f'<p><img src="{body.image_url}" style="max-width:600px" /></p>' if body.image_url else "") + "</body></html>"
                _rq.put(f"{base}/campaigns/{campaign_id}/content",
                        headers={"Authorization": f"Bearer {access_token}"},
                        json={"html": html}, timeout=30).raise_for_status()
                _rq.post(f"{base}/campaigns/{campaign_id}/actions/send",
                         headers={"Authorization": f"Bearer {access_token}"}, timeout=30).raise_for_status()
                rec["provider_post_id"] = campaign_id
                rec["status"] = "published"
            elif provider == "tiktok":
                # TikTok Content Posting API requires video files + business approval — stub with clear error.
                raise HTTPException(501, "TikTok publishing requires video content and production API approval. Coming in Phase 4.")
            else:
                raise HTTPException(400, f"Publishing not implemented for {provider}")
        except HTTPException:
            raise
        except _rq.HTTPError as e:
            rec["status"] = "failed"
            rec["error"] = e.response.text[:500] if e.response is not None else str(e)
        except Exception as e:
            rec["status"] = "failed"; rec["error"] = str(e)
        await db.social_posts.insert_one({**rec})
        if rec["status"] == "failed":
            raise HTTPException(502, f"{provider} publish failed: {rec.get('error', 'unknown')}")
        return {**{k: v for k, v in rec.items() if k != "_id"}}



    async def rotation_nudge_worker():
        """Daily loop: when a stored token turns 55 days old, email the workspace owner once.

        Uses Resend if configured; otherwise silently marks the token as notified so we
        don't spam the check every day.
        """
        import asyncio, logging
        from datetime import datetime, timezone as _tz
        _logger = logging.getLogger(__name__)
        while True:
            try:
                now = datetime.now(_tz.utc)
                async for tok in db.oauth_tokens.find(
                        {"revoked": {"$ne": True},
                         "rotation_notified_at": {"$exists": False}}):
                    connected = tok.get("connected_at")
                    if not connected:
                        continue
                    try:
                        age = (now - datetime.fromisoformat(connected.replace("Z", "+00:00"))).days
                    except Exception:
                        continue
                    if age < 55:
                        continue
                    # Find workspace owner email
                    ws_id = tok["workspace_id"]
                    owner = await db.users.find_one(
                        {"workspace_id": ws_id, "role": {"$in": ["owner", "admin"]}},
                        {"_id": 0, "email": 1, "name": 1})
                    if not owner or not owner.get("email"):
                        # No addressable owner; mark notified so we don't retry every day
                        await db.oauth_tokens.update_one({"_id": tok["_id"]},
                            {"$set": {"rotation_notified_at": now.isoformat(),
                                      "rotation_note": "no owner email on file"}})
                        continue
                    try:
                        from server import RESEND_API_KEY, SENDER_EMAIL, resend
                        if RESEND_API_KEY:
                            subject = f"Rotate your {tok.get('label', tok['provider'])} token soon"
                            html = f"""
                            <div style='font-family:Helvetica,Arial,sans-serif;padding:24px;background:#0A0A0A;color:#fff'>
                              <h2 style='color:#CCFF00;margin:0 0 12px'>Time to rotate your {tok.get('label')} token</h2>
                              <p style='color:#A1A1AA'>The access token you connected {age} days ago is nearing expiry.
                              Some providers (Meta, LinkedIn) auto-invalidate long-lived tokens at day 60 — rotate now to keep your campaigns firing.</p>
                              <p style='margin:20px 0'><a href='#/integrations' style='background:#CCFF00;color:#0A0A0A;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:700'>Open Integrations</a></p>
                              <p style='color:#71717A;font-size:12px'>You're getting this because you're a workspace admin on PromoOS.</p>
                            </div>"""
                            await asyncio.to_thread(resend.Emails.send, {
                                "from": SENDER_EMAIL, "to": [owner["email"]],
                                "subject": subject, "html": html})
                            _logger.info("rotation nudge sent to %s for %s", owner["email"], tok["provider"])
                    except Exception as e:
                        _logger.warning("rotation nudge failed: %s", e)
                    await db.oauth_tokens.update_one({"_id": tok["_id"]},
                        {"$set": {"rotation_notified_at": now.isoformat()}})
            except Exception as e:
                _logger.exception("rotation_nudge_worker crash: %s", e)
            # Once a day is plenty
            await asyncio.sleep(24 * 60 * 60)

    return {"rotation_nudge_worker": rotation_nudge_worker}
