import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  ArrowLeft, Save, Send, Trash2, Plus, ChevronUp, ChevronDown, Loader2,
  Heading, Type, Image as ImageIcon, MousePointerClick, Ticket, Gift, Rocket, Minus, Share2, Users, Sparkles, Upload,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";

const BLOCK_LIB = [
  { t: "heading", label: "Heading", icon: Heading, defaults: { level: "h2", text: "Section title" } },
  { t: "text", label: "Text", icon: Type, defaults: { text: "Write a paragraph…" } },
  { t: "image", label: "Image", icon: ImageIcon, defaults: { url: "", alt: "" } },
  { t: "button", label: "Button", icon: MousePointerClick, defaults: { label: "Learn more", url: "https://" } },
  { t: "coupon", label: "Coupon", icon: Ticket, defaults: { code: "" } },
  { t: "giftcard", label: "Gift card", icon: Gift, defaults: { giftcard_id: "" } },
  { t: "funnel", label: "Funnel", icon: Rocket, defaults: { slug: "" } },
  { t: "subscribe_form", label: "Subscribe form", icon: Users, defaults: {} },
  { t: "referral_cta", label: "Referral CTA", icon: Share2, defaults: {} },
  { t: "divider", label: "Divider", icon: Minus, defaults: {} },
];

export default function NewsletterPostEditor() {
  const { pubId, postId } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [saving, setSaving] = useState(false);
  const [sendTo, setSendTo] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const [aiBrief, setAiBrief] = useState("");
  const [aiBusy, setAiBusy] = useState(false);

  const toggleChannel = (ch) => {
    setPost((p) => {
      const cur = p.channels || ["email"];
      const next = cur.includes(ch) ? cur.filter((c) => c !== ch) : [...cur, ch];
      return { ...p, channels: next.length ? next : ["email"] };
    });
  };

  useEffect(() => {
    api.get(`/newsletter/publications/${pubId}/posts/${postId}`)
      .then((r) => setPost(r.data)).catch((e) => toast.error(apiError(e)));
  }, [pubId, postId]);

  const set = (k, v) => setPost((p) => ({ ...p, [k]: v }));
  const setBlock = (i, props) =>
    setPost((p) => ({ ...p, blocks: p.blocks.map((b, j) => j === i ? { ...b, props: { ...b.props, ...props } } : b) }));
  const addBlock = (t) => {
    const cfg = BLOCK_LIB.find((x) => x.t === t);
    setPost((p) => ({ ...p, blocks: [...p.blocks, { id: Math.random().toString(36).slice(2, 8), type: t, props: { ...cfg.defaults } }] }));
  };
  const removeBlock = (i) => setPost((p) => ({ ...p, blocks: p.blocks.filter((_, j) => j !== i) }));
  const moveBlock = (i, dir) => setPost((p) => {
    const j = i + dir; if (j < 0 || j >= p.blocks.length) return p;
    const arr = [...p.blocks]; [arr[i], arr[j]] = [arr[j], arr[i]];
    return { ...p, blocks: arr };
  });

  const save = async () => {
    setSaving(true);
    try {
      await api.put(`/newsletter/publications/${pubId}/posts/${postId}`,
        { title: post.title, subtitle: post.subtitle, blocks: post.blocks,
          channels: post.channels, sms_body: post.sms_body });
      toast.success("Draft saved");
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };
  const sendTest = async () => {
    if (!sendTo.includes("@")) { toast.error("Enter a test email"); return; }
    try {
      await save();
      await api.post(`/newsletter/publications/${pubId}/posts/${postId}/send-test`, { email: sendTo });
      toast.success(`Test sent to ${sendTo}`);
    } catch (e) { toast.error(apiError(e)); }
  };
  const sendNow = async () => {
    if (!window.confirm("Send to ALL active subscribers now?")) return;
    try {
      await save();
      await api.post(`/newsletter/publications/${pubId}/posts/${postId}/send-now`);
      toast.success("Queued to send");
      navigate(`/newsletters/${pubId}`);
    } catch (e) { toast.error(apiError(e)); }
  };

  const draftWithAI = async () => {
    if (!aiBrief.trim()) { toast.error("Give AI a one-line brief"); return; }
    setAiBusy(true);
    try {
      const { data } = await api.post(`/newsletter/publications/${pubId}/ai-draft`,
        { brief: aiBrief });
      // Overwrite in-memory draft; user must Save to persist.
      setPost((p) => ({ ...p, title: data.title || p.title,
                          subtitle: data.subtitle || p.subtitle,
                          blocks: data.blocks || p.blocks }));
      toast.success(`AI drafted ${data.blocks?.length || 0} block${data.blocks?.length === 1 ? "" : "s"} — Save to persist`);
      setAiOpen(false); setAiBrief("");
    } catch (e) { toast.error(apiError(e)); } finally { setAiBusy(false); }
  };

  if (!post) return <div className="text-[#71717A] py-12 text-center">Loading…</div>;

  return (
    <div className="fade-up max-w-[1200px]" data-testid="post-editor">
      <button data-testid="editor-back" onClick={() => navigate(`/newsletters/${pubId}`)}
        className="text-xs text-[#71717A] hover:text-white mb-4 flex items-center gap-1">
        <ArrowLeft className="w-3 h-3" /> Back to newsletter
      </button>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
          post.status === "sent" ? "bg-emerald-500/15 text-emerald-400" :
          post.status === "scheduled" ? "bg-amber-500/15 text-amber-400" :
          "bg-[#27272A] text-[#A1A1AA]"
        }`}>{post.status}</span>
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          <Dialog open={aiOpen} onOpenChange={setAiOpen}>
            <DialogTrigger asChild>
              <Button data-testid="editor-ai-draft" disabled={post.status === "sent"}
                className="rounded-md gap-2 h-9 text-xs bg-gradient-to-r from-fuchsia-500/20 to-cyan-500/20 border border-fuchsia-500/40 hover:border-fuchsia-400 text-white">
                <Sparkles className="w-3.5 h-3.5" /> Draft with AI
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#141414] border-[#27272A] text-white" data-testid="ai-draft-dialog">
              <DialogHeader><DialogTitle>Draft this post with AI</DialogTitle></DialogHeader>
              <div className="space-y-2">
                <Label className="text-xs text-[#A1A1AA]">One-line brief</Label>
                <Textarea data-testid="ai-brief-input" value={aiBrief} onChange={(e) => setAiBrief(e.target.value)}
                  rows={3}
                  placeholder="e.g. Announce our summer swim capsule drop with 25% off for readers only for 48 hours"
                  className="bg-[#0A0A0A] border-[#27272A] text-white" />
                <div className="text-[10px] text-[#71717A]">
                  AI produces title + subtitle + 5-9 blocks. Coupons and gift cards you'll add manually.
                </div>
              </div>
              <DialogFooter>
                <Button data-testid="ai-draft-submit" onClick={draftWithAI} disabled={aiBusy}
                  className="btn-primary rounded-md gap-2">
                  {aiBusy ? <Loader2 className="w-4 h-4 spin" /> : <Sparkles className="w-4 h-4" />}
                  Generate draft
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Input placeholder="you@example.com" value={sendTo} onChange={(e) => setSendTo(e.target.value)}
            data-testid="editor-test-email"
            className="h-9 w-56 bg-[#0A0A0A] border-[#27272A] text-white text-xs" />
          <Button data-testid="editor-send-test" onClick={sendTest} variant="ghost"
            className="rounded-md gap-2 border border-[#27272A] h-9 text-xs hover:border-[#CCFF00]">
            <Send className="w-3.5 h-3.5" /> Test
          </Button>
          <Button data-testid="editor-save" onClick={save} disabled={saving || post.status === "sent"}
            className="btn-ghost rounded-md gap-2 border border-[#27272A] h-9 text-xs">
            {saving ? <Loader2 className="w-3.5 h-3.5 spin" /> : <Save className="w-3.5 h-3.5" />} Save
          </Button>
          <Button data-testid="editor-send-now" onClick={sendNow} disabled={post.status === "sent"}
            className="btn-primary rounded-md gap-2 h-9 text-xs">
            <Send className="w-3.5 h-3.5" /> Send to all
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-4">
        <div className="surface rounded-lg p-6 space-y-3">
          <div className="flex items-center gap-2 flex-wrap pb-3 border-b border-[#27272A]" data-testid="channel-chips">
            <span className="text-[10px] uppercase tracking-widest text-[#71717A] mr-1">Channels</span>
            {[
              { k: "email", label: "Email", icon: "✉" },
              { k: "sms", label: "SMS", icon: "💬" },
              { k: "whatsapp", label: "WhatsApp", icon: "🟢" },
            ].map((c) => {
              const on = (post.channels || ["email"]).includes(c.k);
              return (
                <button key={c.k} onClick={() => toggleChannel(c.k)} disabled={post.status === "sent"}
                  data-testid={`channel-toggle-${c.k}`}
                  className={`text-[11px] px-2.5 py-1 rounded-full border transition ${
                    on ? "bg-[#CCFF00]/20 border-[#CCFF00] text-[#CCFF00]"
                       : "border-[#27272A] text-[#71717A] hover:border-[#CCFF00]/40"
                  }`}>
                  {c.icon} {c.label}
                </button>
              );
            })}
          </div>
          {((post.channels || []).includes("sms") || (post.channels || []).includes("whatsapp")) && (
            <div data-testid="sms-body-row" className="pb-3 border-b border-[#27272A]">
              <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-1 flex justify-between">
                <span>SMS / WhatsApp body</span>
                <span className={(post.sms_body || "").length > 160 ? "text-amber-400" : "text-[#71717A]"}>
                  {(post.sms_body || "").length} / 160
                </span>
              </div>
              <Textarea data-testid="sms-body-input" value={post.sms_body || ""}
                onChange={(e) => set("sms_body", e.target.value)}
                maxLength={300} rows={2} disabled={post.status === "sent"}
                placeholder="If empty, we'll auto-derive a message from your title + a link to the web version."
                className="bg-[#0A0A0A] border-[#27272A] text-white text-sm" />
            </div>
          )}
          <Input data-testid="editor-title" value={post.title} onChange={(e) => set("title", e.target.value)}
            placeholder="Post title" disabled={post.status === "sent"}
            className="bg-transparent border-0 text-3xl font-display font-bold text-white p-0 focus-visible:ring-0 h-auto" />
          <Input data-testid="editor-subtitle" value={post.subtitle} onChange={(e) => set("subtitle", e.target.value)}
            placeholder="Subtitle (optional)" disabled={post.status === "sent"}
            className="bg-transparent border-0 text-sm text-[#A1A1AA] p-0 focus-visible:ring-0 h-auto" />
          <div className="border-t border-[#27272A] pt-3 space-y-2">
            {post.blocks.map((b, i) => (
              <BlockEditor key={b.id} b={b} i={i}
                disabled={post.status === "sent"}
                onChange={(props) => setBlock(i, props)}
                onRemove={() => removeBlock(i)}
                onMove={(dir) => moveBlock(i, dir)} />
            ))}
            {post.blocks.length === 0 && (
              <div className="text-center text-xs text-[#71717A] py-6">Add your first block from the library →</div>
            )}
          </div>
        </div>
        <div className="surface rounded-lg p-4 h-fit" data-testid="block-library">
          <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-2">Block library</div>
          <div className="grid grid-cols-2 gap-1">
            {BLOCK_LIB.map((cfg) => (
              <button key={cfg.t} onClick={() => addBlock(cfg.t)}
                disabled={post.status === "sent"}
                data-testid={`add-block-${cfg.t}`}
                className="text-[11px] px-2 py-2 rounded border border-[#27272A] hover:border-[#CCFF00] hover:text-[#CCFF00] transition-colors flex flex-col items-center gap-1 disabled:opacity-40">
                <cfg.icon className="w-4 h-4" /> {cfg.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function BlockEditor({ b, i, disabled, onChange, onRemove, onMove }) {
  const p = b.props || {};
  return (
    <div className="rounded-md border border-[#27272A] p-3 bg-[#0A0A0A]" data-testid={`block-${i}-${b.type}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-[10px] uppercase tracking-widest text-[#71717A]">{b.type.replace("_", " ")}</span>
        <div className="ml-auto flex items-center gap-1">
          <button onClick={() => onMove(-1)} disabled={disabled} className="p-1 hover:text-[#CCFF00] disabled:opacity-40"><ChevronUp className="w-3.5 h-3.5" /></button>
          <button onClick={() => onMove(1)} disabled={disabled} className="p-1 hover:text-[#CCFF00] disabled:opacity-40"><ChevronDown className="w-3.5 h-3.5" /></button>
          <button onClick={onRemove} disabled={disabled} data-testid={`remove-block-${i}`}
            className="p-1 hover:text-red-400 disabled:opacity-40"><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      </div>
      {b.type === "heading" && (
        <Input value={p.text || ""} onChange={(e) => onChange({ text: e.target.value })}
          disabled={disabled} data-testid={`block-heading-${i}`}
          className="bg-transparent border-0 text-xl font-bold p-0 focus-visible:ring-0 h-auto text-white" />
      )}
      {b.type === "text" && (
        <Textarea value={p.text || ""} onChange={(e) => onChange({ text: e.target.value })}
          rows={3} disabled={disabled} data-testid={`block-text-${i}`}
          className="bg-transparent border-0 text-sm p-0 focus-visible:ring-0 text-[#E4E4E7] resize-y" />
      )}
      {b.type === "image" && (
        <ImageBlockEditor p={p} onChange={onChange} disabled={disabled} i={i} />
      )}
      {b.type === "button" && (
        <div className="grid grid-cols-2 gap-2">
          <Input value={p.label || ""} onChange={(e) => onChange({ label: e.target.value })}
            placeholder="Label" disabled={disabled}
            data-testid={`block-btn-label-${i}`}
            className="bg-[#141414] border-[#27272A] text-white text-xs" />
          <Input value={p.url || ""} onChange={(e) => onChange({ url: e.target.value })}
            placeholder="https://" disabled={disabled}
            data-testid={`block-btn-url-${i}`}
            className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
        </div>
      )}
      {b.type === "coupon" && (
        <Input value={p.code || ""} onChange={(e) => onChange({ code: e.target.value.toUpperCase() })}
          placeholder="COUPON CODE (must exist in this workspace)" disabled={disabled}
          data-testid={`block-coupon-code-${i}`}
          className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
      )}
      {b.type === "giftcard" && (
        <Input value={p.giftcard_id || ""} onChange={(e) => onChange({ giftcard_id: e.target.value })}
          placeholder="Gift card ID"
          data-testid={`block-giftcard-id-${i}`}
          className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
      )}
      {b.type === "funnel" && (
        <Input value={p.slug || ""} onChange={(e) => onChange({ slug: e.target.value })}
          placeholder="Funnel slug (e.g. summer-drop)"
          data-testid={`block-funnel-slug-${i}`}
          className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
      )}
      {(b.type === "subscribe_form" || b.type === "referral_cta" || b.type === "divider") && (
        <div className="text-[11px] text-[#71717A]">No config needed — auto-rendered.</div>
      )}
    </div>
  );
}

function ImageBlockEditor({ p, onChange, disabled, i }) {
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [galleryOpen, setGalleryOpen] = useState(false);
  const [gallery, setGallery] = useState(null);

  const openGallery = async () => {
    setGalleryOpen(true);
    if (gallery) return;
    try {
      const { data } = await api.get("/uploads");
      // Filter to images only
      const imgs = (data || []).filter((u) => (u.content_type || "").startsWith("image/"));
      setGallery(imgs);
    } catch (e) { toast.error(apiError(e)); }
  };
  const pickFromGallery = (u) => {
    const abs = u.url.startsWith("http") ? u.url
      : `${process.env.REACT_APP_BACKEND_URL}${u.url}`;
    onChange({ url: abs, ai_generated: !!u.ai_generated,
                 ai_provider: u.ai_provider, ai_prompt: u.ai_prompt });
    setGalleryOpen(false);
  };

  const uploadFile = async (file) => {
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error("Max 8 MB"); return; }
    setUploading(true);
    try {
      const fd = new FormData(); fd.append("file", file);
      const { data } = await api.post("/uploads", fd,
        { headers: { "Content-Type": "multipart/form-data" } });
      const abs = data.url.startsWith("http") ? data.url
        : `${process.env.REACT_APP_BACKEND_URL}${data.url}`;
      onChange({ url: abs, ai_generated: false });
      setGallery(null);  // invalidate gallery cache
      toast.success("Image uploaded");
    } catch (e) { toast.error(apiError(e)); } finally { setUploading(false); }
  };

  const generateAI = async () => {
    if (!aiPrompt.trim()) { toast.error("Describe the image first"); return; }
    setGenerating(true);
    try {
      const { data } = await api.post("/ai/image", { prompt: aiPrompt });
      // Prefer the persisted storage URL so it works in email; fall back to data URL.
      const useUrl = data.storage_url
        ? `${process.env.REACT_APP_BACKEND_URL}${data.storage_url}`
        : data.image_url;
      onChange({ url: useUrl, ai_generated: !!data.ai_generated,
                   ai_provider: data.provider, ai_prompt: aiPrompt });
      setGallery(null);  // invalidate so the new image appears next open
      toast.success("AI generated a graphic");
      setAiPrompt("");
    } catch (e) { toast.error(apiError(e, "Image generation failed")); }
    finally { setGenerating(false); }
  };

  return (
    <div className="space-y-2" data-testid={`block-image-${i}`}>
      {p.url ? (
        <div className="relative">
          <img src={p.url} alt={p.alt || ""}
            className="w-full max-h-64 object-cover rounded-md border border-[#27272A]" />
          {p.ai_generated && (
            <span className="absolute top-2 left-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/70 backdrop-blur-sm border border-fuchsia-400/50 text-[9px] font-bold uppercase tracking-widest text-fuchsia-300"
              data-testid={`block-image-ai-badge-${i}`}>
              <Sparkles className="w-3 h-3" /> AI-generated
            </span>
          )}
          <button onClick={() => onChange({ url: "", ai_generated: false, ai_provider: null, ai_prompt: null })}
            disabled={disabled}
            data-testid={`block-image-clear-${i}`}
            className="absolute top-2 right-2 px-2 py-0.5 rounded bg-black/70 text-white text-[10px] hover:bg-red-500/70">
            Replace
          </button>
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-[#27272A] p-4 text-center">
          <ImageIcon className="w-6 h-6 text-[#71717A] mx-auto mb-2" />
          <div className="text-[11px] text-[#71717A] mb-3">Upload a custom graphic or generate one with AI</div>
          <div className="flex gap-2 justify-center flex-wrap">
            <label className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#27272A] hover:border-[#CCFF00] hover:text-[#CCFF00] cursor-pointer text-[11px] ${uploading ? "opacity-60 pointer-events-none" : ""}`}
              data-testid={`block-image-upload-btn-${i}`}>
              {uploading ? <Loader2 className="w-3 h-3 spin" /> : <Upload className="w-3 h-3" />}
              {uploading ? "Uploading…" : "Upload"}
              <input type="file" accept="image/*" className="hidden" disabled={disabled || uploading}
                onChange={(e) => { uploadFile(e.target.files?.[0]); e.target.value = ""; }} />
            </label>
            <button onClick={openGallery} disabled={disabled}
              data-testid={`block-image-gallery-btn-${i}`}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-[#27272A] hover:border-[#CCFF00] hover:text-[#CCFF00] text-[11px]">
              <ImageIcon className="w-3 h-3" /> Gallery
            </button>
          </div>
        </div>
      )}
      <Dialog open={galleryOpen} onOpenChange={setGalleryOpen}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-3xl max-h-[80vh] overflow-y-auto"
          data-testid={`block-image-gallery-dialog-${i}`}>
          <DialogHeader><DialogTitle>Pick from your image library</DialogTitle></DialogHeader>
          {!gallery ? (
            <div className="py-12 text-center text-[#71717A]"><Loader2 className="w-6 h-6 spin mx-auto" /></div>
          ) : gallery.length === 0 ? (
            <div className="py-12 text-center text-[#71717A]">
              No images yet. Upload one or generate with AI to start your library.
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {gallery.map((u) => {
                const src = u.url.startsWith("http") ? u.url : `${process.env.REACT_APP_BACKEND_URL}${u.url}`;
                return (
                  <button key={u.id} onClick={() => pickFromGallery(u)}
                    data-testid={`gallery-pick-${u.id}`}
                    className="relative rounded-md overflow-hidden border border-[#27272A] hover:border-[#CCFF00] transition group">
                    <img src={src} alt="" className="w-full h-24 object-cover" loading="lazy" />
                    {u.ai_generated && (
                      <span className="absolute top-1 left-1 px-1.5 py-0.5 rounded-full bg-black/70 backdrop-blur-sm border border-fuchsia-400/50 text-[8px] font-bold uppercase tracking-widest text-fuchsia-300">
                        <Sparkles className="w-2 h-2 inline mr-0.5" /> AI
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </DialogContent>
      </Dialog>
      <div className="flex gap-2 items-stretch">
        <Input value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)}
          placeholder="or describe an image for AI to generate…"
          disabled={disabled || generating}
          data-testid={`block-image-ai-prompt-${i}`}
          className="flex-1 bg-[#141414] border-[#27272A] text-white text-xs h-8" />
        <Button data-testid={`block-image-ai-generate-${i}`}
          onClick={generateAI} disabled={disabled || generating || !aiPrompt.trim()}
          className="rounded-md gap-1 h-8 text-[11px] px-3 bg-gradient-to-r from-fuchsia-500/20 to-cyan-500/20 border border-fuchsia-500/40 hover:border-fuchsia-400 text-white">
          {generating ? <Loader2 className="w-3 h-3 spin" /> : <Sparkles className="w-3 h-3" />}
          {generating ? "…" : "AI"}
        </Button>
      </div>
      <Input value={p.alt || ""} onChange={(e) => onChange({ alt: e.target.value })}
        placeholder="Alt text (accessibility)" disabled={disabled}
        data-testid={`block-image-alt-${i}`}
        className="bg-[#141414] border-[#27272A] text-white text-xs h-8" />
    </div>
  );
}

