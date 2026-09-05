import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Loader2, Plus, Megaphone, Trash2, Mail, Timer, Ticket, MessageSquare, UserPlus, Activity, Sparkles } from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter,
} from "@/components/ui/dialog";

const TRIGGERS = [
  { v: "signup", label: "Customer signs up" },
  { v: "purchase", label: "First purchase" },
  { v: "inactive_30d", label: "Inactive 30 days" },
  { v: "birthday", label: "Customer birthday" },
];

const STEP_TYPES = [
  { v: "send_email", label: "Send email", icon: Mail },
  { v: "send_sms", label: "Send SMS", icon: MessageSquare },
  { v: "send_coupon", label: "Give a coupon", icon: Ticket },
  { v: "wait", label: "Wait", icon: Timer },
];

function StepChip({ step, i, onRemove }) {
  const cfg = STEP_TYPES.find((s) => s.v === step.type) || STEP_TYPES[0];
  const Icon = cfg.icon;
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-[#0A0A0A] border border-[#27272A] text-sm" data-testid={`step-${i}`}>
      <Icon className="w-4 h-4 text-[#CCFF00]" />
      <span className="font-medium">{cfg.label}</span>
      {step.type === "wait" && <span className="text-xs text-[#71717A]">· {step.hours}h</span>}
      {step.type === "send_email" && step.subject && <span className="text-xs text-[#71717A]">· "{step.subject.slice(0, 30)}"</span>}
      {step.type === "send_coupon" && <span className="text-xs text-[#71717A]">· {step.discount}% off</span>}
      <button onClick={() => onRemove(i)} className="ml-auto text-[#71717A] hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
    </div>
  );
}

function NewJourneyDialog({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("Welcome flow");
  const [trigger, setTrigger] = useState("signup");
  const [enabled, setEnabled] = useState(true);
  const [steps, setSteps] = useState([{ type: "send_email", subject: "Welcome to our world" }]);
  const [busy, setBusy] = useState(false);

  const addStep = (v) => {
    const defaults = {
      send_email: { type: "send_email", subject: "Hi there" },
      send_sms: { type: "send_sms", body: "Thanks for joining" },
      send_coupon: { type: "send_coupon", discount: 15 },
      wait: { type: "wait", hours: 48 },
    };
    setSteps((s) => [...s, defaults[v]]);
  };

  const create = async () => {
    setBusy(true);
    try {
      await api.post("/journeys", { name, trigger, steps, enabled });
      toast.success("Journey created");
      setOpen(false); setSteps([{ type: "send_email", subject: "Welcome" }]);
      onCreated?.();
    } catch (e) { toast.error(apiError(e)); } finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button data-testid="journey-new-btn" className="btn-primary rounded-md gap-2">
          <Plus className="w-4 h-4" /> New journey
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-lg">
        <DialogHeader><DialogTitle>New journey</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div><Label className="text-xs text-[#A1A1AA]">Name</Label>
            <Input data-testid="journey-name" value={name} onChange={(e) => setName(e.target.value)} className="mt-1 bg-[#0A0A0A] border-[#27272A]" /></div>
          <div><Label className="text-xs text-[#A1A1AA]">Trigger</Label>
            <select data-testid="journey-trigger" value={trigger} onChange={(e) => setTrigger(e.target.value)} className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] px-3 text-sm">
              {TRIGGERS.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
            </select></div>
          <div className="flex items-center justify-between p-3 rounded-md bg-[#0A0A0A] border border-[#27272A]">
            <div className="text-sm">Enabled</div>
            <Switch data-testid="journey-enabled" checked={enabled} onCheckedChange={setEnabled} />
          </div>
          <div>
            <Label className="text-xs text-[#A1A1AA] mb-2 block">Steps</Label>
            <div className="space-y-1">{steps.map((s, i) => <StepChip key={i} step={s} i={i} onRemove={(idx) => setSteps((old) => old.filter((_, j) => j !== idx))} />)}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {STEP_TYPES.map((t) => (
                <button key={t.v} onClick={() => addStep(t.v)} data-testid={`journey-add-${t.v}`}
                        className="text-xs text-[#A1A1AA] px-2 py-1 rounded border border-[#27272A] hover:border-[#CCFF00]/40">+ {t.label}</button>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button data-testid="journey-create-submit" onClick={create} disabled={busy} className="btn-primary rounded-md gap-2">
            {busy && <Loader2 className="w-4 h-4 spin" />} Create
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Campaigns() {
  const [rows, setRows] = useState([]);
  const [runs, setRuns] = useState({});
  const [enrolling, setEnrolling] = useState(null);
  const [enrollFor, setEnrollFor] = useState({ customer: "", email: "" });
  const [templates, setTemplates] = useState([]);
  const [applyingTpl, setApplyingTpl] = useState(null);

  const load = () => api.get("/journeys").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); api.get("/journey-templates").then((r) => setTemplates(r.data.templates || [])).catch(() => {}); }, []);

  const applyTemplate = async (tid) => {
    setApplyingTpl(tid);
    try {
      await api.post(`/journey-templates/${tid}/apply`);
      toast.success("Template installed and enabled");
      load();
    } catch (e) { toast.error(apiError(e)); } finally { setApplyingTpl(null); }
  };

  // Auto-refresh runs feed every 8s while an enroll panel is open
  useEffect(() => {
    if (!enrolling) return;
    const id = setInterval(() => loadRuns(enrolling), 8000);
    return () => clearInterval(id);
    // eslint-disable-next-line
  }, [enrolling]);

  const loadRuns = async (jid) => {
    const { data } = await api.get(`/journeys/${jid}/runs`);
    setRuns((s) => ({ ...s, [jid]: data }));
  };

  const del = async (id) => {
    if (!window.confirm("Delete this journey?")) return;
    await api.delete(`/journeys/${id}`);
    toast.success("Deleted"); load();
  };

  const toggle = async (j, v) => {
    await api.put(`/journeys/${j.id}`, { ...j, enabled: v });
    load();
  };

  const enroll = async (jid) => {
    if (!enrollFor.customer.trim()) { toast.error("Customer id/email required"); return; }
    try {
      const { data } = await api.post(`/journeys/${jid}/enroll`, {
        customer: enrollFor.customer.trim(),
        email: enrollFor.email || (enrollFor.customer.includes("@") ? enrollFor.customer : null),
      });
      if (data.skipped) toast.info(`Skipped: ${data.reason}`);
      else toast.success("Customer enrolled");
      setEnrolling(null); setEnrollFor({ customer: "", email: "" });
      loadRuns(jid);
    } catch (e) { toast.error(apiError(e)); }
  };

  return (
    <div className="fade-up max-w-[1200px]" data-testid="campaigns-page">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-2">
            <Megaphone className="w-7 h-7 text-[#CCFF00]" /> Campaigns & Journeys
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">Automation flows that fire on customer events — signup, purchase, birthday, inactivity.</p>
        </div>
        <NewJourneyDialog onCreated={load} />
      </div>

      {templates.length > 0 && (
        <div className="surface rounded-lg p-4 mb-6" data-testid="journey-templates-strip">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-[#CCFF00]" />
            <div className="text-xs uppercase tracking-widest text-[#71717A]">Ready-to-run templates</div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {templates.map((t) => (
              <div key={t.id} className="rounded-md p-4 bg-[#0A0A0A] border border-[#27272A] hover:border-[#CCFF00] transition-colors" data-testid={`journey-template-${t.id}`}>
                <div className="font-display font-bold text-sm mb-1">{t.name}</div>
                <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-2">Trigger · {t.trigger.replace("_", " ")}</div>
                <div className="text-xs text-[#A1A1AA] mb-3">{t.description}</div>
                <div className="text-[10px] text-[#71717A] mb-3">{(t.steps || []).length} step{(t.steps || []).length === 1 ? "" : "s"}</div>
                <Button
                  data-testid={`journey-template-apply-${t.id}`}
                  onClick={() => applyTemplate(t.id)}
                  disabled={applyingTpl === t.id}
                  className="btn-primary rounded-md gap-1 h-8 text-xs w-full"
                >
                  {applyingTpl === t.id && <Loader2 className="w-3 h-3 spin" />} Install
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
      {rows.length === 0 ? (
        <div className="surface rounded-lg p-12 text-center">
          <Megaphone className="w-8 h-8 text-[#CCFF00] mx-auto mb-3" />
          <div className="font-display font-bold text-lg mb-1">No journeys yet</div>
          <p className="text-sm text-[#A1A1AA]">Create a welcome flow, a birthday surprise, or a win-back sequence.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {rows.map((j) => (
            <div key={j.id} className="surface rounded-lg p-5" data-testid={`journey-card-${j.id}`}>
              <div className="flex items-center justify-between mb-2">
                <div className="font-display font-bold text-lg">{j.name}</div>
                <Switch checked={j.enabled} onCheckedChange={(v) => toggle(j, v)} />
              </div>
              <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-3">Trigger · {j.trigger.replace("_", " ")}</div>
              <div className="space-y-1 mb-3">
                {(j.steps || []).map((s, i) => <StepChip key={i} step={s} i={i} onRemove={() => {}} />)}
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div><div className="text-[10px] text-[#71717A]">Entered</div><div className="text-sm font-bold">{j.stats?.entered || 0}</div></div>
                <div><div className="text-[10px] text-[#71717A]">Completed</div><div className="text-sm font-bold">{j.stats?.completed || 0}</div></div>
                <div><div className="text-[10px] text-[#71717A]">Conversions</div><div className="text-sm font-bold text-[#CCFF00]">{j.stats?.conversions || 0}</div></div>
              </div>
              <div className="mt-3 flex justify-between items-center">
                <button data-testid={`journey-enroll-btn-${j.id}`} onClick={() => { setEnrolling(j.id); loadRuns(j.id); }} className="text-xs text-[#CCFF00] hover:underline flex items-center gap-1">
                  <UserPlus className="w-3 h-3" /> Enroll · view runs
                </button>
                <button onClick={() => del(j.id)} className="text-xs text-[#71717A] hover:text-red-400 flex items-center gap-1">
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              </div>
              {enrolling === j.id && (
                <div className="mt-3 p-3 rounded-md bg-[#0A0A0A] border border-[#27272A]" data-testid={`journey-enroll-panel-${j.id}`}>
                  <div className="text-xs font-bold mb-2 flex items-center gap-1"><UserPlus className="w-3 h-3 text-[#CCFF00]" /> Enroll a customer</div>
                  <div className="flex gap-2">
                    <Input data-testid={`journey-enroll-customer-${j.id}`} placeholder="customer@example.com" value={enrollFor.customer} onChange={(e) => setEnrollFor({ ...enrollFor, customer: e.target.value })} className="bg-[#141416] border-[#27272A] text-white h-8 text-xs" />
                    <Button data-testid={`journey-enroll-submit-${j.id}`} onClick={() => enroll(j.id)} className="btn-primary rounded-md text-xs h-8">Enroll</Button>
                  </div>
                  {runs[j.id]?.length > 0 && (
                    <div className="mt-3">
                      <div className="text-[10px] uppercase tracking-widest text-[#71717A] mb-1 flex items-center gap-1"><Activity className="w-3 h-3" /> Recent runs</div>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {runs[j.id].slice(0, 6).map((r) => (
                          <div key={r.id} className="text-[11px] flex items-center justify-between font-mono">
                            <span className="text-[#A1A1AA]">{r.customer}</span>
                            <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-bold ${
                              r.status === "completed" ? "bg-emerald-500/15 text-emerald-400" :
                              r.status === "cancelled" ? "bg-red-500/15 text-red-400" :
                              "bg-[#005CEE]/15 text-[#005CEE]"}`}>{r.status}</span>
                            <span className="text-[#71717A]">step {r.current_step}/{(j.steps || []).length}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
