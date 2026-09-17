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
  Heading, Type, Image as ImageIcon, MousePointerClick, Ticket, Gift, Rocket, Minus, Share2, Users,
} from "lucide-react";

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
        { title: post.title, subtitle: post.subtitle, blocks: post.blocks });
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
        <div className="ml-auto flex items-center gap-2">
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
        <Input value={p.url || ""} onChange={(e) => onChange({ url: e.target.value })}
          placeholder="https://…" disabled={disabled} data-testid={`block-image-url-${i}`}
          className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
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
