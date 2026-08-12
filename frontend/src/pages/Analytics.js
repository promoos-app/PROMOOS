import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import {
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import { STATE_STYLES } from "@/lib/couponUtils";

const COLORS = ["#005CEE", "#CCFF00", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

export default function Analytics() {
  const { data: series = [] } = useQuery({ queryKey: ["ts"], queryFn: async () => (await api.get("/analytics/timeseries")).data });
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: async () => (await api.get("/dashboard/stats")).data });

  const byState = Object.entries(stats?.by_state || {}).map(([k, v]) => ({ name: k, value: v }));

  return (
    <div className="fade-up max-w-[1400px]">
      <div className="mb-6">
        <h1 className="font-display font-bold text-3xl tracking-tight">Analytics</h1>
        <p className="text-sm text-[#A1A1AA] mt-1">Performance across all your promotions.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="surface rounded-lg p-6 lg:col-span-2">
          <h3 className="font-display font-bold text-lg mb-6">Redemptions over time</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={series}>
                <defs>
                  <linearGradient id="r2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#CCFF00" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#CCFF00" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E1E1E" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#71717A", fontSize: 11 }} tickFormatter={(d) => d?.slice(5)} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#71717A", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#141414", border: "1px solid #27272A", borderRadius: 8, color: "#fff" }} />
                <Area type="monotone" dataKey="redemptions" stroke="#CCFF00" strokeWidth={2} fill="url(#r2)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="surface rounded-lg p-6">
          <h3 className="font-display font-bold text-lg mb-6">Coupons by state</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={byState} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={3}>
                  {byState.map((e, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#141414", border: "1px solid #27272A", borderRadius: 8, color: "#fff" }} />
                <Legend wrapperStyle={{ fontSize: 12, color: "#A1A1AA", textTransform: "capitalize" }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="surface rounded-lg p-6 lg:col-span-3">
          <h3 className="font-display font-bold text-lg mb-6">Revenue by top campaign</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.top_campaigns || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E1E1E" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: "#71717A", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "#71717A", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ fill: "#1E1E1E" }} contentStyle={{ background: "#141414", border: "1px solid #27272A", borderRadius: 8, color: "#fff" }} />
                <Bar dataKey="revenue" fill="#005CEE" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
