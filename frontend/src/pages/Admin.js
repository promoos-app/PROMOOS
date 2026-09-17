import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { Navigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Shield, Users, Building2, ScrollText, CreditCard, BarChart3, Plus, Loader2,
  Pause, Play, RotateCcw, Trash2, Palette, HeartPulse, CheckCircle2, XCircle, AlertTriangle, Rocket, Copy, TrendingUp,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

const TABS = [
  { k: "stats", label: "Stats", icon: BarChart3 },
  { k: "health", label: "Health Check", icon: HeartPulse },
  { k: "onboard", label: "Onboard", icon: Rocket },
  { k: "funnel", label: "Funnel", icon: TrendingUp },
  { k: "ops", label: "Ops", icon: Shield },
  { k: "users", label: "Users", icon: Users },
  { k: "workspaces", label: "Workspaces", icon: Building2 },
  { k: "payments", label: "Payments", icon: CreditCard },
  { k: "presets", label: "Preset Packs", icon: Palette },
  { k: "logs", label: "Audit Log", icon: ScrollText },
];

function CreateUserDialog({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", email: "", password: "", role: "owner", workspace_name: "" });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/admin/users", f);
      toast.success("User created");
      setOpen(false);
      setF({ name: "", email: "", password: "", role: "owner", workspace_name: "" });
      onCreated?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button data-testid="admin-create-user-btn" className="btn-primary rounded-md gap-2">
          <Plus className="w-4 h-4" /> New user
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white">
        <DialogHeader><DialogTitle>Create account</DialogTitle></DialogHeader>
        <div className="space-y-3">
          {["name", "email", "password", "workspace_name"].map((k) => (
            <div key={k}>
              <Label className="text-xs text-[#A1A1AA] capitalize">{k.replace("_", " ")}</Label>
              <Input data-testid={`admin-cu-${k}`} type={k === "password" ? "password" : "text"} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
            </div>
          ))}
          <div>
            <Label className="text-xs text-[#A1A1AA]">Role</Label>
            <select data-testid="admin-cu-role" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] px-3 text-sm">
              {["owner", "marketer", "viewer", "superadmin"].map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>
        <DialogFooter>
          <Button data-testid="admin-cu-submit" onClick={submit} disabled={busy} className="btn-primary rounded-md gap-2">
            {busy && <Loader2 className="w-4 h-4 spin" />} Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PresetPacksManager() {
  const [packs, setPacks] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", scope: "both", is_public: true, presets: [] });
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const [importBusy, setImportBusy] = useState(false);
  const emptyPreset = () => ({ key: "", label: "", accent: "#CCFF00", prompt: "" });

  const load = () => {
    api.get("/admin/preset-packs").then((r) => setPacks(r.data)).catch((e) => toast.error(apiError(e)));
  };
  useEffect(() => { load(); }, []);

  const openNew = () => {
    setEditing(null);
    setForm({ name: "", scope: "both", is_public: true, presets: [emptyPreset()] });
    setOpen(true);
  };
  const openEdit = (p) => {
    setEditing(p);
    setForm({ name: p.name, scope: p.scope, is_public: p.is_public,
      presets: p.presets.length ? p.presets : [emptyPreset()] });
    setOpen(true);
  };

  const save = async () => {
    if (!form.name.trim()) { toast.error("Give the pack a name"); return; }
    const cleaned = form.presets.filter((x) => x.key && x.label && x.prompt);
    if (!cleaned.length) { toast.error("Add at least one preset with key, label and prompt"); return; }
    setBusy(true);
    try {
      const body = { ...form, presets: cleaned };
      if (editing) await api.put(`/admin/preset-packs/${editing.id}`, body);
      else await api.post("/admin/preset-packs", body);
      toast.success(editing ? "Pack updated" : "Pack published");
      setOpen(false); load();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const del = async (p) => {
    if (!window.confirm(`Delete "${p.name}"?`)) return;
    try { await api.delete(`/admin/preset-packs/${p.id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  const setPreset = (i, k, v) => setForm((f) => {
    const arr = [...f.presets]; arr[i] = { ...arr[i], [k]: v }; return { ...f, presets: arr };
  });

  const doImport = async () => {
    let parsed;
    try { parsed = JSON.parse(importText); }
    catch (e) { toast.error("Invalid JSON — check your syntax"); return; }
    setImportBusy(true);
    try {
      await api.post("/admin/preset-packs/import", parsed);
      toast.success("Pack imported");
      setImportOpen(false); load();
    } catch (e) { toast.error(apiError(e)); } finally { setImportBusy(false); }
  };

  const sampleJson = JSON.stringify({
    name: "Acme Holiday Kit",
    scope: "both",
    is_public: true,
    presets: [
      { key: "cranberry", label: "Cranberry", accent: "#8B1E1E", prompt: "warm cranberry red holiday premium banner, subtle snowflakes, cinematic" },
      { key: "pine", label: "Pine", accent: "#2F5D3A", prompt: "deep pine forest holiday banner, snow-dusted needles, cinematic lighting" },
    ],
  }, null, 2);

  return (
    <div className="surface rounded-lg p-5" data-testid="admin-preset-packs">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-sm font-bold">Preset Packs</div>
          <div className="text-xs text-[#71717A]">Curated style chips available in every workspace's Coupon and Gift Card studios.</div>
        </div>
        <Button data-testid="preset-pack-new-btn" onClick={openNew} className="btn-primary rounded-md gap-2">
          <Plus className="w-4 h-4" /> New pack
        </Button>
        <Button data-testid="preset-pack-import-btn" onClick={() => { setImportText(""); setImportOpen(true); }}
          className="ml-2 rounded-md gap-2 border border-[#27272A] text-[#CCFF00] hover:border-[#CCFF00] bg-transparent">
          Import JSON
        </Button>
      </div>

      {packs.length === 0 ? (
        <div className="text-xs text-[#71717A] py-4">No packs yet. Publish your first pack.</div>
      ) : (
        <table className="w-full text-sm" data-testid="preset-packs-table">
          <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Scope</th>
              <th className="text-right px-3 py-2">Presets</th>
              <th className="text-left px-3 py-2">Public</th>
              <th className="text-right px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {packs.map((p) => (
              <tr key={p.id} className="border-t border-[#27272A]" data-testid={`preset-pack-row-${p.id}`}>
                <td className="px-3 py-2 font-medium">{p.name}</td>
                <td className="px-3 py-2 text-xs uppercase text-[#CCFF00]">{p.scope}</td>
                <td className="px-3 py-2 text-right">{(p.presets || []).length}</td>
                <td className="px-3 py-2 text-xs">{p.is_public ? "Yes" : "No"}</td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => {
                    const payload = {
                      name: p.name, scope: p.scope,
                      is_public: p.is_public,
                      presets: (p.presets || []).map(({ key, label, accent, prompt }) => ({ key, label, accent, prompt })),
                    };
                    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
                    const a = document.createElement("a");
                    a.href = URL.createObjectURL(blob);
                    a.download = `${p.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.preset-pack.json`;
                    a.click();
                    URL.revokeObjectURL(a.href);
                  }} className="text-[10px] uppercase text-[#A1A1AA] hover:text-white mr-3" data-testid={`preset-pack-export-${p.id}`}>Export</button>
                  <button onClick={() => openEdit(p)} className="text-[10px] uppercase text-[#CCFF00] mr-3" data-testid={`preset-pack-edit-${p.id}`}>Edit</button>
                  <button onClick={() => del(p)} className="text-[10px] uppercase text-red-400" data-testid={`preset-pack-delete-${p.id}`}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-2xl">
          <DialogHeader><DialogTitle>{editing ? "Edit pack" : "New preset pack"}</DialogTitle></DialogHeader>
          <div className="space-y-3 max-h-[65vh] overflow-y-auto pr-1">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Name</Label>
              <Input data-testid="preset-pack-name" value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="Acme Holiday Kit" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-[#A1A1AA]">Scope</Label>
                <select data-testid="preset-pack-scope" value={form.scope}
                  onChange={(e) => setForm((f) => ({ ...f, scope: e.target.value }))}
                  className="mt-1 w-full h-9 px-2 bg-[#0A0A0A] border border-[#27272A] rounded-md text-sm">
                  <option value="both">Both studios</option>
                  <option value="coupon">Coupon only</option>
                  <option value="gift_card">Gift card only</option>
                </select>
              </div>
              <label className="flex items-end gap-2 text-sm text-[#A1A1AA] pb-1">
                <input type="checkbox" checked={form.is_public}
                  onChange={(e) => setForm((f) => ({ ...f, is_public: e.target.checked }))}
                  data-testid="preset-pack-public" />
                Published to all workspaces
              </label>
            </div>
            <div className="pt-2">
              <div className="flex items-center justify-between mb-2">
                <div className="text-xs uppercase tracking-widest text-[#71717A]">Presets in this pack</div>
                <button className="text-[10px] uppercase text-[#CCFF00]" data-testid="preset-pack-add-preset"
                  onClick={() => setForm((f) => ({ ...f, presets: [...f.presets, emptyPreset()] }))}>+ Add preset</button>
              </div>
              {form.presets.map((p, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 mb-2 items-start" data-testid={`preset-row-${i}`}>
                  <Input placeholder="key (unique)" value={p.key} onChange={(e) => setPreset(i, "key", e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} className="col-span-3 bg-[#0A0A0A] border-[#27272A]" />
                  <Input placeholder="Label" value={p.label} onChange={(e) => setPreset(i, "label", e.target.value)} className="col-span-3 bg-[#0A0A0A] border-[#27272A]" />
                  <Input type="color" value={p.accent} onChange={(e) => setPreset(i, "accent", e.target.value)} className="col-span-1 h-9 p-1 bg-[#0A0A0A] border-[#27272A]" />
                  <Input placeholder="Image prompt" value={p.prompt} onChange={(e) => setPreset(i, "prompt", e.target.value)} className="col-span-4 bg-[#0A0A0A] border-[#27272A]" />
                  <button onClick={() => setForm((f) => ({ ...f, presets: f.presets.filter((_, x) => x !== i) }))}
                    className="col-span-1 text-red-400 text-xs pt-2" data-testid={`preset-row-remove-${i}`}>Remove</button>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button onClick={save} disabled={busy} data-testid="preset-pack-save" className="btn-primary rounded-md gap-2">
              {busy && <Loader2 className="w-4 h-4 spin" />} {editing ? "Save" : "Publish pack"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-2xl" data-testid="preset-pack-import-dialog">
          <DialogHeader><DialogTitle>Import preset pack from JSON</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <p className="text-xs text-[#A1A1AA]">
              Paste a JSON blob shared by a partner or agency. Required keys:
              <code className="mx-1 text-[#CCFF00]">name</code>,
              <code className="mx-1 text-[#CCFF00]">scope</code>,
              <code className="mx-1 text-[#CCFF00]">presets[]</code>.
              Each preset needs <code className="text-[#CCFF00]">key</code>, <code className="text-[#CCFF00]">label</code>, and <code className="text-[#CCFF00]">prompt</code>.
            </p>
            <textarea
              data-testid="preset-pack-import-textarea"
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder={sampleJson}
              className="w-full h-64 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white text-xs font-mono p-3"
            />
            <button
              type="button"
              onClick={() => setImportText(sampleJson)}
              className="text-[10px] uppercase tracking-widest text-[#CCFF00] hover:opacity-80"
              data-testid="preset-pack-import-sample"
            >Fill with sample</button>
          </div>
          <DialogFooter>
            <Button onClick={doImport} disabled={importBusy} data-testid="preset-pack-import-submit" className="btn-primary rounded-md gap-2">
              {importBusy && <Loader2 className="w-4 h-4 spin" />} Import pack
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function Admin() {
  const { user } = useAuth();
  const [tab, setTab] = useState("stats");
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [ws, setWs] = useState([]);
  const [payments, setPayments] = useState(null);
  const [logs, setLogs] = useState([]);

  const [stripeInfo, setStripeInfo] = useState(null);

  const load = () => {
    api.get("/admin/stats").then((r) => setStats(r.data)).catch((e) => toast.error(apiError(e)));
    api.get("/admin/users").then((r) => setUsers(r.data)).catch(() => {});
    api.get("/admin/workspaces").then((r) => setWs(r.data)).catch(() => {});
    api.get("/admin/payments").then((r) => setPayments(r.data)).catch(() => {});
    api.get("/admin/logs").then((r) => setLogs(r.data)).catch(() => {});
    api.get("/admin/stripe-onboarding").then((r) => setStripeInfo(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  if (user && user.role !== "superadmin") return <Navigate to="/" replace />;

  const act = async (uid, action) => {
    const conf = action === "delete" ? "Delete this user? (soft-delete)" : null;
    if (conf && !window.confirm(conf)) return;
    try {
      if (action === "delete") await api.delete(`/admin/users/${uid}`);
      else await api.post(`/admin/users/${uid}/${action}`, {});
      toast.success(action);
      load();
    } catch (e) { toast.error(apiError(e)); }
  };

  return (
    <div className="fade-up max-w-[1400px]" data-testid="admin-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Shield className="w-7 h-7 text-[#CCFF00]" /> Admin Portal
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Platform-wide user, workspace, payment, and audit management. Superadmin only.</p>
        </div>
        {tab === "users" && <CreateUserDialog onCreated={load} />}
      </div>

      <div className="inline-flex bg-[#0A0A0A] border border-[#27272A] rounded-lg p-1 mb-5">
        {TABS.map((t) => (
          <button key={t.k} data-testid={`admin-tab-${t.k}`} onClick={() => setTab(t.k)}
                  className={`px-3 py-1.5 rounded-md text-xs font-medium transition flex items-center gap-1.5 ${tab === t.k ? "bg-[#005CEE] text-white" : "text-[#A1A1AA] hover:text-white"}`}>
            <t.icon className="w-3.5 h-3.5" /> {t.label}
          </button>
        ))}
      </div>

      {tab === "stats" && stats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          <div className="surface rounded-lg p-4"><div className="text-xs uppercase text-[#71717A]">Active users</div><div className="text-3xl font-bold text-[#CCFF00]">{stats.users.active}</div></div>
          <div className="surface rounded-lg p-4"><div className="text-xs uppercase text-[#71717A]">Suspended</div><div className="text-3xl font-bold text-orange-400">{stats.users.suspended}</div></div>
          <div className="surface rounded-lg p-4"><div className="text-xs uppercase text-[#71717A]">Deleted</div><div className="text-3xl font-bold text-red-400">{stats.users.deleted}</div></div>
          <div className="surface rounded-lg p-4"><div className="text-xs uppercase text-[#71717A]">Workspaces</div><div className="text-3xl font-bold">{stats.workspaces}</div></div>
          <div className="surface rounded-lg p-4"><div className="text-xs uppercase text-[#71717A]">Coupons</div><div className="text-3xl font-bold">{stats.coupons}</div></div>
          <div className="surface rounded-lg p-4"><div className="text-xs uppercase text-[#71717A]">Redemptions</div><div className="text-3xl font-bold">{stats.redemptions}</div></div>
        </div>
      )}

      {tab === "health" && <HealthCheckPanel />}
      {tab === "onboard" && <OnboardMerchantPanel />}
      {tab === "funnel" && <OnboardingFunnelPanel />}
      {tab === "ops" && <OpsPanel />}

      {tab === "users" && (
        <div className="surface rounded-lg overflow-hidden">
          <table className="w-full text-sm" data-testid="admin-users-table">
            <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-6 py-2">Email</th>
                <th className="text-left px-3 py-2">Name</th>
                <th className="text-left px-3 py-2">Role</th>
                <th className="text-left px-3 py-2">Workspace</th>
                <th className="text-left px-3 py-2">State</th>
                <th className="text-right px-6 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-[#27272A]" data-testid={`admin-user-${u.email}`}>
                  <td className="px-6 py-2 font-mono text-xs">{u.email}</td>
                  <td className="px-3 py-2">{u.name}</td>
                  <td className="px-3 py-2 text-xs uppercase font-bold text-[#CCFF00]">{u.role}</td>
                  <td className="px-3 py-2 text-xs text-[#A1A1AA]">{u.workspace_name}</td>
                  <td className="px-3 py-2">
                    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                      u.state === "active" ? "bg-emerald-500/15 text-emerald-400" :
                      u.state === "suspended" ? "bg-orange-500/15 text-orange-400" :
                      "bg-red-500/15 text-red-400"}`}>{u.state}</span>
                  </td>
                  <td className="px-6 py-2 text-right">
                    <div className="inline-flex gap-1">
                      {u.state === "active" && <button data-testid={`admin-suspend-${u.email}`} onClick={() => act(u.id, "suspend")} title="Suspend" className="p-1.5 rounded hover:bg-white/5 text-orange-400"><Pause className="w-3.5 h-3.5" /></button>}
                      {u.state === "suspended" && <button data-testid={`admin-activate-${u.email}`} onClick={() => act(u.id, "activate")} title="Activate" className="p-1.5 rounded hover:bg-white/5 text-emerald-400"><Play className="w-3.5 h-3.5" /></button>}
                      {u.state === "deleted" && <button data-testid={`admin-restore-${u.email}`} onClick={() => act(u.id, "restore")} title="Restore" className="p-1.5 rounded hover:bg-white/5 text-[#CCFF00]"><RotateCcw className="w-3.5 h-3.5" /></button>}
                      {u.state !== "deleted" && <button data-testid={`admin-delete-${u.email}`} onClick={() => act(u.id, "delete")} title="Delete" className="p-1.5 rounded hover:bg-white/5 text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "workspaces" && (
        <div className="surface rounded-lg overflow-hidden">
          <table className="w-full text-sm" data-testid="admin-workspaces-table">
            <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-6 py-2">Name</th>
                <th className="text-right px-3 py-2">Users</th>
                <th className="text-right px-3 py-2">Coupons</th>
                <th className="text-right px-3 py-2">Redemptions</th>
                <th className="text-right px-6 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {ws.map((w) => (
                <tr key={w.id} className="border-t border-[#27272A]">
                  <td className="px-6 py-2 font-medium">{w.name} {w.is_platform && <span className="text-[10px] uppercase text-[#CCFF00] ml-1">platform</span>}</td>
                  <td className="px-3 py-2 text-right">{w.user_count}</td>
                  <td className="px-3 py-2 text-right">{w.coupon_count}</td>
                  <td className="px-3 py-2 text-right">{w.redemption_count}</td>
                  <td className="px-6 py-2 text-right text-xs text-[#71717A]">{(w.created_at || "").slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "payments" && payments && (
        <div>
          {stripeInfo && (
            <div className="surface rounded-lg p-5 mb-4 border-[#CCFF00]/30" data-testid="stripe-onboarding-card">
              <div className="flex items-center gap-2 mb-2">
                <CreditCard className="w-4 h-4 text-[#CCFF00]" />
                <div className="font-display font-bold">Stripe · {stripeInfo.mode === "test" ? "Sandbox" : "Live"} mode</div>
                <span className="ml-auto text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400">Connected</span>
              </div>
              <div className="text-xs text-[#A1A1AA] mb-3">
                Account <span className="font-mono">{stripeInfo.account_id}</span> · publishable key {stripeInfo.publishable_key.slice(0, 20)}…
              </div>
              {stripeInfo.onboarding_url && (
                <a href={stripeInfo.onboarding_url} target="_blank" rel="noopener noreferrer"
                   data-testid="stripe-onboard-link"
                   className="btn-primary rounded-md text-xs inline-flex items-center gap-2 px-3 py-2">
                  Claim your Stripe account to go live
                </a>
              )}
            </div>
          )}
          <div className="surface rounded-lg p-6 mb-4">
            <div className="text-xs uppercase text-[#71717A]">Total collected</div>
            <div className="text-4xl font-bold text-[#CCFF00]">${payments.total_collected.toFixed(2)}</div>
            <div className="text-xs text-[#A1A1AA] mt-1">{payments.count} payment records.</div>
          </div>
          {payments.payments.length === 0 ? (
            <div className="surface rounded-lg p-8 text-center text-sm text-[#71717A]">
              No customer subscriptions yet. Once workspaces subscribe to Basic/Pro via the /pricing page, they'll appear here.
            </div>
          ) : (
            <div className="surface rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
                  <tr><th className="text-left px-6 py-2">Workspace</th><th className="text-right px-3 py-2">Amount</th><th className="text-left px-3 py-2">Status</th><th className="text-right px-6 py-2">Date</th></tr>
                </thead>
                <tbody>
                  {payments.payments.map((p) => (
                    <tr key={p.id} className="border-t border-[#27272A]">
                      <td className="px-6 py-2">{p.workspace_id}</td>
                      <td className="px-3 py-2 text-right">${Number(p.amount).toFixed(2)}</td>
                      <td className="px-3 py-2 text-xs">{p.status}</td>
                      <td className="px-6 py-2 text-right text-xs text-[#71717A]">{(p.created_at || "").slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "presets" && <PresetPacksManager />}

      {tab === "logs" && (
        <div className="surface rounded-lg overflow-hidden">
          {logs.length === 0 ? (
            <div className="p-6 text-sm text-[#71717A]">No admin actions yet.</div>
          ) : (
            <table className="w-full text-sm" data-testid="admin-logs-table">
              <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
                <tr><th className="text-left px-6 py-2">When</th><th className="text-left px-3 py-2">Actor</th><th className="text-left px-3 py-2">Action</th><th className="text-left px-3 py-2">Target</th></tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id} className="border-t border-[#27272A]">
                    <td className="px-6 py-2 font-mono text-xs">{(l.created_at || "").slice(0, 19).replace("T", " ")}</td>
                    <td className="px-3 py-2 text-xs text-[#A1A1AA]">{l.actor_email}</td>
                    <td className="px-3 py-2 text-xs font-bold text-[#CCFF00]">{l.action}</td>
                    <td className="px-3 py-2 font-mono text-xs text-[#71717A]">{l.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

function HealthCheckPanel() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const run = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/health-check");
      setData(data);
    } catch (e) { toast.error(apiError(e)); } finally { setLoading(false); }
  };
  useEffect(() => { run(); }, []);

  const levelStyles = {
    critical: "text-red-400 bg-red-500/10 border-red-500/30",
    warning: "text-amber-400 bg-amber-500/10 border-amber-500/30",
    info: "text-[#A1A1AA] bg-[#0A0A0A] border-[#27272A]",
  };

  return (
    <div className="space-y-4" data-testid="health-check-panel">
      <div className="surface rounded-lg p-5 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {data ? (
            data.ready_for_launch ? (
              <div className="w-11 h-11 rounded-full bg-emerald-500/20 flex items-center justify-center">
                <CheckCircle2 className="w-6 h-6 text-emerald-400" />
              </div>
            ) : data.ok ? (
              <div className="w-11 h-11 rounded-full bg-amber-500/20 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-amber-400" />
              </div>
            ) : (
              <div className="w-11 h-11 rounded-full bg-red-500/20 flex items-center justify-center">
                <XCircle className="w-6 h-6 text-red-400" />
              </div>
            )
          ) : (
            <div className="w-11 h-11 rounded-full bg-[#27272A] flex items-center justify-center">
              <HeartPulse className="w-6 h-6 text-[#71717A]" />
            </div>
          )}
          <div className="min-w-0">
            <div className="font-display font-bold text-lg" data-testid="health-check-title">
              {data
                ? (data.ready_for_launch
                    ? "Ready for launch"
                    : data.ok ? "Operational — warnings to review" : "Critical failures — do not launch")
                : "Running checks…"}
            </div>
            <div className="text-xs text-[#71717A]">
              {data
                ? `${data.critical_failures} critical · ${data.warnings} warning${data.warnings === 1 ? "" : "s"} · ${data.checks.length} check${data.checks.length === 1 ? "" : "s"}`
                : "Provisioning Runbook Phase 8"}
            </div>
          </div>
        </div>
        <Button data-testid="health-check-refresh" onClick={run} disabled={loading}
          className="btn-primary rounded-md gap-2">
          {loading ? <Loader2 className="w-4 h-4 spin" /> : <RotateCcw className="w-4 h-4" />}
          Re-run
        </Button>
      </div>

      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2" data-testid="health-check-results">
          {data.checks.map((c, i) => {
            const cls = c.ok ? levelStyles.info : (levelStyles[c.level] || levelStyles.info);
            return (
              <div
                key={i}
                className={`rounded-md border p-3 flex items-start gap-3 ${cls}`}
                data-testid={`health-check-${c.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`}
              >
                {c.ok ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-400" />
                ) : c.level === "critical" ? (
                  <XCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
                ) : (
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-bold text-white">{c.name}</div>
                  <div className="text-[11px] text-[#A1A1AA] mt-0.5 break-words">{c.message}</div>
                </div>
                <span className="text-[9px] uppercase tracking-widest text-[#71717A] shrink-0">
                  {c.ok ? "pass" : c.level}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}


function OpsPanel() {
  const [backup, setBackup] = useState(null);
  const [rateEvents, setRateEvents] = useState(null);
  const [busy, setBusy] = useState(null);

  const loadBackup = async () => {
    try {
      const { data } = await api.get("/admin/backup-status");
      setBackup(data);
    } catch (e) { toast.error(apiError(e)); }
  };
  const loadRateEvents = async () => {
    try {
      const { data } = await api.get("/admin/rate-limit-events?limit=50");
      setRateEvents(data);
    } catch (e) { toast.error(apiError(e)); }
  };
  useEffect(() => { loadBackup(); loadRateEvents(); }, []);

  const runBackup = async () => {
    setBusy("backup");
    try {
      const { data } = await api.post("/admin/run-backup");
      if (data.ok) toast.success("Backup completed");
      else toast.error(data.error || data.skipped || "Backup failed");
      loadBackup();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(null); }
  };

  return (
    <div className="space-y-6" data-testid="ops-panel">
      <div className="surface rounded-lg p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-[#005CEE]/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-[#005CEE]" />
          </div>
          <div className="flex-1">
            <h2 className="font-display font-bold text-lg">Daily Mongo backup</h2>
            <p className="text-xs text-[#71717A]">
              Runs at 03:15 UTC via in-process scheduler. Archives to <span className="font-mono text-[#A1A1AA]">/app/backups/</span>,
              14-day retention.
            </p>
          </div>
          <Button data-testid="ops-run-backup" onClick={runBackup} disabled={busy === "backup"}
            className="btn-primary rounded-md gap-2">
            {busy === "backup" ? <Loader2 className="w-4 h-4 spin" /> : <Play className="w-4 h-4" />}
            Run now
          </Button>
        </div>
        {backup && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs" data-testid="ops-backup-state">
            <div className="rounded-md p-3 bg-[#0A0A0A] border border-[#27272A]">
              <div className="text-[#71717A] uppercase tracking-widest text-[10px]">Script</div>
              <div className={`font-bold ${backup.script_present ? "text-emerald-400" : "text-red-400"}`}>
                {backup.script_present ? "present" : "missing"}
              </div>
            </div>
            <div className="rounded-md p-3 bg-[#0A0A0A] border border-[#27272A]">
              <div className="text-[#71717A] uppercase tracking-widest text-[10px]">Last run</div>
              <div className="font-mono text-[#A1A1AA] text-[11px]">
                {backup.state.last_run ? new Date(backup.state.last_run).toLocaleString() : "never"}
              </div>
            </div>
            <div className="rounded-md p-3 bg-[#0A0A0A] border border-[#27272A]">
              <div className="text-[#71717A] uppercase tracking-widest text-[10px]">Status</div>
              <div className={`font-bold ${
                backup.state.last_status === "ok" ? "text-emerald-400" :
                backup.state.last_status === "fail" ? "text-red-400" : "text-[#71717A]"
              }`}>
                {backup.state.last_status || "—"}
              </div>
            </div>
            <div className="rounded-md p-3 bg-[#0A0A0A] border border-[#27272A]">
              <div className="text-[#71717A] uppercase tracking-widest text-[10px]">Scheduler</div>
              <div className={`font-bold ${backup.state.disabled ? "text-amber-400" : "text-emerald-400"}`}>
                {backup.state.disabled ? "paused" : "active"}
              </div>
            </div>
          </div>
        )}
        {backup?.state?.last_error && (
          <div className="mt-3 rounded-md p-3 bg-red-500/10 border border-red-500/30 text-[11px] font-mono text-red-300 break-all">
            {backup.state.last_error}
          </div>
        )}
      </div>

      <div className="surface rounded-lg p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          </div>
          <div className="flex-1">
            <h2 className="font-display font-bold text-lg">Rate-limit events</h2>
            <p className="text-xs text-[#71717A]">
              429s emitted by the public API middleware. Persisted at ≤1 event per (IP, tier)
              per minute so this table stays readable under an attack.
            </p>
          </div>
          <Button data-testid="ops-refresh-rate" onClick={loadRateEvents}
            className="btn-ghost rounded-md gap-2 border border-[#27272A]">
            <RotateCcw className="w-4 h-4" /> Refresh
          </Button>
        </div>
        {rateEvents && rateEvents.top_offenders.length > 0 && (
          <div className="mb-3" data-testid="ops-top-offenders">
            <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-2">Top offenders</div>
            <div className="flex flex-wrap gap-2">
              {rateEvents.top_offenders.map(([ip, n]) => (
                <span key={ip} className="text-xs font-mono px-2 py-1 rounded bg-red-500/10 border border-red-500/30 text-red-300">
                  {ip} · {n}
                </span>
              ))}
            </div>
          </div>
        )}
        {rateEvents && rateEvents.events.length === 0 ? (
          <div className="text-xs text-[#71717A] py-4 text-center">
            No rate-limit events yet — nothing is being blocked. 🎉
          </div>
        ) : rateEvents ? (
          <div className="rounded-md border border-[#27272A] overflow-hidden">
            <table className="w-full text-xs" data-testid="ops-rate-table">
              <thead className="bg-[#0A0A0A] text-[10px] uppercase tracking-widest text-[#71717A]">
                <tr>
                  <th className="text-left px-3 py-2">When</th>
                  <th className="text-left px-3 py-2">IP</th>
                  <th className="text-left px-3 py-2">Tier</th>
                  <th className="text-left px-3 py-2">Path</th>
                </tr>
              </thead>
              <tbody>
                {rateEvents.events.slice(0, 30).map((e, i) => (
                  <tr key={i} className="border-t border-[#27272A]">
                    <td className="px-3 py-1.5 font-mono text-[#A1A1AA]">{e.at}</td>
                    <td className="px-3 py-1.5 font-mono">{e.ip}</td>
                    <td className="px-3 py-1.5">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-bold ${
                        e.tier === "strict" ? "bg-red-500/15 text-red-400" :
                        e.tier === "standard" ? "bg-amber-500/15 text-amber-400" :
                        "bg-[#71717A]/15 text-[#A1A1AA]"
                      }`}>{e.tier}</span>
                    </td>
                    <td className="px-3 py-1.5 font-mono text-[#71717A] truncate max-w-xs">{e.path}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </div>
  );
}


function OnboardMerchantPanel() {
  const [form, setForm] = useState({
    merchant_name: "", owner_name: "", owner_email: "", owner_password: "",
    primary_color: "#005CEE", secondary_color: "#CCFF00",
    currency: "USD", create_demo_publication: true,
  });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const gen = () => Math.random().toString(36).slice(2, 8) + Math.random().toString(36).slice(2, 8).toUpperCase() + "!";
  const submit = async () => {
    if (!form.merchant_name.trim() || !form.owner_name.trim() ||
        !form.owner_email.includes("@") || form.owner_password.length < 8) {
      toast.error("Fill every field (password ≥ 8 chars)");
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post("/admin/onboard-merchant", form);
      setResult({ ...data, credentials: { email: form.owner_email, password: form.owner_password } });
      toast.success(data.already_exists ? "Merchant already existed — pulled IDs" : "Merchant onboarded");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };
  const copy = (v) => { navigator.clipboard.writeText(v); toast.success("Copied"); };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-4" data-testid="onboard-panel">
      <div className="surface rounded-lg p-5 space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <Rocket className="w-5 h-5 text-[#CCFF00]" />
          <h2 className="font-display font-bold text-lg">Onboard a merchant</h2>
        </div>
        <p className="text-xs text-[#71717A]">
          Creates workspace + owner + starter newsletter in one click. Follow Phase 5 of
          <span className="font-mono"> PROVISIONING_RUNBOOK.md</span>.
        </p>
        <div className="grid grid-cols-1 gap-3">
          <div><label className="text-xs text-[#A1A1AA]">Merchant / brand name</label>
            <input data-testid="onboard-merchant-name" value={form.merchant_name}
              onChange={(e) => set("merchant_name", e.target.value)}
              placeholder="Acme Swimwear"
              className="mt-1 w-full h-10 px-3 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white text-sm" /></div>
          <div><label className="text-xs text-[#A1A1AA]">Owner name</label>
            <input data-testid="onboard-owner-name" value={form.owner_name}
              onChange={(e) => set("owner_name", e.target.value)}
              placeholder="Jane Doe"
              className="mt-1 w-full h-10 px-3 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white text-sm" /></div>
          <div><label className="text-xs text-[#A1A1AA]">Owner email</label>
            <input data-testid="onboard-owner-email" type="email" value={form.owner_email}
              onChange={(e) => set("owner_email", e.target.value)}
              placeholder="jane@acme.com"
              className="mt-1 w-full h-10 px-3 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white text-sm font-mono" /></div>
          <div><label className="text-xs text-[#A1A1AA]">Temporary password (owner will rotate)</label>
            <div className="flex gap-2 mt-1">
              <input data-testid="onboard-owner-password" value={form.owner_password}
                onChange={(e) => set("owner_password", e.target.value)}
                placeholder="AtLeast8Chars!"
                className="flex-1 h-10 px-3 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white text-sm font-mono" />
              <button type="button" onClick={() => set("owner_password", gen())}
                data-testid="onboard-generate-password"
                className="px-3 rounded-md border border-[#27272A] text-xs hover:border-[#CCFF00]">Generate</button>
            </div></div>
          <div className="grid grid-cols-3 gap-2">
            <div><label className="text-xs text-[#A1A1AA]">Primary</label>
              <input type="color" value={form.primary_color} onChange={(e) => set("primary_color", e.target.value)}
                className="mt-1 h-10 w-full p-1 rounded-md bg-[#0A0A0A] border border-[#27272A]" /></div>
            <div><label className="text-xs text-[#A1A1AA]">Accent</label>
              <input type="color" value={form.secondary_color} onChange={(e) => set("secondary_color", e.target.value)}
                className="mt-1 h-10 w-full p-1 rounded-md bg-[#0A0A0A] border border-[#27272A]" /></div>
            <div><label className="text-xs text-[#A1A1AA]">Currency</label>
              <input value={form.currency} onChange={(e) => set("currency", e.target.value.toUpperCase().slice(0, 3))}
                className="mt-1 h-10 w-full px-3 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white text-sm font-mono" /></div>
          </div>
          <label className="flex items-center gap-2 text-xs text-[#A1A1AA] cursor-pointer">
            <input type="checkbox" checked={form.create_demo_publication}
              data-testid="onboard-create-demo-pub"
              onChange={(e) => set("create_demo_publication", e.target.checked)} />
            Create a starter newsletter publication
          </label>
        </div>
        <Button data-testid="onboard-submit" onClick={submit} disabled={busy}
          className="btn-primary rounded-md gap-2 w-full h-10 mt-2">
          {busy ? <Loader2 className="w-4 h-4 spin" /> : <Rocket className="w-4 h-4" />}
          Onboard merchant
        </Button>
      </div>

      {result && (
        <div className="surface rounded-lg p-5 space-y-3" data-testid="onboard-result">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <h3 className="font-display font-bold text-lg">
              {result.already_exists ? "Already exists" : "Merchant ready"}
            </h3>
            {result.email_sent && (
              <span data-testid="onboard-email-sent-badge"
                className="ml-auto px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/40 text-[10px] font-bold uppercase tracking-widest text-emerald-300">
                Email sent
              </span>
            )}
          </div>
          <p className="text-xs text-[#A1A1AA]">
            {result.email_sent
              ? "We emailed the merchant a one-click magic sign-in link plus the temporary password below."
              : "Share the magic link (or credentials) with the merchant. They should rotate the password on first sign-in."}
          </p>
          <div className="rounded-md border border-[#27272A] bg-[#0A0A0A] p-4 space-y-2">
            <RowKV label="Login email" value={result.credentials?.email} onCopy={copy} />
            <RowKV label="Temp password" value={result.credentials?.password} onCopy={copy} secret />
            {result.magic_link && (
              <RowKV label="Magic link" value={result.magic_link} onCopy={copy} mono link
                testid="onboard-magic-link" />
            )}
            <RowKV label="Workspace ID" value={result.workspace_id} onCopy={copy} mono />
            <RowKV label="Owner ID" value={result.user_id} onCopy={copy} mono />
            {result.publication_id && (
              <RowKV label="Newsletter ID" value={result.publication_id} onCopy={copy} mono />
            )}
          </div>
          <div className="text-[11px] text-[#71717A]">
            Magic link expires in 72 hours. Next: ask the merchant to add their Stripe live key and
            Resend sending domain via Settings → Integrations.
          </div>
        </div>
      )}
    </div>
  );
}

function OnboardingFunnelPanel() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(true);
  const load = async () => {
    setBusy(true);
    try { const { data } = await api.get("/admin/onboarding-funnel"); setData(data); }
    catch (e) { toast.error(apiError(e)); }
    finally { setBusy(false); }
  };
  useEffect(() => { load(); }, []);
  if (busy && !data) return (
    <div className="py-12 text-center text-[#71717A]" data-testid="funnel-loading">
      <Loader2 className="w-6 h-6 spin mx-auto" />
    </div>
  );
  if (!data) return null;
  const stages = [
    { key: "onboarded", label: "Onboarded", count: data.totals.onboarded, color: "#005CEE",
      pct: 100 },
    { key: "magic_clicked", label: "Magic clicked", count: data.totals.magic_clicked,
      color: "#CCFF00", pct: data.conversion.onboard_to_magic },
    { key: "first_email_sent", label: "First email sent", count: data.totals.first_email_sent,
      color: "#F472B6", pct: data.conversion.onboard_to_first_send },
  ];
  const fmt = (iso) => iso ? new Date(iso).toLocaleString(undefined,
    { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
  return (
    <div className="space-y-4" data-testid="funnel-panel">
      <div className="flex items-center gap-2">
        <TrendingUp className="w-5 h-5 text-[#CCFF00]" />
        <h2 className="font-display font-bold text-lg">Onboarding funnel</h2>
        <button onClick={load} disabled={busy}
          data-testid="funnel-refresh"
          className="ml-auto px-3 py-1 rounded-md border border-[#27272A] text-xs hover:border-[#CCFF00] disabled:opacity-60">
          {busy ? <Loader2 className="w-3 h-3 spin inline" /> : "Refresh"}
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {stages.map((s, i) => (
          <div key={s.key} className="surface rounded-lg p-5" data-testid={`funnel-stage-${s.key}`}>
            <div className="text-[10px] uppercase tracking-widest text-[#71717A]">{i + 1}. {s.label}</div>
            <div className="mt-1 flex items-baseline gap-2">
              <div className="text-4xl font-bold" style={{ color: s.color }}>{s.count}</div>
              <div className="text-xs text-[#71717A]">{s.pct}% of onboarded</div>
            </div>
            <div className="mt-3 h-1.5 rounded-full bg-[#27272A] overflow-hidden">
              <div className="h-full rounded-full transition-all"
                style={{ width: `${s.pct}%`, background: s.color }} />
            </div>
          </div>
        ))}
      </div>
      <div className="surface rounded-lg overflow-hidden">
        <table className="w-full text-sm" data-testid="funnel-table">
          <thead className="bg-[#0A0A0A] text-[#71717A] text-[10px] uppercase tracking-widest">
            <tr>
              <th className="text-left px-4 py-2">Merchant</th>
              <th className="text-left px-3 py-2">Email</th>
              <th className="text-left px-3 py-2">Onboarded</th>
              <th className="text-left px-3 py-2">Magic clicked</th>
              <th className="text-left px-3 py-2">First send</th>
              <th className="text-left px-3 py-2">Stage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#27272A]">
            {data.rows.length === 0 && (
              <tr><td colSpan={6} className="text-center py-6 text-[#71717A]" data-testid="funnel-empty">
                No merchants onboarded yet. Use the Onboard tab to add your first one.</td></tr>
            )}
            {data.rows.map((r) => {
              const stageStyle = r.stage === "first_sent" ? "bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/40"
                : r.stage === "magic_clicked" ? "bg-[#CCFF00]/10 text-[#CCFF00] border-[#CCFF00]/40"
                : "bg-blue-500/10 text-blue-300 border-blue-500/40";
              return (
                <tr key={r.user_id} className="hover:bg-white/5">
                  <td className="px-4 py-2 font-medium">{r.merchant || r.name}</td>
                  <td className="px-3 py-2 text-xs text-[#A1A1AA] font-mono">{r.email}</td>
                  <td className="px-3 py-2 text-xs text-[#A1A1AA]">{fmt(r.onboarded_at)}</td>
                  <td className="px-3 py-2 text-xs text-[#A1A1AA]">{fmt(r.magic_clicked_at)}</td>
                  <td className="px-3 py-2 text-xs text-[#A1A1AA]">{fmt(r.first_email_sent_at)}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-block px-2 py-0.5 rounded-full border text-[9px] font-bold uppercase tracking-widest ${stageStyle}`}>
                      {r.stage.replace("_", " ")}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RowKV({ label, value, onCopy, mono, secret, link, testid }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-2" data-testid={testid}>
      <span className="text-[10px] uppercase tracking-widest text-[#71717A] w-24 shrink-0">{label}</span>
      {link ? (
        <a href={value} target="_blank" rel="noopener noreferrer"
          className={`flex-1 text-xs break-all text-[#CCFF00] hover:underline ${mono ? "font-mono" : ""}`}>
          {value}
        </a>
      ) : (
        <span className={`flex-1 text-xs break-all ${mono || secret ? "font-mono" : ""}`}>{value}</span>
      )}
      <button onClick={() => onCopy(value)} className="text-[#71717A] hover:text-[#CCFF00]">
        <Copy className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

