import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { STATE_STYLES, TYPE_LABELS, discountText } from "@/lib/couponUtils";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Loader2, Download, RefreshCw, Zap, Mail, ExternalLink, Code2, Users, MessageSquare, Beaker, Trophy } from "lucide-react";

function Stat({ label, value }) {
  return (
    <div className="surface rounded-lg p-4">
      <div className="text-xs uppercase tracking-wide text-[#71717A]">{label}</div>
      <div className="font-display font-bold text-2xl mt-1">{value}</div>
    </div>
  );
}

export default function CouponDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setC] = useState(null);
  const [bulkN, setBulkN] = useState(10);
  const [bulkCodes, setBulkCodes] = useState([]);
  const [busy, setBusy] = useState(false);
  const [redeemAmt, setRedeemAmt] = useState(80);
  const [redeemResult, setRedeemResult] = useState(null);
  const [redeemError, setRedeemError] = useState("");
  const [emailTo, setEmailTo] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailResult, setEmailResult] = useState(null);
  const [channel, setChannel] = useState("email");   // email | sms | whatsapp
  const [refs, setRefs] = useState(null);
  const [snippetCopied, setSnippetCopied] = useState(false);
  const [widgetVariant, setWidgetVariant] = useState("inline");
  const [experiments, setExperiments] = useState([]);
  const [expBusy, setExpBusy] = useState(false);
  const [nVariants, setNVariants] = useState(3);

  const load = useCallback(() => {
    api.get(`/coupons/${id}`).then((r) => setC(r.data)).catch((e) => toast.error(apiError(e)));
    api.get(`/coupons/${id}/referrals`).then((r) => setRefs(r.data)).catch(() => {});
    api.get(`/coupons/${id}/experiments`).then((r) => setExperiments(r.data)).catch(() => {});
  }, [id]);
  useEffect(() => { load(); }, [load]);

  if (!c) return <div className="text-[#71717A]">Loading…</div>;

  const genBulk = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/coupons/${id}/bulk-codes`, { count: Number(bulkN) });
      setBulkCodes(data.codes);
      toast.success(`Generated ${data.generated} unique codes`);
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const testRedeem = async () => {
    setRedeemResult(null);
    setRedeemError("");
    try {
      const { data } = await api.post("/coupons/redeem", { code: c.code, amount: Number(redeemAmt), customer: "demo-tester-" + Date.now() });
      setRedeemResult(data);
      toast.success(`Redeemed — $${data.discount.toFixed(2)} discount applied`);
      load();
    } catch (e) { const m = apiError(e); setRedeemError(m); toast.error(m); }
  };

  const downloadQR = () => {
    const a = document.createElement("a");
    a.href = c.qr_code; a.download = `${c.code}-qr.png`; a.click();
  };

  const sendEmail = async () => {
    const list = emailTo.split(",").map((s) => s.trim()).filter(Boolean);
    if (list.length === 0) { toast.error(channel === "email" ? "Enter at least one email" : "Enter at least one phone number in E.164"); return; }
    setEmailBusy(true); setEmailResult(null);
    try {
      let data;
      if (channel === "email") {
        const r = await api.post(`/coupons/${id}/send-email`, { to: list, landing_url: `${window.location.origin}/c/${c.code}` });
        data = r.data; setEmailResult({ ok: true, ids: data.sent_to });
        toast.success(`Sent to ${data.sent_to.length} recipient(s)`);
      } else {
        const r = await api.post(`/coupons/${id}/send-message`, { to: list, channel, landing_url: `${window.location.origin}/c/${c.code}` });
        data = r.data; setEmailResult({ ok: true, ids: data.sent });
        toast.success(`Sent ${data.sent.length} ${channel.toUpperCase()} message(s)`);
      }
    } catch (e) {
      const m = apiError(e);
      setEmailResult({ ok: false, msg: m });
      toast.error(m);
    } finally { setEmailBusy(false); }
  };

  const runExperiment = async () => {
    setExpBusy(true);
    try {
      await api.post(`/coupons/${id}/experiments`, { n: Number(nVariants), use_ai: true });
      toast.success("Generated variants with AI");
      const r = await api.get(`/coupons/${id}/experiments`); setExperiments(r.data);
    } catch (e) { toast.error(apiError(e)); } finally { setExpBusy(false); }
  };

  const promoteWinner = async (eid, variantId) => {
    try {
      const { data } = await api.post(`/experiments/${eid}/promote`, variantId ? { variant_id: variantId } : {});
      toast.success(`Promoted: ${data.winner.headline.slice(0, 40)}…`);
      load();
    } catch (e) { toast.error(apiError(e)); }
  };

  return (
    <div className="fade-up max-w-[1200px]">
      <button data-testid="detail-back-btn" onClick={() => navigate("/coupons")} className="flex items-center gap-1.5 text-sm text-[#A1A1AA] hover:text-white mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to coupons
      </button>

      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display font-bold text-3xl tracking-tight">{c.name}</h1>
            <span className={`px-2 py-0.5 rounded text-xs capitalize font-medium ${STATE_STYLES[c.state]}`}>{c.state}</span>
          </div>
          <p className="text-sm text-[#A1A1AA] mt-1">{TYPE_LABELS[c.type]} · {discountText(c)}</p>
        </div>
        <Button data-testid="detail-edit-btn" onClick={() => navigate(`/coupons/${id}/edit`)} className="btn-primary rounded-md">Edit</Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Stat label="Impressions" value={(c.stats?.impressions ?? 0).toLocaleString()} />
        <Stat label="Clicks" value={(c.stats?.clicks ?? 0).toLocaleString()} />
        <Stat label="Redemptions" value={(c.stats?.redemptions ?? 0).toLocaleString()} />
        <Stat label="Revenue" value={"$" + Number(c.stats?.revenue ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* QR */}
        <div className="surface rounded-lg p-6">
          <h3 className="font-display font-bold mb-4">QR Code</h3>
          <img data-testid="coupon-qr" src={c.qr_code} alt="QR" className="w-40 h-40 rounded-md bg-white p-2 mx-auto" />
          <div className="text-center mt-3">
            <span className="font-mono text-sm bg-[#0A0A0A] border border-[#27272A] px-3 py-1.5 rounded">{c.code}</span>
          </div>
          <Button data-testid="download-qr-btn" onClick={downloadQR} className="w-full mt-4 rounded-md gap-2 bg-[#0A0A0A] border border-[#27272A] text-white hover:bg-[#1E1E1E]">
            <Download className="w-4 h-4" /> Download QR
          </Button>
        </div>

        {/* Bulk codes */}
        <div className="surface rounded-lg p-6">
          <h3 className="font-display font-bold mb-4">Bulk Codes</h3>
          <p className="text-xs text-[#71717A] mb-3">Generate unique one-time codes for this campaign.</p>
          <div className="flex gap-2">
            <Input data-testid="bulk-count-input" type="number" value={bulkN} onChange={(e) => setBulkN(e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white" />
            <Button data-testid="generate-bulk-btn" onClick={genBulk} disabled={busy} className="btn-ai rounded-md gap-2 shrink-0">
              {busy ? <Loader2 className="w-4 h-4 spin" /> : <RefreshCw className="w-4 h-4" />} Generate
            </Button>
          </div>
          {bulkCodes.length > 0 && (
            <div className="mt-3 max-h-40 overflow-y-auto space-y-1">
              {bulkCodes.map((code, index) => (
                <div key={code} data-testid={`bulk-code-${index}`} className="font-mono text-xs text-[#A1A1AA] bg-[#0A0A0A] px-2 py-1 rounded border border-[#27272A]">{code}</div>
              ))}
            </div>
          )}
        </div>

        {/* Validate / redeem sandbox */}
        <div className="surface rounded-lg p-6">
          <h3 className="font-display font-bold mb-4">Redeem Sandbox</h3>
          <p className="text-xs text-[#71717A] mb-3">Simulate a redemption to test rules & fraud checks.</p>
          <Label className="text-xs text-[#A1A1AA]">Cart amount</Label>
          <Input data-testid="redeem-amount-input" type="number" value={redeemAmt} onChange={(e) => setRedeemAmt(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white mb-3" />
          <Button data-testid="test-redeem-btn" onClick={testRedeem} disabled={c.state !== "active"} className="w-full btn-primary rounded-md gap-2 disabled:opacity-50">
            <Zap className="w-4 h-4" /> Redeem {c.code}
          </Button>
          {c.state !== "active" && (
            <p className="text-xs text-amber-400 mt-2">Coupon must be <span className="font-medium">active</span> to redeem (currently {c.state}).</p>
          )}
          {redeemError && (
            <div data-testid="redeem-error" className="mt-3 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-sm text-red-400">{redeemError}</div>
          )}
          {redeemResult && (
            <div data-testid="redeem-result" className="mt-3 p-3 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-sm">
              <div className="text-emerald-400 font-medium">Redeemed ✓</div>
              <div className="text-[#A1A1AA] text-xs mt-1 font-mono">Discount: ${redeemResult.discount.toFixed(2)} · Net revenue: ${redeemResult.revenue.toFixed(2)}</div>
            </div>
          )}
        </div>
      </div>

      {/* Send by channel */}
      <div className="surface rounded-lg p-6 mt-6">
        <div className="flex items-center gap-2 mb-1">
          {channel === "email" ? <Mail className="w-4 h-4 text-[#CCFF00]" /> : <MessageSquare className="w-4 h-4 text-[#CCFF00]" />}
          <h3 className="font-display font-bold">Send Coupon</h3>
        </div>
        <p className="text-xs text-[#71717A] mb-3">Deliver to customers over Email (Resend), SMS or WhatsApp (Twilio).</p>
        <div className="inline-flex bg-[#0A0A0A] border border-[#27272A] rounded-lg p-1 mb-3">
          {[
            { k: "email", label: "Email" },
            { k: "sms", label: "SMS" },
            { k: "whatsapp", label: "WhatsApp" },
          ].map((t) => (
            <button
              key={t.k}
              data-testid={`channel-tab-${t.k}`}
              onClick={() => setChannel(t.k)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${channel === t.k ? "bg-[#005CEE] text-white" : "text-[#A1A1AA] hover:text-white"}`}
            >{t.label}</button>
          ))}
        </div>
        <div className="flex gap-2 flex-col sm:flex-row">
          <Input
            data-testid="send-to-input"
            type="text"
            placeholder={channel === "email" ? "customer@example.com, another@example.com" : "+15551234567, +14155550101"}
            value={emailTo}
            onChange={(e) => setEmailTo(e.target.value)}
            className="bg-[#0A0A0A] border-[#27272A] text-white flex-1"
          />
          <Button data-testid="send-btn" onClick={sendEmail} disabled={emailBusy} className="btn-primary rounded-md gap-2 shrink-0">
            {emailBusy ? <Loader2 className="w-4 h-4 spin" /> : (channel === "email" ? <Mail className="w-4 h-4" /> : <MessageSquare className="w-4 h-4" />)} Send
          </Button>
        </div>
        {emailResult?.ok && (
          <div data-testid="send-result" className="mt-3 p-3 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400">
            Delivered · {emailResult.ids.join(", ").slice(0, 200)}
          </div>
        )}
        {emailResult && !emailResult.ok && (
          <div data-testid="send-error" className="mt-3 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-sm text-red-400">
            {emailResult.msg}
          </div>
        )}
      </div>

      {/* Public landing + Embed */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div className="surface rounded-lg p-6">
          <div className="flex items-center gap-2 mb-1">
            <ExternalLink className="w-4 h-4 text-[#CCFF00]" />
            <h3 className="font-display font-bold">Public Landing Page</h3>
          </div>
          <p className="text-xs text-[#71717A] mb-3">Share this shoppable page anywhere — QR, copy, and redeem all built in.</p>
          {(() => {
            const url = `${window.location.origin}/c/${c.code}`;
            return (
              <>
                <div className="flex gap-2">
                  <Input data-testid="public-url" readOnly value={url} className="bg-[#0A0A0A] border-[#27272A] text-white font-mono text-xs" />
                  <Button
                    data-testid="copy-public-url"
                    onClick={() => { navigator.clipboard.writeText(url); toast.success("Link copied"); }}
                    className="btn-primary rounded-md shrink-0"
                  >
                    Copy
                  </Button>
                </div>
                <a
                  data-testid="open-public-page"
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 inline-flex items-center gap-1.5 text-sm text-[#CCFF00] hover:underline"
                >
                  Open page <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </>
            );
          })()}
        </div>

        <div className="surface rounded-lg p-6">
          <div className="flex items-center gap-2 mb-1">
            <Code2 className="w-4 h-4 text-[#CCFF00]" />
            <h3 className="font-display font-bold">Embed Widget</h3>
          </div>
          <p className="text-xs text-[#71717A] mb-3">Paste this snippet into any Shopify/WordPress/plain HTML page.</p>
          {(() => {
            const src = `${process.env.REACT_APP_BACKEND_URL}/api/embed/coupon.js${widgetVariant !== "inline" ? `?variant=${widgetVariant}` : ""}`;
            const snippet = `<script async src="${src}" data-promoos-code="${c.code}"></script>`;
            return (
              <>
                <div className="flex flex-wrap gap-1 mb-3 bg-[#0A0A0A] border border-[#27272A] rounded-md p-1 w-fit">
                  {["inline", "popup", "bar", "wheel", "wallet"].map((v) => (
                    <button
                      key={v}
                      data-testid={`widget-variant-${v}`}
                      onClick={() => setWidgetVariant(v)}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium transition capitalize ${widgetVariant === v ? "bg-[#005CEE] text-white" : "text-[#A1A1AA] hover:text-white"}`}
                    >{v}</button>
                  ))}
                </div>
                <pre data-testid="embed-snippet" className="text-xs bg-[#0A0A0A] border border-[#27272A] rounded-md p-3 overflow-x-auto text-[#A1A1AA] whitespace-pre-wrap break-all">{snippet}</pre>
                <Button
                  data-testid="copy-embed-btn"
                  onClick={() => {
                    navigator.clipboard.writeText(snippet).catch(() => {});
                    setSnippetCopied(true);
                    toast.success("Snippet copied");
                    setTimeout(() => setSnippetCopied(false), 1500);
                  }}
                  className="mt-3 btn-primary rounded-md"
                >
                  {snippetCopied ? "Copied ✓" : "Copy snippet"}
                </Button>
              </>
            );
          })()}
        </div>
      </div>

      {/* Referral leaderboard */}
      {c.rules?.referral_enabled && (
        <div className="surface rounded-lg p-6 mt-6" data-testid="referral-panel">
          <div className="flex items-center gap-2 mb-1">
            <Users className="w-4 h-4 text-[#CCFF00]" />
            <h3 className="font-display font-bold">Referral Program</h3>
            <span className="text-xs text-[#71717A] ml-2">{c.rules.referral_credit_pct}% credit per redemption</span>
          </div>
          <p className="text-xs text-[#71717A] mb-4">Customers who share their `/c/{c.code}?ref=…` link earn credit when friends redeem.</p>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <Stat label="Visits via ref" value={refs?.visits ?? 0} />
            <Stat label="Referred redemptions" value={refs?.redemptions ?? 0} />
            <Stat label="Credit owed" value={"$" + Number(refs?.total_credit ?? 0).toFixed(2)} />
          </div>
          {refs?.leaders?.length > 0 ? (
            <div className="border border-[#27272A] rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
                  <tr><th className="text-left px-3 py-2">Referrer</th><th className="text-right px-3 py-2">Redemptions</th><th className="text-right px-3 py-2">Credit</th></tr>
                </thead>
                <tbody>
                  {refs.leaders.map((l) => (
                    <tr key={l.referrer} className="border-t border-[#27272A]" data-testid={`ref-leader-${l.referrer}`}>
                      <td className="px-3 py-2 font-mono text-xs">{l.referrer}</td>
                      <td className="px-3 py-2 text-right">{l.count}</td>
                      <td className="px-3 py-2 text-right text-[#CCFF00]">${l.credit.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-xs text-[#71717A]">No referrals yet — share the landing page to kick things off.</div>
          )}
        </div>
      )}

      {/* A/B Testing */}
      <div className="surface rounded-lg p-6 mt-6" data-testid="ab-test-panel">
        <div className="flex items-center gap-2 mb-1">
          <Beaker className="w-4 h-4 text-[#CCFF00]" />
          <h3 className="font-display font-bold">A/B Test Copy</h3>
        </div>
        <p className="text-xs text-[#71717A] mb-3">Let Claude write bold variants. We deterministically bucket visitors and auto-track wins. Promote the winner in one click.</p>
        <div className="flex items-center gap-2 mb-4">
          <Input
            data-testid="ab-n-variants"
            type="number" min={2} max={5}
            value={nVariants}
            onChange={(e) => setNVariants(e.target.value)}
            className="w-24 bg-[#0A0A0A] border-[#27272A] text-white"
          />
          <span className="text-xs text-[#71717A]">variants</span>
          <Button data-testid="ab-run-btn" onClick={runExperiment} disabled={expBusy} className="btn-primary rounded-md gap-2 ml-2">
            {expBusy ? <Loader2 className="w-4 h-4 spin" /> : <Zap className="w-4 h-4" />}
            {experiments.some((e) => e.status === "running") ? "New experiment" : "Generate & run"}
          </Button>
        </div>

        {experiments.length === 0 ? (
          <div className="text-xs text-[#71717A]">No experiments yet.</div>
        ) : (
          <div className="space-y-4">
            {experiments.map((exp) => (
              <div key={exp.id} className="rounded-lg border border-[#27272A] p-4" data-testid={`ab-experiment-${exp.id}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded ${exp.status === "running" ? "bg-emerald-500/15 text-emerald-400" : exp.status === "complete" ? "bg-[#005CEE]/15 text-[#005CEE]" : "bg-[#27272A] text-[#71717A]"}`}>{exp.status}</span>
                    <span className="text-xs text-[#71717A] font-mono">{exp.id.slice(0, 8)}</span>
                  </div>
                  {exp.status === "running" && (
                    <Button data-testid={`ab-promote-auto-${exp.id}`} onClick={() => promoteWinner(exp.id)} className="btn-ghost rounded-md text-xs gap-1">
                      <Trophy className="w-3.5 h-3.5" /> Promote best
                    </Button>
                  )}
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {exp.variants.map((v) => (
                    <div key={v.id} className={`rounded-md p-3 border ${exp.winner_variant_id === v.id ? "border-[#CCFF00] bg-[#CCFF00]/5" : "border-[#27272A] bg-[#0A0A0A]"}`}
                         data-testid={`ab-variant-${v.id}`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-mono text-[10px] text-[#71717A]">{v.id}</span>
                        {exp.winner_variant_id === v.id && (<span className="text-[10px] text-[#CCFF00] font-bold">WINNER</span>)}
                      </div>
                      <div className="font-medium text-sm leading-tight">{v.headline}</div>
                      <div className="text-xs text-[#A1A1AA] mt-1 line-clamp-2">{v.description}</div>
                      <div className="mt-2 text-[10px] text-[#71717A]">CTA: <span className="text-white font-medium">{v.cta}</span></div>
                      <div className="mt-2 grid grid-cols-3 gap-1 text-center">
                        <div><div className="text-[10px] text-[#71717A]">Views</div><div className="text-xs font-bold">{v.impressions || 0}</div></div>
                        <div><div className="text-[10px] text-[#71717A]">Redeems</div><div className="text-xs font-bold">{v.redemptions || 0}</div></div>
                        <div><div className="text-[10px] text-[#71717A]">CVR</div><div className="text-xs font-bold text-[#CCFF00]">{v.cvr || 0}%</div></div>
                      </div>
                      {exp.status === "running" && (
                        <button
                          data-testid={`ab-promote-${v.id}`}
                          onClick={() => promoteWinner(exp.id, v.id)}
                          className="mt-2 w-full text-xs py-1.5 rounded border border-[#27272A] hover:border-[#CCFF00] hover:text-[#CCFF00] transition"
                        >Promote this</button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Label({ children, className }) {
  return <div className={`text-xs ${className}`}>{children}</div>;
}
