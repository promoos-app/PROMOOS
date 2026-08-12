import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Loader2, Trophy, Users, Sparkles } from "lucide-react";

function StatCard({ label, value, sub }) {
  return (
    <div className="surface rounded-lg p-4">
      <div className="text-xs uppercase tracking-wide text-[#71717A]">{label}</div>
      <div className="font-display font-bold text-3xl mt-1">{value}</div>
      {sub && <div className="text-xs text-[#71717A] mt-1">{sub}</div>}
    </div>
  );
}

const TIER_COLORS = { Bronze: "#CD7F32", Silver: "#C0C0C0", Gold: "#FFD700", Platinum: "#E5E4E2" };

export default function Rewards() {
  const [data, setData] = useState(null);
  const [enabled, setEnabled] = useState(true);
  const [ppd, setPpd] = useState(1);
  const [tiers, setTiers] = useState([]);
  const [saving, setSaving] = useState(false);

  const load = () => api.get("/loyalty").then((r) => {
    setData(r.data);
    setEnabled(!!r.data.config?.enabled);
    setPpd(r.data.config?.points_per_dollar ?? 1);
    setTiers(r.data.config?.tiers || []);
  }).catch((e) => toast.error(apiError(e)));

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const save = async () => {
    setSaving(true);
    try {
      const sortedTiers = [...tiers].sort((a, b) => (Number(a.threshold) || 0) - (Number(b.threshold) || 0));
      await api.put("/workspace/loyalty", { enabled, points_per_dollar: Number(ppd), tiers: sortedTiers });
      toast.success("Loyalty saved");
      setTiers(sortedTiers);
      load();
    } catch (e) { toast.error(apiError(e)); } finally { setSaving(false); }
  };

  const updateTier = (i, k, v) => {
    setTiers((old) => old.map((t, idx) => idx === i ? { ...t, [k]: k === "threshold" ? Number(v) : v } : t));
  };
  const addTier = () => setTiers((old) => [...old, { name: "New Tier", threshold: 0 }]);
  const removeTier = (i) => setTiers((old) => old.filter((_, idx) => idx !== i));

  if (!data) return <div className="text-[#71717A]">Loading…</div>;

  return (
    <div className="space-y-6" data-testid="rewards-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl">Loyalty & Rewards</h1>
          <p className="text-sm text-[#71717A] mt-1">Every redemption earns points. Members climb tiers as they spend.</p>
        </div>
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[#CCFF00]" />
          <span className="text-sm text-[#A1A1AA]">Points/$: <span className="text-white font-bold">{data.config.points_per_dollar}</span></span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard label="Members" value={data.total_members} sub={<><Users className="inline w-3 h-3 mr-1" />lifetime</>} />
        <StatCard label="Total Points" value={Math.round(data.total_points).toLocaleString()} />
        <StatCard label="Top Tier" value={Object.keys(data.by_tier).sort((a, b) => (data.by_tier[b] - data.by_tier[a]))[0] || "—"} sub={<><Trophy className="inline w-3 h-3 mr-1" />by count</>} />
      </div>

      {/* Config */}
      <div className="surface rounded-lg p-6">
        <h3 className="font-display font-bold mb-4">Program configuration</h3>
        <div className="flex items-center justify-between mb-4 p-3 bg-[#0A0A0A] border border-[#27272A] rounded-md">
          <div>
            <div className="font-medium text-sm">Enable loyalty</div>
            <div className="text-xs text-[#71717A]">When on, redemptions credit points to the customer identifier.</div>
          </div>
          <Switch data-testid="loyalty-enabled" checked={enabled} onCheckedChange={setEnabled} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <div>
            <Label className="text-xs text-[#A1A1AA]">Points per $ spent</Label>
            <Input data-testid="loyalty-ppd" type="number" min={0} step="0.5" value={ppd} onChange={(e) => setPpd(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A] text-white" />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label className="text-xs text-[#A1A1AA]">Tiers</Label>
            <Button data-testid="loyalty-add-tier" onClick={addTier} className="btn-ghost rounded-md text-xs">+ Add tier</Button>
          </div>
          <div className="space-y-2">
            {tiers.map((t, i) => (
              <div key={i} className="grid grid-cols-[1fr_140px_60px] gap-2" data-testid={`tier-row-${i}`}>
                <Input value={t.name} onChange={(e) => updateTier(i, "name", e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white" />
                <Input type="number" value={t.threshold} onChange={(e) => updateTier(i, "threshold", e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white" placeholder="points" />
                <Button onClick={() => removeTier(i)} className="btn-ghost text-xs">✕</Button>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-4">
          <Button data-testid="loyalty-save" onClick={save} disabled={saving} className="btn-primary rounded-md gap-2">
            {saving && <Loader2 className="w-4 h-4 spin" />} Save
          </Button>
        </div>
      </div>

      {/* Members leaderboard */}
      <div className="surface rounded-lg overflow-hidden">
        <div className="p-6 pb-3">
          <h3 className="font-display font-bold">Top members</h3>
          <p className="text-xs text-[#71717A]">Sorted by current point balance.</p>
        </div>
        {data.members.length === 0 ? (
          <div className="px-6 pb-6 text-sm text-[#71717A]">No members yet — points accrue as customers redeem via the public landing page or checkout.</div>
        ) : (
          <table className="w-full text-sm" data-testid="loyalty-table">
            <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-6 py-2">Customer</th>
                <th className="text-left px-3 py-2">Tier</th>
                <th className="text-right px-3 py-2">Points</th>
                <th className="text-right px-3 py-2">Lifetime</th>
                <th className="text-right px-6 py-2">Last activity</th>
              </tr>
            </thead>
            <tbody>
              {data.members.map((m) => (
                <tr key={m.id || m.customer} className="border-t border-[#27272A]" data-testid={`loyalty-row-${m.customer}`}>
                  <td className="px-6 py-2 font-mono text-xs">{m.customer}</td>
                  <td className="px-3 py-2">
                    <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: `${TIER_COLORS[m.tier] || "#71717A"}22`, color: TIER_COLORS[m.tier] || "#71717A" }}>{m.tier}</span>
                  </td>
                  <td className="px-3 py-2 text-right font-bold">{Math.round(m.points).toLocaleString()}</td>
                  <td className="px-3 py-2 text-right text-[#A1A1AA]">{Math.round(m.lifetime_points).toLocaleString()}</td>
                  <td className="px-6 py-2 text-right text-xs text-[#71717A]">{(m.last_activity || "").slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
