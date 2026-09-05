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
import { Sparkles, Wand2, ArrowLeft, Loader2, Image as ImageIcon, Copy as CopyIcon, Trash2, Download } from "lucide-react";

// -------------------------------------------------------------------------
// Bulk unique codes — generate a batch of derived codes for a coupon, select
// them individually, copy/delete/export in bulk. Fixes user report "Bulk Codes
// are not selecting and applying correctly."
// -------------------------------------------------------------------------
function BulkCodesPanel({ cid, parentCode }) {
  const [codes, setCodes] = useState([]);
  const [selected, setSelected] = useState(() => new Set());
  const [count, setCount] = useState(10);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/coupons/${cid}/codes`);
      setCodes(data.codes || []);
    } catch (e) { toast.error(apiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { if (cid) load(); }, [cid]);

  const toggle = (code) => {
    setSelected((s) => {
      const next = new Set(s);
      next.has(code) ? next.delete(code) : next.add(code);
      return next;
    });
  };
  const toggleAll = () => {
    setSelected((s) => (s.size === codes.length ? new Set() : new Set(codes)));
  };
  const generate = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/coupons/${cid}/bulk-codes`, { count: Number(count) });
      toast.success(`Generated ${data.generated} unique codes`);
      load();
    } catch (e) { toast.error(apiError(e)); }
    finally { setBusy(false); }
  };
  const copySelected = async () => {
    const list = Array.from(selected);
    if (!list.length) { toast.error("Select codes first"); return; }
    try {
      await navigator.clipboard.writeText(list.join("\n"));
      toast.success(`Copied ${list.length} codes to clipboard`);
    } catch { toast.error("Clipboard blocked — try Download CSV"); }
  };
  const downloadCsv = () => {
    const list = selected.size ? Array.from(selected) : codes;
    if (!list.length) { toast.error("Nothing to export"); return; }
    const csv = "code\n" + list.join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url; a.download = `${parentCode || "codes"}.csv`; a.click();
    URL.revokeObjectURL(url);
  };
  const deleteSelected = async () => {
    const list = Array.from(selected);
    if (!list.length) { toast.error("Select codes first"); return; }
    if (!window.confirm(`Delete ${list.length} codes? This cannot be undone.`)) return;
    setBusy(true);
    try {
      await api.post(`/coupons/${cid}/codes/delete`, { codes: list });
      toast.success(`Deleted ${list.length} codes`);
      setSelected(new Set());
      load();
    } catch (e) { toast.error(apiError(e)); }
    finally { setBusy(false); }
  };

  const allSelected = selected.size > 0 && selected.size === codes.length;

  return (
    <div className="surface rounded-lg p-5 space-y-3" data-testid="coupon-bulk-codes-panel">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-display font-bold">Bulk unique codes</h3>
          <div className="text-xs text-[#71717A]">One-time-use codes derived from <code className="font-mono">{parentCode || "PARENT"}-*</code>. Each recipient gets their own.</div>
        </div>
        <div className="flex items-center gap-2">
          <Input type="number" min="1" max="500" value={count}
            onChange={(e) => setCount(e.target.value)}
            className="w-20 bg-[#0A0A0A] border-[#27272A] text-white h-9"
            data-testid="bulk-codes-count" />
          <Button data-testid="bulk-codes-generate" onClick={generate} disabled={busy}
            className="btn-primary rounded-md gap-1 h-9">
            {busy ? <Loader2 className="w-3 h-3 spin" /> : <Sparkles className="w-3 h-3" />}
            Generate
          </Button>
        </div>
      </div>
      {codes.length > 0 && (
        <>
          <div className="flex items-center justify-between text-xs">
            <label className="flex items-center gap-2 text-[#A1A1AA] cursor-pointer">
              <input type="checkbox" checked={allSelected} onChange={toggleAll}
                data-testid="bulk-codes-select-all" />
              <span>{selected.size} of {codes.length} selected</span>
            </label>
            <div className="flex items-center gap-1">
              <button onClick={copySelected} disabled={!selected.size}
                data-testid="bulk-codes-copy"
                className="btn-ghost rounded-md text-[11px] px-2 py-1 disabled:opacity-40 flex items-center gap-1">
                <CopyIcon className="w-3 h-3" /> Copy
              </button>
              <button onClick={downloadCsv}
                data-testid="bulk-codes-export"
                className="btn-ghost rounded-md text-[11px] px-2 py-1 flex items-center gap-1">
                <Download className="w-3 h-3" /> CSV
              </button>
              <button onClick={deleteSelected} disabled={!selected.size || busy}
                data-testid="bulk-codes-delete"
                className="btn-ghost rounded-md text-[11px] px-2 py-1 disabled:opacity-40 text-red-400 flex items-center gap-1">
                <Trash2 className="w-3 h-3" /> Delete
              </button>
            </div>
          </div>
          <div className="max-h-72 overflow-y-auto rounded-md border border-[#27272A] bg-[#0A0A0A] divide-y divide-[#1a1a1c]">
            {codes.map((code) => (
              <label key={code} className="flex items-center gap-2 px-3 py-2 text-xs font-mono hover:bg-white/[0.03] cursor-pointer"
                data-testid={`bulk-code-row-${code}`}>
                <input type="checkbox" checked={selected.has(code)}
                  onChange={() => toggle(code)}
                  data-testid={`bulk-code-check-${code}`} />
                <span className="flex-1">{code}</span>
                <button onClick={(e) => { e.preventDefault(); navigator.clipboard.writeText(code); toast.success("Copied"); }}
                  className="text-[10px] text-[#71717A] hover:text-white uppercase tracking-widest">copy</button>
              </label>
            ))}
          </div>
        </>
      )}
      {loading && <div className="text-xs text-[#71717A]">Loading codes…</div>}
      {!loading && codes.length === 0 && (
        <div className="text-xs text-[#71717A] text-center py-4">No unique codes yet. Generate a batch above.</div>
      )}
    </div>
  );
}

const empty = {
  name: "", type: "percentage", discount_value: 25, code: "",
  headline: "", description: "", terms: "", cta: "Claim Offer", state: "draft",
  image_url: "",
  design: { bg: "", accent: "", fg: "", badge_bg: "", badge_fg: "" },
  payment_link: "",
  codes: [],
  rules: { min_cart: 0, scope: "all", scope_value: "", usage_limit: 0, per_customer_limit: 1, stackable: false, start_date: null, end_date: null, referral_enabled: false, referral_credit_pct: 10 },
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
  const [marketPresets, setMarketPresets] = useState([]);

  useEffect(() => {
    if (id) {
      api.get(`/coupons/${id}`).then((r) => {
        const c = r.data;
        setForm({ ...empty, ...c, rules: { ...empty.rules, ...c.rules } });
      }).catch((e) => toast.error(apiError(e)));
    }
    api.get("/preset-packs?scope=coupon").then((r) => {
      const flat = (r.data || []).flatMap((pack) =>
        (pack.presets || []).map((p) => ({ ...p, packName: pack.name })));
      setMarketPresets(flat);
    }).catch(() => {});
  }, [id]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setRule = (k, v) => setForm((f) => ({ ...f, rules: { ...f.rules, [k]: v } }));
  const setDesign = (k, v) => setForm((f) => ({ ...f, design: { ...(f.design || {}), [k]: v } }));

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

  const runAIImage = async (presetOverride) => {
    const basePrompt = presetOverride
      ? presetOverride.prompt
      : (prompt.trim() || form.headline || form.name);
    if (!basePrompt) { toast.error("Add a prompt or headline first"); return; }
    setAiImgLoading(true);
    try {
      const { data } = await api.post("/ai/image", { prompt: basePrompt });
      set("image_url", data.image_url);
      toast.success(presetOverride ? `${presetOverride.label} visual generated` : "AI generated a promo visual");
    } catch (e) { toast.error(apiError(e, "Image generation failed")); }
    finally { setAiImgLoading(false); }
  };

  const IMAGE_PRESETS = [
    { key: "champagne", label: "Champagne", accent: "#E7CB8E",
      prompt: "elegant champagne gold luxury promotional banner background, soft warm bokeh, silk texture, premium boutique, cinematic lighting, no text" },
    { key: "neon", label: "Neon", accent: "#CCFF00",
      prompt: "vibrant neon night promotional banner, electric magenta and cyan glow, glossy reflections, futuristic cyberpunk aesthetic, high contrast, no text" },
    { key: "minimal", label: "Minimal", accent: "#111111",
      prompt: "minimal off-white paper promotional banner, subtle warm grain, tasteful architectural shadow, editorial premium, matte finish, no text" },
    { key: "botanical", label: "Botanical", accent: "#7C9A5F",
      prompt: "soft botanical greenery watercolor promotional banner, sage and olive palette, hand-painted leaves, airy natural light, no text" },
    { key: "midnight", label: "Midnight", accent: "#8B5CF6",
      prompt: "deep midnight blue promotional banner with starfield, aurora streaks in violet and teal, cinematic astro aesthetic, premium, no text" },
  ];

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
              <Button data-testid="ai-generate-image-btn" onClick={() => runAIImage()} disabled={aiImgLoading}
                className="rounded-md gap-2 flex-1 bg-[#0A0A0A] border border-[#CCFF00]/40 text-white hover:bg-[#1E1E1E]">
                {aiImgLoading ? <Loader2 className="w-4 h-4 spin" /> : <ImageIcon className="w-4 h-4" />} Generate Visual
              </Button>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-3" data-testid="coupon-style-presets">
              {[...IMAGE_PRESETS, ...marketPresets].map((p) => (
                <button
                  key={`${p.packName || 'builtin'}-${p.key}`}
                  onClick={() => runAIImage(p)}
                  disabled={aiImgLoading}
                  data-testid={`coupon-preset-${p.key}`}
                  title={p.packName ? `${p.packName} · ${p.label}` : `One-tap ${p.label} style`}
                  className="text-[10px] tracking-widest uppercase inline-flex items-center gap-1 px-2 py-1 rounded-full border border-[#27272A] hover:border-[#CCFF00] hover:text-[#CCFF00] transition-colors disabled:opacity-40"
                >
                  <span className="w-2 h-2 rounded-full" style={{ background: p.accent }} />
                  {p.label}
                </button>
              ))}
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
            <div className="p-3 rounded-md bg-[#0A0A0A] border border-[#27272A] space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium">Referral program</div>
                  <div className="text-xs text-[#71717A]">Reward customers who share this coupon</div>
                </div>
                <Switch data-testid="rule-referral-switch" checked={!!form.rules.referral_enabled} onCheckedChange={(v) => setRule("referral_enabled", v)} />
              </div>
              {form.rules.referral_enabled && (
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Referrer credit %</Label>
                  <Input
                    data-testid="rule-referral-pct"
                    type="number" min={1} max={100}
                    value={form.rules.referral_credit_pct}
                    onChange={(e) => setRule("referral_credit_pct", Number(e.target.value))}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Custom design — per-coupon color overrides */}
          <div className="surface rounded-lg p-5 space-y-3" data-testid="coupon-design-panel">
            <h3 className="font-display font-bold">Custom Design</h3>
            <div className="text-xs text-[#71717A]">Optional. Tint every section of this coupon — card background, accent, text, badge, and add a graphic behind everything (photo, gradient, pattern URL, or Unsplash image).</div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                ["bg", "Card BG"],
                ["accent", "Accent"],
                ["fg", "Text"],
                ["badge_bg", "Badge BG"],
                ["badge_fg", "Badge Text"],
              ].map(([k, label]) => (
                <div key={k}>
                  <Label className="text-[10px] text-[#71717A] uppercase tracking-widest">{label}</Label>
                  <div className="flex items-center gap-1 mt-1">
                    <input type="color" value={form.design?.[k] || "#0A0A0A"}
                      onChange={(e) => setDesign(k, e.target.value)}
                      data-testid={`coupon-design-${k}`}
                      className="h-9 w-10 rounded bg-[#0A0A0A] border border-[#27272A] cursor-pointer" />
                    <Input value={form.design?.[k] || ""} onChange={(e) => setDesign(k, e.target.value)}
                      placeholder="—" className="bg-[#0A0A0A] border-[#27272A] text-white h-9 text-xs font-mono" />
                    {form.design?.[k] ? (
                      <button onClick={() => setDesign(k, "")} className="text-[9px] text-[#71717A] hover:text-red-400 px-1">×</button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
            {/* Background graphic URL — a photo/pattern/gradient painted behind the coupon card. */}
            <div className="pt-2 border-t border-[#27272A]">
              <Label className="text-[10px] text-[#71717A] uppercase tracking-widest">Background graphic</Label>
              <div
                data-testid="coupon-bg-dropzone"
                onDragOver={(e) => { e.preventDefault(); e.currentTarget.dataset.hover = "1"; }}
                onDragLeave={(e) => { delete e.currentTarget.dataset.hover; }}
                onDrop={async (e) => {
                  e.preventDefault();
                  delete e.currentTarget.dataset.hover;
                  const file = e.dataTransfer?.files?.[0];
                  if (!file || !file.type.startsWith("image/")) { toast.error("Drop an image file"); return; }
                  const fd = new FormData(); fd.append("file", file);
                  try {
                    const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
                    setDesign("bg_image", `${process.env.REACT_APP_BACKEND_URL}${data.url}`);
                    toast.success("Background uploaded");
                  } catch (er) { toast.error(apiError(er)); }
                }}
                className="mt-1 border-2 border-dashed border-[#27272A] hover:border-[#CCFF00] rounded-md p-4 text-center text-xs text-[#71717A] transition-colors data-[hover='1']:border-[#CCFF00] data-[hover='1']:bg-[#CCFF00]/5"
              >
                {form.design?.bg_image ? (
                  <div className="flex items-center gap-3">
                    <div className="w-20 h-14 rounded overflow-hidden border border-[#27272A]"
                      style={{ backgroundImage: `url(${form.design.bg_image})`, backgroundSize: "cover", backgroundPosition: "center" }} />
                    <div className="flex-1 text-left">
                      <div className="text-white text-[11px] truncate">{form.design.bg_image}</div>
                      <div className="text-[10px] text-[#71717A]">Drop a new image to replace, or clear below</div>
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="text-white text-sm mb-1">Drop your hero image here</div>
                    <div>or paste a URL below · JPG/PNG/WebP/SVG · max 10MB</div>
                    <label className="btn-ghost inline-flex items-center gap-2 cursor-pointer rounded-md px-3 py-1.5 text-[10px] mt-2 uppercase tracking-widest" data-testid="coupon-bg-upload-btn">
                      Choose file
                      <input type="file" accept="image/*" className="hidden" onChange={async (e) => {
                        const f = e.target.files?.[0]; if (!f) return;
                        const fd = new FormData(); fd.append("file", f);
                        try {
                          const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
                          setDesign("bg_image", `${process.env.REACT_APP_BACKEND_URL}${data.url}`);
                          toast.success("Background uploaded");
                        } catch (er) { toast.error(apiError(er)); }
                      }} />
                    </label>
                  </div>
                )}
              </div>
              <Input value={form.design?.bg_image || ""} onChange={(e) => setDesign("bg_image", e.target.value)}
                placeholder="https://images.unsplash.com/photo-… or your own image URL"
                data-testid="coupon-design-bg_image"
                className="mt-2 bg-[#0A0A0A] border-[#27272A] text-white text-xs font-mono" />
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-2">
                {[
                  { name: "Confetti", url: "https://images.unsplash.com/photo-1513151233558-d860c5398176?auto=format&fit=crop&w=1200&q=60" },
                  { name: "Neon", url: "https://images.unsplash.com/photo-1620121692029-d088224ddc74?auto=format&fit=crop&w=1200&q=60" },
                  { name: "Marble", url: "https://images.unsplash.com/photo-1618764400608-9e7115eede40?auto=format&fit=crop&w=1200&q=60" },
                  { name: "Sunset", url: "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=60" },
                ].map((preset) => (
                  <button key={preset.name} type="button"
                    onClick={() => setDesign("bg_image", preset.url)}
                    data-testid={`coupon-design-bg_image-preset-${preset.name}`}
                    className="rounded-md h-14 overflow-hidden border border-[#27272A] hover:border-[#CCFF00] transition relative"
                    style={{ backgroundImage: `url(${preset.url})`, backgroundSize: "cover", backgroundPosition: "center" }}>
                    <span className="absolute inset-x-0 bottom-0 text-[10px] text-center py-0.5 bg-black/60 text-white">{preset.name}</span>
                  </button>
                ))}
              </div>
              {form.design?.bg_image ? (
                <button type="button" onClick={() => setDesign("bg_image", "")}
                  className="text-[10px] text-[#71717A] hover:text-red-400 mt-2">Clear background image</button>
              ) : null}
            </div>
          </div>

          {/* Payment Link — attach a Stripe hosted checkout so customers can buy with this discount */}
          <div className="surface rounded-lg p-5 space-y-3" data-testid="coupon-payment-panel">
            <h3 className="font-display font-bold">Stripe Payment Link</h3>
            <div className="text-xs text-[#71717A]">Paste a Stripe hosted <a href="https://dashboard.stripe.com/payment-links" target="_blank" rel="noreferrer" className="text-[#CCFF00] underline">Payment Link</a> and this coupon will show a "Buy now" button on the public page. Configure the discount inside your Stripe Payment Link so the price applied at checkout matches this coupon.</div>
            <Input value={form.payment_link || ""}
              onChange={(e) => set("payment_link", e.target.value)}
              placeholder="https://buy.stripe.com/…"
              className="bg-[#0A0A0A] border-[#27272A] text-white font-mono text-xs"
              data-testid="coupon-payment-link" />
            {form.payment_link ? (
              <div className="text-[10px] text-[#22C55E]">✓ Ready — customers can now pay with this coupon.</div>
            ) : null}
          </div>

          {/* Bulk unique codes — generate a batch of unique codes derived from the parent code */}
          {id ? <BulkCodesPanel cid={id} parentCode={form.code} /> : (
            <div className="surface rounded-lg p-5 space-y-2" data-testid="coupon-bulk-codes-placeholder">
              <h3 className="font-display font-bold">Bulk unique codes</h3>
              <div className="text-xs text-[#71717A]">Save this coupon first, then generate bulk unique codes here.</div>
            </div>
          )}
        </div>

        {/* RIGHT: live preview */}
        <div className="lg:sticky lg:top-0 h-fit space-y-4">
          <h3 className="font-display font-bold text-lg">Live Preview</h3>

          {/* Coupon card */}
          <div data-testid="preview-card" className="rounded-xl overflow-hidden border border-[#27272A]"
            style={{
              background: form.design?.bg || undefined,
              color: form.design?.fg || undefined,
            }}>
            {!form.design?.bg && (
              <div className="absolute inset-0 pointer-events-none rounded-xl bg-gradient-to-br from-[#141414] to-[#0A0A0A]" style={{ zIndex: -1 }} />
            )}
            {form.image_url ? (
              <img src={form.image_url} alt="promo" className="w-full h-44 object-cover" />
            ) : (
              <div className="w-full h-44 flex items-center justify-center bg-[#0A0A0A] text-[#3a3a3e] border-b border-[#27272A]">
                <ImageIcon className="w-8 h-8" />
              </div>
            )}
            <div className="p-6" style={form.design?.bg ? { background: form.design.bg } : undefined}>
              <div className="inline-block px-2 py-0.5 rounded text-xs font-bold mb-3"
                style={{
                  background: form.design?.badge_bg || "#CCFF00",
                  color: form.design?.badge_fg || "#0A0A0A",
                }}>{discountText(form)}</div>
              <h2 className="font-display font-extrabold text-2xl leading-tight mb-2"
                style={form.design?.fg ? { color: form.design.fg } : undefined}>
                {form.headline || "Your headline appears here"}
              </h2>
              <p className="text-sm mb-4"
                style={{ color: form.design?.fg ? `${form.design.fg}CC` : "#A1A1AA" }}>
                {form.description || "Your promotional description will show here as you type or generate it with AI."}
              </p>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm bg-[#0A0A0A] border border-dashed px-3 py-1.5 rounded"
                  style={{ borderColor: `${form.design?.accent || "#CCFF00"}80` }}>
                  {form.code || "CODE"}
                </span>
                <span className="px-4 py-1.5 rounded-md text-sm font-medium"
                  style={{
                    background: form.design?.accent || "#CCFF00",
                    color: form.design?.bg || "#0A0A0A",
                  }}>{form.cta || "Claim Offer"}</span>
              </div>
              {form.terms && <p className="text-[10px] mt-4" style={{ color: form.design?.fg ? `${form.design.fg}66` : "#52525B" }}>{form.terms}</p>}
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
