import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Loader2, Sparkles, Zap, Calendar as CalendarIcon, CheckCircle2 } from "lucide-react";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function Calendar() {
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState([]);
  const [approving, setApproving] = useState({});
  const [approved, setApproved] = useState({});

  const { data: config } = useQuery({
    queryKey: ["autopilot-config"],
    queryFn: async () => (await api.get("/autopilot/config")).data,
  });

  const generate = async () => {
    setBusy(true); setApproved({});
    try {
      const { data } = await api.post("/ai/weekly-calendar");
      setPlan(data.days || []);
      toast.success("Weekly plan generated");
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  const approve = async (idx) => {
    const day = plan[idx];
    setApproving((s) => ({ ...s, [idx]: true }));
    try {
      const pkg = {
        coupon: {
          type: day.type, discount_value: day.discount_value,
          name: day.name || `${day.day} promo`, headline: day.headline,
          description: day.headline, cta: day.cta || "Claim Offer",
          audience: day.audience || "all",
        },
      };
      await api.post("/ai/one-click-campaign/approve", { package: pkg, activate: false });
      setApproved((s) => ({ ...s, [idx]: true }));
      toast.success(`${day.day} approved as draft coupon`);
    } catch (e) { toast.error(apiError(e)); } finally {
      setApproving((s) => ({ ...s, [idx]: false }));
    }
  };

  const approveAll = async () => {
    for (let i = 0; i < plan.length; i++) if (!approved[i]) await approve(i);
    toast.success("All 7 days added to your coupon library");
  };

  return (
    <div className="fade-up max-w-[1400px]" data-testid="calendar-page">
      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <CalendarIcon className="w-7 h-7 text-[#CCFF00]" /> Weekly Promo Calendar
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Let the AI plan a distinct promotion for every day of the week — approve individually or all at once.</p>
          {config && (
            <div className="text-xs text-[#71717A] mt-2">
              Cap {config.max_discount}% · Voice "{config.brand_voice}" · Goal {config.goal.replace("_", " ")}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <Button data-testid="calendar-generate-btn" onClick={generate} disabled={busy} className="btn-primary rounded-md gap-2">
            {busy ? <Loader2 className="w-4 h-4 spin" /> : <Sparkles className="w-4 h-4" />} Generate plan
          </Button>
          {plan.length > 0 && (
            <Button data-testid="calendar-approve-all-btn" onClick={approveAll} className="btn-ghost rounded-md gap-2">
              <Zap className="w-4 h-4" /> Approve all
            </Button>
          )}
        </div>
      </div>

      {plan.length === 0 ? (
        <div className="surface rounded-lg p-12 text-center">
          <Sparkles className="w-8 h-8 text-[#CCFF00] mx-auto mb-3" />
          <div className="font-display font-bold text-lg mb-1">No plan yet</div>
          <p className="text-sm text-[#A1A1AA] max-w-md mx-auto">Hit "Generate plan" and Claude will produce a 7-day rotation tuned to your top-performing days and your goal.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {plan.map((d, i) => (
            <div key={i} data-testid={`calendar-day-${d.day || DAYS[i]}`}
                 className="surface rounded-lg p-4 flex flex-col min-h-[220px] transition-transform hover:-translate-y-0.5">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] uppercase tracking-widest font-bold text-[#71717A]">{d.day || DAYS[i]}</span>
                <span className="text-xs font-bold px-1.5 py-0.5 rounded bg-[#CCFF00]/15 text-[#CCFF00]">{d.discount_value}%</span>
              </div>
              <div className="font-display font-bold text-base leading-tight mb-1">{d.headline}</div>
              <div className="text-xs text-[#A1A1AA] mb-3 flex-1">{(d.name || "").slice(0, 60)}</div>
              <div className="text-[10px] text-[#71717A] mb-3">
                <span className="uppercase tracking-wider">Type</span> · {d.type} · <span className="uppercase tracking-wider">Aud</span> · {d.audience}
              </div>
              <Button
                data-testid={`calendar-approve-${d.day || DAYS[i]}`}
                onClick={() => approve(i)}
                disabled={approving[i] || approved[i]}
                className={`rounded-md text-xs h-8 ${approved[i] ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" : "btn-primary"}`}
              >
                {approving[i] ? <Loader2 className="w-3.5 h-3.5 spin" /> :
                 approved[i] ? <><CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Added</> : "Approve"}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
