import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sparkles, Wand2, Loader2, Save, ArrowLeft, Palette, Image as ImageIcon } from "lucide-react";

const CARD_WIDTH = 420;
const CARD_HEIGHT = 260;

function CardPreview({ tpl, design, small }) {
  const bg = design?.background || tpl.background;
  const style = bg.type === "gradient"
    ? { background: bg.value }
    : bg.type === "image"
    ? { backgroundImage: `url(${bg.value})`, backgroundSize: "cover", backgroundPosition: "center" }
    : { background: bg.value };
  const accent = design?.accent || tpl.accent;
  const fg = design?.text_color || tpl.text_color;
  const font = design?.font || tpl.font;
  return (
    <div
      className="relative rounded-2xl overflow-hidden shadow-2xl"
      style={{ width: small ? 240 : CARD_WIDTH, height: small ? 150 : CARD_HEIGHT, ...style, fontFamily: font, color: fg }}
      data-testid="giftcard-preview"
    >
      <div className="absolute inset-0 p-6 flex flex-col justify-between">
        <div className="flex items-center justify-between">
          <div className="text-[10px] tracking-[0.2em] uppercase opacity-70" style={{ color: accent }}>Gift Card</div>
          {design?.logo_url && <img src={design.logo_url.startsWith("/api/") ? `${process.env.REACT_APP_BACKEND_URL}${design.logo_url}` : design.logo_url} alt="" className="h-6 opacity-90" />}
        </div>
        <div>
          <div className={`font-bold ${small ? "text-lg" : "text-2xl"} leading-tight mb-1`}>{design?.headline || tpl.headline}</div>
          <div className={`${small ? "text-xs" : "text-sm"} opacity-80`}>{design?.subline || tpl.subline}</div>
        </div>
      </div>
      <div className="absolute bottom-3 right-4 text-[10px] tracking-widest uppercase font-mono opacity-60">
        {design?.code || "GC-XXXXXXXX"}
      </div>
    </div>
  );
}

export default function GiftCardStudio() {
  const nav = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [category, setCategory] = useState("all");
  const [selected, setSelected] = useState(null);
  const [design, setDesign] = useState(null);
  const [amount, setAmount] = useState(50);
  const [currency, setCurrency] = useState("USD");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [recipientName, setRecipientName] = useState("");
  const [saving, setSaving] = useState(false);
  const [aiBusy, setAiBusy] = useState(null);
  const [marketPresets, setMarketPresets] = useState([]);

  useEffect(() => {
    api.get("/giftcard-templates").then((r) => {
      setTemplates(r.data.templates);
      setCategories(r.data.categories);
    }).catch((e) => toast.error(apiError(e)));
    api.get("/preset-packs?scope=gift_card").then((r) => {
      const flat = (r.data || []).flatMap((pack) =>
        (pack.presets || []).map((p) => ({ ...p, packName: pack.name })));
      setMarketPresets(flat);
    }).catch(() => {});
  }, []);

  const pick = (tpl) => {
    setSelected(tpl);
    setDesign({
      headline: tpl.headline, subline: tpl.subline,
      background: tpl.background, accent: tpl.accent,
      text_color: tpl.text_color, font: tpl.font, logo_url: null,
    });
  };

  const regen = async (field, promptOverride) => {
    setAiBusy(promptOverride ? `preset:${promptOverride.key}` : field);
    try {
      const { data } = await api.post("/giftcards/regenerate", {
        field, template_id: selected.id,
        current_headline: design.headline, current_subline: design.subline,
        occasion: selected.category,
        prompt: promptOverride ? promptOverride.prompt : undefined,
      });
      if (field === "background" || field === "image_bg") {
        setDesign((d) => ({ ...d, background: data.value }));
        if (promptOverride?.accent) setDesign((d) => ({ ...d, accent: promptOverride.accent }));
      } else {
        setDesign((d) => ({ ...d, [field]: data.value }));
      }
      toast.success(promptOverride ? `${promptOverride.label} style applied` : `AI regenerated ${field}`);
    } catch (e) { toast.error(apiError(e)); } finally { setAiBusy(null); }
  };

  const IMAGE_PRESETS = [
    { key: "champagne", label: "Champagne", accent: "#E7CB8E",
      prompt: "elegant champagne gold luxury gradient background, soft warm golden bokeh, silk texture, premium boutique, cinematic lighting, no text" },
    { key: "neon", label: "Neon", accent: "#CCFF00",
      prompt: "vibrant neon night background, electric magenta and cyan glow, glossy reflections, futuristic cyberpunk aesthetic, high contrast, no text" },
    { key: "minimal", label: "Minimal", accent: "#111111",
      prompt: "minimal off-white paper background, subtle warm grain, tasteful architectural shadow, editorial premium, matte finish, no text" },
    { key: "botanical", label: "Botanical", accent: "#7C9A5F",
      prompt: "soft botanical greenery watercolor background, sage and olive palette, hand-painted leaves at edges, airy natural light, no text" },
    { key: "midnight", label: "Midnight", accent: "#8B5CF6",
      prompt: "deep midnight blue background with starfield, aurora streaks in violet and teal, cinematic astro aesthetic, premium, no text" },
  ];

  const uploadLogo = async (file) => {
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setDesign((d) => ({ ...d, logo_url: data.url }));
      toast.success("Logo added");
    } catch (e) { toast.error(apiError(e)); }
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.post("/giftcards/design", {
        template_id: selected.id, amount: Number(amount), currency,
        recipient_email: recipientEmail || null,
        recipient_name: recipientName || null,
        headline: design.headline, subline: design.subline,
        background_override: design.background, accent_override: design.accent,
        font_override: design.font, logo_url: design.logo_url,
      });
      toast.success(`Gift card created: ${data.code}`);
      nav("/gift-cards");
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  const filtered = category === "all" ? templates : templates.filter((t) => t.category === category);

  if (!selected) {
    return (
      <div className="fade-up max-w-[1400px]" data-testid="giftcard-studio-gallery">
        <div className="flex items-center justify-between mb-6">
          <div>
            <button onClick={() => nav("/gift-cards")} className="text-xs text-[#71717A] hover:text-white flex items-center gap-1 mb-2">
              <ArrowLeft className="w-3 h-3" /> Back to gift cards
            </button>
            <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
              <Palette className="w-7 h-7 text-[#CCFF00]" /> Gift Card Studio
            </h1>
            <p className="text-sm text-[#A1A1AA] mt-1">Pick a design. Then customize text, colors, background — or let AI Copilot generate anything.</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-1 mb-5" data-testid="giftcard-categories">
          <button onClick={() => setCategory("all")} data-testid="gc-cat-all"
            className={`px-3 py-1.5 rounded-md text-xs uppercase tracking-wider ${category === "all" ? "bg-white text-black" : "text-[#A1A1AA] hover:text-white"}`}>All</button>
          {categories.map((c) => (
            <button key={c} onClick={() => setCategory(c)} data-testid={`gc-cat-${c}`}
              className={`px-3 py-1.5 rounded-md text-xs uppercase tracking-wider capitalize ${category === c ? "bg-white text-black" : "text-[#A1A1AA] hover:text-white"}`}>{c}</button>
          ))}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="giftcard-templates-grid">
          {filtered.map((tpl) => (
            <button key={tpl.id} onClick={() => pick(tpl)} data-testid={`gc-tpl-${tpl.id}`}
              className="text-left group focus:outline-none">
              <CardPreview tpl={tpl} />
              <div className="mt-2 flex items-center justify-between">
                <div className="text-sm font-medium">{tpl.name}</div>
                <div className="text-[10px] uppercase tracking-widest text-[#71717A]">{tpl.category}</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="fade-up max-w-[1400px]" data-testid="giftcard-studio-editor">
      <button onClick={() => setSelected(null)} className="text-xs text-[#71717A] hover:text-white flex items-center gap-1 mb-3" data-testid="editor-back">
        <ArrowLeft className="w-3 h-3" /> Back to gallery
      </button>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div>
          <div className="text-xs uppercase tracking-widest text-[#71717A] mb-3">Live preview</div>
          <CardPreview tpl={selected} design={design} />
          <div className="mt-4 text-xs text-[#71717A]">Template: <span className="text-white">{selected.name}</span></div>
        </div>
        <div className="space-y-5">
          <div>
            <div className="flex items-center justify-between mb-1">
              <Label className="text-xs text-[#A1A1AA]">Headline</Label>
              <button onClick={() => regen("headline")} disabled={aiBusy === "headline"} data-testid="regen-headline"
                className="text-[10px] tracking-widest uppercase text-[#CCFF00] flex items-center gap-1 hover:opacity-80">
                {aiBusy === "headline" ? <Loader2 className="w-3 h-3 spin" /> : <Wand2 className="w-3 h-3" />} AI regenerate
              </button>
            </div>
            <Input data-testid="gc-headline-input" value={design.headline} onChange={(e) => setDesign((d) => ({ ...d, headline: e.target.value }))} className="bg-[#0A0A0A] border-[#27272A] text-white" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <Label className="text-xs text-[#A1A1AA]">Subline</Label>
              <button onClick={() => regen("subline")} disabled={aiBusy === "subline"} data-testid="regen-subline"
                className="text-[10px] tracking-widest uppercase text-[#CCFF00] flex items-center gap-1 hover:opacity-80">
                {aiBusy === "subline" ? <Loader2 className="w-3 h-3 spin" /> : <Wand2 className="w-3 h-3" />} AI regenerate
              </button>
            </div>
            <Input data-testid="gc-subline-input" value={design.subline} onChange={(e) => setDesign((d) => ({ ...d, subline: e.target.value }))} className="bg-[#0A0A0A] border-[#27272A] text-white" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <Label className="text-xs text-[#A1A1AA]">Background</Label>
              <button onClick={() => regen("image_bg")} disabled={aiBusy === "image_bg"} data-testid="regen-background"
                className="text-[10px] tracking-widest uppercase text-[#CCFF00] flex items-center gap-1 hover:opacity-80">
                {aiBusy === "image_bg" ? <Loader2 className="w-3 h-3 spin" /> : <Sparkles className="w-3 h-3" />} AI generate image
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5 mb-2" data-testid="gc-style-presets">
              {[...IMAGE_PRESETS, ...marketPresets].map((p) => {
                const busy = aiBusy === `preset:${p.key}`;
                const anyBusy = !!aiBusy;
                return (
                  <button
                    key={`${p.packName || 'builtin'}-${p.key}`}
                    onClick={() => regen("image_bg", p)}
                    disabled={anyBusy}
                    data-testid={`preset-${p.key}`}
                    title={p.packName ? `${p.packName} · ${p.label}` : `One-tap ${p.label} style`}
                    className="text-[10px] tracking-widest uppercase inline-flex items-center gap-1 px-2 py-1 rounded-full border border-[#27272A] hover:border-[#CCFF00] hover:text-[#CCFF00] transition-colors disabled:opacity-40"
                  >
                    <span className="w-2 h-2 rounded-full" style={{ background: p.accent }} />
                    {busy ? <Loader2 className="w-3 h-3 spin" /> : null}
                    {p.label}
                  </button>
                );
              })}
            </div>
            <div className="flex items-center gap-2 mb-2">
              <Input type="color" value={design.background?.type === "solid" ? design.background.value : "#141414"}
                data-testid="gc-solid-color"
                onChange={(e) => setDesign((d) => ({ ...d, background: { type: "solid", value: e.target.value } }))}
                className="w-14 h-10 p-1 bg-[#0A0A0A] border-[#27272A]" />
              <button className="btn-ghost rounded-md text-xs px-3 py-1.5" onClick={() => setDesign((d) => ({ ...d, background: selected.background }))} data-testid="reset-bg">
                Reset to template
              </button>
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Accent color</Label>
            <div className="flex items-center gap-2 mt-1">
              <Input type="color" value={design.accent} onChange={(e) => setDesign((d) => ({ ...d, accent: e.target.value }))} data-testid="gc-accent" className="w-14 h-10 p-1 bg-[#0A0A0A] border-[#27272A]" />
              <Input value={design.accent} onChange={(e) => setDesign((d) => ({ ...d, accent: e.target.value }))} className="flex-1 bg-[#0A0A0A] border-[#27272A] text-white font-mono text-xs" />
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA] flex items-center gap-1"><ImageIcon className="w-3 h-3" /> Logo</Label>
            <label className="btn-ghost mt-1 inline-flex items-center gap-2 cursor-pointer rounded-md px-3 py-2 text-xs" data-testid="gc-logo-upload">
              Upload logo
              <input type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0])} />
            </label>
          </div>
          <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[#27272A]">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Amount</Label>
              <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} data-testid="gc-studio-amount" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Currency</Label>
              <Input value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} data-testid="gc-studio-currency" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Recipient email (opt)</Label>
              <Input value={recipientEmail} onChange={(e) => setRecipientEmail(e.target.value)} data-testid="gc-studio-email" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Recipient name (opt)</Label>
              <Input value={recipientName} onChange={(e) => setRecipientName(e.target.value)} data-testid="gc-studio-name" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
            </div>
          </div>
          <Button onClick={save} disabled={saving} data-testid="gc-save" className="btn-primary rounded-md w-full gap-2 mt-4">
            {saving ? <Loader2 className="w-4 h-4 spin" /> : <Save className="w-4 h-4" />} Create gift card
          </Button>
        </div>
      </div>
    </div>
  );
}
