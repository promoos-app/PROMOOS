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
  Pause, Play, RotateCcw, Trash2, Palette,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

const TABS = [
  { k: "stats", label: "Stats", icon: BarChart3 },
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
