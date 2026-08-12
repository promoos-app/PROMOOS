import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Users, Sparkles } from "lucide-react";

const SEG_COLOR = {
  vip: "#CCFF00", frequent: "#005CEE", regular: "#A1A1AA",
  new: "#FF4EC7", at_risk: "#EF4444",
};

function Chip({ seg, count, active, onClick }) {
  return (
    <button data-testid={`segment-${seg}`} onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-xs font-bold border transition ${active ? "text-[#0A0A0A]" : "text-[#A1A1AA] hover:text-white"}`}
      style={active ? { background: SEG_COLOR[seg] || "#fff", borderColor: SEG_COLOR[seg] || "#fff" } : { borderColor: "#27272A" }}>
      {seg} · {count}
    </button>
  );
}

export default function Customers() {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [promoBusy, setPromoBusy] = useState(false);
  const [promo, setPromo] = useState(null);

  const load = () => api.get("/customers").then((r) => setData(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);

  if (!data) return <div className="text-[#71717A]">Loading…</div>;

  const filtered = data.customers.filter((c) => {
    if (filter !== "all" && c.segment !== filter) return false;
    if (search && !c.customer.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const generateSegmentPromo = async (seg) => {
    setPromoBusy(true); setPromo(null);
    try {
      const { data: d } = await api.post("/ai/segment-promo", { segment: seg });
      setPromo({ segment: seg, ...d });
    } catch (e) { toast.error(apiError(e)); } finally { setPromoBusy(false); }
  };

  return (
    <div className="fade-up max-w-[1400px]" data-testid="customers-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Users className="w-7 h-7 text-[#CCFF00]" /> Customers
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">{data.total} customers · auto-segmented from redemption + loyalty behavior.</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <Chip seg="all" count={data.total} active={filter === "all"} onClick={() => setFilter("all")} />
        {Object.entries(data.by_segment).map(([seg, n]) => (
          <Chip key={seg} seg={seg} count={n} active={filter === seg} onClick={() => setFilter(seg)} />
        ))}
        <div className="flex-1 min-w-[220px]">
          <Input data-testid="customer-search" placeholder="Search customer…" value={search} onChange={(e) => setSearch(e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white" />
        </div>
      </div>

      {filter !== "all" && filter !== "" && (
        <div className="surface rounded-lg p-4 mb-4 flex items-center justify-between" data-testid="segment-promo-cta">
          <div>
            <div className="text-sm font-bold flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#CCFF00]" />
              Send a personalized promo to <span className="text-[#CCFF00]">{filter}</span> customers
            </div>
            <div className="text-xs text-[#71717A] mt-1">Claude will write copy tuned to this segment's mindset.</div>
          </div>
          <Button data-testid="segment-promo-btn" onClick={() => generateSegmentPromo(filter)} disabled={promoBusy} className="btn-primary rounded-md gap-2">
            {promoBusy ? <Loader2 className="w-4 h-4 spin" /> : <Sparkles className="w-4 h-4" />} Generate promo
          </Button>
        </div>
      )}
      {promo && (
        <div className="rounded-lg border border-[#CCFF00]/30 bg-[#CCFF00]/5 p-4 mb-4" data-testid="segment-promo-preview">
          <div className="text-[10px] uppercase tracking-widest text-[#CCFF00] font-bold mb-1">For {promo.segment}</div>
          <div className="font-display font-bold text-lg">{promo.headline}</div>
          <div className="text-sm text-[#A1A1AA] mt-1">{promo.description}</div>
          <div className="text-xs text-[#71717A] mt-2">Type · {promo.type} · {promo.discount_value}% · CTA · {promo.cta}</div>
        </div>
      )}

      <div className="surface rounded-lg overflow-hidden">
        <table className="w-full text-sm" data-testid="customers-table">
          <thead className="bg-[#0A0A0A] text-[#71717A] text-xs uppercase tracking-wider">
            <tr>
              <th className="text-left px-6 py-2">Customer</th>
              <th className="text-left px-3 py-2">Segment</th>
              <th className="text-right px-3 py-2">Orders</th>
              <th className="text-right px-3 py-2">Spend</th>
              <th className="text-right px-3 py-2">Points</th>
              <th className="text-right px-3 py-2">Credit</th>
              <th className="text-right px-6 py-2">Last seen</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 300).map((c) => (
              <tr key={c.customer} className="border-t border-[#27272A]" data-testid={`customer-row-${c.customer}`}>
                <td className="px-6 py-2 font-mono text-xs">{c.customer}</td>
                <td className="px-3 py-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded" style={{ background: (SEG_COLOR[c.segment] || "#71717A") + "22", color: SEG_COLOR[c.segment] || "#71717A" }}>{c.segment}</span>
                </td>
                <td className="px-3 py-2 text-right">{c.orders}</td>
                <td className="px-3 py-2 text-right font-bold text-[#CCFF00]">${c.spend.toFixed(0)}</td>
                <td className="px-3 py-2 text-right">{Math.round(c.loyalty_points).toLocaleString()}</td>
                <td className="px-3 py-2 text-right">${c.store_credit.toFixed(0)}</td>
                <td className="px-6 py-2 text-right text-xs text-[#71717A]">{(c.last_at || "").slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
