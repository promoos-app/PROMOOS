import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { STATE_STYLES, TYPE_LABELS, discountText } from "@/lib/couponUtils";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Loader2, Download, RefreshCw, Zap, Mail } from "lucide-react";

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

  const load = useCallback(() => {
    api.get(`/coupons/${id}`).then((r) => setC(r.data)).catch((e) => toast.error(apiError(e)));
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
    if (list.length === 0) { toast.error("Enter at least one email"); return; }
    setEmailBusy(true); setEmailResult(null);
    try {
      const { data } = await api.post(`/coupons/${id}/send-email`, {
        to: list,
        landing_url: window.location.origin,
      });
      setEmailResult({ ok: true, ids: data.sent_to });
      toast.success(`Sent to ${data.sent_to.length} recipient(s)`);
    } catch (e) {
      const m = apiError(e);
      setEmailResult({ ok: false, msg: m });
      toast.error(m);
    } finally { setEmailBusy(false); }
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

      {/* Send by email */}
      <div className="surface rounded-lg p-6 mt-6">
        <div className="flex items-center gap-2 mb-1">
          <Mail className="w-4 h-4 text-[#CCFF00]" />
          <h3 className="font-display font-bold">Send by Email</h3>
        </div>
        <p className="text-xs text-[#71717A] mb-3">Deliver this coupon as a branded transactional email via Resend. Comma-separate multiple recipients.</p>
        <div className="flex gap-2 flex-col sm:flex-row">
          <Input
            data-testid="email-to-input"
            type="text"
            placeholder="customer@example.com, another@example.com"
            value={emailTo}
            onChange={(e) => setEmailTo(e.target.value)}
            className="bg-[#0A0A0A] border-[#27272A] text-white flex-1"
          />
          <Button data-testid="send-email-btn" onClick={sendEmail} disabled={emailBusy} className="btn-primary rounded-md gap-2 shrink-0">
            {emailBusy ? <Loader2 className="w-4 h-4 spin" /> : <Mail className="w-4 h-4" />} Send
          </Button>
        </div>
        {emailResult?.ok && (
          <div data-testid="email-result" className="mt-3 p-3 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-sm text-emerald-400">
            Delivered to {emailResult.ids.join(", ")}
          </div>
        )}
        {emailResult && !emailResult.ok && (
          <div data-testid="email-error" className="mt-3 p-3 rounded-md bg-red-500/10 border border-red-500/20 text-sm text-red-400">
            {emailResult.msg}
          </div>
        )}
      </div>
    </div>
  );
}

function Label({ children, className }) {
  return <div className={`text-xs ${className}`}>{children}</div>;
}
