import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Ticket, Search, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const CAT_COLOR = {
  Discount: "#005CEE", Bundle: "#F59E0B", Perk: "#10B981", Acquisition: "#EC4899",
  Retention: "#8B5CF6", Growth: "#CCFF00", Lifecycle: "#06B6D4", Loyalty: "#EAB308",
  Urgency: "#EF4444", Geo: "#14B8A6", Campaign: "#F97316", Recurring: "#0EA5E9",
  Attribution: "#A78BFA",
};

export default function CouponLibrary() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [cat, setCat] = useState("all");
  const [q, setQ] = useState("");

  useEffect(() => {
    api.get("/library/coupon-types").then((r) => setItems(r.data)).catch((e) => toast.error(apiError(e)));
  }, []);

  const cats = ["all", ...Array.from(new Set(items.map((x) => x.cat)))];
  const filtered = items.filter((x) =>
    (cat === "all" || x.cat === cat) &&
    (!q || (x.name.toLowerCase() + " " + x.desc.toLowerCase()).includes(q.toLowerCase()))
  );

  const use = (item) => {
    // Navigate to the new-coupon editor with preset params
    navigate(`/coupons/new?type=${encodeURIComponent(item.id)}&value=${item.default_value}&audience=${item.audience}`);
  };

  return (
    <div className="fade-up max-w-[1400px]" data-testid="coupon-library-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Ticket className="w-7 h-7 text-[#CCFF00]" /> Coupon Library
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">All 23 promotional styles — click any card to spin up a preconfigured coupon in seconds.</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {cats.map((c) => (
          <button key={c} data-testid={`lib-cat-${c}`} onClick={() => setCat(c)}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold border transition ${cat === c ? "text-[#0A0A0A]" : "text-[#A1A1AA] hover:text-white"}`}
                  style={cat === c ? { background: CAT_COLOR[c] || "#fff", borderColor: CAT_COLOR[c] || "#fff" } : { borderColor: "#27272A" }}>
            {c === "all" ? "All" : c}
          </button>
        ))}
        <div className="flex-1 min-w-[220px] relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#71717A]" />
          <Input data-testid="lib-search" placeholder="Search library…" value={q} onChange={(e) => setQ(e.target.value)} className="bg-[#0A0A0A] border-[#27272A] text-white pl-10" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {filtered.map((x) => (
          <div key={x.id} className="surface rounded-lg p-5 flex flex-col hover:-translate-y-0.5 transition-transform" data-testid={`lib-card-${x.id}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] uppercase tracking-widest font-bold px-2 py-0.5 rounded" style={{ background: (CAT_COLOR[x.cat] || "#71717A") + "22", color: CAT_COLOR[x.cat] || "#71717A" }}>{x.cat}</span>
              {x.default_value > 0 && <span className="text-lg font-bold text-[#CCFF00]">{x.default_value}%</span>}
            </div>
            <h3 className="font-display font-bold leading-tight text-lg mb-1">{x.name}</h3>
            <p className="text-xs text-[#A1A1AA] mb-3 flex-1">{x.desc}</p>
            <div className="text-[10px] text-[#71717A] uppercase tracking-wider mb-3">Audience · {x.audience}</div>
            <Button data-testid={`lib-use-${x.id}`} onClick={() => use(x)} className="btn-primary rounded-md gap-2 w-full">
              <Sparkles className="w-3.5 h-3.5" /> Use this style
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
