import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Plug, Key, Copy, Trash2, ShieldOff, Webhook, Code2, ShieldCheck, RefreshCw, Link as LinkIcon } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

function OAuthConnector({ provider, label, icon, hint, tokens, providers, onChange }) {
  const cfg = providers.find((p) => p.id === provider);
  const token = tokens.find((t) => t.provider === provider);
  const [apiKey, setApiKey] = useState("");
  const [open, setOpen] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [postContent, setPostContent] = useState("");
  const [postImage, setPostImage] = useState("");

  const connectOAuth = async () => {
    setBusy(true);
    try {
      const { data } = await api.get(`/oauth/${provider}/start`);
      window.location.href = data.authorize_url;
    } catch (e) { toast.error(apiError(e)); setBusy(false); }
  };
  const connectKey = async () => {
    if (!apiKey.trim()) { toast.error("API key required"); return; }
    setBusy(true);
    try {
      const { data } = await api.post(`/oauth/${provider}/connect`, { api_key: apiKey.trim() });
      const acct = data?.health?.account;
      const okHealth = data?.health?.ok;
      if (okHealth === false) {
        toast.warning(`${label} connected — but the token failed a live check.${data?.health?.error ? ` ${data.health.error}` : ""}`);
      } else if (acct) {
        toast.success(`${label} connected — ${acct}`);
      } else {
        toast.success(`${label} connected`);
      }
      setOpen(false); setApiKey(""); onChange?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const disconnect = async () => {
    if (!window.confirm(`Disconnect ${label}?`)) return;
    await api.delete(`/oauth/${provider}`); toast.success("Disconnected"); onChange?.();
  };
  const publish = async () => {
    if (!postContent.trim()) { toast.error("Message required"); return; }
    setBusy(true);
    try {
      const { data } = await api.post(`/oauth/${provider}/publish`, {
        content: postContent, image_url: postImage || null,
      });
      toast.success(`Published to ${label}${data.provider_post_id ? ` · ${data.provider_post_id.slice(0, 12)}…` : ""}`);
      setPublishOpen(false); setPostContent(""); setPostImage("");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <div className="surface rounded-lg p-5" data-testid={`connector-${provider}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{icon}</span>
        <div className="font-display font-bold">{label}</div>
        <span className={`ml-auto text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded ${token ? "bg-emerald-500/15 text-emerald-400" : "bg-[#27272A] text-[#71717A]"}`}>
          {token ? "Connected" : "Not connected"}
        </span>
      </div>
      <p className="text-xs text-[#A1A1AA] leading-relaxed mb-3">{hint}</p>
      {token ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex-1 min-w-0">
              {token.metadata?.account_name && (
                <div className="text-xs text-white font-bold truncate" data-testid={`account-${provider}`}>
                  {token.metadata.account_name}
                </div>
              )}
              <div className="text-[10px] font-mono text-[#71717A]">{token.access_token_preview}</div>
              {token.expires_soon && (
                <div className="mt-1 inline-flex items-center gap-1 text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/40"
                  title={`Token was connected ${token.age_days} days ago — rotate before it expires.`}
                  data-testid={`rotate-badge-${provider}`}>
                  <RefreshCw className="w-3 h-3" /> Rotate soon · {token.age_days}d old
                </div>
              )}
              {token.metadata?.last_health_error && (
                <div className="mt-1 text-[10px] text-red-400 truncate" data-testid={`health-error-${provider}`}>
                  ⚠ {token.metadata.last_health_error}
                </div>
              )}
            </div>
            <div className="flex gap-1 shrink-0">
              {(cfg?.category || "social") === "social" && (
              <Dialog open={publishOpen} onOpenChange={setPublishOpen}>
                <DialogTrigger asChild>
                  <Button data-testid={`publish-${provider}`} className="btn-ghost rounded-md text-xs gap-1">
                    <LinkIcon className="w-3 h-3" /> Publish
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-[#141414] border-[#27272A] text-white">
                  <DialogHeader><DialogTitle>Publish to {label}</DialogTitle></DialogHeader>
                  <div className="space-y-3">
                    <div>
                      <Label className="text-xs text-[#A1A1AA]">Message</Label>
                      <textarea data-testid={`publish-content-${provider}`} value={postContent} onChange={(e) => setPostContent(e.target.value)} rows={4}
                        className="mt-1 w-full bg-[#0A0A0A] border border-[#27272A] text-white rounded-md p-2 text-sm"
                        placeholder="Big news — 20% off this week with code WINTER20…" />
                    </div>
                    <div>
                      <Label className="text-xs text-[#A1A1AA]">Image URL (optional)</Label>
                      <Input data-testid={`publish-image-${provider}`} value={postImage} onChange={(e) => setPostImage(e.target.value)}
                        className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" placeholder="https://…jpg" />
                      <div className="text-[10px] text-[#71717A] mt-1">Instagram requires an image.</div>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button data-testid={`publish-submit-${provider}`} onClick={publish} disabled={busy} className="btn-primary rounded-md gap-1">
                      {busy && <Loader2 className="w-3 h-3 spin" />} Publish now
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
              )}
              <Button data-testid={`disconnect-${provider}`} onClick={disconnect} className="btn-ghost rounded-md text-xs gap-1">
                <Trash2 className="w-3 h-3" /> Disconnect
              </Button>
            </div>
          </div>
        </div>
      ) : cfg?.mode === "api_key" ? (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid={`connect-${provider}`} className="btn-primary rounded-md text-xs w-full gap-1">
              <Key className="w-3 h-3" /> Connect with API key
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#141414] border-[#27272A] text-white">
            <DialogHeader><DialogTitle>Connect {label}</DialogTitle></DialogHeader>
            <div>
              <Label className="text-xs text-[#A1A1AA]">API key</Label>
              <Input data-testid={`api-key-input-${provider}`} value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white font-mono" placeholder={cfg?.key_hint || "SG.xxxx or key_xxxx"} />
              <div className="text-[10px] text-[#71717A] mt-1">
                {cfg?.key_hint ? `Format: ${cfg.key_hint}. ` : ""}
                Stored encrypted per-workspace. Rotate anytime from your {label} dashboard.
              </div>
            </div>
            <DialogFooter>
              <Button data-testid={`api-key-submit-${provider}`} onClick={connectKey} disabled={busy} className="btn-primary rounded-md">
                {busy && <Loader2 className="w-3 h-3 spin mr-1" />} Connect
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      ) : (
        // OAuth provider: offer OAuth flow if platform owner configured app creds,
        // and always offer the paste-a-token fallback so merchants aren't blocked.
        <div className="space-y-2">
          {cfg?.oauth_configured && (
            <Button data-testid={`connect-oauth-${provider}`} onClick={connectOAuth} disabled={busy} className="btn-primary rounded-md text-xs w-full gap-1">
              {busy ? <Loader2 className="w-3 h-3 spin" /> : <LinkIcon className="w-3 h-3" />} Connect with OAuth
            </Button>
          )}
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid={`connect-${provider}`}
                className={`rounded-md text-xs w-full gap-1 ${cfg?.oauth_configured ? "btn-ghost border border-[#27272A]" : "btn-primary"}`}>
                <Key className="w-3 h-3" /> {cfg?.oauth_configured ? "Or paste access token" : "Connect with access token"}
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#141414] border-[#27272A] text-white">
              <DialogHeader><DialogTitle>Connect {label} with access token</DialogTitle></DialogHeader>
              <div>
                <Label className="text-xs text-[#A1A1AA]">Access token</Label>
                <Input data-testid={`api-key-input-${provider}`} value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                  className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white font-mono"
                  placeholder={cfg?.key_hint || "Paste long-lived access token"} />
                <div className="text-[10px] text-[#71717A] mt-1">
                  {cfg?.key_hint ? `${cfg.key_hint}. ` : ""}
                  Stored encrypted per-workspace.{" "}
                  {cfg?.token_docs && (
                    <a href={cfg.token_docs} target="_blank" rel="noopener noreferrer" className="text-[#CCFF00] underline"
                      data-testid={`api-key-docs-${provider}`}>How to get one →</a>
                  )}
                </div>
              </div>
              <DialogFooter>
                <Button data-testid={`api-key-submit-${provider}`} onClick={connectKey} disabled={busy} className="btn-primary rounded-md">
                  {busy && <Loader2 className="w-3 h-3 spin mr-1" />} Connect
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      )}
    </div>
  );
}

function ConnectorCard({ name, icon, connected, hint, envHint }) {
  return (
    <div className="surface rounded-lg p-5" data-testid={`connector-${name.toLowerCase().replace(/[^a-z0-9]/g, "-")}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{icon}</span>
        <div className="font-display font-bold">{name}</div>
        <span className={`ml-auto text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded ${connected ? "bg-emerald-500/15 text-emerald-400" : "bg-[#27272A] text-[#71717A]"}`}>
          {connected ? "Connected" : "Not configured"}
        </span>
      </div>
      <p className="text-xs text-[#A1A1AA] leading-relaxed mb-2">{hint}</p>
      {envHint && <div className="text-[10px] font-mono text-[#71717A] bg-[#0A0A0A] border border-[#27272A] rounded px-2 py-1">{envHint}</div>}
    </div>
  );
}

function PosSecrets() {
  const [state, setState] = useState(null);
  const [rotating, setRotating] = useState(null);
  const [fresh, setFresh] = useState({});
  const load = () => api.get("/pos/secrets").then((r) => setState(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  const rotate = async (provider) => {
    setRotating(provider);
    try {
      const { data } = await api.post("/pos/rotate-secret", { provider });
      setFresh((s) => ({ ...s, [provider]: data.secret }));
      toast.success("Secret rotated — copy it now, it won't be shown again");
      load();
    } catch (e) { toast.error(apiError(e)); } finally { setRotating(null); }
  };
  if (!state) return null;
  return (
    <div className="surface rounded-lg p-5 mb-3" data-testid="pos-secrets">
      <div className="flex items-center gap-2 mb-1">
        <ShieldCheck className="w-4 h-4 text-[#CCFF00]" />
        <div className="font-display font-bold">Webhook HMAC secrets</div>
      </div>
      <p className="text-xs text-[#A1A1AA] mb-3">Rotate per-provider secrets. When set, all incoming webhooks MUST include a valid X-Shopify-Hmac-Sha256 / X-WC-Webhook-Signature header.</p>
        {["shopify", "woocommerce"].map((p) => (
        <div key={p} className="flex items-center justify-between p-3 rounded-md bg-[#0A0A0A] border border-[#27272A] mb-2" data-testid={`secret-row-${p}`}>
          <div>
            <div className="text-sm font-medium">{p === "woocommerce" ? "WooCommerce" : "Shopify"}</div>
            <div className="text-xs text-[#71717A] font-mono mt-0.5">
              {state[p]?.configured ? `${state[p].preview} · rotated ${(state[p].rotated_at || '').slice(0, 10)}` : "Not configured — unsigned webhooks allowed"}
            </div>
            {fresh[p] && (
              <div className="mt-2 text-[11px] font-mono bg-[#CCFF00]/5 border border-[#CCFF00]/30 rounded p-2 break-all" data-testid={`fresh-secret-${p}`}>
                {fresh[p]}
                <button className="ml-2 text-[#CCFF00] hover:underline" onClick={() => { navigator.clipboard.writeText(fresh[p]).catch(() => {}); toast.success("Copied"); }}>copy</button>
              </div>
            )}
          </div>
          <Button data-testid={`rotate-${p}`} onClick={() => rotate(p)} disabled={rotating === p} className="btn-ghost rounded-md gap-1 text-xs">
            {rotating === p ? <Loader2 className="w-3.5 h-3.5 spin" /> : <RefreshCw className="w-3.5 h-3.5" />} {state[p]?.configured ? "Rotate" : "Generate"}
          </Button>
        </div>
      ))}
    </div>
  );
}

export default function Integrations() {
  const [keys, setKeys] = useState([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [freshKey, setFreshKey] = useState(null);
  const [pos, setPos] = useState(null);
  const [oauthTokens, setOauthTokens] = useState([]);
  const [oauthProviders, setOauthProviders] = useState([]);

  const load = () => api.get("/api-keys").then((r) => setKeys(r.data)).catch(() => {});
  const loadOauth = () => {
    api.get("/oauth/tokens").then((r) => setOauthTokens(r.data)).catch(() => {});
    api.get("/oauth/providers").then((r) => setOauthProviders(r.data.providers)).catch(() => {});
  };
  useEffect(() => {
    load();
    loadOauth();
    api.get("/pos/snippets").then((r) => setPos(r.data)).catch(() => {});
  }, []);

  const create = async () => {
    if (!name.trim()) { toast.error("Give the key a name"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/api-keys", { name: name.trim(), scopes: ["read", "write"] });
      setFreshKey(data.key);
      setName(""); load();
      toast.success("Key created — copy it now, it will not be shown again");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const revoke = async (id) => {
    if (!window.confirm("Revoke this key? Applications using it will stop working.")) return;
    await api.post(`/api-keys/${id}/revoke`, {});
    toast.success("Key revoked"); load();
  };

  return (
    <div className="fade-up max-w-[1200px]" data-testid="integrations-page">
      <div className="mb-6">
        <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
          <Plug className="w-7 h-7 text-[#CCFF00]" /> Integrations
        </h1>
        <p className="text-sm text-[#A1A1AA] mt-1">Connect PromoOS to your store, email, SMS, and any external system.</p>
      </div>

      <h2 className="font-display font-bold text-lg mb-3">Email marketing platforms</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8" data-testid="email-platforms-grid">
        <OAuthConnector provider="mailchimp" label="Mailchimp" icon="🐵" hint="Sync audiences, send campaigns, auto-publish coupons."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="sendgrid" label="SendGrid" icon="📧" hint="High-volume transactional email. Uses your SG.xxx API key."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="resend" label="Resend" icon="✉️" hint="Transactional + branded coupon emails. Paste your re_ key."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="convertkit" label="ConvertKit" icon="✍️" hint="Creator-focused broadcasts and sequences."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="brevo" label="Brevo (Sendinblue)" icon="💌" hint="Combined email + SMS marketing platform."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="postmark" label="Postmark" icon="📬" hint="Best-in-class deliverability for receipts."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="mailgun" label="Mailgun" icon="📨" hint="Developer-friendly SMTP + API email."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="ses" label="AWS SES" icon="☁️" hint="Amazon Simple Email Service — cheap at scale. Paste ACCESS:SECRET."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="klaviyo" label="Klaviyo" icon="🎯" hint="E-commerce-first email + SMS flows."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
      </div>

      <h2 className="font-display font-bold text-lg mb-3">Social media & AI auto-publishing</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8" data-testid="social-platforms-grid">
        <OAuthConnector provider="facebook" label="Facebook Pages" icon="📘" hint="Auto-post generated coupon graphics and captions to your Pages."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="instagram" label="Instagram Business" icon="📸" hint="Feed posts, stories, reels — scheduled by AI."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="linkedin" label="LinkedIn" icon="in" hint="Company page posts for B2B campaigns."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="tiktok" label="TikTok" icon="🎵" hint="Video promos and hashtag challenges."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="twitter" label="X (Twitter)" icon="𝕏" hint="Tweet promos with generated visuals. Paste your Bearer token."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="youtube" label="YouTube" icon="▶️" hint="Community posts + Shorts scheduling."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="pinterest" label="Pinterest" icon="📌" hint="Pin coupon graphics to boards."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="threads" label="Threads" icon="@" hint="Meta's text-first social feed."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="snapchat" label="Snapchat Ads" icon="👻" hint="Snap AR filter promos + geofilters."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
      </div>

      <h2 className="font-display font-bold text-lg mb-3">Delivery channels</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8" data-testid="delivery-platforms-grid">
        <OAuthConnector provider="twilio" label="Twilio" icon="💬" hint="Send SMS and WhatsApp coupons. Paste SID:AUTH_TOKEN."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="stripe" label="Stripe" icon="💳" hint="Subscription billing + 100+ global payment methods. Paste your Stripe secret key."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="paypal" label="PayPal" icon="🅿️" hint="Alternative payment provider for global reach."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="razorpay" label="Razorpay" icon="🇮🇳" hint="India-first payments — UPI, NetBanking, cards."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="paystack" label="Paystack" icon="🌍" hint="Africa-first payments — cards, bank transfer, mobile money."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
        <OAuthConnector provider="telegram" label="Telegram Bot" icon="✈️" hint="Push coupons to Telegram channels. Paste bot token from @BotFather."
                        tokens={oauthTokens} providers={oauthProviders} onChange={loadOauth} />
      </div>

      <h2 className="font-display font-bold text-lg mb-3">Commerce connectors</h2>
      <PosSecrets />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-8">
        {pos && ["shopify", "woocommerce"].map((k) => {
          const p = pos[k];
          return (
            <div key={k} className="surface rounded-lg p-5" data-testid={`pos-${k}`}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">{k === "shopify" ? "🛍" : "🧡"}</span>
                <div className="font-display font-bold capitalize">{k}</div>
                <span className="ml-auto text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400">Ready</span>
              </div>
              <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-1">Webhook URL</div>
              <div className="flex gap-1 mb-3">
                <code data-testid={`pos-${k}-url`} className="flex-1 text-[11px] font-mono break-all bg-[#0A0A0A] border border-[#27272A] rounded px-2 py-1.5 text-[#E4E4E7]">{p.webhook_url}</code>
                <button onClick={() => { navigator.clipboard.writeText(p.webhook_url).catch(() => {}); toast.success("Copied"); }} className="p-1.5 rounded hover:bg-white/5 shrink-0"><Copy className="w-3.5 h-3.5" /></button>
              </div>
              <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-1">Topic</div>
              <div className="text-xs font-mono mb-3">{p.topic}</div>
              <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-1">Steps</div>
              <ol className="text-xs text-[#A1A1AA] space-y-1.5 list-decimal pl-4">
                {p.instructions.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </div>
          );
        })}
        {!pos && ["shopify", "woocommerce"].map((k) => (
          <div key={k} className="surface rounded-lg p-5 opacity-50">Loading…</div>
        ))}
      </div>

      {pos && (
        <div className="surface rounded-lg p-5 mb-8" data-testid="pos-curl">
          <div className="flex items-center gap-2 mb-2">
            <Webhook className="w-4 h-4 text-[#CCFF00]" />
            <div className="font-display font-bold">Any other system</div>
          </div>
          <p className="text-xs text-[#A1A1AA] mb-2">Send any order to the public redeem endpoint from a webhook, a Zap, or a custom app:</p>
          <pre className="text-[11px] font-mono text-[#E4E4E7] bg-[#0A0A0A] border border-[#27272A] rounded p-3 overflow-x-auto whitespace-pre-wrap break-all">{pos.generic_curl}</pre>
        </div>
      )}

      <h2 className="font-display font-bold text-lg mb-3 flex items-center gap-2"><Code2 className="w-4 h-4 text-[#CCFF00]" /> Public REST API</h2>
      <div className="surface rounded-lg p-5 mb-4">
        <p className="text-xs text-[#A1A1AA] mb-3">Everything in this dashboard is powered by the same public API. Use these keys to integrate coupons directly into your app.</p>
        <div className="flex gap-2">
          <Input data-testid="api-key-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Key name (e.g. Shopify Prod)" className="flex-1 bg-[#0A0A0A] border-[#27272A] text-white" />
          <Button data-testid="api-key-create" onClick={create} disabled={busy} className="btn-primary rounded-md gap-2">
            {busy ? <Loader2 className="w-4 h-4 spin" /> : <Key className="w-4 h-4" />} Create key
          </Button>
        </div>
        {freshKey && (
          <div className="mt-3 rounded-md border border-[#CCFF00]/30 bg-[#CCFF00]/5 p-3" data-testid="fresh-api-key">
            <div className="text-[10px] uppercase tracking-widest text-[#CCFF00] font-bold mb-1">Copy now — will not be shown again</div>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-xs font-mono break-all">{freshKey}</code>
              <button onClick={() => { navigator.clipboard.writeText(freshKey).catch(() => {}); toast.success("Copied"); }} className="p-1.5 rounded hover:bg-white/5"><Copy className="w-4 h-4" /></button>
            </div>
          </div>
        )}
      </div>

      <div className="surface rounded-lg overflow-hidden">
        {keys.length === 0 ? (
          <div className="p-6 text-sm text-[#71717A]">No API keys yet.</div>
        ) : (
          <table className="w-full text-sm" data-testid="api-keys-table">
            <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-6 py-2">Name</th>
                <th className="text-left px-3 py-2">Preview</th>
                <th className="text-left px-3 py-2">Scopes</th>
                <th className="text-left px-3 py-2">State</th>
                <th className="text-right px-3 py-2">Created</th>
                <th className="text-right px-6 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id} className="border-t border-[#27272A]" data-testid={`api-key-row-${k.id}`}>
                  <td className="px-6 py-2 font-medium">{k.name}</td>
                  <td className="px-3 py-2 font-mono text-xs text-[#A1A1AA]">{k.key_preview}</td>
                  <td className="px-3 py-2 text-xs">{k.scopes?.join(", ")}</td>
                  <td className="px-3 py-2">
                    {k.revoked ? <span className="text-xs text-red-400">revoked</span> : <span className="text-xs text-emerald-400">active</span>}
                  </td>
                  <td className="px-3 py-2 text-right text-xs text-[#71717A]">{(k.created_at || "").slice(0, 10)}</td>
                  <td className="px-6 py-2 text-right">
                    {!k.revoked && (
                      <button onClick={() => revoke(k.id)} className="text-xs text-[#71717A] hover:text-red-400 flex items-center gap-1 ml-auto" data-testid={`api-key-revoke-${k.id}`}>
                        <ShieldOff className="w-3 h-3" /> Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
