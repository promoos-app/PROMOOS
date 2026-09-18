import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  ArrowLeft, FileText, Users, BarChart3, Palette, Gift, Settings as SettingsIcon,
  Plus, Loader2, ExternalLink, Trash2, Send, Upload, Share2, Copy, LayoutTemplate, Eye, Save as SaveIcon,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

const TABS = [
  { k: "posts", label: "Posts", icon: FileText },
  { k: "subs", label: "Subscribers", icon: Users },
  { k: "analytics", label: "Analytics", icon: BarChart3 },
  { k: "referrals", label: "Referrals", icon: Gift },
  { k: "design", label: "Design", icon: Palette },
  { k: "settings", label: "Settings", icon: SettingsIcon },
];

// Minimal client-side render for saved-template preview so we skip an extra API call.
function _renderSavedTemplateHtml(st, pub) {
  const primary = (pub && pub.primary_color) || "#005CEE";
  const blocks = (st.blocks || []).map((b) => {
    const p = b.props || {};
    const align = ["left", "center", "right"].includes(p.align) ? p.align : "left";
    if (b.type === "heading") {
      const tag = ["h1", "h2", "h3", "h4"].includes(p.level) ? p.level : "h2";
      return `<${tag} style="margin:20px 0 8px;text-align:${align};color:${p.color || "#0A0A0A"}">${(p.text || "").replace(/</g, "&lt;")}</${tag}>`;
    }
    if (b.type === "text")
      return `<p style="margin:0 0 16px;text-align:${align};font-size:${p.font_size || 15}px;line-height:1.6;color:${p.color || "#3F3F46"};white-space:pre-wrap">${(p.text || "").replace(/</g, "&lt;")}</p>`;
    if (b.type === "image" && p.url)
      return `<img src="${p.url}" style="display:block;width:100%;border-radius:8px;margin:16px 0" />`;
    if (b.type === "button")
      return `<div style="margin:24px 0;text-align:${align}"><a href="${p.url || "#"}" style="display:inline-block;background:${p.background || primary};color:${p.color || "#fff"};text-decoration:none;padding:12px 24px;border-radius:${p.radius || 8}px;font-weight:700">${p.label || "Learn more"}</a></div>`;
    if (b.type === "divider") return '<hr style="border:0;border-top:1px solid #E4E4E7;margin:24px 0" />';
    if (b.type === "spacer") return `<div style="height:${p.height || 24}px"></div>`;
    return "";
  }).join("");
  return `<!doctype html><html><body style="margin:0;padding:0;background:#F4F4F5;font-family:Helvetica,Arial,sans-serif">
<table width="100%" style="padding:24px 12px"><tr><td align="center">
<table width="640" style="background:#fff;border-radius:12px;overflow:hidden;max-width:640px">
<tr><td style="padding:20px 28px;background:${primary};color:#fff;font-weight:700;letter-spacing:1px;font-size:13px;text-transform:uppercase">${(pub && pub.name) || "Your Newsletter"}</td></tr>
<tr><td style="padding:28px 32px 8px"><h1 style="margin:0 0 8px;font-size:26px">${(st.title || "").replace(/</g, "&lt;")}</h1>
${st.subtitle ? `<p style="margin:0 0 24px;color:#71717A;font-size:14px">${st.subtitle.replace(/</g, "&lt;")}</p>` : ""}
${blocks}</td></tr>
</table></td></tr></table></body></html>`;
}

export default function NewsletterDashboard() {
  const { pubId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState("posts");

  const { data: pub } = useQuery({
    queryKey: ["publication", pubId],
    queryFn: async () => (await api.get(`/newsletter/publications/${pubId}`)).data,
  });

  if (!pub) return <div className="text-[#71717A] py-12 text-center">Loading…</div>;

  return (
    <div className="fade-up max-w-[1400px]" data-testid="publication-dashboard">
      <button data-testid="pub-back" onClick={() => navigate("/newsletters")}
        className="text-xs text-[#71717A] hover:text-white mb-4 flex items-center gap-1">
        <ArrowLeft className="w-3 h-3" /> All newsletters
      </button>

      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <div className="min-w-0">
          <h1 className="font-display font-bold text-3xl truncate">{pub.name}</h1>
          <div className="text-xs text-[#71717A] font-mono">/n/{pub.slug}</div>
        </div>
        <a href={`/n/${pub.slug}`} target="_blank" rel="noopener noreferrer"
          data-testid="pub-public-open"
          className="btn-ghost rounded-md gap-2 inline-flex items-center px-3 h-9 text-xs border border-[#27272A] hover:border-[#CCFF00]">
          <ExternalLink className="w-4 h-4" /> View public page
        </a>
      </div>

      <div className="flex gap-1 mb-6 flex-wrap border-b border-[#27272A]">
        {TABS.map((t) => (
          <button key={t.k} data-testid={`pub-tab-${t.k}`}
            onClick={() => setTab(t.k)}
            className={`px-3 py-2 text-xs font-medium transition flex items-center gap-1.5 border-b-2 -mb-px ${
              tab === t.k ? "text-white border-[#CCFF00]" : "text-[#71717A] border-transparent hover:text-white"
            }`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {tab === "posts" && <PostsTab pub={pub} />}
      {tab === "subs" && <SubscribersTab pub={pub} />}
      {tab === "analytics" && <AnalyticsTab pub={pub} />}
      {tab === "referrals" && <ReferralsTab pub={pub} />}
      {tab === "design" && <DesignTab pub={pub} onSaved={() => qc.invalidateQueries({ queryKey: ["publication", pubId] })} />}
      {tab === "settings" && <SettingsTab pub={pub} onDeleted={() => navigate("/newsletters")} />}
    </div>
  );
}

function PostsTab({ pub }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [tplOpen, setTplOpen] = useState(false);
  const [templates, setTemplates] = useState(null);
  const [tplBusy, setTplBusy] = useState(null);  // template id being applied
  const [savedTpls, setSavedTpls] = useState(null);
  const [tplPreview, setTplPreview] = useState({ id: null, html: "", busy: false });
  const { data: posts = [] } = useQuery({
    queryKey: ["posts", pub.id],
    queryFn: async () => (await api.get(`/newsletter/publications/${pub.id}/posts`)).data,
  });
  const create = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/newsletter/publications/${pub.id}/posts`,
        { title: "Untitled draft" });
      navigate(`/newsletters/${pub.id}/posts/${data.id}`);
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const openTemplates = async () => {
    setTplOpen(true);
    if (!templates) {
      try {
        const { data } = await api.get("/newsletter/templates");
        setTemplates(data);
      } catch (e) { toast.error(apiError(e)); }
    }
    if (!savedTpls) {
      try {
        const { data } = await api.get("/newsletter/saved-templates");
        setSavedTpls(data);
      } catch (e) { /* silent — table may not exist yet */ }
    }
  };
  const previewTemplate = async (tid, isSaved = false) => {
    setTplPreview({ id: tid, html: "", busy: true });
    try {
      if (isSaved) {
        // Render locally from stored blocks — no dedicated endpoint needed for saved templates.
        const st = (savedTpls || []).find((s) => s.id === tid);
        if (!st) throw new Error("Template not found");
        // Simpler: reuse curated preview endpoint isn't applicable — build a minimal HTML preview client-side.
        const html = _renderSavedTemplateHtml(st, pub);
        setTplPreview({ id: tid, html, busy: false });
      } else {
        const { data } = await api.get(
          `/newsletter/templates/${tid}/preview`,
          { responseType: "text", transformResponse: [(x) => x] });
        setTplPreview({ id: tid, html: data, busy: false });
      }
    } catch (e) { toast.error(apiError(e)); setTplPreview({ id: null, html: "", busy: false }); }
  };
  const applyTemplate = async (tid) => {
    setTplBusy(tid);
    try {
      const { data } = await api.post(
        `/newsletter/publications/${pub.id}/posts/from-template`,
        { template_id: tid });
      toast.success("Draft created from template");
      navigate(`/newsletters/${pub.id}/posts/${data.id}`);
    } catch (e) { toast.error(apiError(e)); }
    finally { setTplBusy(null); }
  };
  const applySavedTemplate = async (tid) => {
    setTplBusy(tid);
    try {
      const { data } = await api.post(
        `/newsletter/publications/${pub.id}/posts/from-saved/${tid}`);
      toast.success("Draft created from your saved template");
      navigate(`/newsletters/${pub.id}/posts/${data.id}`);
    } catch (e) { toast.error(apiError(e)); }
    finally { setTplBusy(null); }
  };
  const deleteSaved = async (tid, name) => {
    if (!window.confirm(`Delete template "${name}"?`)) return;
    try {
      await api.delete(`/newsletter/saved-templates/${tid}`);
      setSavedTpls((s) => (s || []).filter((t) => t.id !== tid));
      toast.success("Template deleted");
    } catch (e) { toast.error(apiError(e)); }
  };
  const del = async (id) => {
    if (!window.confirm("Delete this draft?")) return;
    try {
      await api.delete(`/newsletter/publications/${pub.id}/posts/${id}`);
      toast.success("Deleted");
      qc.invalidateQueries({ queryKey: ["posts", pub.id] });
    } catch (e) { toast.error(apiError(e)); }
  };
  return (
    <div>
      <div className="flex justify-end gap-2 mb-3">
        <Button data-testid="post-templates-btn" onClick={openTemplates}
          variant="ghost"
          className="rounded-md gap-2 border border-[#27272A] hover:border-fuchsia-400">
          <LayoutTemplate className="w-4 h-4" /> Start from template
        </Button>
        <Button data-testid="new-post-btn" onClick={create} disabled={busy}
          className="btn-primary rounded-md gap-2">
          {busy ? <Loader2 className="w-4 h-4 spin" /> : <Plus className="w-4 h-4" />} New post
        </Button>
      </div>
      <Dialog open={tplOpen} onOpenChange={(o) => { setTplOpen(o); if (!o) setTplPreview({ id: null, html: "", busy: false }); }}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-6xl h-[85vh] flex flex-col overflow-hidden"
          data-testid="templates-dialog">
          <DialogHeader>
            <DialogTitle>Start from a template</DialogTitle>
            <div className="text-xs text-[#71717A] mt-1">
              Preview any card first, then click "Use" to create a draft. Personal templates sit at the top.
            </div>
          </DialogHeader>
          {!templates ? (
            <div className="py-16 text-center"><Loader2 className="w-6 h-6 spin mx-auto text-[#CCFF00]" /></div>
          ) : (
            <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-4">
              <div className="overflow-y-auto pr-2 space-y-4">
                {savedTpls && savedTpls.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-widest text-emerald-300 mb-2">
                      Your workspace templates ({savedTpls.length})
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                      {savedTpls.map((t) => (
                        <div key={t.id} className="surface rounded-lg p-3 border border-emerald-500/20 flex items-center gap-3"
                          data-testid={`saved-template-${t.id}`}>
                          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center text-emerald-300 text-lg shrink-0">
                            <SaveIcon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-semibold text-sm truncate">{t.name}</div>
                            <div className="text-[11px] text-[#71717A] truncate">{t.title}</div>
                          </div>
                          <button onClick={() => previewTemplate(t.id, true)}
                            className="text-[11px] text-sky-300 hover:underline"
                            data-testid={`preview-saved-${t.id}`}>Preview</button>
                          <Button onClick={() => applySavedTemplate(t.id)} disabled={!!tplBusy}
                            data-testid={`use-saved-${t.id}`}
                            size="sm" className="btn-primary rounded-md h-8 text-[11px]">
                            {tplBusy === t.id ? <Loader2 className="w-3 h-3 spin" /> : "Use"}
                          </Button>
                          <button onClick={() => deleteSaved(t.id, t.name)}
                            data-testid={`delete-saved-${t.id}`}
                            className="text-[#71717A] hover:text-red-400">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div>
                  <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-2">Curated templates</div>
                  <div className="grid grid-cols-1 gap-2">
                    {templates.map((t) => (
                      <div key={t.id}
                        data-testid={`template-card-${t.id}`}
                        className={`surface rounded-lg p-4 border transition ${
                          tplPreview.id === t.id ? "border-[#CCFF00]" : "border-[#27272A] hover:border-[#CCFF00]/60"
                        }`}>
                        <div className="flex items-start gap-3">
                          <div className="w-11 h-11 rounded-lg flex items-center justify-center text-2xl shrink-0"
                            style={{ background: `${t.accent}22`, border: `1px solid ${t.accent}55` }}>
                            {t.preview_emoji}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <h3 className="font-display font-bold text-sm">{t.name}</h3>
                              <span className="text-[9px] uppercase tracking-widest px-1.5 py-0.5 rounded bg-[#27272A] text-[#A1A1AA]">
                                {t.category}
                              </span>
                            </div>
                            <p className="text-xs text-[#A1A1AA] mt-1 leading-relaxed">{t.description}</p>
                            <div className="mt-2 flex items-center gap-3">
                              <button onClick={() => previewTemplate(t.id)}
                                data-testid={`preview-template-${t.id}`}
                                className="inline-flex items-center gap-1 text-[11px] text-sky-300 hover:underline">
                                <Eye className="w-3 h-3" /> Preview
                              </button>
                              <button onClick={() => applyTemplate(t.id)}
                                disabled={!!tplBusy}
                                data-testid={`use-template-${t.id}`}
                                className="inline-flex items-center gap-1 text-[11px] font-medium"
                                style={{ color: t.accent }}>
                                {tplBusy === t.id ? (
                                  <><Loader2 className="w-3 h-3 spin" /> Creating…</>
                                ) : (
                                  <>Use this template →</>
                                )}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="rounded-md border border-[#27272A] bg-[#0A0A0A] overflow-hidden flex flex-col">
                <div className="px-3 py-2 border-b border-[#27272A] text-[10px] uppercase tracking-widest text-[#71717A]">
                  Live preview
                </div>
                {tplPreview.busy ? (
                  <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="w-6 h-6 spin text-[#CCFF00]" />
                  </div>
                ) : tplPreview.html ? (
                  <iframe title="tpl-preview" srcDoc={tplPreview.html}
                    data-testid="template-preview-iframe"
                    className="flex-1 bg-white border-0"
                    sandbox="allow-same-origin" />
                ) : (
                  <div className="flex-1 flex items-center justify-center text-[#71717A] text-xs px-6 text-center">
                    Click "Preview" on any template card to see how it will look.
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      {posts.length === 0 ? (
        <div className="surface rounded-lg p-12 text-center text-[#71717A]">
          No posts yet. Create your first draft.
        </div>
      ) : (
        <div className="surface rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#0A0A0A] text-[10px] uppercase tracking-widest text-[#71717A]">
              <tr>
                <th className="text-left px-4 py-2">Title</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-right px-4 py-2">Sent</th>
                <th className="text-right px-4 py-2">Opens</th>
                <th className="text-right px-4 py-2">Clicks</th>
                <th className="w-10 px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {posts.map((p) => (
                <tr key={p.id} data-testid={`post-row-${p.id}`}
                  className="border-t border-[#27272A] hover:bg-[#141414] cursor-pointer"
                  onClick={() => navigate(`/newsletters/${pub.id}/posts/${p.id}`)}>
                  <td className="px-4 py-3">
                    <div className="font-medium">{p.title}</div>
                    <div className="text-[10px] text-[#71717A] font-mono">/p/{p.slug}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                      p.status === "sent" ? "bg-emerald-500/15 text-emerald-400" :
                      p.status === "scheduled" ? "bg-amber-500/15 text-amber-400" :
                      "bg-[#27272A] text-[#A1A1AA]"
                    }`}>{p.status}</span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs">{p.stats?.sent || 0}</td>
                  <td className="px-4 py-3 text-right font-mono text-xs">{p.stats?.unique_opens || 0}</td>
                  <td className="px-4 py-3 text-right font-mono text-xs">{p.stats?.unique_clicks || 0}</td>
                  <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    {p.status !== "sent" && (
                      <button data-testid={`delete-post-${p.id}`} onClick={() => del(p.id)}
                        className="text-[#71717A] hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SubscribersTab({ pub }) {
  const qc = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const { data: subs = [] } = useQuery({
    queryKey: ["subs", pub.id],
    queryFn: async () => (await api.get(`/newsletter/publications/${pub.id}/subscribers`)).data,
  });
  const add = async () => {
    if (!email.includes("@")) { toast.error("Valid email required"); return; }
    try {
      await api.post(`/newsletter/publications/${pub.id}/subscribers`, { email, name, phone });
      toast.success("Subscriber added"); setAddOpen(false); setEmail(""); setName(""); setPhone("");
      qc.invalidateQueries({ queryKey: ["subs", pub.id] });
    } catch (e) { toast.error(apiError(e)); }
  };
  const remove = async (sid) => {
    if (!window.confirm("Remove this subscriber?")) return;
    try {
      await api.delete(`/newsletter/publications/${pub.id}/subscribers/${sid}`);
      toast.success("Removed");
      qc.invalidateQueries({ queryKey: ["subs", pub.id] });
    } catch (e) { toast.error(apiError(e)); }
  };
  const importCsv = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post(
        `/newsletter/publications/${pub.id}/subscribers/import-csv`, fd,
        { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Imported ${data.created} · Skipped ${data.skipped}`);
      qc.invalidateQueries({ queryKey: ["subs", pub.id] });
    } catch (e) { toast.error(apiError(e)); }
  };
  const importCustomers = async () => {
    if (!window.confirm("Import every customer in this workspace as a subscriber? Previously unsubscribed customers will be respected.")) return;
    try {
      const { data } = await api.post(`/newsletter/publications/${pub.id}/import-customers`);
      toast.success(`Imported ${data.created} new · Skipped ${data.skipped}`);
      qc.invalidateQueries({ queryKey: ["subs", pub.id] });
    } catch (e) { toast.error(apiError(e)); }
  };
  return (
    <div>
      <div className="flex justify-end gap-2 mb-3 flex-wrap">
        <Button data-testid="import-customers-btn" onClick={importCustomers} variant="ghost"
          className="btn-ghost rounded-md gap-2 border border-[#27272A] hover:border-[#CCFF00] h-9 text-sm">
          <Users className="w-4 h-4" /> Import from Customers
        </Button>
        <label className="btn-ghost rounded-md cursor-pointer gap-2 inline-flex items-center px-3 h-9 text-sm border border-[#27272A] hover:border-[#CCFF00]"
          data-testid="import-subs-csv">
          <Upload className="w-4 h-4" /> Import CSV
          <input type="file" accept=".csv" className="hidden"
            data-testid="import-subs-csv-input"
            onChange={(e) => { importCsv(e.target.files?.[0]); e.target.value = ""; }} />
        </label>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button data-testid="add-subscriber-btn" className="btn-primary rounded-md gap-2">
              <Plus className="w-4 h-4" /> Add
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#141414] border-[#27272A] text-white">
            <DialogHeader><DialogTitle>Add subscriber</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input data-testid="add-sub-email" placeholder="email@example.com" value={email} onChange={(e) => setEmail(e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white" />
              <Input data-testid="add-sub-name" placeholder="Name (optional)" value={name} onChange={(e) => setName(e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white" />
              <Input data-testid="add-sub-phone" placeholder="Phone (optional, for SMS/WhatsApp)"
                value={phone} onChange={(e) => setPhone(e.target.value)}
                className="bg-[#0A0A0A] border-[#27272A] text-white font-mono text-xs" />
            </div>
            <DialogFooter>
              <Button data-testid="add-sub-submit" onClick={add} className="btn-primary rounded-md">Add subscriber</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      {subs.length === 0 ? (
        <div className="surface rounded-lg p-12 text-center text-[#71717A]">No subscribers yet.</div>
      ) : (
        <div className="surface rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#0A0A0A] text-[10px] uppercase tracking-widest text-[#71717A]">
              <tr>
                <th className="text-left px-4 py-2">Email</th>
                <th className="text-left px-4 py-2">Name</th>
                <th className="text-left px-4 py-2">Phone</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-left px-4 py-2">Source</th>
                <th className="text-right px-4 py-2">Refs</th>
                <th className="w-10 px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {subs.map((s) => (
                <tr key={s.id} className="border-t border-[#27272A]" data-testid={`sub-row-${s.id}`}>
                  <td className="px-4 py-2 font-mono text-xs">{s.email}</td>
                  <td className="px-4 py-2 text-[#A1A1AA]">{s.name || "—"}</td>
                  <td className="px-4 py-2 font-mono text-xs text-[#A1A1AA]">{s.phone || "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                      s.status === "subscribed" ? "bg-emerald-500/15 text-emerald-400" :
                      s.status === "pending" ? "bg-amber-500/15 text-amber-400" :
                      "bg-red-500/15 text-red-400"
                    }`}>{s.status}</span>
                  </td>
                  <td className="px-4 py-2 text-[10px] text-[#71717A]">{s.source}</td>
                  <td className="px-4 py-2 text-right font-mono text-xs">{s.referral_count || 0}</td>
                  <td className="px-4 py-2">
                    <button data-testid={`remove-sub-${s.id}`} onClick={() => remove(s.id)}
                      className="text-[#71717A] hover:text-red-400"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AnalyticsTab({ pub }) {
  const { data } = useQuery({
    queryKey: ["nl-analytics", pub.id],
    queryFn: async () => (await api.get(`/newsletter/publications/${pub.id}/analytics`)).data,
  });
  if (!data) return <div className="text-[#71717A]">Loading…</div>;
  return (
    <div className="space-y-4" data-testid="analytics-tab">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Active subscribers" value={data.subscribers_active} accent="#CCFF00" />
        <Stat label="Total (incl. pending / unsub)" value={data.subscribers_total} />
        <Stat label="Posts sent" value={data.posts_sent} />
      </div>
      {data.top_posts?.length > 0 && (
        <div className="surface rounded-lg p-4">
          <h3 className="font-display font-bold text-sm mb-3">Top posts by unique opens</h3>
          <div className="space-y-1 text-sm">
            {data.top_posts.map((p) => (
              <div key={p.id} className="flex justify-between text-xs" data-testid={`analytics-top-post-${p.id}`}>
                <span className="truncate mr-2">{p.title}</span>
                <span className="font-mono text-[#CCFF00]">{p.stats?.unique_opens || 0}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="surface rounded-lg p-4">
      <div className="text-xs uppercase text-[#71717A]">{label}</div>
      <div className="text-3xl font-bold mt-1" style={accent ? { color: accent } : {}}>{value}</div>
    </div>
  );
}

function ReferralsTab({ pub }) {
  const { data } = useQuery({
    queryKey: ["nl-analytics", pub.id],
    queryFn: async () => (await api.get(`/newsletter/publications/${pub.id}/analytics`)).data,
  });
  return (
    <div className="space-y-4" data-testid="referrals-tab">
      <div className="surface rounded-lg p-5">
        <h3 className="font-display font-bold text-sm mb-3">Milestone rewards</h3>
        <p className="text-xs text-[#71717A] mb-4">
          Every subscriber gets a unique referral link. Cross a milestone → an active coupon is auto-issued to them via email.
        </p>
        <div className="grid grid-cols-3 gap-3">
          {(pub.referral_rewards || []).map((r, i) => (
            <div key={i} className="rounded-md p-4 bg-[#0A0A0A] border border-[#27272A]">
              <div className="text-[10px] uppercase tracking-widest text-[#71717A]">Refer</div>
              <div className="text-2xl font-bold">{r.count}</div>
              <div className="text-xs text-[#CCFF00] font-bold mt-1">→ {r.coupon_percent}% off coupon</div>
            </div>
          ))}
        </div>
      </div>
      <div className="surface rounded-lg p-5">
        <h3 className="font-display font-bold text-sm mb-3">Top referrers</h3>
        {(!data?.top_referrers?.length) ? (
          <div className="text-xs text-[#71717A]">No referrals yet. Add a Referral CTA block to your posts.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-[10px] uppercase tracking-widest text-[#71717A]">
              <tr><th className="text-left py-2">Email</th><th className="text-right py-2">Refs</th></tr>
            </thead>
            <tbody>
              {data.top_referrers.map((r) => (
                <tr key={r.email} className="border-t border-[#27272A]" data-testid={`top-referrer-${r.email}`}>
                  <td className="py-2 font-mono text-xs">{r.email}</td>
                  <td className="py-2 text-right font-mono text-xs text-[#CCFF00]">{r.referral_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function DesignTab({ pub, onSaved }) {
  const [f, setF] = useState({
    subscribe_headline: pub.subscribe_headline || "",
    subscribe_body: pub.subscribe_body || "",
    thanks_headline: pub.thanks_headline || "",
    thanks_body: pub.thanks_body || "",
    primary_color: pub.primary_color || "#005CEE",
  });
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/newsletter/publications/${pub.id}`, { name: pub.name, ...f });
      toast.success("Design saved"); onSaved?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-5 max-w-2xl" data-testid="design-tab">
      <div className="surface rounded-lg p-5 space-y-4">
        <h3 className="font-display font-bold text-sm">Landing page copy</h3>
        <div><Label className="text-xs text-[#A1A1AA]">Subscribe headline</Label>
          <Input value={f.subscribe_headline} onChange={(e) => setF({ ...f, subscribe_headline: e.target.value })}
            data-testid="design-subscribe-headline"
            className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <div><Label className="text-xs text-[#A1A1AA]">Subscribe subline</Label>
          <Input value={f.subscribe_body} onChange={(e) => setF({ ...f, subscribe_body: e.target.value })}
            className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <div><Label className="text-xs text-[#A1A1AA]">Thanks headline</Label>
          <Input value={f.thanks_headline} onChange={(e) => setF({ ...f, thanks_headline: e.target.value })}
            className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <div><Label className="text-xs text-[#A1A1AA]">Thanks body</Label>
          <Textarea value={f.thanks_body} onChange={(e) => setF({ ...f, thanks_body: e.target.value })}
            rows={2} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <div><Label className="text-xs text-[#A1A1AA]">Brand color</Label>
          <div className="flex gap-2 mt-1">
            <Input type="color" value={f.primary_color} onChange={(e) => setF({ ...f, primary_color: e.target.value })}
              className="w-14 h-10 p-1 bg-[#0A0A0A] border-[#27272A]" />
            <Input value={f.primary_color} onChange={(e) => setF({ ...f, primary_color: e.target.value })}
              className="flex-1 bg-[#0A0A0A] border-[#27272A] text-white font-mono text-xs" />
          </div>
        </div>
        <Button data-testid="design-save" onClick={save} disabled={busy} className="btn-primary rounded-md gap-2">
          {busy && <Loader2 className="w-4 h-4 spin" />} Save design
        </Button>
      </div>
      <SendingDomainPanel pub={pub} onChanged={onSaved} />
    </div>
  );
}

function SendingDomainPanel({ pub, onChanged }) {
  const [domain, setDomain] = useState(null);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(null);
  const [copied, setCopied] = useState(null);

  const load = async () => {
    try {
      const { data } = await api.get(`/newsletter/publications/${pub.id}/domain`);
      setDomain(data);
    } catch (e) { toast.error(apiError(e)); }
  };
  useEffect(() => { load(); }, [pub.id]);

  const add = async () => {
    if (!name.trim() || !name.includes(".")) { toast.error("Enter a valid domain"); return; }
    setBusy("add");
    try {
      const { data } = await api.post(`/newsletter/publications/${pub.id}/domain`, { name });
      setDomain(data); setName("");
      toast.success("Domain added — now publish the DNS records below");
      onChanged?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };
  const verify = async () => {
    setBusy("verify");
    try {
      const { data } = await api.post(`/newsletter/publications/${pub.id}/domain/verify`);
      setDomain(data);
      toast.success(data.status === "verified" ? "Domain verified ✓" : `Status: ${data.status}`);
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };
  const remove = async () => {
    if (!window.confirm("Remove this sending domain?")) return;
    setBusy("remove");
    try {
      await api.delete(`/newsletter/publications/${pub.id}/domain`);
      setDomain({ configured: false });
      toast.success("Domain removed");
      onChanged?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };
  const copyValue = (v, k) => {
    navigator.clipboard.writeText(v);
    setCopied(k); setTimeout(() => setCopied(null), 1200);
  };

  return (
    <div className="surface rounded-lg p-5" data-testid="sending-domain-panel">
      <h3 className="font-display font-bold text-sm mb-1">Custom sending domain</h3>
      <p className="text-xs text-[#71717A] mb-4">
        Send from <span className="font-mono">hello@yourdomain.com</span> instead of the shared PromoOS
        sender. Requires Resend + DNS access.
      </p>
      {!domain?.configured ? (
        <div className="flex gap-2 flex-wrap">
          <Input value={name} onChange={(e) => setName(e.target.value)}
            placeholder="mail.yourdomain.com"
            data-testid="domain-name-input"
            className="flex-1 min-w-[220px] bg-[#0A0A0A] border-[#27272A] text-white font-mono text-sm" />
          <Button data-testid="domain-add-btn" onClick={add} disabled={busy === "add"} className="btn-primary rounded-md gap-2">
            {busy === "add" && <Loader2 className="w-4 h-4 spin" />} Add domain
          </Button>
        </div>
      ) : (
        <div className="space-y-3" data-testid="domain-status">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-mono text-sm">{domain.name}</span>
            <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
              domain.status === "verified" ? "bg-emerald-500/15 text-emerald-400" :
              domain.status === "pending" ? "bg-amber-500/15 text-amber-400" :
              "bg-red-500/15 text-red-400"
            }`}>{domain.status || "unknown"}</span>
            <div className="ml-auto flex gap-2">
              <Button data-testid="domain-verify-btn" onClick={verify} disabled={busy === "verify"}
                className="btn-ghost rounded-md gap-2 border border-[#27272A] hover:border-[#CCFF00] h-8 text-xs">
                {busy === "verify" ? <Loader2 className="w-3.5 h-3.5 spin" /> : null} Re-check
              </Button>
              <Button data-testid="domain-remove-btn" onClick={remove} disabled={busy === "remove"}
                className="rounded-md gap-2 bg-red-500/10 text-red-300 border border-red-500/40 hover:bg-red-500/20 h-8 text-xs">
                Remove
              </Button>
            </div>
          </div>
          {domain.warning && (
            <div className="text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/30 rounded p-2">
              {domain.warning}
            </div>
          )}
          {(domain.records || []).length > 0 && (
            <div className="rounded-md border border-[#27272A] overflow-hidden" data-testid="domain-records">
              <div className="bg-[#0A0A0A] px-3 py-2 text-[10px] uppercase tracking-widest text-[#71717A]">
                DNS records to publish
              </div>
              <table className="w-full text-xs">
                <thead className="text-[9px] uppercase tracking-widest text-[#71717A]">
                  <tr>
                    <th className="text-left px-3 py-1.5">Type</th>
                    <th className="text-left px-3 py-1.5">Name</th>
                    <th className="text-left px-3 py-1.5">Value</th>
                    <th className="w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {domain.records.map((r, i) => (
                    <tr key={i} className="border-t border-[#27272A]">
                      <td className="px-3 py-1.5 font-mono">{r.type || r.record}</td>
                      <td className="px-3 py-1.5 font-mono text-[#A1A1AA] break-all">{r.name}</td>
                      <td className="px-3 py-1.5 font-mono text-[#A1A1AA] break-all max-w-md truncate" title={r.value}>{r.value}</td>
                      <td className="px-2 py-1.5">
                        <button onClick={() => copyValue(r.value, `${i}`)}
                          data-testid={`domain-copy-${i}`}
                          title="Copy value"
                          className="text-[#71717A] hover:text-[#CCFF00]">
                          <Copy className="w-3.5 h-3.5" />
                          {copied === `${i}` && <span className="ml-1 text-[9px] text-emerald-400">✓</span>}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="text-[10px] text-[#71717A]">
            After publishing the records at your DNS provider, wait 10-20 minutes then hit "Re-check".
            Once <b>verified</b>, set the "Sender email" in Settings to use this domain.
          </p>
        </div>
      )}
    </div>
  );
}

function SettingsTab({ pub, onDeleted }) {
  const [f, setF] = useState({
    name: pub.name, description: pub.description || "",
    sender_name: pub.sender_name || "", sender_email: pub.sender_email || "",
  });
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/newsletter/publications/${pub.id}`,
        { ...f, sender_email: f.sender_email || null });
      toast.success("Saved");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const del = async () => {
    if (!window.confirm(`Delete "${pub.name}"? This removes all subscribers, posts, and events.`)) return;
    if (!window.confirm("Really sure? This cannot be undone.")) return;
    try {
      await api.delete(`/newsletter/publications/${pub.id}`);
      toast.success("Publication deleted"); onDeleted?.();
    } catch (e) { toast.error(apiError(e)); }
  };
  return (
    <div className="space-y-4 max-w-2xl" data-testid="settings-tab">
      <div className="surface rounded-lg p-5 space-y-3">
        <div><Label className="text-xs text-[#A1A1AA]">Name</Label>
          <Input data-testid="settings-name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}
            className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <div><Label className="text-xs text-[#A1A1AA]">Description</Label>
          <Textarea value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })}
            rows={2} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <div><Label className="text-xs text-[#A1A1AA]">Sender name</Label>
          <Input value={f.sender_name} onChange={(e) => setF({ ...f, sender_name: e.target.value })}
            className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <div><Label className="text-xs text-[#A1A1AA]">Sender email (must be verified in Resend)</Label>
          <Input data-testid="settings-sender-email" value={f.sender_email}
            onChange={(e) => setF({ ...f, sender_email: e.target.value })}
            placeholder="you@yourdomain.com"
            className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
        <Button data-testid="settings-save" onClick={save} disabled={busy} className="btn-primary rounded-md gap-2">
          {busy && <Loader2 className="w-4 h-4 spin" />} Save
        </Button>
      </div>
      <div className="surface rounded-lg p-5 border border-red-500/30">
        <h3 className="font-display font-bold text-sm text-red-300 mb-2">Danger zone</h3>
        <Button data-testid="settings-delete-pub" onClick={del}
          className="rounded-md bg-red-500/10 text-red-300 border border-red-500/40 hover:bg-red-500/20">
          Delete this newsletter
        </Button>
      </div>
    </div>
  );
}
