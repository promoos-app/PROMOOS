import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  ArrowLeft, Save, Send, Trash2, Plus, ChevronUp, ChevronDown, Loader2,
  Heading, Type, Image as ImageIcon, MousePointerClick, Ticket, Gift, Rocket, Minus, Share2, Users, Sparkles, Upload, Search, Check as CheckIcon, Eye, Video, Music, MoveVertical, MessageSquare, Link2, Save as SaveIcon, Palette, History, RotateCcw, AlertCircle,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";

const BLOCK_LIB = [
  { t: "heading", label: "Heading", icon: Heading, defaults: { level: "h2", text: "Section title", align: "left" } },
  { t: "text", label: "Text", icon: Type, defaults: { text: "Write a paragraph…", align: "left" } },
  { t: "image", label: "Image", icon: ImageIcon, defaults: { url: "", alt: "", align: "center" } },
  { t: "video", label: "Video", icon: Video, defaults: { url: "", poster: "", align: "center" } },
  { t: "audio", label: "Audio", icon: Music, defaults: { url: "", title: "Listen" } },
  { t: "button", label: "Button", icon: MousePointerClick, defaults: { label: "Learn more", url: "https://", align: "left" } },
  { t: "coupon", label: "Coupon", icon: Ticket, defaults: { code: "" } },
  { t: "giftcard", label: "Gift card", icon: Gift, defaults: { giftcard_id: "" } },
  { t: "funnel", label: "Funnel", icon: Rocket, defaults: { slug: "" } },
  { t: "subscribe_form", label: "Subscribe form", icon: Users, defaults: {} },
  { t: "referral_cta", label: "Referral CTA", icon: Share2, defaults: {} },
  { t: "divider", label: "Divider", icon: Minus, defaults: {} },
  { t: "spacer", label: "Spacer", icon: MoveVertical, defaults: { height: 24 } },
];

export default function NewsletterPostEditor() {
  const { pubId, postId } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState(null);
  const [pub, setPub] = useState(null);
  const [saving, setSaving] = useState(false);
  const [sendTo, setSendTo] = useState("");
  const [aiOpen, setAiOpen] = useState(false);
  const [aiBrief, setAiBrief] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewDevice, setPreviewDevice] = useState("desktop");    // desktop | mobile
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [versionsBusy, setVersionsBusy] = useState(false);

  const openVersions = async () => {
    setVersionsOpen(true); setVersionsBusy(true);
    try {
      const { data } = await api.get(
        `/newsletter/publications/${pubId}/posts/${postId}/versions`);
      setVersions(data);
    } catch (e) { toast.error(apiError(e)); }
    finally { setVersionsBusy(false); }
  };
  const restoreVersion = async (vid, num) => {
    if (!window.confirm(`Restore version ${num}? Your current draft will be snapshotted first, so this is reversible.`)) return;
    try {
      await api.post(`/newsletter/publications/${pubId}/posts/${postId}/versions/${vid}/restore`);
      toast.success(`Restored v${num}`);
      const { data } = await api.get(`/newsletter/publications/${pubId}/posts/${postId}`);
      setPost(data);
      setVersionsOpen(false);
      openVersions();  // refresh list
    } catch (e) { toast.error(apiError(e)); }
  };

  const openPreview = async () => {
    setPreviewOpen(true); setPreviewBusy(true); setPreviewHtml("");
    try {
      // Save first so the preview reflects what the recipient will actually see.
      await save();
      const { data } = await api.get(
        `/newsletter/publications/${pubId}/posts/${postId}/preview`,
        { responseType: "text", transformResponse: [(x) => x] });
      setPreviewHtml(data);
    } catch (e) { toast.error(apiError(e, "Preview failed")); setPreviewOpen(false); }
    finally { setPreviewBusy(false); }
  };

  const [saveTplOpen, setSaveTplOpen] = useState(false);
  const [saveTplName, setSaveTplName] = useState("");
  const [saveTplBusy, setSaveTplBusy] = useState(false);
  const doSaveAsTemplate = async () => {
    const name = saveTplName.trim();
    if (!name) { toast.error("Give the template a name"); return; }
    setSaveTplBusy(true);
    try {
      await save();
      await api.post("/newsletter/saved-templates",
        { name, post_id: postId });
      toast.success("Saved to your workspace templates");
      setSaveTplOpen(false); setSaveTplName("");
    } catch (e) { toast.error(apiError(e)); }
    finally { setSaveTplBusy(false); }
  };

  const [shareOpen, setShareOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [shareBusy, setShareBusy] = useState(false);
  const [comments, setComments] = useState([]);
  const [commentsBusy, setCommentsBusy] = useState(false);
  const loadComments = async () => {
    setCommentsBusy(true);
    try {
      const { data } = await api.get(
        `/newsletter/publications/${pubId}/posts/${postId}/comments`);
      setComments(data);
    } catch (e) { /* silent — no comments yet is fine */ }
    finally { setCommentsBusy(false); }
  };
  useEffect(() => { if (postId) loadComments(); }, [postId, pubId]);
  const createShareLink = async () => {
    setShareBusy(true);
    try {
      await save();
      const { data } = await api.post(
        `/newsletter/publications/${pubId}/posts/${postId}/share`);
      setShareUrl(data.url);
      try { await navigator.clipboard.writeText(data.url); toast.success("Link copied — valid 7 days"); }
      catch (_) { toast.success("Link ready — valid 7 days"); }
    } catch (e) { toast.error(apiError(e)); }
    finally { setShareBusy(false); }
  };
  const resolveComment = async (cid) => {
    try {
      await api.post(`/newsletter/publications/${pubId}/posts/${postId}/comments/${cid}/resolve`);
      loadComments();
    } catch (e) { toast.error(apiError(e)); }
  };

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
    api.get(`/newsletter/publications/${pubId}`)
      .then((r) => setPub(r.data)).catch(() => {});
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
          <Button data-testid="editor-preview" onClick={openPreview} variant="ghost"
            className="rounded-md gap-2 border border-[#27272A] h-9 text-xs hover:border-sky-400">
            <Eye className="w-3.5 h-3.5" /> Preview
          </Button>
          <Button data-testid="editor-share" onClick={createShareLink} disabled={shareBusy}
            variant="ghost"
            className="rounded-md gap-2 border border-[#27272A] h-9 text-xs hover:border-fuchsia-400">
            {shareBusy ? <Loader2 className="w-3.5 h-3.5 spin" /> : <Link2 className="w-3.5 h-3.5" />}
            Share for review
          </Button>
          <Button data-testid="editor-save-as-template" onClick={() => setSaveTplOpen(true)}
            variant="ghost"
            className="rounded-md gap-2 border border-[#27272A] h-9 text-xs hover:border-emerald-400">
            <SaveIcon className="w-3.5 h-3.5" /> Save as template
          </Button>
          <Button data-testid="editor-versions" onClick={openVersions} variant="ghost"
            className="rounded-md gap-2 border border-[#27272A] h-9 text-xs hover:border-amber-400">
            <History className="w-3.5 h-3.5" /> Versions
          </Button>
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

      {/* Approval gate banner — visible when publication requires approval and
          there are still unresolved review comments. */}
      {pub && pub.require_approval && comments.filter((c) => !c.resolved).length > 0 && (
        <div data-testid="approval-gate-banner"
          className="mb-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 flex items-center gap-2 text-sm">
          <AlertCircle className="w-4 h-4 text-amber-300 shrink-0" />
          <span className="text-amber-100">
            Approval required — resolve {comments.filter((c) => !c.resolved).length} review comment{comments.filter((c) => !c.resolved).length > 1 ? "s" : ""} before you can send.
          </span>
        </div>
      )}

      {/* Preview dialog — WYSIWYG email render in a sandboxed iframe. */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-5xl h-[90vh] flex flex-col"
          data-testid="preview-dialog">
          <DialogHeader className="flex-row items-center justify-between gap-4 space-y-0">
            <div>
              <DialogTitle>Email preview</DialogTitle>
              <div className="text-[11px] text-[#71717A] mt-1">
                This is exactly what your subscribers will see. Not a send — no tracking pixels.
              </div>
            </div>
            <div className="flex items-center gap-1 mr-8">
              <button onClick={() => setPreviewDevice("desktop")}
                data-testid="preview-device-desktop"
                className={`px-3 h-8 rounded-md border text-[11px] transition ${
                  previewDevice === "desktop"
                    ? "bg-[#CCFF00] text-black border-[#CCFF00]"
                    : "bg-transparent text-[#A1A1AA] border-[#27272A] hover:border-[#CCFF00]"
                }`}>Desktop</button>
              <button onClick={() => setPreviewDevice("mobile")}
                data-testid="preview-device-mobile"
                className={`px-3 h-8 rounded-md border text-[11px] transition ${
                  previewDevice === "mobile"
                    ? "bg-[#CCFF00] text-black border-[#CCFF00]"
                    : "bg-transparent text-[#A1A1AA] border-[#27272A] hover:border-[#CCFF00]"
                }`}>Mobile</button>
            </div>
          </DialogHeader>
          <div className="flex-1 min-h-0 bg-[#0A0A0A] rounded-md border border-[#27272A] p-4 overflow-y-auto flex items-start justify-center">
            {previewBusy ? (
              <div className="flex-1 flex items-center justify-center text-[#71717A]">
                <Loader2 className="w-6 h-6 spin" />
              </div>
            ) : (
              <iframe
                title="preview"
                srcDoc={previewHtml}
                data-testid="preview-iframe"
                className="bg-white rounded-md shadow-2xl transition-all"
                style={{
                  width: previewDevice === "mobile" ? 375 : "100%",
                  maxWidth: previewDevice === "mobile" ? 375 : 760,
                  height: "100%",
                  minHeight: 600,
                  border: 0,
                }}
                sandbox="allow-same-origin"
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Save as template dialog */}
      <Dialog open={saveTplOpen} onOpenChange={setSaveTplOpen}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white" data-testid="save-template-dialog">
          <DialogHeader>
            <DialogTitle>Save as personal template</DialogTitle>
            <div className="text-xs text-[#71717A] mt-1">
              Stored in your workspace. Reuse from the Post → "Start from template" picker.
            </div>
          </DialogHeader>
          <Label className="text-xs text-[#A1A1AA]">Template name</Label>
          <Input value={saveTplName} onChange={(e) => setSaveTplName(e.target.value)}
            placeholder="e.g. Monthly VIP drop"
            data-testid="save-template-name"
            className="bg-[#0A0A0A] border-[#27272A] text-white" />
          <DialogFooter>
            <Button data-testid="save-template-submit" onClick={doSaveAsTemplate}
              disabled={saveTplBusy}
              className="btn-primary rounded-md gap-2">
              {saveTplBusy ? <Loader2 className="w-4 h-4 spin" /> : <SaveIcon className="w-4 h-4" />}
              Save template
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Share for review dialog */}
      <Dialog open={!!shareUrl && !shareBusy} onOpenChange={(o) => !o && setShareUrl("")}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white" data-testid="share-dialog">
          <DialogHeader>
            <DialogTitle>Share for team review</DialogTitle>
            <div className="text-xs text-[#71717A] mt-1">
              Anyone with this link can preview and leave comments for 7 days. No login required.
            </div>
          </DialogHeader>
          <div className="flex items-center gap-2 rounded-md bg-[#0A0A0A] border border-[#27272A] p-3">
            <Link2 className="w-4 h-4 text-fuchsia-400 shrink-0" />
            <span className="flex-1 truncate font-mono text-xs" data-testid="share-url">{shareUrl}</span>
            <button onClick={() => { navigator.clipboard.writeText(shareUrl); toast.success("Copied"); }}
              className="text-[#71717A] hover:text-[#CCFF00]" data-testid="share-copy">
              <CheckIcon className="w-4 h-4" />
            </button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Versions dialog — full save history with restore. */}
      <Dialog open={versionsOpen} onOpenChange={setVersionsOpen}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-2xl max-h-[85vh] overflow-y-auto"
          data-testid="versions-dialog">
          <DialogHeader>
            <DialogTitle>Version history</DialogTitle>
            <div className="text-xs text-[#71717A] mt-1">
              Every save is snapshotted (up to 30). Restore any version — your current draft will be snapshotted first so it's reversible.
            </div>
          </DialogHeader>
          {versionsBusy ? (
            <div className="py-12 text-center"><Loader2 className="w-6 h-6 spin mx-auto text-[#CCFF00]" /></div>
          ) : versions.length === 0 ? (
            <div className="py-12 text-center text-[#71717A] text-xs italic">
              No versions yet. Save the draft to start building history.
            </div>
          ) : (
            <div className="divide-y divide-[#27272A] rounded-md border border-[#27272A]">
              {versions.map((v) => (
                <div key={v.id} data-testid={`version-row-${v.version_num}`}
                  className="px-4 py-3 flex items-center gap-3 hover:bg-white/5">
                  <div className="w-10 h-10 rounded-md bg-amber-500/10 border border-amber-500/40 flex items-center justify-center text-amber-300 font-mono font-bold text-xs shrink-0">
                    v{v.version_num}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{v.title || "(no title)"}</div>
                    <div className="text-[11px] text-[#71717A]">
                      {new Date(v.created_at).toLocaleString()} · {v.saved_by_name || v.saved_by?.slice(0, 8)} · {v.reason}
                    </div>
                  </div>
                  <Button size="sm" onClick={() => restoreVersion(v.id, v.version_num)}
                    data-testid={`restore-version-${v.version_num}`}
                    className="rounded-md gap-1 h-8 text-[11px] bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/50 text-white">
                    <RotateCcw className="w-3 h-3" /> Restore
                  </Button>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>

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
        <div className="surface rounded-lg p-4 h-fit space-y-4" data-testid="block-library">
          <div>
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
          <div className="pt-3 border-t border-[#27272A]">
            <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-2 flex items-center gap-1">
              <MessageSquare className="w-3 h-3" /> Review comments
              {comments.filter((c) => !c.resolved).length > 0 && (
                <span className="ml-auto px-1.5 py-0.5 rounded-full bg-fuchsia-500/20 text-fuchsia-300 text-[9px] font-bold">
                  {comments.filter((c) => !c.resolved).length}
                </span>
              )}
            </div>
            {commentsBusy ? (
              <Loader2 className="w-4 h-4 spin text-[#71717A] mx-auto" />
            ) : comments.length === 0 ? (
              <div className="text-[10px] text-[#71717A] italic">No comments yet. Share the review link with your team.</div>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {comments.map((c) => {
                  const blk = c.block_id && (post?.blocks || []).find((b) => b.id === c.block_id);
                  return (
                  <div key={c.id} data-testid={`comment-${c.id}`}
                    className={`rounded-md p-2 border text-[11px] ${
                      c.resolved
                        ? "border-emerald-500/20 bg-emerald-500/5 opacity-60"
                        : "border-fuchsia-500/30 bg-fuchsia-500/5"
                    }`}>
                    <div className="flex items-center gap-1 mb-1">
                      <span className="font-semibold text-white">{c.reviewer_name}</span>
                      <span className="text-[9px] text-[#71717A]">
                        {new Date(c.created_at).toLocaleString(undefined,
                          { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </span>
                      {!c.resolved && (
                        <button onClick={() => resolveComment(c.id)}
                          data-testid={`resolve-comment-${c.id}`}
                          className="ml-auto text-[9px] text-emerald-300 hover:underline">
                          Resolve
                        </button>
                      )}
                    </div>
                    {blk && (
                      <div className="mb-1 inline-block px-1.5 py-0.5 rounded bg-fuchsia-500/20 text-fuchsia-200 text-[9px] uppercase tracking-widest">
                        On: {blk.type}
                      </div>
                    )}
                    <div className="text-[#E4E4E7] whitespace-pre-wrap">{c.body}</div>
                  </div>
                )})}
              </div>
            )}
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
      {b.type === "video" && (
        <div className="grid grid-cols-1 gap-2">
          <Input value={p.url || ""} onChange={(e) => onChange({ url: e.target.value })}
            placeholder="Video URL (MP4 or YouTube/Vimeo link)" disabled={disabled}
            data-testid={`block-video-url-${i}`}
            className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
          <Input value={p.poster || ""} onChange={(e) => onChange({ poster: e.target.value })}
            placeholder="Poster image URL (shown in email clients)" disabled={disabled}
            data-testid={`block-video-poster-${i}`}
            className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
        </div>
      )}
      {b.type === "audio" && (
        <div className="grid grid-cols-2 gap-2">
          <Input value={p.title || ""} onChange={(e) => onChange({ title: e.target.value })}
            placeholder="Track title" disabled={disabled}
            data-testid={`block-audio-title-${i}`}
            className="bg-[#141414] border-[#27272A] text-white text-xs" />
          <Input value={p.url || ""} onChange={(e) => onChange({ url: e.target.value })}
            placeholder="MP3/OGG URL" disabled={disabled}
            data-testid={`block-audio-url-${i}`}
            className="bg-[#141414] border-[#27272A] text-white text-xs font-mono" />
        </div>
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
      {b.type === "spacer" && (
        <div className="flex items-center gap-2">
          <Label className="text-[11px] text-[#71717A] shrink-0">Height (px)</Label>
          <Input type="number" min={4} max={120} value={p.height || 24}
            onChange={(e) => onChange({ height: parseInt(e.target.value || 0, 10) })}
            data-testid={`block-spacer-height-${i}`}
            className="w-24 bg-[#141414] border-[#27272A] text-white text-xs" />
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
      {["heading", "text", "button", "image", "video", "divider"].includes(b.type) && (
        <BlockStylePanel p={p} onChange={onChange} type={b.type} i={i} />
      )}
    </div>
  );
}

function BlockStylePanel({ p, onChange, type, i }) {
  const [open, setOpen] = useState(false);
  const supportsAlign = ["heading", "text", "button", "image", "video"].includes(type);
  const supportsColor = ["heading", "text", "button", "divider"].includes(type);
  const supportsBg    = ["heading", "text", "button"].includes(type);
  const supportsSize  = ["heading", "text"].includes(type);
  return (
    <div className="mt-2 pt-2 border-t border-[#27272A]">
      <button type="button" onClick={() => setOpen((v) => !v)}
        data-testid={`block-style-toggle-${i}`}
        className="flex items-center gap-1 text-[10px] uppercase tracking-widest text-[#71717A] hover:text-[#CCFF00]">
        <Palette className="w-3 h-3" /> {open ? "Hide" : "Style"} options
      </button>
      {open && (
        <div className="mt-2 grid grid-cols-2 sm:grid-cols-4 gap-2">
          {supportsAlign && (
            <label className="flex flex-col text-[10px] text-[#71717A]">
              Align
              <select value={p.align || "left"}
                onChange={(e) => onChange({ align: e.target.value })}
                data-testid={`block-style-align-${i}`}
                className="mt-0.5 bg-[#141414] border border-[#27272A] rounded px-2 py-1 text-white text-xs">
                <option value="left">Left</option>
                <option value="center">Center</option>
                <option value="right">Right</option>
              </select>
            </label>
          )}
          {supportsColor && (
            <label className="flex flex-col text-[10px] text-[#71717A]">
              {type === "button" ? "Text color" : type === "divider" ? "Line color" : "Text color"}
              <input type="color" value={p.color || (type === "button" ? "#FFFFFF" : type === "divider" ? "#E4E4E7" : "#0A0A0A")}
                onChange={(e) => onChange({ color: e.target.value })}
                data-testid={`block-style-color-${i}`}
                className="mt-0.5 h-8 w-full bg-transparent border border-[#27272A] rounded cursor-pointer" />
            </label>
          )}
          {supportsBg && (
            <label className="flex flex-col text-[10px] text-[#71717A]">
              {type === "button" ? "Button color" : "Background"}
              <input type="color" value={p.background || (type === "button" ? "#005CEE" : "#FFFFFF")}
                onChange={(e) => onChange({ background: e.target.value })}
                data-testid={`block-style-bg-${i}`}
                className="mt-0.5 h-8 w-full bg-transparent border border-[#27272A] rounded cursor-pointer" />
            </label>
          )}
          {supportsSize && (
            <label className="flex flex-col text-[10px] text-[#71717A]">
              Font size (px)
              <Input type="number" min={10} max={64}
                value={p.font_size || (type === "heading" ? 24 : 15)}
                onChange={(e) => onChange({ font_size: parseInt(e.target.value || 0, 10) })}
                data-testid={`block-style-fontsize-${i}`}
                className="mt-0.5 h-8 bg-[#141414] border-[#27272A] text-white text-xs" />
            </label>
          )}
          {type === "heading" && (
            <label className="flex flex-col text-[10px] text-[#71717A]">
              Level
              <select value={p.level || "h2"}
                onChange={(e) => onChange({ level: e.target.value })}
                data-testid={`block-style-level-${i}`}
                className="mt-0.5 bg-[#141414] border border-[#27272A] rounded px-2 py-1 text-white text-xs">
                <option value="h1">H1</option>
                <option value="h2">H2</option>
                <option value="h3">H3</option>
                <option value="h4">H4</option>
              </select>
            </label>
          )}
          {type === "button" && (
            <label className="flex flex-col text-[10px] text-[#71717A]">
              Radius (px)
              <Input type="number" min={0} max={48} value={p.radius || 8}
                onChange={(e) => onChange({ radius: parseInt(e.target.value || 0, 10) })}
                data-testid={`block-style-radius-${i}`}
                className="mt-0.5 h-8 bg-[#141414] border-[#27272A] text-white text-xs" />
            </label>
          )}
        </div>
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
  const [galleryQuery, setGalleryQuery] = useState("");
  const [galleryTag, setGalleryTag] = useState("all");    // all | ai | user
  const [galleryLoading, setGalleryLoading] = useState(false);
  const [manageMode, setManageMode] = useState(false);
  const [selected, setSelected] = useState({});           // {id: true}

  const toggleSelect = (id) => setSelected((s) => {
    const n = { ...s }; if (n[id]) delete n[id]; else n[id] = true; return n;
  });
  const clearSelection = () => setSelected({});
  const bulkDelete = async () => {
    const ids = Object.keys(selected);
    if (!ids.length) return;
    if (!window.confirm(`Delete ${ids.length} image${ids.length > 1 ? "s" : ""} from your library?`)) return;
    try {
      const { data } = await api.post("/uploads/bulk-delete", { ids });
      toast.success(`Deleted ${data.deleted} image${data.deleted !== 1 ? "s" : ""}`);
      clearSelection();
      await fetchGallery();
    } catch (e) { toast.error(apiError(e)); }
  };

  const fetchGallery = async (opts = {}) => {
    setGalleryLoading(true);
    try {
      const params = {};
      const q = opts.q ?? galleryQuery;
      const tag = opts.tag ?? galleryTag;
      if (q && q.trim()) params.q = q.trim();
      if (tag && tag !== "all") params.tag = tag;
      const { data } = await api.get("/uploads", { params });
      const imgs = (data || []).filter((u) => (u.content_type || "").startsWith("image/"));
      setGallery(imgs);
    } catch (e) { toast.error(apiError(e)); }
    finally { setGalleryLoading(false); }
  };

  const openGallery = async () => {
    setGalleryOpen(true);
    if (gallery === null) await fetchGallery();
  };
  // Debounced re-fetch on search/tag change while dialog is open.
  React.useEffect(() => {
    if (!galleryOpen) return;
    const t = setTimeout(() => { fetchGallery(); }, 250);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [galleryQuery, galleryTag, galleryOpen]);

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
          <div className="flex flex-col sm:flex-row gap-2 items-stretch sm:items-center mb-3">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-[#71717A]" />
              <Input value={galleryQuery} onChange={(e) => setGalleryQuery(e.target.value)}
                placeholder="Search filenames or AI prompts…"
                data-testid={`gallery-search-input-${i}`}
                className="bg-[#0A0A0A] border-[#27272A] text-white text-xs h-8 pl-8" />
            </div>
            <div className="flex gap-1" role="tablist">
              {[
                { k: "all", label: "All" },
                { k: "ai", label: "AI" },
                { k: "user", label: "Uploads" },
              ].map((t) => (
                <button key={t.k} onClick={() => setGalleryTag(t.k)}
                  data-testid={`gallery-tag-${t.k}-${i}`}
                  className={`px-3 h-8 rounded-md border text-[11px] font-medium transition ${
                    galleryTag === t.k
                      ? "bg-[#CCFF00] text-black border-[#CCFF00]"
                      : "bg-transparent text-[#A1A1AA] border-[#27272A] hover:border-[#CCFF00]"
                  }`}>{t.label}</button>
              ))}
              <button onClick={() => { setManageMode((m) => !m); clearSelection(); }}
                data-testid={`gallery-manage-toggle-${i}`}
                className={`px-3 h-8 rounded-md border text-[11px] font-medium transition ${
                  manageMode
                    ? "bg-red-500/20 text-red-300 border-red-500/50"
                    : "bg-transparent text-[#A1A1AA] border-[#27272A] hover:border-red-500/60"
                }`}>{manageMode ? "Done" : "Manage"}</button>
            </div>
          </div>
          {manageMode && Object.keys(selected).length > 0 && (
            <div className="flex items-center gap-2 mb-3 px-3 py-2 rounded-md bg-red-500/10 border border-red-500/40"
              data-testid={`gallery-bulk-bar-${i}`}>
              <span className="text-xs text-red-200">
                {Object.keys(selected).length} selected
              </span>
              <button onClick={clearSelection}
                className="ml-auto text-[11px] text-[#A1A1AA] hover:text-white">Clear</button>
              <button onClick={bulkDelete}
                data-testid={`gallery-bulk-delete-${i}`}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-md bg-red-500 hover:bg-red-600 text-white text-[11px] font-semibold">
                <Trash2 className="w-3 h-3" /> Delete selected
              </button>
            </div>
          )}
          {galleryLoading || gallery === null ? (
            <div className="py-12 text-center text-[#71717A]"><Loader2 className="w-6 h-6 spin mx-auto" /></div>
          ) : gallery.length === 0 ? (
            <div className="py-12 text-center text-[#71717A]" data-testid={`gallery-empty-${i}`}>
              {galleryQuery.trim() || galleryTag !== "all"
                ? "No images match your search. Try a different query or filter."
                : "No images yet. Upload one or generate with AI to start your library."}
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {gallery.map((u) => {
                const src = u.url.startsWith("http") ? u.url : `${process.env.REACT_APP_BACKEND_URL}${u.url}`;
                const isSel = !!selected[u.id];
                return (
                  <button key={u.id}
                    onClick={() => manageMode ? toggleSelect(u.id) : pickFromGallery(u)}
                    data-testid={`gallery-pick-${u.id}`}
                    title={u.ai_prompt || u.original_filename || ""}
                    className={`relative rounded-md overflow-hidden border transition group ${
                      manageMode && isSel
                        ? "border-red-500 ring-2 ring-red-500/60"
                        : "border-[#27272A] hover:border-[#CCFF00]"
                    }`}>
                    <img src={src} alt="" className="w-full h-24 object-cover" loading="lazy" />
                    {u.ai_generated && (
                      <span className="absolute top-1 left-1 px-1.5 py-0.5 rounded-full bg-black/70 backdrop-blur-sm border border-fuchsia-400/50 text-[8px] font-bold uppercase tracking-widest text-fuchsia-300">
                        <Sparkles className="w-2 h-2 inline mr-0.5" /> AI
                      </span>
                    )}
                    {manageMode && (
                      <span className={`absolute top-1 right-1 w-5 h-5 rounded flex items-center justify-center border-2 ${
                        isSel ? "bg-red-500 border-red-500 text-white"
                              : "bg-black/60 border-white/60 text-transparent"
                      }`} data-testid={`gallery-select-${u.id}`}>
                        <CheckIcon className="w-3 h-3" />
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

