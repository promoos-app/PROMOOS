import { useEffect, useState, useMemo } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Download, Save, Trash2, QrCode, Sparkles, Link as LinkIcon, Phone, MessageSquare, Mail, Wifi, User, FileText, Printer } from "lucide-react";

const CONTENT_TYPE_ICONS = {
  url: LinkIcon, text: FileText, phone: Phone, sms: MessageSquare,
  email: Mail, wifi: Wifi, vcard: User,
};

export default function QRStudio() {
  const [opts, setOpts] = useState(null);
  const [saved, setSaved] = useState([]);
  const [contentType, setContentType] = useState("url");
  const [data, setData] = useState({ url: "https://promoos.app" });
  const [style, setStyle] = useState("rounded");
  const [colorMask, setColorMask] = useState("radial");
  const [frontColor, setFrontColor] = useState("#0A0A0A");
  const [backColor, setBackColor] = useState("#FFFFFF");
  const [edgeColor, setEdgeColor] = useState("#CCFF00");
  const [ec, setEc] = useState("H");
  const [logoUploadId, setLogoUploadId] = useState(null);
  const [label, setLabel] = useState("");
  const [tracking, setTracking] = useState(false);
  const [scanCount, setScanCount] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get("/qr/options").then((r) => setOpts(r.data)).catch((e) => toast.error(apiError(e)));
    loadSaved();
  }, []);

  const loadSaved = () => api.get("/qr/saved").then((r) => setSaved(r.data)).catch(() => {});

  const payload = useMemo(() => ({
    content_type: contentType, data, style, color_mask: colorMask,
    front_color: frontColor, back_color: backColor, edge_color: edgeColor,
    error_correction: ec, box_size: 16, border: 4,
    logo_upload_id: logoUploadId,
  }), [contentType, data, style, colorMask, frontColor, backColor, edgeColor, ec, logoUploadId]);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!contentType) return;
      setBusy(true);
      try {
        const { data: r } = await api.post("/qr/preview", payload);
        setPreview(r);
      } catch (e) { setPreview(null); }
      finally { setBusy(false); }
    }, 400);
    return () => clearTimeout(t);
  }, [payload, contentType]);

  const applyPreset = (p) => {
    setStyle(p.style); setColorMask(p.color_mask);
    setFrontColor(p.front_color); setBackColor(p.back_color); setEdgeColor(p.edge_color);
  };

  const download = async () => {
    try {
      const res = await api.post("/qr/download", { ...payload, label }, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url;
      a.download = `${label || contentType}.png`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      toast.success("Downloaded");
    } catch (e) { toast.error(apiError(e)); }
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.post("/qr/preview", {
        ...payload, save: true, label: label || null,
        tracking, origin_url: tracking ? window.location.origin : undefined,
      });
      toast.success(tracking ? "Saved with scan tracking enabled" : "Saved");
      if (data.tracking_id) setScanCount({ id: data.saved_id, tracking_id: data.tracking_id, count: 0 });
      loadSaved();
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  const loadScans = async (qid) => {
    try {
      const { data } = await api.get(`/qr/saved/${qid}/scans`);
      setScanCount({ id: qid, count: data.scan_count, scans: data.scans });
    } catch {}
  };

  const del = async (id) => {
    try { await api.delete(`/qr/saved/${id}`); loadSaved(); toast.success("Deleted"); }
    catch (e) { toast.error(apiError(e)); }
  };

  const uploadLogo = async (file) => {
    const fd = new FormData(); fd.append("file", file);
    try {
      const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setLogoUploadId(data.id);
      toast.success("Logo attached");
    } catch (e) { toast.error(apiError(e)); }
  };

  const [selectedForPrint, setSelectedForPrint] = useState([]);
  const [printFormat, setPrintFormat] = useState("a4");
  const toggleSelect = (id) => setSelectedForPrint((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);
  const printSheet = async () => {
    if (!selectedForPrint.length) { toast.error("Select at least one QR"); return; }
    try {
      const res = await api.post("/qr/print-sheet", { ids: selectedForPrint, format: printFormat, columns: 3 }, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a"); a.href = url;
      a.download = `qr-sheet-${selectedForPrint.length}.pdf`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      toast.success(`Downloaded ${selectedForPrint.length}-QR sheet`);
    } catch (e) { toast.error(apiError(e)); }
  };

  if (!opts) return <div className="text-[#71717A]">Loading…</div>;

  return (
    <div className="fade-up max-w-[1400px]" data-testid="qr-studio">
      <div className="mb-6">
        <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
          <QrCode className="w-7 h-7 text-[#CCFF00]" /> QR Code Studio
        </h1>
        <p className="text-sm text-[#A1A1AA] mt-1">Generate colorful, on-brand QR codes for URLs, phone numbers, WiFi, vCards and more. Download high-res PNG or save to your library.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        {/* Controls */}
        <div className="space-y-4">
          <div className="surface rounded-lg p-4">
            <Label className="text-xs uppercase tracking-widest text-[#71717A]">Content type</Label>
            <div className="grid grid-cols-4 gap-1 mt-2" data-testid="qr-content-types">
              {opts.content_types.map((t) => {
                const Icon = CONTENT_TYPE_ICONS[t] || FileText;
                return (
                  <button key={t} onClick={() => { setContentType(t); setData({}); }}
                    data-testid={`qr-type-${t}`}
                    className={`p-2 rounded-md text-[10px] uppercase tracking-widest flex flex-col items-center gap-1 ${contentType === t ? "bg-[#CCFF00] text-[#0A0A0A] font-bold" : "bg-[#0A0A0A] border border-[#27272A] text-[#A1A1AA] hover:text-white"}`}>
                    <Icon className="w-4 h-4" />
                    {t}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="surface rounded-lg p-4 space-y-3" data-testid="qr-content-fields">
            {contentType === "url" && (
              <div>
                <Label className="text-xs text-[#A1A1AA]">URL</Label>
                <Input data-testid="qr-url-input" value={data.url || ""} onChange={(e) => setData({ url: e.target.value })}
                  placeholder="https://…" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
              </div>
            )}
            {contentType === "text" && (
              <div>
                <Label className="text-xs text-[#A1A1AA]">Text</Label>
                <textarea data-testid="qr-text-input" value={data.text || ""} onChange={(e) => setData({ text: e.target.value })}
                  rows={4} className="mt-1 w-full bg-[#0A0A0A] border border-[#27272A] text-white rounded-md p-2 text-sm" />
              </div>
            )}
            {contentType === "phone" && (
              <div>
                <Label className="text-xs text-[#A1A1AA]">Phone number</Label>
                <Input data-testid="qr-phone-input" value={data.phone || ""} onChange={(e) => setData({ phone: e.target.value })}
                  placeholder="+1 555 555 0100" className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                <div className="text-[10px] text-[#71717A] mt-1">Scanning opens the phone dialer.</div>
              </div>
            )}
            {contentType === "sms" && (
              <>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Phone number</Label>
                  <Input data-testid="qr-sms-phone-input" value={data.phone || ""} onChange={(e) => setData({ ...data, phone: e.target.value })}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Prefilled message</Label>
                  <Input data-testid="qr-sms-message-input" value={data.message || ""} onChange={(e) => setData({ ...data, message: e.target.value })}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
              </>
            )}
            {contentType === "email" && (
              <>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Email address</Label>
                  <Input data-testid="qr-email-address-input" value={data.email || ""} onChange={(e) => setData({ ...data, email: e.target.value })}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Subject</Label>
                  <Input value={data.subject || ""} onChange={(e) => setData({ ...data, subject: e.target.value })}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Body</Label>
                  <Input value={data.body || ""} onChange={(e) => setData({ ...data, body: e.target.value })}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
              </>
            )}
            {contentType === "wifi" && (
              <>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">SSID (network name)</Label>
                  <Input data-testid="qr-wifi-ssid-input" value={data.ssid || ""} onChange={(e) => setData({ ...data, ssid: e.target.value })}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Password</Label>
                  <Input data-testid="qr-wifi-password-input" value={data.password || ""} onChange={(e) => setData({ ...data, password: e.target.value })}
                    className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
                </div>
                <div>
                  <Label className="text-xs text-[#A1A1AA]">Encryption</Label>
                  <select value={data.encryption || "WPA"} onChange={(e) => setData({ ...data, encryption: e.target.value })}
                    className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                    <option>WPA</option><option>WEP</option><option>nopass</option>
                  </select>
                </div>
              </>
            )}
            {contentType === "vcard" && (
              <>
                <div><Label className="text-xs text-[#A1A1AA]">Full name</Label><Input value={data.name || ""} onChange={(e) => setData({ ...data, name: e.target.value })} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
                <div><Label className="text-xs text-[#A1A1AA]">Organization</Label><Input value={data.org || ""} onChange={(e) => setData({ ...data, org: e.target.value })} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
                <div><Label className="text-xs text-[#A1A1AA]">Phone</Label><Input value={data.phone || ""} onChange={(e) => setData({ ...data, phone: e.target.value })} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
                <div><Label className="text-xs text-[#A1A1AA]">Email</Label><Input value={data.email || ""} onChange={(e) => setData({ ...data, email: e.target.value })} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
                <div><Label className="text-xs text-[#A1A1AA]">Website</Label><Input value={data.url || ""} onChange={(e) => setData({ ...data, url: e.target.value })} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" /></div>
              </>
            )}
          </div>

          <div className="surface rounded-lg p-4">
            <Label className="text-xs uppercase tracking-widest text-[#71717A] flex items-center gap-1"><Sparkles className="w-3 h-3 text-[#CCFF00]" /> Style presets</Label>
            <div className="grid grid-cols-5 gap-1.5 mt-2" data-testid="qr-presets">
              {opts.presets.map((p) => (
                <button key={p.id} onClick={() => applyPreset(p)} data-testid={`qr-preset-${p.id}`}
                  title={p.id} style={{ background: p.back_color, border: `2px solid ${p.edge_color}` }}
                  className="aspect-square rounded-md relative overflow-hidden group hover:scale-105 transition">
                  <div className="absolute inset-1 rounded-sm" style={{ background: p.front_color }} />
                </button>
              ))}
            </div>
          </div>

          <div className="surface rounded-lg p-4 space-y-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Module shape</Label>
              <select value={style} onChange={(e) => setStyle(e.target.value)} data-testid="qr-style-select"
                className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm capitalize">
                {opts.styles.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
              </select>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Color gradient</Label>
              <select value={colorMask} onChange={(e) => setColorMask(e.target.value)} data-testid="qr-mask-select"
                className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm capitalize">
                {opts.color_masks.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <Label className="text-[10px] text-[#71717A] uppercase tracking-widest">Front</Label>
                <input type="color" data-testid="qr-front-color" value={frontColor} onChange={(e) => setFrontColor(e.target.value)}
                  className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] cursor-pointer" />
              </div>
              <div>
                <Label className="text-[10px] text-[#71717A] uppercase tracking-widest">Back</Label>
                <input type="color" data-testid="qr-back-color" value={backColor} onChange={(e) => setBackColor(e.target.value)}
                  className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] cursor-pointer" />
              </div>
              <div>
                <Label className="text-[10px] text-[#71717A] uppercase tracking-widest">Accent</Label>
                <input type="color" data-testid="qr-edge-color" value={edgeColor} onChange={(e) => setEdgeColor(e.target.value)}
                  className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] cursor-pointer" />
              </div>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Error correction (higher = more logo tolerance)</Label>
              <div className="flex gap-1 mt-1" data-testid="qr-ec-levels">
                {opts.error_correction.map((l) => (
                  <button key={l} onClick={() => setEc(l)} data-testid={`qr-ec-${l}`}
                    className={`flex-1 h-8 rounded-md text-xs uppercase tracking-widest font-bold ${ec === l ? "bg-[#CCFF00] text-[#0A0A0A]" : "bg-[#0A0A0A] border border-[#27272A] text-[#A1A1AA]"}`}>
                    {l}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Center logo (optional)</Label>
              <label className="btn-ghost mt-1 inline-flex items-center gap-2 cursor-pointer rounded-md px-3 py-2 text-xs" data-testid="qr-logo-upload">
                Upload logo
                <input type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0])} />
              </label>
              {logoUploadId && <button onClick={() => setLogoUploadId(null)} className="ml-2 text-xs text-red-400" data-testid="qr-logo-clear">Clear</button>}
            </div>
          </div>
        </div>

        {/* Preview */}
        <div className="space-y-4">
          <div className="surface rounded-lg p-6 flex flex-col items-center justify-center min-h-[500px]" data-testid="qr-preview-card">
            {busy && !preview ? (
              <Loader2 className="w-8 h-8 text-[#CCFF00] spin" />
            ) : preview ? (
              <>
                <img src={preview.image_data_url} alt="QR preview" className="rounded-lg max-w-[380px] w-full shadow-2xl" data-testid="qr-preview-image" />
                <div className="mt-4 text-center">
                  <div className="text-[10px] uppercase tracking-widest text-[#71717A]">Payload</div>
                  <code className="text-xs text-[#E4E4E7] break-all max-w-md block mt-1">{preview.payload}</code>
                </div>
              </>
            ) : (
              <div className="text-[#71717A] text-sm">Enter content to generate preview</div>
            )}
          </div>

          <div className="flex gap-2">
            <div className="flex-1">
              <Input value={label} onChange={(e) => setLabel(e.target.value)} placeholder="Label (optional, for library)" data-testid="qr-label-input"
                className="bg-[#141414] border-[#27272A] text-white" />
            </div>
            <Button data-testid="qr-save-btn" onClick={save} disabled={saving || !preview} className="btn-ghost rounded-md gap-2">
              {saving ? <Loader2 className="w-4 h-4 spin" /> : <Save className="w-4 h-4" />} Save to library
            </Button>
            <Button data-testid="qr-download-btn" onClick={download} disabled={!preview} className="btn-primary rounded-md gap-2">
              <Download className="w-4 h-4" /> Download PNG
            </Button>
          </div>
          {contentType === "url" && (
            <label className="flex items-center gap-2 text-xs text-[#A1A1AA] px-1 cursor-pointer" data-testid="qr-tracking-toggle-label">
              <input type="checkbox" checked={tracking} onChange={(e) => setTracking(e.target.checked)} data-testid="qr-tracking-toggle" className="rounded" />
              <Sparkles className="w-3 h-3 text-[#CCFF00]" />
              Enable scan tracking (URL redirect adds analytics)
            </label>
          )}
          {scanCount && (
            <div className="surface rounded-lg p-4 text-sm" data-testid="qr-scan-analytics">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs uppercase tracking-widest text-[#71717A]">Scans</div>
                  <div className="text-2xl font-bold text-[#CCFF00]">{scanCount.count}</div>
                </div>
                <div className="text-[10px] text-[#71717A] text-right">Last {scanCount.scans?.length || 0} events</div>
              </div>
            </div>
          )}

          {saved.length > 0 && (
            <div className="surface rounded-lg p-4" data-testid="qr-saved-list">
              <div className="flex items-center justify-between mb-3">
                <div className="text-xs uppercase tracking-widest text-[#71717A]">Your saved QR codes ({saved.length})</div>
                <div className="flex items-center gap-2">
                  <select value={printFormat} onChange={(e) => setPrintFormat(e.target.value)} data-testid="qr-print-format"
                    className="h-8 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-2 text-xs">
                    <option value="a4">A4</option><option value="letter">US Letter</option>
                  </select>
                  <Button data-testid="qr-print-sheet-btn" onClick={printSheet} disabled={!selectedForPrint.length}
                    className="btn-primary rounded-md text-xs gap-1">
                    <Printer className="w-3 h-3" /> Print sheet ({selectedForPrint.length})
                  </Button>
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {saved.map((q) => (
                  <div key={q.id} data-testid={`qr-saved-${q.id}`}
                    onClick={() => toggleSelect(q.id)}
                    className={`group relative border rounded-md p-3 bg-[#0A0A0A] cursor-pointer transition ${selectedForPrint.includes(q.id) ? "border-[#CCFF00] ring-2 ring-[#CCFF00]/30" : "border-[#27272A] hover:border-[#3f3f46]"}`}>
                    <div className="text-xs font-medium truncate mb-0.5">{q.label}</div>
                    <div className="text-[10px] text-[#71717A] capitalize">{q.content_type} · {q.style}</div>
                    {q.tracking_id && (
                      <button onClick={(e) => { e.stopPropagation(); loadScans(q.id); }} className="mt-1 text-[10px] text-[#CCFF00] hover:underline flex items-center gap-1" data-testid={`qr-saved-scans-${q.id}`}>
                        <Sparkles className="w-2.5 h-2.5" /> {q.scan_count || 0} scans
                      </button>
                    )}
                    <button onClick={(e) => { e.stopPropagation(); del(q.id); }} className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 text-red-400 hover:bg-red-500/10 rounded p-1 transition"
                      data-testid={`qr-saved-delete-${q.id}`}>
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="text-[10px] text-[#71717A] mt-2">Tap cards to select for the printable sheet.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
