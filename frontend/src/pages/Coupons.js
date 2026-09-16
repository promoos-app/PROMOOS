import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { STATE_STYLES, TYPE_LABELS, discountText } from "@/lib/couponUtils";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Search, MoreHorizontal, Ticket, Share2, Download, Copy, Sparkles, ImageIcon, Loader2, Upload } from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

const FILTERS = ["all", "draft", "scheduled", "active", "paused", "expired", "archived"];
const NEXT_STATES = ["draft", "scheduled", "active", "paused", "expired", "archived"];

export default function Coupons() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(new Set());
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkBg, setBulkBg] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkStateBusy, setBulkStateBusy] = useState(false);
  const [csvPreview, setCsvPreview] = useState(null);
  const [csvBusy, setCsvBusy] = useState(false);

  const commitCsv = async () => {
    if (!csvPreview?.file) return;
    setCsvBusy(true);
    try {
      const fd = new FormData(); fd.append("file", csvPreview.file);
      const { data } = await api.post("/coupons/import-csv", fd,
        { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Imported ${data.created} coupon${data.created === 1 ? "" : "s"}`);
      if (data.errors?.length) toast.warning(`${data.errors.length} row error(s) skipped`);
      qc.invalidateQueries({ queryKey: ["coupons"] });
      setCsvPreview(null);
    } catch (e) { toast.error(apiError(e)); } finally { setCsvBusy(false); }
  };

  const bulkState = async (state) => {
    if (selected.size === 0) return;
    if (!window.confirm(`Move ${selected.size} coupon${selected.size === 1 ? "" : "s"} to "${state}"?`)) return;
    setBulkStateBusy(true);
    try {
      const { data } = await api.post("/coupons/bulk-state",
        { coupon_ids: Array.from(selected), state });
      toast.success(`${data.updated} coupon${data.updated === 1 ? "" : "s"} → ${state}`);
      qc.invalidateQueries({ queryKey: ["coupons"] });
      clearSelection();
    } catch (e) { toast.error(apiError(e)); } finally { setBulkStateBusy(false); }
  };

  const toggleSelect = (id) => setSelected((s) => {
    const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n;
  });
  const selectAllVisible = (rows) => setSelected((s) => {
    const n = new Set(s); rows.forEach((r) => n.add(r.id)); return n;
  });
  const clearSelection = () => setSelected(new Set());

  const uploadBulkBg = async (file) => {
    if (!file || !file.type.startsWith("image/")) { toast.error("Drop an image file"); return; }
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setBulkBg(`${process.env.REACT_APP_BACKEND_URL}${data.url}`);
      toast.success("Image uploaded — click Apply");
    } catch (e) { toast.error(apiError(e)); }
  };
  const applyBulkBg = async () => {
    if (!bulkBg.trim() || selected.size === 0) return;
    setBulkBusy(true);
    try {
      const { data } = await api.post("/coupons/bulk-background",
        { coupon_ids: Array.from(selected), bg_image: bulkBg.trim() });
      toast.success(`Applied to ${data.updated} coupon${data.updated === 1 ? "" : "s"}`);
      qc.invalidateQueries({ queryKey: ["coupons"] });
      setBulkOpen(false); setBulkBg(""); clearSelection();
    } catch (e) { toast.error(apiError(e)); } finally { setBulkBusy(false); }
  };

  const { data: coupons = [], isLoading } = useQuery({
    queryKey: ["coupons", filter],
    queryFn: async () => (await api.get(`/coupons?state=${filter}`)).data,
  });

  const filtered = coupons.filter((c) => c.name.toLowerCase().includes(search.toLowerCase()) || c.code.toLowerCase().includes(search.toLowerCase()));

  const changeState = async (id, state) => {
    try {
      await api.post(`/coupons/${id}/state`, { state });
      qc.invalidateQueries({ queryKey: ["coupons"] });
      toast.success(`Moved to ${state}`);
    } catch (e) { toast.error(apiError(e)); }
  };
  const del = async (id) => {
    try {
      await api.delete(`/coupons/${id}`);
      qc.invalidateQueries({ queryKey: ["coupons"] });
      toast.success("Coupon deleted");
    } catch (e) { toast.error(apiError(e)); }
  };

  const [shareData, setShareData] = useState(null);
  const openShare = async (cid) => {
    try {
      const { data } = await api.get(`/coupons/${cid}/share`);
      setShareData({ ...data, cid });
    } catch (e) { toast.error(apiError(e)); }
  };
  const downloadPng = async (cid, code) => {
    try {
      const res = await api.get(`/coupons/${cid}/download.png`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url; a.download = `coupon-${code}.png`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      toast.success("Downloaded");
    } catch (e) { toast.error(apiError(e)); }
  };
  const publish = async (cid) => {
    try { await api.post(`/coupons/${cid}/publish`); qc.invalidateQueries({ queryKey: ["coupons"] }); toast.success("Coupon published"); }
    catch (e) { toast.error(apiError(e)); }
  };
  const cp = (t) => { navigator.clipboard.writeText(t).catch(() => {}); toast.success("Copied"); };

  return (
    <div className="fade-up max-w-[1400px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight">Coupons</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Create, manage and publish your offers.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="btn-ghost rounded-md cursor-pointer gap-2 inline-flex items-center px-3 h-9 text-sm border border-[#27272A] hover:border-[#CCFF00]" data-testid="import-csv-btn"
            title="Bulk-create coupons from a CSV">
            <Upload className="w-4 h-4" /> Import CSV
            <input type="file" accept=".csv" className="hidden" data-testid="import-csv-input"
              onChange={async (e) => {
                const f = e.target.files?.[0]; if (!f) return;
                const fd = new FormData(); fd.append("file", f);
                try {
                  const { data } = await api.post("/coupons/import-csv?dry_run=true", fd,
                    { headers: { "Content-Type": "multipart/form-data" } });
                  const csvHeaders = data.csv_headers || [];
                  // Auto-map exact matches. Unknown headers stay unmapped.
                  const INTERNAL = ["name","code","type","discount_value","headline","description","terms","cta","state"];
                  const initialMapping = {};
                  csvHeaders.forEach((h) => {
                    const norm = h.trim().toLowerCase();
                    if (INTERNAL.includes(norm)) initialMapping[h] = norm;
                  });
                  setCsvPreview({
                    file: f,
                    preview: data.preview || [], errors: data.errors || [],
                    total_valid: data.total_valid || 0,
                    csv_headers: csvHeaders, mapping: initialMapping,
                  });
                } catch (er) { toast.error(apiError(er)); }
                finally { e.target.value = ""; }
              }} />
          </label>
          <Button data-testid="new-coupon-btn" onClick={() => navigate("/coupons/new")} className="btn-primary gap-2 rounded-md">
            <Plus className="w-4 h-4" /> New Coupon
          </Button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex gap-1 flex-wrap">
          {FILTERS.map((f) => (
            <button key={f} data-testid={`filter-${f}`} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-md text-sm capitalize transition-colors ${
                filter === f ? "bg-[#141414] text-white border border-[#27272A]" : "text-[#A1A1AA] hover:text-white"
              }`}>{f}</button>
          ))}
        </div>
        <div className="relative sm:ml-auto sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
          <Input data-testid="coupon-search" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search coupons…" className="pl-9 bg-[#141414] border-[#27272A] text-white h-9" />
        </div>
      </div>

      <div className="surface rounded-lg overflow-hidden">
        {selected.size > 0 && (
          <div className="flex items-center justify-between gap-3 p-3 bg-[#CCFF00]/5 border-b border-[#CCFF00]/30 flex-wrap" data-testid="coupons-bulk-bar">
            <div className="text-xs text-[#CCFF00] font-bold">{selected.size} selected</div>
            <div className="flex items-center gap-2 flex-wrap">
              <Button data-testid="coupons-bulk-bg-btn" onClick={() => setBulkOpen(true)}
                className="btn-primary rounded-md gap-2 h-8 text-xs">
                <ImageIcon className="w-3 h-3" /> Set background
              </Button>
              <Button data-testid="coupons-bulk-publish"
                onClick={() => bulkState("active")} disabled={bulkStateBusy}
                className="btn-ghost rounded-md gap-2 h-8 text-xs border border-[#27272A]">
                <Sparkles className="w-3 h-3" /> Publish
              </Button>
              <Button data-testid="coupons-bulk-pause"
                onClick={() => bulkState("paused")} disabled={bulkStateBusy}
                className="btn-ghost rounded-md gap-2 h-8 text-xs border border-[#27272A]">
                Pause
              </Button>
              <Button data-testid="coupons-bulk-expire"
                onClick={() => bulkState("expired")} disabled={bulkStateBusy}
                className="btn-ghost rounded-md gap-2 h-8 text-xs border border-[#27272A]">
                Expire
              </Button>
              <Button data-testid="coupons-bulk-archive"
                onClick={() => bulkState("archived")} disabled={bulkStateBusy}
                className="btn-ghost rounded-md gap-2 h-8 text-xs border border-[#27272A]">
                Archive
              </Button>
              <button onClick={clearSelection} className="text-xs text-[#71717A] hover:text-white">Clear</button>
            </div>
          </div>
        )}
        {isLoading ? (
          <div className="p-12 text-center text-[#71717A]">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-16 text-center">
            <Ticket className="w-10 h-10 mx-auto text-[#3a3a3e] mb-3" />
            <p className="text-[#A1A1AA]">No coupons yet.</p>
            <Button data-testid="empty-new-coupon-btn" onClick={() => navigate("/coupons/new")} className="btn-ai mt-4 rounded-md gap-2">
              <Plus className="w-4 h-4" /> Create your first coupon
            </Button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-[#71717A] border-b border-[#27272A]">
                <th className="w-10 p-4">
                  <input type="checkbox" data-testid="coupons-select-all"
                    checked={filtered.length > 0 && filtered.every((c) => selected.has(c.id))}
                    onChange={(e) => e.target.checked ? selectAllVisible(filtered) : clearSelection()} />
                </th>
                <th className="text-left font-medium p-4">Name</th>
                <th className="text-left font-medium p-4">Code</th>
                <th className="text-left font-medium p-4">Type</th>
                <th className="text-left font-medium p-4">Discount</th>
                <th className="text-left font-medium p-4">State</th>
                <th className="text-right font-medium p-4">Redemptions</th>
                <th className="w-10 p-4"></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} data-testid={`coupon-row-${c.id}`}
                  className="border-b border-[#1E1E1E] last:border-0 hover:bg-[#141414] transition-colors cursor-pointer"
                  onClick={() => navigate(`/coupons/${c.id}`)}>
                  <td className="p-4" onClick={(e) => e.stopPropagation()}>
                    <input type="checkbox" data-testid={`coupon-select-${c.id}`}
                      checked={selected.has(c.id)} onChange={() => toggleSelect(c.id)} />
                  </td>
                  <td className="p-4 font-medium">{c.name}</td>
                  <td className="p-4"><span className="font-mono text-xs bg-[#0A0A0A] border border-[#27272A] px-2 py-1 rounded">{c.code}</span></td>
                  <td className="p-4 text-[#A1A1AA]">{TYPE_LABELS[c.type] || c.type}</td>
                  <td className="p-4 font-mono">{discountText(c)}</td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded text-xs capitalize font-medium ${STATE_STYLES[c.state]}`}>{c.state}</span>
                  </td>
                  <td className="p-4 text-right font-mono">{c.stats?.redemptions ?? 0}</td>
                  <td className="p-4" onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button data-testid={`coupon-menu-${c.id}`} className="p-1.5 rounded hover:bg-[#1E1E1E] transition-colors">
                          <MoreHorizontal className="w-4 h-4 text-[#A1A1AA]" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="bg-[#141414] border-[#27272A] text-white">
                        <DropdownMenuItem className="focus:bg-[#1E1E1E]" onClick={() => navigate(`/coupons/${c.id}/edit`)}>Edit</DropdownMenuItem>
                        <DropdownMenuItem className="focus:bg-[#1E1E1E]" onClick={() => navigate(`/coupons/${c.id}`)}>View & QR</DropdownMenuItem>
                        <DropdownMenuItem data-testid={`publish-${c.id}`} className="focus:bg-[#1E1E1E]" onClick={() => publish(c.id)}>
                          <Sparkles className="w-3.5 h-3.5 mr-2 text-[#CCFF00]" /> Publish
                        </DropdownMenuItem>
                        <DropdownMenuItem data-testid={`share-${c.id}`} className="focus:bg-[#1E1E1E]" onClick={() => openShare(c.id)}>
                          <Share2 className="w-3.5 h-3.5 mr-2" /> Share & embed
                        </DropdownMenuItem>
                        <DropdownMenuItem data-testid={`download-${c.id}`} className="focus:bg-[#1E1E1E]" onClick={() => downloadPng(c.id, c.code)}>
                          <Download className="w-3.5 h-3.5 mr-2" /> Download PNG
                        </DropdownMenuItem>
                        <DropdownMenuSeparator className="bg-[#27272A]" />
                        {NEXT_STATES.filter((s) => s !== c.state).map((s) => (
                          <DropdownMenuItem key={s} className="focus:bg-[#1E1E1E] capitalize" onClick={() => changeState(c.id, s)}>
                            Move to {s}
                          </DropdownMenuItem>
                        ))}
                        <DropdownMenuSeparator className="bg-[#27272A]" />
                        <DropdownMenuItem className="focus:bg-[#1E1E1E] text-red-400" onClick={() => del(c.id)}>Delete</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Dialog open={!!shareData} onOpenChange={(v) => !v && setShareData(null)}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="share-dialog">
          <DialogHeader><DialogTitle className="flex items-center gap-2"><Share2 className="w-5 h-5 text-[#CCFF00]" /> Share & embed</DialogTitle></DialogHeader>
          {shareData && (
            <div className="space-y-4">
              <div>
                <div className="text-xs uppercase tracking-widest text-[#71717A] mb-1">Landing page</div>
                <div className="flex gap-1">
                  <code className="flex-1 text-xs font-mono bg-[#0A0A0A] border border-[#27272A] rounded px-2 py-1.5 break-all">{shareData.landing_url}</code>
                  <button onClick={() => cp(shareData.landing_url)} className="p-1.5 rounded hover:bg-white/5"><Copy className="w-3.5 h-3.5" /></button>
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-widest text-[#71717A] mb-1">Share on socials</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(shareData.share_links).map(([k, v]) => (
                    <a key={k} href={v} target="_blank" rel="noopener noreferrer" data-testid={`share-link-${k}`}
                       className="btn-ghost rounded-md text-xs px-3 py-1.5 capitalize">{k}</a>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-widest text-[#71717A] mb-1">Embed on your site (5 variants)</div>
                <div className="space-y-2">
                  {Object.entries(shareData.embed_snippets).map(([variant, snippet]) => (
                    <div key={variant} data-testid={`embed-${variant}`}>
                      <div className="text-[10px] uppercase tracking-widest text-[#CCFF00] mb-0.5">{variant}</div>
                      <div className="flex gap-1">
                        <code className="flex-1 text-[10px] font-mono bg-[#0A0A0A] border border-[#27272A] rounded px-2 py-1.5 break-all">{snippet}</code>
                        <button onClick={() => cp(snippet)} className="p-1.5 rounded hover:bg-white/5"><Copy className="w-3.5 h-3.5" /></button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <Button data-testid="dialog-download-png" onClick={() => downloadPng(shareData.cid, shareData.code)} className="btn-primary rounded-md gap-2 w-full">
                <Download className="w-4 h-4" /> Download printable PNG (1200×630)
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-lg" data-testid="coupons-bulk-bg-dialog">
          <DialogHeader><DialogTitle>Set background · {selected.size} coupon{selected.size === 1 ? "" : "s"}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div
              onDragOver={(e) => { e.preventDefault(); e.currentTarget.dataset.hover = "1"; }}
              onDragLeave={(e) => { delete e.currentTarget.dataset.hover; }}
              onDrop={(e) => { e.preventDefault(); delete e.currentTarget.dataset.hover; uploadBulkBg(e.dataTransfer?.files?.[0]); }}
              className="border-2 border-dashed border-[#27272A] hover:border-[#CCFF00] rounded-md p-6 text-center text-xs text-[#71717A] transition-colors data-[hover='1']:border-[#CCFF00] data-[hover='1']:bg-[#CCFF00]/5"
              data-testid="coupons-bulk-bg-dropzone"
            >
              {bulkBg ? (
                <div className="flex items-center gap-3">
                  <div className="w-24 h-16 rounded overflow-hidden border border-[#27272A]"
                    style={{ backgroundImage: `url(${bulkBg})`, backgroundSize: "cover", backgroundPosition: "center" }} />
                  <div className="text-left">
                    <div className="text-white text-[11px] truncate max-w-xs">{bulkBg}</div>
                    <div className="text-[10px] text-[#71717A]">Drop a new image to replace</div>
                  </div>
                </div>
              ) : (
                <>
                  <div className="text-white text-sm mb-1">Drop your hero image here</div>
                  <div>or</div>
                  <label className="btn-ghost inline-flex items-center gap-2 cursor-pointer rounded-md px-3 py-1.5 text-[10px] mt-2 uppercase tracking-widest">
                    Choose file
                    <input type="file" accept="image/*" className="hidden" data-testid="coupons-bulk-bg-file"
                      onChange={(e) => uploadBulkBg(e.target.files?.[0])} />
                  </label>
                </>
              )}
            </div>
            <Input value={bulkBg} onChange={(e) => setBulkBg(e.target.value)}
              placeholder="or paste a URL"
              data-testid="coupons-bulk-bg-url"
              className="bg-[#0A0A0A] border-[#27272A] text-white text-xs font-mono" />
            <Button data-testid="coupons-bulk-bg-apply"
              onClick={applyBulkBg} disabled={bulkBusy || !bulkBg.trim()}
              className="btn-primary rounded-md gap-2 w-full">
              {bulkBusy && <Loader2 className="w-4 h-4 spin" />}
              Apply to {selected.size} coupon{selected.size === 1 ? "" : "s"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={!!csvPreview} onOpenChange={(o) => !o && setCsvPreview(null)}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-2xl" data-testid="csv-preview-dialog">
          <DialogHeader><DialogTitle>Preview import · {csvPreview?.file?.name}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="text-xs text-[#A1A1AA]">
              <span className="text-[#CCFF00] font-bold">{csvPreview?.total_valid ?? 0}</span> row{csvPreview?.total_valid === 1 ? "" : "s"} will be created ·{" "}
              <span className={csvPreview?.errors?.length ? "text-red-400" : ""}>{csvPreview?.errors?.length ?? 0} skipped</span>
            </div>
            {(csvPreview?.preview || []).length > 0 ? (
              <div className="rounded-md border border-[#27272A] overflow-hidden">
                <table className="w-full text-xs" data-testid="csv-preview-table">
                  <thead className="bg-[#0A0A0A] text-[10px] uppercase tracking-widest text-[#71717A]">
                    <tr>
                      <th className="text-left px-2 py-2 w-8">#</th>
                      <th className="text-left px-2 py-2">Name</th>
                      <th className="text-left px-2 py-2">Code</th>
                      <th className="text-left px-2 py-2">Type</th>
                      <th className="text-right px-2 py-2">Disc.</th>
                      <th className="text-left px-2 py-2">State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {csvPreview.preview.map((p) => (
                      <tr key={p.row} className="border-t border-[#27272A]" data-testid={`csv-preview-row-${p.row}`}>
                        <td className="px-2 py-1.5 text-[#71717A] font-mono">{p.row}</td>
                        <td className="px-2 py-1.5">{p.name}</td>
                        <td className="px-2 py-1.5 font-mono text-[#CCFF00]">{p.code}</td>
                        <td className="px-2 py-1.5 text-[#A1A1AA]">{p.type}</td>
                        <td className="px-2 py-1.5 text-right font-mono">{p.discount_value}</td>
                        <td className="px-2 py-1.5 text-[#A1A1AA]">{p.state}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-xs text-[#71717A] py-3 text-center">No valid rows found. Check your header row and required columns (name, discount_value).</div>
            )}
            {csvPreview?.errors?.length > 0 && (
              <div className="rounded-md border border-red-500/30 bg-red-500/5 p-3 text-xs" data-testid="csv-preview-errors">
                <div className="text-red-300 font-bold mb-1">Skipped rows</div>
                <ul className="space-y-1 text-red-200/80 max-h-32 overflow-y-auto">
                  {csvPreview.errors.slice(0, 20).map((e, i) => (
                    <li key={i}>Row {e.row}: {e.error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <DialogFooter>
            <button onClick={() => setCsvPreview(null)} className="text-xs text-[#71717A] hover:text-white mr-3">Cancel</button>
            <Button data-testid="csv-preview-commit" onClick={commitCsv}
              disabled={csvBusy || !(csvPreview?.total_valid > 0)}
              className="btn-primary rounded-md gap-2">
              {csvBusy && <Loader2 className="w-4 h-4 spin" />}
              Import {csvPreview?.total_valid ?? 0} coupon{csvPreview?.total_valid === 1 ? "" : "s"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
