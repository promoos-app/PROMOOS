import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { toast } from "sonner";
import { Copy, Check, Share2, Loader2, ExternalLink } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

function shortToken(email) {
  return btoa(email).replace(/=+$/g, "").slice(0, 14);
}

export default function PublicCoupon() {
  const { code } = useParams();
  const [params] = useSearchParams();
  const ref = params.get("ref") || "";
  const [c, setC] = useState(null);
  const [err, setErr] = useState("");
  const [copied, setCopied] = useState(false);
  const [shareEmail, setShareEmail] = useState("");
  const [shareLink, setShareLink] = useState("");
  const [redeemAmt, setRedeemAmt] = useState(80);
  const [redeeming, setRedeeming] = useState(false);
  const [redeemDone, setRedeemDone] = useState(null);

  useEffect(() => {
    axios
      .get(`${API}/public/coupons/${encodeURIComponent(code)}${ref ? `?ref=${encodeURIComponent(ref)}` : ""}`)
      .then((r) => setC(r.data))
      .catch(() => setErr("This offer is no longer available."));
  }, [code, ref]);

  const bg = useMemo(() => c?.brand?.primary_color || "#005CEE", [c]);
  const accent = useMemo(() => c?.brand?.secondary_color || "#CCFF00", [c]);

  if (err) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center p-6">
        <div className="text-center text-[#A1A1AA]" data-testid="public-not-available">
          <div className="text-2xl font-bold text-white mb-2">Offer unavailable</div>
          <div>{err}</div>
        </div>
      </div>
    );
  }
  if (!c) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-white spin" />
      </div>
    );
  }

  const copyCode = () => {
    navigator.clipboard.writeText(c.code).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
    toast.success("Code copied");
  };

  const generateShareLink = () => {
    if (!shareEmail.trim()) { toast.error("Enter your email to earn credit"); return; }
    const token = shortToken(shareEmail.trim().toLowerCase());
    const link = `${window.location.origin}/c/${c.code}?ref=${token}`;
    setShareLink(link);
    navigator.clipboard.writeText(link).catch(() => {});
    toast.success("Share link ready");
  };

  const testRedeem = async () => {
    setRedeeming(true); setRedeemDone(null);
    try {
      const { data } = await axios.post(`${API}/public/coupons/redeem`, {
        code: c.code, amount: Number(redeemAmt),
        customer: "web-" + Math.random().toString(36).slice(2, 8),
        ref: ref || null,
      });
      setRedeemDone(data);
      toast.success(`Applied $${data.discount.toFixed(2)} off`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not redeem");
    } finally { setRedeeming(false); }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex items-center justify-center px-4 py-10"
         style={{ backgroundImage: `radial-gradient(1200px 400px at 50% -100px, ${bg}22, transparent)` }}>
      <div className="w-full max-w-[520px]" data-testid="public-coupon-card">
        <div className="text-center mb-6">
          <div className="inline-block text-[11px] tracking-[0.14em] uppercase font-bold px-3 py-1 rounded-full"
               style={{ background: accent, color: "#0A0A0A" }} data-testid="public-brand-name">
            {c.brand?.name || "PromoOS"}
          </div>
          {ref && (
            <div className="text-xs text-[#A1A1AA] mt-3" data-testid="public-ref-banner">
              A friend shared this offer with you ✨
            </div>
          )}
        </div>

        <div className="rounded-2xl overflow-hidden border border-[#27272A] bg-gradient-to-b from-[#141416] to-[#0A0A0A]">
          {c.image_url ? (
            <img src={c.image_url} alt="" className="w-full h-56 object-cover" />
          ) : (
            <div className="w-full h-40 flex items-center justify-center"
                 style={{ background: `linear-gradient(135deg, ${bg}, ${accent})` }}>
              <div className="text-5xl font-black text-white/90 tracking-tight">
                {c.discount_value}{c.type === "fixed" ? "" : "%"} OFF
              </div>
            </div>
          )}
          <div className="p-6">
            <h1 className="text-3xl font-bold leading-tight" data-testid="public-headline">{c.headline}</h1>
            <p className="text-sm text-[#A1A1AA] mt-2" data-testid="public-description">{c.description}</p>

            <div className="mt-6 flex items-center gap-3">
              <div className="flex-1 rounded-lg px-4 py-3 text-center font-mono text-xl font-bold tracking-widest border-2 border-dashed"
                   style={{ borderColor: bg, color: bg, background: `${bg}11` }}
                   data-testid="public-code">{c.code}</div>
              <button
                data-testid="public-copy-btn"
                onClick={copyCode}
                className="px-4 py-3 rounded-lg font-bold text-sm"
                style={{ background: accent, color: "#0A0A0A" }}
              >
                {copied ? <Check className="w-4 h-4" /> : <><Copy className="w-4 h-4 inline mr-1" />Copy</>}
              </button>
            </div>

            {c.state === "active" && (
              <div className="mt-4 flex items-center gap-2">
                <input
                  data-testid="public-redeem-amount"
                  type="number"
                  value={redeemAmt}
                  onChange={(e) => setRedeemAmt(e.target.value)}
                  className="flex-1 bg-[#0A0A0A] border border-[#27272A] rounded-lg px-3 py-2 text-sm"
                  placeholder="Cart amount"
                />
                <button
                  data-testid="public-redeem-btn"
                  onClick={testRedeem}
                  disabled={redeeming}
                  className="px-4 py-2 rounded-lg font-bold text-sm text-white disabled:opacity-50"
                  style={{ background: bg }}
                >
                  {redeeming ? <Loader2 className="w-4 h-4 spin" /> : c.cta}
                </button>
              </div>
            )}
            {redeemDone && (
              <div data-testid="public-redeem-result" className="mt-3 text-sm rounded-lg p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                You saved ${redeemDone.discount.toFixed(2)}. Net: ${redeemDone.revenue.toFixed(2)}
                {redeemDone.referral_credit > 0 && (
                  <> · Referrer earned ${redeemDone.referral_credit.toFixed(2)}</>
                )}
              </div>
            )}

            <div className="mt-6 grid grid-cols-[1fr_auto] gap-4 items-center border-t border-[#27272A] pt-5">
              <div>
                <div className="text-xs text-[#71717A] uppercase tracking-wider">Scan to save</div>
                <div className="text-xs text-[#A1A1AA] mt-1">Show at checkout or scan on any device.</div>
              </div>
              {c.qr_code && (
                <img src={c.qr_code} alt="QR" className="w-24 h-24 rounded-md bg-white p-1.5" data-testid="public-qr" />
              )}
            </div>

            <p className="text-[11px] text-[#71717A] mt-6 leading-relaxed">{c.terms}</p>
          </div>
        </div>

        {c.referral && (
          <div className="mt-6 rounded-2xl border border-[#27272A] bg-[#141416] p-5" data-testid="public-referral-panel">
            <div className="flex items-center gap-2 mb-1">
              <Share2 className="w-4 h-4" style={{ color: accent }} />
              <div className="font-bold">Share & earn {c.referral_credit_pct}%</div>
            </div>
            <p className="text-xs text-[#A1A1AA] mb-3">
              Get a personal link. When friends redeem, you earn credit toward your next order.
            </p>
            <div className="flex gap-2">
              <input
                data-testid="referral-email-input"
                type="email"
                placeholder="you@example.com"
                value={shareEmail}
                onChange={(e) => setShareEmail(e.target.value)}
                className="flex-1 bg-[#0A0A0A] border border-[#27272A] rounded-lg px-3 py-2 text-sm"
              />
              <button
                data-testid="referral-generate-btn"
                onClick={generateShareLink}
                className="px-4 py-2 rounded-lg font-bold text-sm text-white"
                style={{ background: bg }}
              >
                Get link
              </button>
            </div>
            {shareLink && (
              <div className="mt-3 text-xs bg-[#0A0A0A] border border-[#27272A] rounded-lg p-2 font-mono break-all"
                   data-testid="referral-link">
                {shareLink}
              </div>
            )}
          </div>
        )}

        <div className="text-center mt-6">
          <a href="/" className="text-xs text-[#71717A] hover:text-[#A1A1AA] inline-flex items-center gap-1">
            Powered by PromoOS <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
