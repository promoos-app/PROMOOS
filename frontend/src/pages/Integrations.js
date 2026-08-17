import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Plug, Key, Copy, Trash2, ShieldOff, Webhook, Code2, ShieldCheck, RefreshCw } from "lucide-react";

function ConnectorCard({ name, icon, connected, hint, envHint }) {
  return (
    <div className="surface rounded-lg p-5" data-testid={`connector-${name.toLowerCase()}`}>
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

  const load = () => api.get("/api-keys").then((r) => setKeys(r.data)).catch(() => {});
  useEffect(() => {
    load();
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
        <ConnectorCard name="Resend" icon="✉️" connected={false} hint="Transactional + branded coupon emails."
                       envHint="RESEND_API_KEY=re_..." />
        <ConnectorCard name="SendGrid" icon="📧" connected={false} hint="High-volume transactional email delivery."
                       envHint="SENDGRID_API_KEY=SG.…" />
        <ConnectorCard name="Mailchimp" icon="🐵" connected={false} hint="Sync audiences and send mass campaigns."
                       envHint="MAILCHIMP_API_KEY + MAILCHIMP_SERVER" />
        <ConnectorCard name="ConvertKit" icon="✍️" connected={false} hint="Creator-focused broadcasts and sequences."
                       envHint="CONVERTKIT_API_KEY" />
        <ConnectorCard name="Brevo (Sendinblue)" icon="💌" connected={false} hint="Combined email + SMS marketing platform."
                       envHint="BREVO_API_KEY=xkeysib-…" />
        <ConnectorCard name="Postmark" icon="📬" connected={false} hint="Best-in-class deliverability for receipts."
                       envHint="POSTMARK_SERVER_TOKEN" />
        <ConnectorCard name="Mailgun" icon="📨" connected={false} hint="Developer-friendly SMTP + API email."
                       envHint="MAILGUN_API_KEY + MAILGUN_DOMAIN" />
        <ConnectorCard name="AWS SES" icon="☁️" connected={false} hint="Amazon Simple Email Service — cheap at scale."
                       envHint="AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY" />
        <ConnectorCard name="Klaviyo" icon="🎯" connected={false} hint="E-commerce-first email + SMS flows."
                       envHint="KLAVIYO_API_KEY=pk_…" />
      </div>

      <h2 className="font-display font-bold text-lg mb-3">Social media & AI auto-publishing</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8" data-testid="social-platforms-grid">
        <ConnectorCard name="Facebook Pages" icon="📘" connected={false} hint="Auto-post generated coupon graphics + captions."
                       envHint="FACEBOOK_ACCESS_TOKEN + FACEBOOK_PAGE_ID" />
        <ConnectorCard name="Instagram" icon="📸" connected={false} hint="Feed posts, stories, reels — scheduled by AI."
                       envHint="IG_BUSINESS_ACCOUNT_ID + FACEBOOK_ACCESS_TOKEN" />
        <ConnectorCard name="X (Twitter)" icon="𝕏" connected={false} hint="Tweet promos with generated visuals."
                       envHint="X_BEARER_TOKEN or OAuth 2.0" />
        <ConnectorCard name="LinkedIn" icon="in" connected={false} hint="Company page posts for B2B campaigns."
                       envHint="LINKEDIN_ACCESS_TOKEN + LINKEDIN_ORG_ID" />
        <ConnectorCard name="TikTok" icon="🎵" connected={false} hint="Video promos, hashtag challenges."
                       envHint="TIKTOK_ACCESS_TOKEN" />
        <ConnectorCard name="YouTube" icon="▶️" connected={false} hint="Community posts + Shorts scheduling."
                       envHint="YOUTUBE_API_KEY + OAuth" />
        <ConnectorCard name="Pinterest" icon="📌" connected={false} hint="Pin coupon graphics to boards."
                       envHint="PINTEREST_ACCESS_TOKEN" />
        <ConnectorCard name="Threads" icon="@" connected={false} hint="Meta's text-first social feed." envHint="Meta Graph API" />
        <ConnectorCard name="Snapchat Ads" icon="👻" connected={false} hint="Snap AR filter promos + geofilters."
                       envHint="SNAPCHAT_ACCESS_TOKEN" />
      </div>

      <h2 className="font-display font-bold text-lg mb-3">Delivery channels</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-8">
        <ConnectorCard name="Twilio" icon="💬" connected={false} hint="Send SMS and WhatsApp coupons."
                       envHint="TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_SMS, TWILIO_FROM_WHATSAPP" />
        <ConnectorCard name="Stripe" icon="💳" connected={true} hint="Subscription billing + 100+ global payment methods (cards, Apple/Google Pay, SEPA, iDEAL, Klarna, Afterpay, Alipay, WeChat)." envHint="STRIPE_SECRET_KEY (configured)" />
        <ConnectorCard name="PayPal" icon="🅿️" connected={false} hint="Alternative payment provider for global reach." envHint="PAYPAL_CLIENT_ID + PAYPAL_SECRET" />
        <ConnectorCard name="Razorpay" icon="🇮🇳" connected={false} hint="India-first payments — UPI, NetBanking, cards." envHint="RAZORPAY_KEY_ID + RAZORPAY_SECRET" />
        <ConnectorCard name="Paystack" icon="🌍" connected={false} hint="Africa-first payments — cards, bank transfer, mobile money." envHint="PAYSTACK_SECRET_KEY" />
        <ConnectorCard name="Telegram Bot" icon="✈️" connected={false} hint="Push coupons to Telegram channels."
                       envHint="TELEGRAM_BOT_TOKEN" />
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
