import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { TYPE_LABELS, discountText } from "@/lib/couponUtils";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Sparkles, Wand2, ArrowLeft, Loader2, Image as ImageIcon } from "lucide-react";

const empty = {
  name: "", type: "percentage", discount_value: 25, code: "",
  headline: "", description: "", terms: "", cta: "Claim Offer", state: "draft",
  image_url: "",
  rules: { min_cart: 0, scope: "all", scope_value: "", usage_limit: 0, per_customer_limit: 1, stackable: false, start_date: null, end_date: null },
};

export default function CouponEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState(empty);
  const [prompt, setPrompt] = useState("");
  const [aiCopyLoading, setAiCopyLoading] = useState(false);
  const [aiImgLoading, setAiImgLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (id) {
      api.get(`/coupons/${id}`).then((r) => {
        const c = r.data;
        setForm({ ...empty, ...c, rules: { ...empty.rules, ...c.rules } });
      }).catch((e) => toast.error(apiError(e)));
    }
  }, [id]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setRule = (k, v) => setForm((f) => ({ ...f, rules: { ...f.rules, [k]: v } }));

  const runAICopy = async () => {
    if (!prompt.trim()) { toast.error("Describe your promotion first"); return; }
    setAiCopyLoading(true);
    try {
      const { data } = await api.post("/ai/copy", { prompt });
      setForm((f) => ({
        ...f,
        name: data.name || f.name,
        type: data.type || f.type,
        discount_value: data.discount_value ?? f.discount_value,
        headline: data.headline || f.headline,
        description: data.description || f.description,
        terms: data.terms || f.terms,
        cta: data.cta || f.cta,
      }));
      toast.success("AI generated your coupon copy");
    } catch (e) { toast.error(apiError(e, "AI generation failed")); }
    finally { setAiCopyLoading(false); }
  };

  const runAIImage = async () => {
    const p = prompt.trim() || form.headline || form.name;
    if (!p) { toast.error("Add a prompt or headline first"); return; }
    setAiImgLoading(true);
    try {
      const { data } = await api.post("/ai/image", { prompt: p });
      set("image_url", data.image_url);
      toast.success("AI generated a promo visual");
    } catch (e) { toast.error(apiError(e, "Image generation failed")); }
    finally { setAiImgLoading(false); }
  };

  const save = async () => {
    if (!form.name.trim()) { toast.error("Give your coupon a name"); return; }
    setSaving(true);
    try {
      const payload = { ...form, discount_value: Number(form.discount_value) };
      if (id) await api.put(`/coupons/${id}`, payload);
      else await api.post("/coupons", payload);
      qc.invalidateQueries({ queryKey: ["coupons"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
      toast.success(id ? "Coupon updated" : "Coupon created");
      navigate("/coupons");
    } catch (e) { toast.error(apiError(e)); }
    finally { setSaving(false); }
  };

  return (
    <div className="fade-up max-w-[1400px]">
      <button data-testid="back-btn" onClick={() => navigate("/coupons")} className="flex items-center gap-1.5 text-sm text-[#A1A1AA] hover:text-white mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to coupons
      </button>
      <div className="flex items-center justify-between mb-6">
        <h1 className="font-display font-bold text-3xl tracking-tight">{id ? "Edit Coupon" : "New Coupon"}</h1>
        <Button data-testid="save-coupon-btn" onClick={save} disabled={saving} className="btn-primary rounded-md gap-2">
          {saving && <Loader2 className="w-4 h-4 spin" />} {id ? "Save changes" : "Create coupon"}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT: AI + form */}
        <div className="space-y-6">
          {/* AI Copilot */}
          <div className="ai-glow rounded-lg p-5 bg-[#141414]">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-[#CCFF00]" />
              <h3 className="font-display font-bold">AI Copilot</h3>
            </div>
            <Textarea data-testid="ai-prompt-input" value={prompt} onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g. Summer swimwear sale, 25% off, ends Sunday, target new customers"
              className="bg-[#0A0A0A] border-[#27272A] text-white resize-none mb-3" rows={3} />
            <div className="flex gap-2">
              <Button data-testid="ai-generate-copy-btn" onClick={runAICopy} disabled={aiCopyLoading} className="btn-ai rounded-md gap-2 flex-1">
                {aiCopyLoading ? <Loader2 className="w-4 h-4 spin" /> : <Wand2 className="w-4 h-4" />} Generate Copy
              </Button>
              <Button data-testid="ai-generate-image-btn" onClick={runAIImage} disabled={aiImgLoading}
                className="rounded-md gap-2 flex-1 bg-[#0A0A0A] border border-[#CCFF00]/40 text-white hover:bg-[#1E1E1E]">
                {aiImgLoading ? <Loader2 className="w-4 h-4 spin" /> : <ImageIcon className="w-4 h-4" />} Generate Visual
              </Button>
            </div>
          </div>

          {/* Details */}
          <div className="surface rounded-lg p-5 space-y-4">
            <h3 className="font-display font-bold">Offer Details</h3>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Campaign name</Label>
              <Input data-testid="coupon-name-input" value={form.name} onChange={(e) => set("name", e.target.value)}
                className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" placeholder="Summer Swimwear Sale" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-[#A1A1AA]">Type</Label>
                <Select value={form.type} onValueChange={(v) => set("type", v)}>
                  <SelectTrigger data-testid="coupon-type-select" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-[#141414] border-[#27272A] text-white">
                    {Object.entries(TYPE_LABELS).map(([k, v]) => <SelectItem key={k} value={k} className="focus:bg-[#1E1E1E]">{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs text-[#A1A1AA]">Discount value</Label>
                <Input data-testid="coupon-discount-input" type="number" value={form.discount_value}
                  onChange={(e) => set("discount_value", e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-[#A1A1AA]">Code</Label>
                <Input data-testid="coupon-code-input" value={form.code} onChange={(e) => set("code", e.target.value.toUpperCase())}
                  className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white font-mono" placeholder="auto-generated" />
              </div>
              <div>
                <Label className="text-xs text-[#A1A1AA]">State</Label>
                <Select value={form.state} onValueChange={(v) => set("state", v)}>
                  <SelectTrigger data-testid="coupon-state-select" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-[#141414] border-[#27272A] text-white">
                    {["draft", "scheduled", "active", "paused", "expired", "archived"].map((s) =>
                      <SelectItem key={s} value={s} className="focus:bg-[#1E1E1E] capitalize">{s}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Headline</Label>
              <Input data-testid="coupon-headline-input" value={form.headline} onChange={(e) => set("headline", e.target.value)}
                className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" placeholder="Dive Into 25% Off" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Description</Label>
              <Textarea data-testid="coupon-description-input" value={form.description} onChange={(e) => set("description", e.target.value)}
                className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white resize-none" rows={2} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-[#A1A1AA]">CTA</Label>
                <Input data-testid="coupon-cta-input" value={form.cta} onChange={(e) => set("cta", e.target.value)}
                  className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
              </div>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Terms</Label>
              <Textarea data-testid="coupon-terms-input" value={form.terms} onChange={(e) => set("terms", e.target.value)}
                className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white resize-none" rows={2} />
            </div>
          </div>

          {/* Rule builder */}
          <div className="surface rounded-lg p-5 space-y-4">
            <h3 className="font-display font-bold">Rule Builder</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-[#A1A1AA]">Min. cart value</Label>
                <Input data-testid="rule-mincart-input" type="number" value={form.rules.min_cart}
                  onChange={(e) => setRule("min_cart", Number(e.target.value))} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
              </div>
              <div>
                <Label className="text-xs text-[#A1A1AA]">Usage limit (0 = ∞)</Label>
                <Input data-testid="rule-usagelimit-input" type="number" value={form.rules.usage_limit}
                  onChange={(e) => setRule("usage_limit", Number(e.target.value))} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
              </div>
              <div>
                <Label className="text-xs text-[#A1A1AA]">Per-customer limit</Label>
                <Input data-testid="rule-percustomer-input" type="number" value={form.rules.per_customer_limit}
                  onChange={(e) => setRule("per_customer_limit", Number(e.target.value))} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
              </div>
              <div>
                <Label className="text-xs text-[#A1A1AA]">Scope</Label>
                <Select value={form.rules.scope} onValueChange={(v) => setRule("scope", v)}>
                  <SelectTrigger data-testid="rule-scope-select" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-[#141414] border-[#27272A] text-white">
                    <SelectItem value="all" className="focus:bg-[#1E1E1E]">All products</SelectItem>
                    <SelectItem value="product" className="focus:bg-[#1E1E1E]">Specific product</SelectItem>
                    <SelectItem value="category" className="focus:bg-[#1E1E1E]">Category</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 rounded-md bg-[#0A0A0A] border border-[#27272A]">
              <div>
                <div className="text-sm font-medium">Stackable</div>
                <div className="text-xs text-[#71717A]">Allow combining with other coupons</div>
              </div>
              <Switch data-testid="rule-stackable-switch" checked={form.rules.stackable} onCheckedChange={(v) => setRule("stackable", v)} />
            </div>
          </div>
        </div>

        {/* RIGHT: live preview */}
        <div className="lg:sticky lg:top-0 h-fit space-y-4">
          <h3 className="font-display font-bold text-lg">Live Preview</h3>

          {/* Coupon card */}
          <div data-testid="preview-card" className="rounded-xl overflow-hidden border border-[#27272A] bg-gradient-to-br from-[#141414] to-[#0A0A0A]">
            {form.image_url ? (
              <img src={form.image_url} alt="promo" className="w-full h-44 object-cover" />
            ) : (
              <div className="w-full h-44 flex items-center justify-center bg-[#0A0A0A] text-[#3a3a3e] border-b border-[#27272A]">
                <ImageIcon className="w-8 h-8" />
              </div>
            )}
            <div className="p-6">
              <div className="inline-block px-2 py-0.5 rounded bg-[#CCFF00] text-[#0A0A0A] text-xs font-bold mb-3">{discountText(form)}</div>
              <h2 className="font-display font-extrabold text-2xl leading-tight mb-2">{form.headline || "Your headline appears here"}</h2>
              <p className="text-sm text-[#A1A1AA] mb-4">{form.description || "Your promotional description will show here as you type or generate it with AI."}</p>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm bg-[#0A0A0A] border border-dashed border-[#CCFF00]/50 px-3 py-1.5 rounded">{form.code || "CODE"}</span>
                <span className="btn-primary px-4 py-1.5 rounded-md text-sm font-medium">{form.cta || "Claim Offer"}</span>
              </div>
              {form.terms && <p className="text-[10px] text-[#52525B] mt-4">{form.terms}</p>}
            </div>
          </div>

          {/* Email + Social mini previews */}
          <div className="grid grid-cols-2 gap-4">
            <div className="surface rounded-lg p-4">
              <div className="text-xs uppercase tracking-wide text-[#71717A] mb-2">Email</div>
              <div className="font-display font-bold text-sm leading-tight">{form.headline || "Headline"}</div>
              <div className="text-xs text-[#A1A1AA] mt-1 line-clamp-2">{form.description || "Body copy…"}</div>
              <div className="mt-2 inline-block btn-primary text-[10px] px-2 py-1 rounded">{form.cta || "Shop"}</div>
            </div>
            <div className="surface rounded-lg p-4">
              <div className="text-xs uppercase tracking-wide text-[#71717A] mb-2">Social / SMS</div>
              <div className="text-xs text-[#FAFAFA]">🎉 {form.headline || "Big news"} — use code <span className="font-mono text-[#CCFF00]">{form.code || "CODE"}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
