import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { discountText } from "@/lib/couponUtils";
import {
  Ticket, TrendingUp, DollarSign, Zap, ArrowUpRight, Sparkles, Plus,
} from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { Button } from "@/components/ui/button";

const fmtMoney = (n) => "$" + Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });

function Metric({ icon: Icon, label, value, sub, testid }) {
  return (
    <div data-testid={testid} className="surface card-hover rounded-lg p-6 col-span-6 md:col-span-3">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs uppercase tracking-wide text-[#71717A]">{label}</span>
        <Icon className="w-4 h-4 text-[#71717A]" />
      </div>
      <div className="font-display font-bold text-3xl tracking-tight">{value}</div>
      {sub && <div className="text-xs text-[#A1A1AA] mt-1">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: async () => (await api.get("/dashboard/stats")).data });
  const { data: series } = useQuery({ queryKey: ["ts"], queryFn: async () => (await api.get("/analytics/timeseries")).data });

  const recs = [
    { title: "Run a flash sale this weekend", why: "Weekend redemptions are 38% higher for your store." },
    { title: "Reactivate at-risk customers", why: "112 customers haven't redeemed in 30 days — try a 20% win-back." },
    { title: "Bundle free shipping with SUMMER25", why: "Free-shipping offers lift AOV by ~$14 on average." },
  ];

  return (
    <div className="fade-up max-w-[1400px]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight">Dashboard</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Your promotional command center.</p>
        </div>
        <Button data-testid="dashboard-new-coupon-btn" onClick={() => navigate("/coupons/new")} className="btn-primary gap-2 rounded-md">
          <Plus className="w-4 h-4" /> New Coupon
        </Button>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <Metric testid="metric-active" icon={Ticket} label="Active Coupons" value={stats?.active_coupons ?? "—"} sub={`${stats?.total_coupons ?? 0} total`} />
        <Metric testid="metric-redemptions" icon={Zap} label="Redemptions" value={(stats?.total_redemptions ?? 0).toLocaleString()} sub="all time" />
        <Metric testid="metric-revenue" icon={DollarSign} label="Revenue Impact" value={fmtMoney(stats?.total_revenue)} sub="attributed" />
        <Metric testid="metric-conversion" icon={TrendingUp} label="Avg. per Redemption" value={stats?.total_redemptions ? fmtMoney(stats.total_revenue / stats.total_redemptions) : "—"} sub="revenue / redemption" />

        {/* Chart */}
        <div className="surface rounded-lg p-6 col-span-12 lg:col-span-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="font-display font-bold text-lg">Redemptions & Revenue</h3>
              <p className="text-xs text-[#71717A]">Last 14 days</p>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series || []}>
                <defs>
                  <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#005CEE" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#005CEE" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E1E1E" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#71717A", fontSize: 11 }} tickFormatter={(d) => d?.slice(5)} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#71717A", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#141414", border: "1px solid #27272A", borderRadius: 8, color: "#fff" }} />
                <Area type="monotone" dataKey="revenue" stroke="#005CEE" strokeWidth={2} fill="url(#rev)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* AI recommendations */}
        <div className="ai-glow rounded-lg p-6 col-span-12 lg:col-span-4 bg-[#141414]">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-[#CCFF00]" />
            <h3 className="font-display font-bold text-lg">AI Promotion Engine</h3>
          </div>
          <p className="text-xs text-[#71717A] mb-4">What to run this week</p>
          <div className="space-y-3">
            {recs.map((r, i) => (
              <button key={i} data-testid={`ai-rec-${i}`} onClick={() => navigate("/coupons/new")}
                className="w-full text-left p-3 rounded-md bg-[#0A0A0A] border border-[#27272A] hover:border-[#CCFF00]/40 transition-colors group">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-sm font-medium">{r.title}</span>
                  <ArrowUpRight className="w-4 h-4 text-[#71717A] group-hover:text-[#CCFF00] shrink-0" />
                </div>
                <p className="text-xs text-[#A1A1AA] mt-1">{r.why}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Top campaigns */}
        <div className="surface rounded-lg p-6 col-span-12">
          <h3 className="font-display font-bold text-lg mb-4">Top Campaigns</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wide text-[#71717A] border-b border-[#27272A]">
                <th className="text-left font-medium pb-3">Campaign</th>
                <th className="text-left font-medium pb-3">Type</th>
                <th className="text-right font-medium pb-3">Redemptions</th>
                <th className="text-right font-medium pb-3">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {(stats?.top_campaigns || []).map((c, i) => (
                <tr key={i} data-testid={`top-campaign-${i}`} className="border-b border-[#1E1E1E] last:border-0">
                  <td className="py-3 font-medium">{c.name}</td>
                  <td className="py-3 text-[#A1A1AA]">{c.type}</td>
                  <td className="py-3 text-right font-mono">{c.redemptions}</td>
                  <td className="py-3 text-right font-mono text-[#CCFF00]">{fmtMoney(c.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
