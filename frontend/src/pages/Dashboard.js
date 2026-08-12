import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import {
  Ticket, TrendingUp, DollarSign, Zap, ArrowUpRight, Sparkles, Plus, Loader2, RefreshCw,
} from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { Button } from "@/components/ui/button";
import OneClickCampaign from "@/components/OneClickCampaign";

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
  const [today, setToday] = useState(null);
  const [todayBusy, setTodayBusy] = useState(false);
  const [approvingToday, setApprovingToday] = useState(false);

  const generateToday = async () => {
    setTodayBusy(true);
    try {
      const { data } = await api.post("/ai/todays-promo", {});
      setToday(data);
    } catch (e) { toast.error(apiError(e)); } finally { setTodayBusy(false); }
  };

  const approveToday = async (activate) => {
    if (!today) return;
    setApprovingToday(true);
    try {
      const { data } = await api.post("/ai/one-click-campaign/approve", {
        package: { coupon: today }, activate,
      });
      toast.success(`Coupon ${data.code} created ${activate ? "and activated" : "as draft"}`);
      setToday(null);
    } catch (e) { toast.error(apiError(e)); } finally { setApprovingToday(false); }
  };

  return (
    <div className="fade-up max-w-[1400px]">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight">Dashboard</h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Your promotional command center.</p>
        </div>
        <div className="flex gap-2">
          <OneClickCampaign />
          <Button data-testid="dashboard-new-coupon-btn" onClick={() => navigate("/coupons/new")} className="btn-primary gap-2 rounded-md">
            <Plus className="w-4 h-4" /> New Coupon
          </Button>
        </div>
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

        {/* AI Today's Promo (live) */}
        <div className="ai-glow rounded-lg p-6 col-span-12 lg:col-span-4 bg-[#141414]" data-testid="todays-promo-widget">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#CCFF00]" />
              <h3 className="font-display font-bold text-lg">Today's AI Promo</h3>
            </div>
            <button
              data-testid="todays-promo-generate"
              onClick={generateToday}
              disabled={todayBusy}
              className="text-xs text-[#A1A1AA] hover:text-white flex items-center gap-1 disabled:opacity-50"
            >
              {todayBusy ? <Loader2 className="w-3 h-3 spin" /> : <RefreshCw className="w-3 h-3" />}
              {today ? "Regenerate" : "Generate"}
            </button>
          </div>
          {!today ? (
            <div className="text-xs text-[#A1A1AA]">
              Claude will read your top-performing coupons + redemption hours and design one optimal promo for today.
              <button data-testid="todays-promo-cta" onClick={generateToday} disabled={todayBusy}
                      className="block mt-4 w-full py-2 rounded-md bg-[#CCFF00] text-[#0A0A0A] text-sm font-bold hover:opacity-90 disabled:opacity-50">
                {todayBusy ? "Thinking…" : "Generate today's promo"}
              </button>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs uppercase tracking-widest text-[#CCFF00] font-bold">{today.type}</span>
                <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-[#CCFF00]/15 text-[#CCFF00]">{today.discount_value}%</span>
              </div>
              <div className="font-display font-bold text-base leading-tight mb-1" data-testid="todays-promo-headline">{today.headline}</div>
              <p className="text-xs text-[#A1A1AA] mb-3">{today.description}</p>
              <div className="text-[11px] text-[#71717A] italic mb-4 border-l-2 border-[#CCFF00]/40 pl-2">"{today.reasoning}"</div>
              <div className="flex gap-2">
                <Button data-testid="todays-promo-launch" onClick={() => approveToday(true)} disabled={approvingToday} className="btn-primary rounded-md text-xs flex-1 gap-1">
                  {approvingToday && <Loader2 className="w-3 h-3 spin" />} Launch
                </Button>
                <Button data-testid="todays-promo-draft" onClick={() => approveToday(false)} disabled={approvingToday} className="btn-ghost rounded-md text-xs flex-1">
                  Save as draft
                </Button>
              </div>
            </div>
          )}
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
