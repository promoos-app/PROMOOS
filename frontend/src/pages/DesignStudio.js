import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Palette, Loader2, Check } from "lucide-react";

export default function DesignStudio() {
  const [templates, setTemplates] = useState([]);
  const [applying, setApplying] = useState(null);
  const [applied, setApplied] = useState({});

  useEffect(() => {
    api.get("/templates").then((r) => setTemplates(r.data)).catch((e) => toast.error(apiError(e)));
  }, []);

  const apply = async (id) => {
    setApplying(id);
    try {
      await api.post("/templates/apply", { template_id: id });
      setApplied((s) => ({ ...s, [id]: true }));
      toast.success("Template applied to your brand kit");
    } catch (e) { toast.error(apiError(e)); } finally { setApplying(null); }
  };

  return (
    <div className="fade-up max-w-[1400px]" data-testid="design-studio-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Palette className="w-7 h-7 text-[#CCFF00]" /> Design Studio
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Pre-built promotional aesthetics. One click applies the palette to every future coupon.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {templates.map((t) => (
          <div key={t.id} className="surface rounded-lg overflow-hidden flex flex-col" data-testid={`template-${t.id}`}>
            <div className="h-40 relative" style={{ background: t.cover }}>
              <div className="absolute inset-0 flex items-center justify-center p-6 text-center"
                   style={{ color: t.id === "minimal-mono" ? "#0A0A0A" : "#fff" }}>
                <div className="font-display font-black text-2xl leading-tight tracking-tight">
                  {t.example_headline}
                </div>
              </div>
            </div>
            <div className="p-4 flex-1">
              <div className="flex items-center justify-between mb-1">
                <div className="font-display font-bold">{t.name}</div>
                <span className="text-[10px] uppercase tracking-widest text-[#71717A]">{t.category}</span>
              </div>
              <div className="flex items-center gap-1.5 mt-2 mb-3">
                <span className="w-4 h-4 rounded" style={{ background: t.primary }} />
                <span className="w-4 h-4 rounded" style={{ background: t.secondary }} />
                <span className="text-[10px] text-[#71717A] font-mono">{t.primary} · {t.secondary}</span>
              </div>
              <Button
                data-testid={`apply-${t.id}`}
                onClick={() => apply(t.id)}
                disabled={applying === t.id}
                className={`w-full rounded-md ${applied[t.id] ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30" : "btn-primary"}`}
              >
                {applying === t.id ? <Loader2 className="w-4 h-4 spin" /> :
                 applied[t.id] ? <><Check className="w-4 h-4 mr-1" /> Applied</> :
                 "Apply to brand kit"}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
