import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Sparkles, ShieldCheck, Upload, Loader2 } from "lucide-react";

export default function Settings() {
  const { user } = useAuth();
  const [brand, setBrand] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [fonts, setFonts] = useState([]);
  const [currencies, setCurrencies] = useState([]);

  const { data: ws } = useQuery({ queryKey: ["workspace"], queryFn: async () => (await api.get("/workspace")).data });
  const { data: team = [] } = useQuery({ queryKey: ["team"], queryFn: async () => (await api.get("/team")).data });
  const { data: apCfg } = useQuery({ queryKey: ["autopilot-config"], queryFn: async () => (await api.get("/autopilot/config")).data });

  useEffect(() => {
    api.get("/fonts").then((r) => setFonts(r.data.fonts)).catch(() => setFonts(["Cabinet Grotesk", "Inter", "Poppins"]));
    api.get("/currencies").then((r) => setCurrencies(r.data)).catch(() => setCurrencies([{ code: "USD", name: "US Dollar", symbol: "$" }]));
  }, []);

  const [ap, setAp] = useState(null);
  const [apSaving, setApSaving] = useState(false);
  useEffect(() => { if (apCfg) setAp(apCfg); }, [apCfg]);
  const setApField = (k, v) => setAp((s) => ({ ...s, [k]: v }));
  const saveAp = async () => {
    setApSaving(true);
    try {
      await api.put("/autopilot/config", ap);
      toast.success("Autopilot saved");
    } catch (e) { toast.error(apiError(e)); } finally { setApSaving(false); }
  };

  useEffect(() => { if (ws) setBrand(ws); }, [ws]);
  if (!brand) return <div className="text-[#71717A]">Loading…</div>;

  const set = (k, v) => setBrand((b) => ({ ...b, [k]: v }));

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/workspace/brand", {
        name: brand.name, logo_url: brand.logo_url, primary_color: brand.primary_color,
        secondary_color: brand.secondary_color, font: brand.font, currency: brand.currency,
      });
      toast.success("Brand kit saved");
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  const roleColor = { owner: "text-[#CCFF00]", marketer: "text-[#005CEE]", viewer: "text-[#A1A1AA]" };

  return (
    <div className="fade-up max-w-[900px]">
      <div className="mb-6">
        <h1 className="font-display font-bold text-3xl tracking-tight">Settings</h1>
        <p className="text-sm text-[#A1A1AA] mt-1">Workspace, brand kit and team.</p>
      </div>

      <div className="surface rounded-lg p-6 mb-6">
        <h3 className="font-display font-bold text-lg mb-4">Brand Kit</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label className="text-xs text-[#A1A1AA]">Workspace name</Label>
            <Input data-testid="brand-name-input" value={brand.name || ""} onChange={(e) => set("name", e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Logo</Label>
            <div className="flex items-start gap-3 mt-1">
              {brand.logo_url && (
                <img src={brand.logo_url.startsWith("/api/") ? `${process.env.REACT_APP_BACKEND_URL}${brand.logo_url}` : brand.logo_url}
                     alt="logo" className="w-14 h-14 rounded-md object-cover bg-[#0A0A0A] border border-[#27272A]" data-testid="brand-logo-preview" />
              )}
              <div className="flex-1 space-y-2">
                <label className="btn-ghost inline-flex items-center gap-2 cursor-pointer rounded-md px-3 py-2 text-sm" data-testid="logo-upload-label">
                  {uploading ? <Loader2 className="w-4 h-4 spin" /> : <Upload className="w-4 h-4" />}
                  {uploading ? "Uploading…" : "Upload image"}
                  <input type="file" accept="image/jpeg,image/png,image/webp,image/svg+xml,image/gif" className="hidden"
                         data-testid="logo-upload-input"
                         onChange={async (e) => {
                           const f = e.target.files?.[0]; if (!f) return;
                           setUploading(true);
                           const fd = new FormData(); fd.append("file", f);
                           try {
                             const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
                             set("logo_url", data.url);
                             toast.success("Logo uploaded");
                           } catch (err) { toast.error(apiError(err)); } finally { setUploading(false); e.target.value = ""; }
                         }} />
                </label>
                <Input data-testid="brand-logo-input" value={brand.logo_url || ""} onChange={(e) => set("logo_url", e.target.value)}
                       className="bg-[#0A0A0A] border-[#27272A] text-white text-xs" placeholder="or paste URL…" />
                <div className="text-[10px] text-[#71717A]">JPG · PNG · WebP · SVG · GIF · max 10MB.</div>
              </div>
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Primary color</Label>
            <div className="flex gap-2 mt-1">
              <input type="color" data-testid="brand-primary-color" value={brand.primary_color || "#005CEE"} onChange={(e) => set("primary_color", e.target.value)} className="w-10 h-10 rounded-md bg-transparent border border-[#27272A] cursor-pointer" />
              <Input value={brand.primary_color || ""} onChange={(e) => set("primary_color", e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white font-mono" />
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Accent color</Label>
            <div className="flex gap-2 mt-1">
              <input type="color" data-testid="brand-secondary-color" value={brand.secondary_color || "#CCFF00"} onChange={(e) => set("secondary_color", e.target.value)} className="w-10 h-10 rounded-md bg-transparent border border-[#27272A] cursor-pointer" />
              <Input value={brand.secondary_color || ""} onChange={(e) => set("secondary_color", e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white font-mono" />
            </div>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Brand font ({fonts.length} options)</Label>
            <select data-testid="brand-font-select" value={brand.font || ""} onChange={(e) => set("font", e.target.value)} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
              {fonts.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA]">Currency ({currencies.length} supported)</Label>
            <select data-testid="brand-currency-select" value={brand.currency || ""} onChange={(e) => set("currency", e.target.value)} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
              {currencies.map((c) => <option key={c.code} value={c.code}>{c.code} — {c.name} ({c.symbol})</option>)}
            </select>
          </div>
        </div>
        <Button data-testid="save-brand-btn" onClick={save} disabled={saving} className="btn-primary rounded-md mt-5">{saving ? "Saving…" : "Save brand kit"}</Button>
      </div>

      <div className="surface rounded-lg p-6">
        <h3 className="font-display font-bold text-lg mb-4">Team & Roles</h3>
        <div className="space-y-2">
          {team.map((m) => (
            <div key={m.id} data-testid={`team-member-${m.id}`} className="flex items-center justify-between p-3 rounded-md bg-[#0A0A0A] border border-[#27272A]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[#005CEE] flex items-center justify-center text-xs font-semibold">{m.name?.[0]}</div>
                <div>
                  <div className="text-sm font-medium">{m.name} {m.id === user.id && <span className="text-[#71717A]">(you)</span>}</div>
                  <div className="text-xs text-[#71717A]">{m.email}</div>
                </div>
              </div>
              <span className={`text-xs uppercase font-mono ${roleColor[m.role]}`}>{m.role}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Autopilot */}
      {ap && (
        <div className="surface rounded-lg p-6 mt-6" data-testid="autopilot-section">
          <div className="flex items-center gap-2 mb-1">
            <Sparkles className="w-4 h-4 text-[#CCFF00]" />
            <h3 className="font-display font-bold text-lg">Promotion Autopilot™</h3>
          </div>
          <p className="text-xs text-[#71717A] mb-4">Let the AI plan, design and schedule your next promotion. Guardrails below keep every draft on-brand and inside your discount ceiling.</p>

          <div className="flex items-center justify-between p-3 rounded-md bg-[#0A0A0A] border border-[#27272A] mb-4">
            <div>
              <div className="font-medium text-sm">Autopilot</div>
              <div className="text-xs text-[#71717A]">Master switch — when off, AI still assists but never publishes automatically.</div>
            </div>
            <Switch data-testid="autopilot-enabled" checked={ap.enabled} onCheckedChange={(v) => setApField("enabled", v)} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Business goal</Label>
              <select data-testid="autopilot-goal" value={ap.goal} onChange={(e) => setApField("goal", e.target.value)} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                <option value="grow_sales">Grow sales</option>
                <option value="acquire">Acquire new customers</option>
                <option value="reactivate">Reactivate at-risk customers</option>
                <option value="clear_inventory">Clear slow-moving inventory</option>
              </select>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Frequency</Label>
              <select data-testid="autopilot-frequency" value={ap.frequency} onChange={(e) => setApField("frequency", e.target.value)} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                <option value="daily">Daily</option>
                <option value="weekdays">Weekdays only</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA] flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Max discount (%)</Label>
              <Input data-testid="autopilot-max-discount" type="number" min={1} max={90} value={ap.max_discount} onChange={(e) => setApField("max_discount", Number(e.target.value))} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Default audience</Label>
              <select data-testid="autopilot-audience" value={ap.audience} onChange={(e) => setApField("audience", e.target.value)} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                <option value="all">Everyone</option>
                <option value="new">New customers</option>
                <option value="returning">Returning customers</option>
                <option value="vip">VIP</option>
              </select>
            </div>
            <div className="md:col-span-2">
              <Label className="text-xs text-[#A1A1AA]">Brand voice</Label>
              <Input data-testid="autopilot-voice" value={ap.brand_voice} onChange={(e) => setApField("brand_voice", e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" placeholder="e.g. bold, confident, benefit-led" />
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded-md bg-[#0A0A0A] border border-[#27272A] mb-4">
            <div>
              <div className="font-medium text-sm">Require approval</div>
              <div className="text-xs text-[#71717A]">If off, the AI publishes generated drafts without waiting for you.</div>
            </div>
            <Switch data-testid="autopilot-approval" checked={ap.require_approval} onCheckedChange={(v) => setApField("require_approval", v)} />
          </div>

          <Button data-testid="autopilot-save" onClick={saveAp} disabled={apSaving} className="btn-primary rounded-md">
            {apSaving ? "Saving…" : "Save Autopilot"}
          </Button>
        </div>
      )}

      <PrivacyPanel user={user} />
    </div>
  );
}

function PrivacyPanel({ user }) {
  const [busy, setBusy] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [reason, setReason] = useState("");
  const exportData = async () => {
    setBusy("export");
    try {
      const { data } = await api.get("/me/export");
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `promoos-data-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      toast.success("Data export downloaded");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };
  const deleteAccount = async () => {
    if (confirmEmail.trim().toLowerCase() !== (user?.email || "").toLowerCase()) {
      toast.error("Type your account email exactly to confirm");
      return;
    }
    setBusy("delete");
    try {
      const { data } = await api.post("/me/data/delete", { confirm_email: confirmEmail.trim(), reason });
      toast.success(`Deletion request queued (${data.request_id?.slice(0, 8)}…) — we'll notify you when processed`);
      setConfirmDelete(false); setConfirmEmail(""); setReason("");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };
  return (
    <div className="surface rounded-lg p-6 mt-6" data-testid="privacy-panel">
      <h2 className="font-display font-bold text-xl mb-1 flex items-center gap-2">
        <ShieldCheck className="w-5 h-5 text-[#CCFF00]" /> Privacy & data rights
      </h2>
      <p className="text-xs text-[#A1A1AA] mb-4">
        Under GDPR (EU) and CCPA (California), you have the right to a copy of everything we hold
        on you, and the right to have it erased. These controls execute both.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="rounded-md p-4 bg-[#0A0A0A] border border-[#27272A]">
          <div className="font-medium text-sm mb-1">Download your data</div>
          <div className="text-xs text-[#71717A] mb-3">
            A JSON dump of your account, workspace, coupons, redemptions and customers.
          </div>
          <Button data-testid="privacy-export-btn" onClick={exportData}
            disabled={busy === "export"}
            className="btn-ghost rounded-md text-xs gap-2 border border-[#27272A] w-full">
            {busy === "export" ? "Preparing…" : "Export JSON"}
          </Button>
        </div>
        <div className="rounded-md p-4 bg-[#0A0A0A] border border-red-500/30">
          <div className="font-medium text-sm mb-1 text-red-300">Delete your data</div>
          <div className="text-xs text-[#71717A] mb-3">
            Queues a right-to-erasure request. A superadmin reviews and confirms within 30 days.
          </div>
          {!confirmDelete ? (
            <Button data-testid="privacy-delete-open-btn"
              onClick={() => setConfirmDelete(true)}
              className="btn-ghost rounded-md text-xs w-full border border-red-500/40 text-red-300 hover:bg-red-500/10">
              Request deletion
            </Button>
          ) : (
            <div className="space-y-2" data-testid="privacy-delete-form">
              <Input
                data-testid="privacy-delete-email"
                placeholder={user?.email || "your account email"}
                value={confirmEmail} onChange={(e) => setConfirmEmail(e.target.value)}
                className="bg-[#141414] border-red-500/30 text-white text-xs h-8" />
              <Input
                data-testid="privacy-delete-reason"
                placeholder="Reason (optional)"
                value={reason} onChange={(e) => setReason(e.target.value)}
                className="bg-[#141414] border-[#27272A] text-white text-xs h-8" />
              <div className="flex gap-2">
                <button onClick={() => { setConfirmDelete(false); setConfirmEmail(""); }}
                  className="text-[10px] text-[#71717A] hover:text-white flex-1 h-7 border border-[#27272A] rounded">
                  Cancel
                </button>
                <Button data-testid="privacy-delete-submit" onClick={deleteAccount}
                  disabled={busy === "delete"}
                  className="rounded-md text-[10px] h-7 bg-red-500/20 text-red-300 border border-red-500/40 hover:bg-red-500/30 flex-1">
                  {busy === "delete" ? "Queuing…" : "Confirm deletion"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
