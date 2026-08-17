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
  Pause, Play, RotateCcw, Trash2,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

const TABS = [
  { k: "stats", label: "Stats", icon: BarChart3 },
  { k: "users", label: "Users", icon: Users },
  { k: "workspaces", label: "Workspaces", icon: Building2 },
  { k: "payments", label: "Payments", icon: CreditCard },
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
