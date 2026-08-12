import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { BarChart3, Download, FileText, TrendingUp, DollarSign, Users, ShoppingCart, Loader2 } from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
  BarChart, Bar,
} from "recharts";

const PERIODS = [7, 14, 30, 60, 90, 180, 365];

function KPI({ label, value, hint, icon: Icon, accent = "#005CEE" }) {
  return (
    <div className="surface rounded-lg p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wide text-[#71717A]">{label}</span>
        <Icon className="w-4 h-4" style={{ color: accent }} />
      </div>
      <div className="font-display font-bold text-3xl">{value}</div>
      {hint && <div className="text-xs text-[#71717A] mt-1">{hint}</div>}
    </div>
  );
}

export default function Analytics() {
  const [period, setPeriod] = useState(30);
  const [downloading, setDownloading] = useState(null);

  const { data: cust } = useQuery({ queryKey: ["cust-metrics"], queryFn: async () => (await api.get("/customers")).data });
  const { data: ts } = useQuery({ queryKey: ["ts-analytics"], queryFn: async () => (await api.get("/analytics/timeseries")).data });
  const { data: stats } = useQuery({ queryKey: ["dash-stats"], queryFn: async () => (await api.get("/dashboard/stats")).data });

  const download = async (format) => {
    setDownloading(format);
    try {
      const resp = await api.get(`/analytics/export?format=${format}&period=${period}`, { responseType: "blob" });
      const blob = new Blob([resp.data], { type: format === "csv" ? "text/csv" : "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `promoos-report-${period}d.${format}`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success(`${format.toUpperCase()} downloaded`);
    } catch (e) { toast.error(apiError(e)); } finally { setDownloading(null); }
  };

  const m = cust?.metrics || {};
  const byState = stats?.by_state || {};
  const topCoupons = (stats?.top_campaigns || []).slice(0, 6);

  return (
    <div className="fade-up max-w-[1400px]" data-testid="analytics-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <BarChart3 className="w-7 h-7 text-[#CCFF00]" /> Analytics
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Revenue, redemptions, CAC, and lifetime value — with one-click board-ready exports.</p>
        </div>
        <div className="flex items-center gap-2">
          <select data-testid="analytics-period" value={period} onChange={(e) => setPeriod(Number(e.target.value))}
                  className="h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
            {PERIODS.map((p) => <option key={p} value={p}>Last {p} days</option>)}
          </select>
          <Button data-testid="analytics-export-csv" onClick={() => download("csv")} disabled={downloading === "csv"} className="btn-ghost rounded-md gap-2">
            {downloading === "csv" ? <Loader2 className="w-4 h-4 spin" /> : <Download className="w-4 h-4" />} CSV
          </Button>
          <Button data-testid="analytics-export-pdf" onClick={() => download("pdf")} disabled={downloading === "pdf"} className="btn-primary rounded-md gap-2">
            {downloading === "pdf" ? <Loader2 className="w-4 h-4 spin" /> : <FileText className="w-4 h-4" />} PDF
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        <KPI label="Total Revenue" value={`$${Math.round(m.total_spend || 0).toLocaleString()}`} icon={DollarSign} accent="#CCFF00" hint="Net across all coupons" />
        <KPI label="Customers" value={cust?.total || 0} icon={Users} hint={`${(cust?.by_segment?.vip || 0)} VIP · ${(cust?.by_segment?.at_risk || 0)} at-risk`} />
        <KPI label="Est. CAC" value={`$${(m.cac || 0).toFixed(2)}`} icon={TrendingUp} accent="#EF4444" hint="Discount cost per new customer" />
        <KPI label="Customer LTV" value={`$${(m.clv || 0).toFixed(2)}`} icon={ShoppingCart} accent="#CCFF00" hint={`${(m.avg_orders || 0)}× avg orders`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="surface rounded-lg p-5 lg:col-span-2" style={{ minHeight: 320 }}>
          <h3 className="font-display font-bold mb-3">Revenue & redemptions · last 14 days</h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={ts?.days || []}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#CCFF00" stopOpacity={0.5} />
                  <stop offset="95%" stopColor="#CCFF00" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#27272A" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" stroke="#71717A" fontSize={10} tickLine={false} />
              <YAxis stroke="#71717A" fontSize={10} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#0A0A0A", border: "1px solid #27272A", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="revenue" stroke="#CCFF00" strokeWidth={2} fill="url(#rev)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="surface rounded-lg p-5" style={{ minHeight: 320 }}>
          <h3 className="font-display font-bold mb-3">Top coupons</h3>
          {topCoupons.length === 0 ? (
            <div className="text-xs text-[#71717A]">No data.</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={topCoupons} layout="vertical" margin={{ left: 30 }}>
                <XAxis type="number" stroke="#71717A" fontSize={10} tickLine={false} />
                <YAxis type="category" dataKey="name" stroke="#71717A" fontSize={10} tickLine={false} width={100} />
                <Tooltip contentStyle={{ background: "#0A0A0A", border: "1px solid #27272A", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="revenue" fill="#005CEE" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="surface rounded-lg p-5">
        <h3 className="font-display font-bold mb-3">Coupon state distribution</h3>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {Object.entries(byState).map(([state, n]) => (
            <div key={state} className="text-center p-3 rounded-md bg-[#0A0A0A] border border-[#27272A]" data-testid={`analytics-state-${state}`}>
              <div className="text-2xl font-bold text-[#CCFF00]">{n}</div>
              <div className="text-[10px] uppercase tracking-widest text-[#71717A] mt-1">{state}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
