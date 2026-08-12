import { useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Sparkles, Rocket, X } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";

const SUGGESTIONS = [
  "Boost weekend traffic with a 20% flash sale",
  "Win back customers who haven't ordered in 30 days",
  "Launch a VIP-only campaign for our top spenders",
  "Clear slow-moving swimwear inventory",
];

function AssetBlock({ label, value }) {
  if (!value) return null;
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 0);
  return (
    <div className="p-3 rounded-md bg-[#0A0A0A] border border-[#27272A]">
      <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-1">{label}</div>
      <div className="text-xs text-[#E4E4E7] whitespace-pre-wrap break-words">{text}</div>
    </div>
  );
}

export default function OneClickCampaign({ trigger }) {
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [pkg, setPkg] = useState(null);
  const [launching, setLaunching] = useState(false);

  const reset = () => { setPkg(null); setPrompt(""); };

  const generate = async () => {
    if (!prompt.trim()) { toast.error("Describe what you want to promote"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/ai/one-click-campaign", { prompt });
      setPkg(data);
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const launch = async (activate) => {
    setLaunching(true);
    try {
      const { data } = await api.post("/ai/one-click-campaign/approve", { package: pkg, activate });
      toast.success(`Campaign ${activate ? "launched" : "saved as draft"} · Code ${data.code}`);
      setOpen(false); reset();
    } catch (e) { toast.error(apiError(e)); } finally { setLaunching(false); }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger asChild>
        {trigger || (
          <Button data-testid="one-click-open-btn" className="btn-ai gap-2 rounded-md">
            <Rocket className="w-4 h-4" /> One-Click Campaign
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-display flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#CCFF00]" />
            One-Click Campaign
          </DialogTitle>
        </DialogHeader>

        {!pkg ? (
          <div>
            <p className="text-sm text-[#A1A1AA] mb-4">
              Describe what you want to promote. Claude will draft a coupon plus every asset — email, SMS, WhatsApp, push, social copy, landing headline, ad copy — respecting your brand voice and discount cap.
            </p>
            <textarea
              data-testid="one-click-prompt"
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Promote my restaurant for Labor Day weekend."
              className="w-full bg-[#0A0A0A] border border-[#27272A] rounded-md p-3 text-sm text-white focus:outline-none focus:border-[#005CEE]"
            />
            <div className="flex flex-wrap gap-2 mt-3">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => setPrompt(s)}
                        className="text-xs text-[#A1A1AA] px-2.5 py-1 rounded-full border border-[#27272A] hover:border-[#CCFF00]/40 hover:text-white transition">{s}</button>
              ))}
            </div>
            <div className="mt-5 flex justify-end">
              <Button data-testid="one-click-generate-btn" onClick={generate} disabled={busy} className="btn-primary rounded-md gap-2">
                {busy ? <Loader2 className="w-4 h-4 spin" /> : <Sparkles className="w-4 h-4" />}
                Generate campaign
              </Button>
            </div>
          </div>
        ) : (
          <div data-testid="one-click-preview">
            <div className="rounded-lg border border-[#CCFF00]/30 bg-[#CCFF00]/5 p-4 mb-4">
              <div className="flex items-center justify-between mb-2">
                <div className="text-[10px] uppercase tracking-widest text-[#CCFF00] font-bold">Coupon</div>
                <span className="text-lg font-bold text-[#CCFF00]">{pkg.coupon?.discount_value}%</span>
              </div>
              <div className="font-display font-bold text-lg leading-tight">{pkg.coupon?.headline}</div>
              <div className="text-sm text-[#A1A1AA] mt-1">{pkg.coupon?.description}</div>
              <div className="text-xs text-[#71717A] mt-2">Type · {pkg.coupon?.type} · Audience · {pkg.coupon?.audience} · CTA · {pkg.coupon?.cta}</div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <AssetBlock label="Email subject" value={pkg.email?.subject} />
              <AssetBlock label="Landing headline" value={pkg.landing_headline} />
              <AssetBlock label="Email body" value={pkg.email?.body_short} />
              <AssetBlock label="SMS" value={pkg.sms} />
              <AssetBlock label="WhatsApp" value={pkg.whatsapp} />
              <AssetBlock label="Push notification" value={pkg.push ? `${pkg.push.title}\n${pkg.push.body}` : null} />
              <AssetBlock label="Social caption" value={pkg.social_caption} />
              <AssetBlock label="Ad copy" value={pkg.ad_copy} />
            </div>
            <div className="mt-5 flex justify-between gap-2">
              <Button data-testid="one-click-back-btn" onClick={reset} className="btn-ghost rounded-md gap-2">
                <X className="w-4 h-4" /> Discard
              </Button>
              <div className="flex gap-2">
                <Button data-testid="one-click-draft-btn" onClick={() => launch(false)} disabled={launching} className="btn-ghost rounded-md">
                  Save as draft
                </Button>
                <Button data-testid="one-click-launch-btn" onClick={() => launch(true)} disabled={launching} className="btn-primary rounded-md gap-2">
                  {launching ? <Loader2 className="w-4 h-4 spin" /> : <Rocket className="w-4 h-4" />}
                  Launch now
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
