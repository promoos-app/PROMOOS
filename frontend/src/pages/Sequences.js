import { useEffect, useState } from "react";
import api, { apiError } from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Mailbox, Plus, Trash2, Zap, Clock } from "lucide-react";

const EMPTY = {
  name: "", trigger: "optin", lead_tag_filter: "", funnel_id: "",
  enabled: true,
  steps: [{ delay_hours: 0, subject: "Welcome — you're in.", body: "Thanks for signing up. Here's your first email..." }],
};

function SequenceForm({ open, onOpenChange, initial, onSubmit }) {
  const [f, setF] = useState(initial || EMPTY);
  useEffect(() => { setF(initial || EMPTY); }, [initial, open]);
  const updateStep = (i, patch) => setF((x) => ({ ...x, steps: x.steps.map((s, k) => k === i ? { ...s, ...patch } : s) }));
  const addStep = () => setF((x) => ({ ...x, steps: [...x.steps, { delay_hours: 24, subject: "Day-1 follow-up", body: "..." }] }));
  const removeStep = (i) => setF((x) => ({ ...x, steps: x.steps.filter((_, k) => k !== i) }));
  const submit = async () => {
    if (!f.name.trim()) { toast.error("Give this sequence a name"); return; }
    if (!f.steps.length) { toast.error("Add at least one email step"); return; }
    await onSubmit(f);
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#141414] border-[#27272A] text-white max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="sequence-form-dialog">
        <DialogHeader><DialogTitle>{initial?.id ? "Edit sequence" : "New sequence"}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Name</Label>
              <Input value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}
                data-testid="sequence-name-input"
                className="mt-1 bg-[#0A0A0A] border-[#27272A]" placeholder="Welcome — lead-magnet series" />
            </div>
            <div>
              <Label className="text-xs text-[#A1A1AA]">Trigger</Label>
              <select value={f.trigger} onChange={(e) => setF({ ...f, trigger: e.target.value })}
                data-testid="sequence-trigger-select"
                className="mt-1 w-full h-10 rounded-md bg-[#0A0A0A] border border-[#27272A] text-white px-3 text-sm">
                <option value="optin">Opt-in form submitted</option>
                <option value="funnel_view">Funnel viewed</option>
                <option value="coupon_redeem">Coupon redeemed</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-[#A1A1AA]">Lead tag filter (optional)</Label>
              <Input value={f.lead_tag_filter || ""} onChange={(e) => setF({ ...f, lead_tag_filter: e.target.value })}
                data-testid="sequence-tag-filter"
                placeholder="leadmagnet / webinar / newsletter" className="mt-1 bg-[#0A0A0A] border-[#27272A]" />
            </div>
            <div className="flex items-end justify-between">
              <div>
                <Label className="text-xs text-[#A1A1AA] block">Enabled</Label>
                <div className="text-[10px] text-[#71717A] mt-1">Off = sequence stays dormant.</div>
              </div>
              <Switch checked={!!f.enabled} onCheckedChange={(v) => setF({ ...f, enabled: v })}
                data-testid="sequence-enabled-switch" />
            </div>
          </div>

          <div className="border-t border-[#27272A] pt-3">
            <div className="flex items-center justify-between mb-3">
              <Label className="text-xs text-[#A1A1AA] uppercase tracking-widest">Emails ({f.steps.length})</Label>
              <button onClick={addStep} data-testid="sequence-add-step"
                className="btn-ghost rounded-md text-[11px] px-2 py-1 flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add step
              </button>
            </div>
            <div className="space-y-3">
              {f.steps.map((s, i) => (
                <div key={i} className="rounded-md p-3 bg-[#0A0A0A] border border-[#27272A]" data-testid={`sequence-step-${i}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-[10px] uppercase tracking-widest text-[#CCFF00] flex items-center gap-1.5">
                      <Clock className="w-3 h-3" /> Step {i + 1}
                    </div>
                    <button onClick={() => removeStep(i)} className="text-red-400 hover:bg-red-500/10 rounded p-1"
                      data-testid={`sequence-step-remove-${i}`}>
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <Label className="text-[10px] text-[#71717A]">Delay (hours)</Label>
                      <Input type="number" min="0" max="720" value={s.delay_hours}
                        onChange={(e) => updateStep(i, { delay_hours: Number(e.target.value) || 0 })}
                        data-testid={`sequence-step-delay-${i}`}
                        className="mt-1 bg-[#141414] border-[#27272A] h-8 text-xs" />
                    </div>
                    <div className="col-span-2">
                      <Label className="text-[10px] text-[#71717A]">Subject</Label>
                      <Input value={s.subject} onChange={(e) => updateStep(i, { subject: e.target.value })}
                        data-testid={`sequence-step-subject-${i}`}
                        className="mt-1 bg-[#141414] border-[#27272A] h-8 text-xs" />
                    </div>
                  </div>
                  <div className="mt-2">
                    <Label className="text-[10px] text-[#71717A]">Body (HTML or plain text)</Label>
                    <Textarea rows={3} value={s.body}
                      onChange={(e) => updateStep(i, { body: e.target.value })}
                      data-testid={`sequence-step-body-${i}`}
                      className="mt-1 bg-[#141414] border-[#27272A] text-xs" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button data-testid="sequence-save-btn" className="btn-primary" onClick={submit}>Save sequence</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Sequences() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const load = async () => {
    try { const { data } = await api.get("/sequences"); setItems(data); }
    catch (e) { toast.error(apiError(e)); }
  };
  useEffect(() => { load(); }, []);
  const save = async (f) => {
    try {
      if (editing?.id) await api.put(`/sequences/${editing.id}`, f);
      else await api.post("/sequences", f);
      toast.success("Saved"); setOpen(false); setEditing(null); load();
    } catch (e) { toast.error(apiError(e)); }
  };
  const del = async (s) => {
    if (!window.confirm(`Delete "${s.name}"?`)) return;
    try { await api.delete(`/sequences/${s.id}`); toast.success("Deleted"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };
  return (
    <div className="space-y-6" data-testid="sequences-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-tight flex items-center gap-3">
            <Zap className="w-7 h-7 text-[#CCFF00]" /> Automations
          </h1>
          <p className="text-sm text-[#A1A1AA] mt-1">
            Send automated emails when a lead opts in, views a funnel, or redeems a coupon.
          </p>
        </div>
        <Button data-testid="sequences-new-btn" className="btn-primary gap-2 rounded-md"
          onClick={() => { setEditing(null); setOpen(true); }}>
          <Plus className="w-4 h-4" /> New sequence
        </Button>
      </div>
      {items.length === 0 ? (
        <div className="text-center py-16 rounded-lg border border-dashed border-[#27272A]">
          <Mailbox className="w-10 h-10 mx-auto text-[#3F3F46] mb-3" />
          <div className="font-bold">No sequences yet</div>
          <div className="text-sm text-[#71717A] mt-1">Wire your opt-in forms to email sequences so leads convert without manual work.</div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {items.map((s) => (
            <div key={s.id} className="rounded-lg p-4 bg-[#141414] border border-[#27272A]"
                 data-testid={`sequence-card-${s.id}`}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-bold">{s.name}</div>
                  <div className="text-[10px] text-[#71717A] mt-1">
                    Trigger: <span className="text-white">{s.trigger}</span>{s.lead_tag_filter ? <> · Tag: <code className="text-[#CCFF00]">{s.lead_tag_filter}</code></> : null}
                  </div>
                </div>
                <span className={`text-[10px] uppercase tracking-widest font-bold px-2 py-1 rounded ${s.enabled ? "bg-[#CCFF00]/10 text-[#CCFF00]" : "bg-[#27272A] text-[#71717A]"}`}>
                  {s.enabled ? "Live" : "Paused"}
                </span>
              </div>
              <div className="mt-3 flex items-center justify-between text-xs">
                <div className="text-[#A1A1AA]">
                  <span className="font-bold text-white">{s.steps?.length || 0}</span> emails · <span className="font-bold text-white">{s.stats?.enrolled || 0}</span> enrolled
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => { setEditing(s); setOpen(true); }}
                    className="text-xs text-[#A1A1AA] hover:text-white px-2 py-1">Edit</button>
                  <button data-testid={`sequence-delete-${s.id}`} onClick={() => del(s)}
                    className="text-xs text-red-400 hover:text-red-300 p-1"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <SequenceForm open={open} onOpenChange={(v) => { setOpen(v); if (!v) setEditing(null); }}
        initial={editing} onSubmit={save} />
    </div>
  );
}
