import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Loader2, ArrowLeft, Globe, ExternalLink, Trash2, Save, Rocket, Copy } from "lucide-react";

// ------------ List page ------------
export function Funnels() {
  const nav = useNavigate();
  const [funnels, setFunnels] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [name, setName] = useState("");
  const [tplId, setTplId] = useState("diamond");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const load = () => api.get("/funnels").then((r) => setFunnels(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => {
    load();
    api.get("/funnels/templates").then((r) => setTemplates(r.data.templates)).catch(() => {});
  }, []);
  const create = async () => {
    if (!name) { toast.error("Name required"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/funnels", { name, template_id: tplId });
      toast.success("Funnel created");
      setOpen(false); setName("");
      nav(`/funnels/${data.id}/edit`);
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const del = async (id) => {
    try { await api.delete(`/funnels/${id}`); load(); toast.success("Deleted"); }
    catch (e) { toast.error(apiError(e)); }
  };

  return (
    <div className="fade-up max-w-[1300px]" data-testid="funnels-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Rocket className="w-7 h-7 text-[#CCFF00]" /> Funnel Builder
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Launch luxury landing pages with drop-in coupons and gift cards. Publish to your own custom domain.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button data-testid="new-funnel-btn" className="btn-primary rounded-md gap-2"><Plus className="w-4 h-4" /> New funnel</Button>
          </DialogTrigger>
          <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-lg">
            <DialogHeader><DialogTitle>Start from a template</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div>
                <Label className="text-xs text-[#A1A1AA]">Funnel name</Label>
                <Input data-testid="new-funnel-name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" placeholder="Black Friday 2026" />
              </div>
              <div>
                <Label className="text-xs text-[#A1A1AA]">Template</Label>
                <div className="grid grid-cols-2 gap-2 mt-1" data-testid="funnel-templates-grid">
                  {templates.map((t) => (
                    <button key={t.id} onClick={() => setTplId(t.id)} data-testid={`funnel-tpl-${t.id}`}
                      className={`rounded-md p-3 text-left border ${tplId === t.id ? "border-[#CCFF00] bg-[#0A0A0A]" : "border-[#27272A] hover:border-[#3f3f46]"}`}
                      style={{ background: tplId === t.id ? "#0A0A0A" : t.theme.bg, color: t.theme.fg }}>
                      <div className="text-xs uppercase tracking-widest opacity-60 mb-1" style={{ color: t.theme.accent }}>{t.aesthetic.split(",")[0]}</div>
                      <div className="font-bold" style={{ fontFamily: t.theme.font_display }}>{t.name}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button data-testid="create-funnel-submit" onClick={create} disabled={busy} className="btn-primary rounded-md gap-2">
                {busy && <Loader2 className="w-4 h-4 spin" />} Create funnel
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {funnels.length === 0 ? (
        <div className="surface rounded-lg p-12 text-center">
          <Rocket className="w-10 h-10 mx-auto text-[#3a3a3e] mb-3" />
          <p className="text-[#A1A1AA]">No funnels yet — pick a template to launch your first luxury landing page.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {funnels.map((f) => (
            <div key={f.id} data-testid={`funnel-card-${f.id}`} className="surface rounded-lg p-5 group hover:border-[#CCFF00]/40 transition">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-xs uppercase tracking-widest text-[#71717A]">{f.template_id || "custom"}</div>
                  <div className="font-display font-bold text-lg truncate">{f.name}</div>
                  <div className="text-xs text-[#71717A] mt-0.5">/f/{f.slug}</div>
                </div>
                <span className={`text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded ${f.published ? "bg-emerald-500/15 text-emerald-400" : "bg-white/5 text-[#A1A1AA]"}`}>
                  {f.published ? "Live" : "Draft"}
                </span>
              </div>
              <div className="text-xs text-[#71717A] mt-3 mb-4">
                {f.custom_domain && (
                  <div className="flex items-center gap-1 text-[#CCFF00]"><Globe className="w-3 h-3" /> {f.custom_domain} {f.domain_verified ? "· verified" : "· pending"}</div>
                )}
                <div className="mt-1">{f.blocks?.length || 0} blocks · {f.views || 0} views</div>
              </div>
              <div className="flex gap-2">
                <Button data-testid={`edit-funnel-${f.id}`} onClick={() => nav(`/funnels/${f.id}/edit`)} className="btn-ghost rounded-md text-xs flex-1">Edit</Button>
                {f.published && (
                  <a data-testid={`view-funnel-${f.id}`} href={`/f/${f.slug}`} target="_blank" rel="noopener noreferrer"
                     className="btn-ghost rounded-md text-xs inline-flex items-center gap-1 px-3 py-1.5">
                    <ExternalLink className="w-3 h-3" /> View
                  </a>
                )}
                <button data-testid={`delete-funnel-${f.id}`} onClick={() => del(f.id)} className="text-red-400 hover:bg-red-500/10 rounded-md p-2">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ------------ Editor page ------------
export function FunnelEditor() {
  const { id } = useParams();
  const nav = useNavigate();
  const [funnel, setFunnel] = useState(null);
  const [coupons, setCoupons] = useState([]);
  const [products, setProducts] = useState([]);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [domain, setDomain] = useState("");
  const [verification, setVerification] = useState(null);

  useEffect(() => {
    api.get(`/funnels/${id}`).then((r) => { setFunnel(r.data); setDomain(r.data.custom_domain || ""); }).catch((e) => toast.error(apiError(e)));
    api.get("/coupons?state=all").then((r) => setCoupons(r.data)).catch(() => {});
    api.get("/products").then((r) => setProducts(r.data)).catch(() => {});
  }, [id]);

  if (!funnel) return <div className="text-[#71717A]">Loading…</div>;

  const updateBlock = (bid, patch) => {
    setFunnel((f) => ({ ...f, blocks: f.blocks.map((b) => b.id === bid ? { ...b, props: { ...b.props, ...patch } } : b) }));
  };
  const removeBlock = (bid) => setFunnel((f) => ({ ...f, blocks: f.blocks.filter((b) => b.id !== bid) }));
  const moveBlock = (idx, dir) => {
    const b = [...funnel.blocks]; const j = idx + dir;
    if (j < 0 || j >= b.length) return;
    [b[idx], b[j]] = [b[j], b[idx]]; setFunnel({ ...funnel, blocks: b });
  };
  const addBlock = (type) => {
    const defaults = {
      hero: { eyebrow: "Announcement", headline: "Your headline here", subline: "Add a supporting subline.", cta_label: "Learn more" },
      coupon: { coupon_code: "", label: "Your coupon" },
      giftcard: { template_id: "midnight-onyx", amount: 50, currency: "USD" },
      cta: { headline: "Ready?", cta_label: "Get started" },
      features: { title: "Why us", items: [{ title: "Fast", text: "Blazing." }, { title: "Simple", text: "No friction." }] },
      testimonial: { quote: "The best decision we made.", author: "Happy Customer" },
      faq: { items: [{ q: "Question?", a: "Answer." }] },
      heading: { text: "Section title" },
      paragraph: { text: "Add your paragraph here." },
      image: { url: "", alt: "", caption: "" },
      video: { url: "", poster_url: "", autoplay: false },
      audio: { url: "", label: "Listen" },
      countdown: { ends_at: new Date(Date.now() + 7*24*3600*1000).toISOString(), label: "Offer ends in" },
      product: { product_id: "", coupon_code: "" },
      row: { columns: [
        { blocks: [{ id: crypto.randomUUID(), type: "heading", props: { text: "Left column" } }] },
        { blocks: [{ id: crypto.randomUUID(), type: "heading", props: { text: "Right column" } }] },
      ]},
    };
    setFunnel((f) => ({ ...f, blocks: [...f.blocks, { id: crypto.randomUUID(), type, props: defaults[type] || {} }] }));
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/funnels/${id}`, {
        name: funnel.name, blocks: funnel.blocks, theme: funnel.theme, seo: funnel.seo, slug: funnel.slug,
      });
      toast.success("Saved");
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  const publish = async () => {
    setPublishing(true);
    try {
      await save();
      const { data } = await api.post(`/funnels/${id}/publish`);
      toast.success("Published! " + data.public_url);
    } catch (e) { toast.error(apiError(e)); } finally { setPublishing(false); }
  };

  const setDomainFn = async () => {
    if (!domain) return;
    try {
      const { data } = await api.post(`/funnels/${id}/domain`, { domain });
      setVerification(data.verification);
      toast.success("Domain saved. Add the DNS records shown below.");
    } catch (e) { toast.error(apiError(e)); }
  };

  return (
    <div className="fade-up max-w-[1400px]" data-testid="funnel-editor">
      <div className="flex items-center justify-between mb-5">
        <div>
          <button onClick={() => nav("/funnels")} className="text-xs text-[#71717A] hover:text-white flex items-center gap-1 mb-1">
            <ArrowLeft className="w-3 h-3" /> All funnels
          </button>
          <Input value={funnel.name} onChange={(e) => setFunnel({ ...funnel, name: e.target.value })} data-testid="funnel-name-input"
            className="font-display font-bold text-2xl bg-transparent border-none px-0 h-auto text-white focus-visible:ring-0" />
          <div className="text-xs text-[#71717A]">/f/{funnel.slug} {funnel.published && <span className="text-emerald-400">· Live</span>}</div>
        </div>
        <div className="flex gap-2">
          <Button data-testid="funnel-save" onClick={save} disabled={saving} className="btn-ghost rounded-md gap-2">
            {saving ? <Loader2 className="w-4 h-4 spin" /> : <Save className="w-4 h-4" />} Save
          </Button>
          <Button data-testid="funnel-publish" onClick={publish} disabled={publishing} className="btn-primary rounded-md gap-2">
            {publishing ? <Loader2 className="w-4 h-4 spin" /> : <Rocket className="w-4 h-4" />} {funnel.published ? "Republish" : "Publish"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
        <div className="space-y-3">
          {funnel.blocks.map((b, idx) => (
            <div key={b.id} data-testid={`block-${b.id}`} className="surface rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="text-[10px] uppercase tracking-widest text-[#CCFF00]">{b.type}</div>
                <div className="flex gap-1">
                  <button onClick={() => moveBlock(idx, -1)} className="text-xs text-[#71717A] hover:text-white px-1">↑</button>
                  <button onClick={() => moveBlock(idx, 1)} className="text-xs text-[#71717A] hover:text-white px-1">↓</button>
                  <button onClick={() => removeBlock(b.id)} className="text-red-400 hover:bg-red-500/10 rounded p-1"><Trash2 className="w-3 h-3" /></button>
                </div>
              </div>
              {b.type === "image" && (
                <div className="space-y-2">
                  <Input value={b.props.url || ""} onChange={(e) => updateBlock(b.id, { url: e.target.value })} placeholder="Image URL (or upload via /api/uploads)" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input value={b.props.caption || ""} onChange={(e) => updateBlock(b.id, { caption: e.target.value })} placeholder="Caption (optional)" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <label className="btn-ghost inline-flex items-center gap-2 cursor-pointer rounded-md px-3 py-2 text-xs">
                    Upload image
                    <input type="file" accept="image/*" className="hidden" onChange={async (e) => {
                      const f = e.target.files?.[0]; if (!f) return;
                      const fd = new FormData(); fd.append("file", f);
                      try { const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
                        updateBlock(b.id, { url: `${process.env.REACT_APP_BACKEND_URL}${data.url}` });
                        toast.success("Uploaded");
                      } catch (er) { toast.error(apiError(er)); }
                    }} />
                  </label>
                </div>
              )}
              {b.type === "video" && (
                <div className="space-y-2">
                  <Input value={b.props.url || ""} onChange={(e) => updateBlock(b.id, { url: e.target.value })} placeholder="Video URL (mp4/YouTube/Vimeo)" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input value={b.props.poster_url || ""} onChange={(e) => updateBlock(b.id, { poster_url: e.target.value })} placeholder="Poster image URL (optional)" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <label className="text-xs text-[#A1A1AA] flex items-center gap-2">
                    <input type="checkbox" checked={!!b.props.autoplay} onChange={(e) => updateBlock(b.id, { autoplay: e.target.checked })} /> Autoplay (muted)
                  </label>
                </div>
              )}
              {b.type === "audio" && (
                <div className="space-y-2">
                  <Input value={b.props.url || ""} onChange={(e) => updateBlock(b.id, { url: e.target.value })} placeholder="Audio URL (mp3/wav)" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input value={b.props.label || ""} onChange={(e) => updateBlock(b.id, { label: e.target.value })} placeholder="Label" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
              )}
              {b.type === "countdown" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <div>
                    <Label className="text-xs text-[#A1A1AA]">Countdown ends at</Label>
                    <Input type="datetime-local" value={(b.props.ends_at || "").slice(0, 16)}
                      onChange={(e) => updateBlock(b.id, { ends_at: new Date(e.target.value).toISOString() })}
                      className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  </div>
                  <div>
                    <Label className="text-xs text-[#A1A1AA]">Label</Label>
                    <Input value={b.props.label || ""} onChange={(e) => updateBlock(b.id, { label: e.target.value })} placeholder="Offer ends in" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  </div>
                </div>
              )}
              {b.type === "product" && (
                <div className="space-y-2">
                  <Label className="text-xs text-[#A1A1AA]">Attach a product</Label>
                  <select value={b.props.product_id || ""} onChange={(e) => updateBlock(b.id, { product_id: e.target.value })}
                    data-testid={`block-product-select-${b.id}`}
                    className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                    <option value="">— Select a product —</option>
                    {products.map((pr) => <option key={pr.id} value={pr.id}>{pr.name} · ${pr.price} {pr.currency}</option>)}
                  </select>
                  <Label className="text-xs text-[#A1A1AA] mt-2 block">Optional launch coupon</Label>
                  <select value={b.props.coupon_code || ""} onChange={(e) => updateBlock(b.id, { coupon_code: e.target.value })}
                    data-testid={`block-product-coupon-select-${b.id}`}
                    className="w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                    <option value="">— No coupon —</option>
                    {coupons.map((c) => <option key={c.id} value={c.code}>{c.name} · {c.code}</option>)}
                  </select>
                  <div className="text-[10px] text-[#71717A]">Buy-Now uses your workspace's Stripe checkout.</div>
                </div>
              )}
              {b.type === "row" && (
                <div className="text-xs text-[#71717A]">Row layout — edit inner blocks via JSON below:
                  <textarea value={JSON.stringify(b.props.columns || [], null, 2)}
                    onChange={(e) => { try { updateBlock(b.id, { columns: JSON.parse(e.target.value) }); } catch {} }}
                    rows={8} className="mt-1 w-full bg-[#0A0A0A] border border-[#27272A] text-white rounded-md p-2 text-[11px] font-mono" />
                </div>
              )}
              {b.type === "hero" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <Input value={b.props.eyebrow || ""} onChange={(e) => updateBlock(b.id, { eyebrow: e.target.value })} placeholder="Eyebrow" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input value={b.props.headline || ""} onChange={(e) => updateBlock(b.id, { headline: e.target.value })} placeholder="Headline" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input value={b.props.subline || ""} onChange={(e) => updateBlock(b.id, { subline: e.target.value })} placeholder="Subline" className="bg-[#0A0A0A] border-[#27272A] text-white md:col-span-2" />
                  <Input value={b.props.cta_label || ""} onChange={(e) => updateBlock(b.id, { cta_label: e.target.value })} placeholder="CTA label" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
              )}
              {b.type === "coupon" && (
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Attach a coupon</Label>
                  <select value={b.props.coupon_code || ""} onChange={(e) => updateBlock(b.id, { coupon_code: e.target.value })} data-testid={`block-coupon-select-${b.id}`}
                    className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                    <option value="">— Select a coupon —</option>
                    {coupons.map((c) => <option key={c.id} value={c.code}>{c.name} · {c.code}</option>)}
                  </select>
                </div>
              )}
              {b.type === "giftcard" && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                  <Input value={b.props.template_id || ""} onChange={(e) => updateBlock(b.id, { template_id: e.target.value })} placeholder="Template id" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input type="number" value={b.props.amount || 0} onChange={(e) => updateBlock(b.id, { amount: Number(e.target.value) })} placeholder="Amount" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input value={b.props.currency || "USD"} onChange={(e) => updateBlock(b.id, { currency: e.target.value })} placeholder="USD" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
              )}
              {b.type === "cta" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <Input value={b.props.headline || ""} onChange={(e) => updateBlock(b.id, { headline: e.target.value })} placeholder="Headline" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                  <Input value={b.props.cta_label || ""} onChange={(e) => updateBlock(b.id, { cta_label: e.target.value })} placeholder="CTA label" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
              )}
              {b.type === "testimonial" && (
                <div className="space-y-2">
                  {Array.isArray(b.props.items) ? (
                    <>
                      <Input value={b.props.title || ""} onChange={(e) => updateBlock(b.id, { title: e.target.value })} placeholder="Section title (optional)" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                      <div className="text-xs text-[#71717A]">Edit reviews (advanced JSON):</div>
                      <textarea value={JSON.stringify(b.props.items, null, 2)}
                        data-testid={`block-testimonial-items-${b.id}`}
                        onChange={(e) => { try { updateBlock(b.id, { items: JSON.parse(e.target.value) }); } catch {} }}
                        rows={8} className="w-full bg-[#0A0A0A] border border-[#27272A] text-white rounded-md p-2 text-[11px] font-mono" />
                      <div className="text-[10px] text-[#71717A]">Each item: {`{ quote, author, role, avatar_url }`}. Link to real reviews later — placeholder-only for now.</div>
                    </>
                  ) : (
                    <>
                      <textarea value={b.props.quote || ""} onChange={(e) => updateBlock(b.id, { quote: e.target.value })} rows={2} className="w-full bg-[#0A0A0A] border border-[#27272A] text-white rounded-md p-2 text-sm" placeholder="Quote" />
                      <Input value={b.props.author || ""} onChange={(e) => updateBlock(b.id, { author: e.target.value })} placeholder="Author" className="bg-[#0A0A0A] border-[#27272A] text-white" />
                      <button onClick={() => updateBlock(b.id, { title: "Loved by customers",
                        items: [{ quote: b.props.quote || "", author: b.props.author || "", role: "", avatar_url: "" }] })}
                        className="text-[10px] text-[#CCFF00] hover:underline">Convert to multi-review section →</button>
                    </>
                  )}
                </div>
              )}
              {b.type === "heading" && (
                <Input value={b.props.text || ""} onChange={(e) => updateBlock(b.id, { text: e.target.value })} className="bg-[#0A0A0A] border-[#27272A] text-white" />
              )}
              {b.type === "paragraph" && (
                <textarea value={b.props.text || ""} onChange={(e) => updateBlock(b.id, { text: e.target.value })} rows={3} className="w-full bg-[#0A0A0A] border border-[#27272A] text-white rounded-md p-2 text-sm" />
              )}
              {(b.type === "features" || b.type === "faq") && (
                <div className="text-xs text-[#71717A]">Edit lists in JSON below (advanced):
                  <textarea value={JSON.stringify(b.props.items || [], null, 2)}
                    onChange={(e) => { try { updateBlock(b.id, { items: JSON.parse(e.target.value) }); } catch {} }}
                    rows={6} className="mt-1 w-full bg-[#0A0A0A] border border-[#27272A] text-white rounded-md p-2 text-[11px] font-mono" />
                </div>
              )}
            </div>
          ))}
          <div className="surface rounded-lg p-4">
            <div className="text-xs uppercase tracking-widest text-[#71717A] mb-2">Add a block</div>
            <div className="flex flex-wrap gap-2">
              {["hero", "coupon", "giftcard", "cta", "features", "testimonial", "faq", "heading", "paragraph", "image", "video", "audio", "countdown", "product", "row"].map((t) => (
                <button key={t} onClick={() => addBlock(t)} data-testid={`add-block-${t}`}
                  className="btn-ghost rounded-md text-xs px-3 py-1.5 capitalize">+ {t}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="surface rounded-lg p-4">
            <div className="text-xs uppercase tracking-widest text-[#71717A] mb-2 flex items-center gap-1"><Globe className="w-3 h-3" /> Custom domain</div>
            <Input value={domain} onChange={(e) => setDomain(e.target.value)} placeholder="promos.yourbrand.com" data-testid="funnel-domain-input"
              className="bg-[#0A0A0A] border-[#27272A] text-white mb-2" />
            <Button data-testid="funnel-domain-save" onClick={setDomainFn} className="btn-ghost rounded-md w-full text-xs gap-2">Save domain</Button>
            {(verification || funnel.custom_domain) && (
              <div className="mt-3 space-y-2 text-[11px] text-[#A1A1AA]" data-testid="funnel-dns-instructions">
                <div className="text-white font-medium">DNS records to add:</div>
                {(verification?.cname || { host: funnel.custom_domain, value: "funnels.promoos.app" }) && (
                  <div className="bg-[#0A0A0A] border border-[#27272A] rounded p-2">
                    <div className="text-[10px] uppercase text-[#71717A]">CNAME</div>
                    <div className="font-mono flex justify-between gap-1"><span>{funnel.custom_domain}</span><span>funnels.promoos.app</span></div>
                  </div>
                )}
                <div className="bg-[#0A0A0A] border border-[#27272A] rounded p-2">
                  <div className="text-[10px] uppercase text-[#71717A]">TXT · _promoos-verify</div>
                  <div className="font-mono break-all">{funnel.id}</div>
                </div>
                {funnel.custom_domain && (
                  <Button data-testid="funnel-verify-domain" onClick={async () => {
                    try { const { data } = await api.post(`/funnels/${id}/verify-domain`); toast[data.verified ? "success" : "warning"](data.note); }
                    catch (e) { toast.error(apiError(e)); }
                  }} className="btn-ghost rounded-md w-full text-xs mt-2">Verify DNS</Button>
                )}
              </div>
            )}
          </div>
          <div className="surface rounded-lg p-4">
            <div className="text-xs uppercase tracking-widest text-[#71717A] mb-2">Public URL</div>
            <div className="flex gap-1 items-center">
              <code className="text-xs font-mono text-white truncate flex-1">{window.location.origin}/f/{funnel.slug}</code>
              <button onClick={() => { navigator.clipboard.writeText(`${window.location.origin}/f/${funnel.slug}`); toast.success("Copied"); }} className="p-1.5 rounded hover:bg-white/5"><Copy className="w-3 h-3" /></button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
